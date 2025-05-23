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
            logger.info(f"📊 Last payment for user {user_id}: {stars
