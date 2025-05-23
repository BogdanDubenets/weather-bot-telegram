import sqlite3
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class DatabaseService:
    """Сервіс для роботи з базою даних"""
    
    def __init__(self, db_path='weather_bot.db'):
        self.db_path = db_path
    
    def get_connection(self):
        """Отримання з'єднання з базою даних"""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def init_database(self):
        """Ініціалізація бази даних"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Таблиця користувачів
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT,
                    registration_date TEXT,
                    last_activity TEXT,
                    last_location_lat REAL,
                    last_location_lon REAL,
                    last_location_name TEXT,
                    total_orders INTEGER DEFAULT 0,
                    total_stars_spent INTEGER DEFAULT 0
                )
            ''')
            
            # Таблиця платежів
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    stars_amount INTEGER,
                    payload TEXT,
                    payment_date TEXT,
                    telegram_payment_id TEXT,
                    status TEXT DEFAULT 'completed',
                    weather_delivered BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблиця статистики використання
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    details TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблиця помилок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    error_type TEXT,
                    error_message TEXT,
                    stack_trace TEXT,
                    timestamp TEXT
                )
            ''')
            
            # Індекси для оптимізації
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_stats_user_id ON usage_stats(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_stats_timestamp ON usage_stats(timestamp)')
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
            return False
    
    def save_user(self, user_data):
        """Збереження або оновлення користувача"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Перевірка чи існує користувач
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_data['id'],))
            exists = cursor.fetchone()
            
            current_time = datetime.now().isoformat()
            
            if exists:
                # Оновлення існуючого користувача
                cursor.execute('''
                    UPDATE users 
                    SET username = ?, first_name = ?, last_name = ?, 
                        language_code = ?, last_activity = ?
                    WHERE user_id = ?
                ''', (
                    user_data.get('username'),
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('language_code'),
                    current_time,
                    user_data['id']
                ))
            else:
                # Створення нового користувача
                cursor.execute('''
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, language_code, 
                     registration_date, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_data['id'],
                    user_data.get('username'),
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('language_code'),
                    current_time,
                    current_time
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ User saved: {user_data.get('username', user_data['id'])}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Save user error: {e}")
            return False
    
    def save_payment(self, user_id, stars_amount, payload, telegram_payment_id):
        """Збереження інформації про платіж"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Збереження платежу
            cursor.execute('''
                INSERT INTO payments 
                (user_id, stars_amount, payload, payment_date, telegram_payment_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                stars_amount,
                payload,
                datetime.now().isoformat(),
                telegram_payment_id
            ))
            
            # Оновлення статистики користувача
            cursor.execute('''
                UPDATE users 
                SET total_orders = total_orders + 1,
                    total_stars_spent = total_stars_spent + ?
                WHERE user_id = ?
            ''', (stars_amount, user_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Payment saved: {stars_amount} stars for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Save payment error: {e}")
            return False
    
    def get_last_payment(self, user_id):
        """Отримання останнього платежу користувача"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT stars_amount FROM payments 
                WHERE user_id = ? 
                ORDER BY payment_date DESC 
                LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            stars = result[0] if result else None
            logger.info(f"📊 Last payment for user {user_id}: {stars} stars")
            return stars
            
        except Exception as e:
            logger.error(f"❌ Get last payment error: {e}")
            return None
    
    def update_location(self, user_id, lat, lon, location_name=None):
        """Оновлення останньої локації користувача"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET last_location_lat = ?, last_location_lon = ?, 
                    last_location_name = ?, last_activity = ?
                WHERE user_id = ?
            ''', (lat, lon, location_name, datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Location updated for user {user_id}: {lat}, {lon}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Update location error: {e}")
            return False
    
    def mark_weather_delivered(self, payment_id):
        """Позначити, що прогноз погоди доставлено"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE payments 
                SET weather_delivered = TRUE 
                WHERE id = ?
            ''', (payment_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Weather marked as delivered for payment {payment_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Mark weather delivered error: {e}")
            return False
    
    def log_user_action(self, user_id, action, details=None):
        """Логування дій користувача"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO usage_stats (user_id, action, details, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (user_id, action, json.dumps(details) if details else None, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Log user action error: {e}")
            return False
    
    def log_error(self, user_id, error_type, error_message, stack_trace=None):
        """Логування помилок"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO error_logs (user_id, error_type, error_message, stack_trace, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, error_type, error_message, stack_trace, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Log error failed: {e}")
            return False
    
    def get_user_stats(self, user_id):
        """Статистика користувача"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, first_name, registration_date, last_activity,
                       total_orders, total_stars_spent
                FROM users 
                WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            
            if user_data:
                cursor.execute('''
                    SELECT COUNT(*) as total_payments,
                           AVG(stars_amount) as avg_stars,
                           MAX(payment_date) as last_payment
                    FROM payments 
                    WHERE user_id = ?
                ''', (user_id,))
                
                payment_stats = cursor.fetchone()
                
                conn.close()
                
                return {
                    'username': user_data[0],
                    'first_name': user_data[1],
                    'registration_date': user_data[2],
                    'last_activity': user_data[3],
                    'total_orders': user_data[4],
                    'total_stars_spent': user_data[5],
                    'total_payments': payment_stats[0] if payment_stats else 0,
                    'avg_stars_per_order': round(payment_stats[1], 2) if payment_stats[1] else 0,
                    'last_payment_date': payment_stats[2] if payment_stats else None
                }
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"❌ Get user stats error: {e}")
            return None
    
    def get_bot_stats(self):
        """Загальна статистика бота"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Загальна кількість користувачів
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            # Активні користувачі за останні 30 днів
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            cursor.execute('SELECT COUNT(*) FROM users WHERE last_activity > ?', (thirty_days_ago,))
            active_users = cursor.fetchone()[0]
            
            # Статистика платежів
            cursor.execute('''
                SELECT COUNT(*) as total_payments,
                       SUM(stars_amount) as total_stars,
                       AVG(stars_amount) as avg_payment
                FROM payments
            ''')
            payment_stats = cursor.fetchone()
            
            # Найпопулярніший тариф
            cursor.execute('''
                SELECT stars_amount, COUNT(*) as count
                FROM payments 
                GROUP BY stars_amount 
                ORDER BY count DESC 
                LIMIT 1
            ''')
            popular_plan = cursor.fetchone()
            
            # Доходи за сьогодні
            today = datetime.now().date().isoformat()
            cursor.execute('''
                SELECT SUM(stars_amount) 
                FROM payments 
                WHERE date(payment_date) = ?
            ''', (today,))
            today_revenue = cursor.fetchone()[0] or 0
            
            # Доходи за останні 7 днів
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute('''
                SELECT SUM(stars_amount) 
                FROM payments 
                WHERE payment_date > ?
            ''', (week_ago,))
            week_revenue = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_users': total_users,
                'active_users_30d': active_users,
                'total_payments': payment_stats[0] or 0,
                'total_stars': payment_stats[1] or 0,
                'avg_payment': round(payment_stats[2], 2) if payment_stats[2] else 0,
                'most_popular_plan': f"{popular_plan[0]} stars" if popular_plan else "N/A",
                'revenue_today': today_revenue,
                'revenue_week': week_revenue,
                'conversion_rate': round((payment_stats[0] / total_users * 100), 2) if total_users > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Get bot stats error: {e}")
            return None
    
    def get_payment_stats(self):
        """Детальна статистика платежів"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Загальна статистика
            cursor.execute('''
                SELECT COUNT(*) as total_payments,
                       SUM(stars_amount) as total_stars,
                       AVG(stars_amount) as avg_payment
                FROM payments
            ''')
            general_stats = cursor.fetchone()
            
            # Розподіл по тарифах
            cursor.execute('''
                SELECT stars_amount, COUNT(*) as count, 
                       SUM(stars_amount) as total_stars
                FROM payments 
                GROUP BY stars_amount 
                ORDER BY stars_amount
            ''')
            plan_distribution = cursor.fetchall()
            
            # Найпопулярніший тариф
            cursor.execute('''
                SELECT stars_amount, COUNT(*) as count
                FROM payments 
                GROUP BY stars_amount 
                ORDER BY count DESC 
                LIMIT 1
            ''')
            most_popular = cursor.fetchone()
            
            # Доходи за сьогодні
            today = datetime.now().date().isoformat()
            cursor.execute('''
                SELECT SUM(stars_amount) 
                FROM payments 
                WHERE date(payment_date) = ?
            ''', (today,))
            revenue_today = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_payments': general_stats[0] or 0,
                'total_stars': general_stats[1] or 0,
                'avg_payment': round(general_stats[2], 2) if general_stats[2] else 0,
                'plan_distribution': [
                    {'stars': row[0], 'count': row[1], 'total_stars': row[2]} 
                    for row in plan_distribution
                ],
                'most_popular_plan': most_popular[0] if most_popular else None,
                'revenue_today': revenue_today
            }
            
        except Exception as e:
            logger.error(f"❌ Get payment stats error: {e}")
            return None
    
    def cleanup_old_data(self, days_to_keep=90):
        """Очищення старих даних"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            # Очищення старих логів використання
            cursor.execute('DELETE FROM usage_stats WHERE timestamp < ?', (cutoff_date,))
            usage_deleted = cursor.rowcount
            
            # Очищення старих логів помилок
            cursor.execute('DELETE FROM error_logs WHERE timestamp < ?', (cutoff_date,))
            errors_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"🧹 Cleanup completed: {usage_deleted} usage logs, {errors_deleted} error logs deleted")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
            return False
    
    def check_connection(self):
        """Перевірка з'єднання з базою даних"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"❌ Database connection check failed: {e}")
            return False
    
    def get_recent_users(self, limit=10):
        """Отримання списку нових користувачів"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, username, first_name, registration_date
                FROM users 
                ORDER BY registration_date DESC 
                LIMIT ?
            ''', (limit,))
            
            users = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'user_id': user[0],
                    'username': user[1],
                    'first_name': user[2],
                    'registration_date': user[3]
                }
                for user in users
            ]
            
        except Exception as e:
            logger.error(f"❌ Get recent users error: {e}")
            return []
    
    def backup_database(self, backup_path=None):
        """Створення резервної копії бази даних"""
        try:
            if not backup_path:
                backup_path = f"backup_weather_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            source = sqlite3.connect(self.db_path)
            backup = sqlite3.connect(backup_path)
            
            source.backup(backup)
            
            backup.close()
            source.close()
            
            logger.info(f"💾 Database backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ Database backup error: {e}")
            return None
