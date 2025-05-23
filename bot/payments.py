import json
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PaymentService:
    """Сервіс для обробки платежів Telegram Stars"""
    
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_invoice(self, chat_id, title, description, payload, stars_amount):
        """Створення та відправка invoice для Telegram Stars"""
        try:
            url = f"{self.base_url}/sendInvoice"
            data = {
                'chat_id': chat_id,
                'title': title,
                'description': description,
                'payload': payload,
                'currency': 'XTR',  # Telegram Stars currency
                'prices': json.dumps([{
                    'label': title,
                    'amount': stars_amount
                }])
            }
            
            logger.info(f"💳 Creating invoice: {title} - {stars_amount} stars for chat {chat_id}")
            
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"✅ Invoice created successfully")
                return True
            else:
                logger.error(f"❌ Invoice creation failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Send invoice error: {e}")
            return False
    
    def answer_pre_checkout_query(self, pre_checkout_query_id, ok=True, error_message=None):
        """Відповідь на pre-checkout запит"""
        try:
            url = f"{self.base_url}/answerPreCheckoutQuery"
            data = {
                'pre_checkout_query_id': pre_checkout_query_id,
                'ok': ok
            }
            
            if not ok and error_message:
                data['error_message'] = error_message
            
            logger.info(f"💳 Answering pre-checkout query: {pre_checkout_query_id} - {'OK' if ok else 'DECLINE'}")
            
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"✅ Pre-checkout answered successfully")
                return True
            else:
                logger.error(f"❌ Pre-checkout answer failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Answer pre-checkout error: {e}")
            return False
    
    def validate_payment(self, payment_data):
        """Валідація даних платежу"""
        try:
            required_fields = ['total_amount', 'invoice_payload', 'telegram_payment_charge_id']
            
            for field in required_fields:
                if field not in payment_data:
                    logger.error(f"❌ Missing payment field: {field}")
                    return False
            
            # Перевірка суми платежу
            total_amount = payment_data['total_amount']
            if not isinstance(total_amount, int) or total_amount < 1 or total_amount > 5:
                logger.error(f"❌ Invalid payment amount: {total_amount}")
                return False
            
            # Перевірка payload
            payload = payment_data['invoice_payload']
            if not payload.startswith('weather_') or not payload.endswith('_days'):
                logger.error(f"❌ Invalid payment payload: {payload}")
                return False
            
            logger.info(f"✅ Payment validation successful: {total_amount} stars")
            return True
            
        except Exception as e:
            logger.error(f"❌ Payment validation error: {e}")
            return False
    
    def process_successful_payment(self, payment_data, user_id):
        """Обробка успішного платежу"""
        try:
            if not self.validate_payment(payment_data):
                return None
            
            stars_amount = payment_data['total_amount']
            payload = payment_data['invoice_payload']
            telegram_charge_id = payment_data['telegram_payment_charge_id']
            
            payment_info = {
                'user_id': user_id,
                'stars_amount': stars_amount,
                'payload': payload,
                'telegram_payment_id': telegram_charge_id,
                'payment_date': datetime.now().isoformat(),
                'status': 'completed'
            }
            
            logger.info(f"💰 Processed successful payment: {stars_amount} stars for user {user_id}")
            return payment_info
            
        except Exception as e:
            logger.error(f"❌ Process payment error: {e}")
            return None
    
    def get_pricing_info(self, stars_count):
        """Отримання інформації про тариф"""
        try:
            from config.settings import Config
            config = Config()
            
            plan = config.get_pricing_plan(stars_count)
            if plan:
                return {
                    'stars': stars_count,
                    'days': plan['days'],
                    'name': plan['name'],
                    'description': plan['description']
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Get pricing info error: {e}")
            return None
    
    def create_refund_request(self, payment_id, user_id, reason="User request"):
        """Створення запиту на повернення коштів (для майбутнього використання)"""
        try:
            # Telegram Stars поки що не підтримує автоматичні повернення
            # Цей метод для майбутнього функціоналу
            
            refund_info = {
                'payment_id': payment_id,
                'user_id': user_id,
                'reason': reason,
                'request_date': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            logger.info(f"💸 Refund request created for payment {payment_id}")
            return refund_info
            
        except Exception as e:
            logger.error(f"❌ Create refund request error: {e}")
            return None
    
    def get_payment_statistics(self, db_service):
        """Статистика платежів"""
        try:
            stats = db_service.get_payment_stats()
            
            if stats:
                total_payments = stats.get('total_payments', 0)
                total_stars = stats.get('total_stars', 0)
                avg_payment = stats.get('avg_payment', 0)
                
                return {
                    'total_payments': total_payments,
                    'total_stars_earned': total_stars,
                    'average_payment': round(avg_payment, 2),
                    'most_popular_plan': stats.get('most_popular_plan', 'N/A'),
                    'revenue_today': stats.get('revenue_today', 0)
                }
            
            return {
                'total_payments': 0,
                'total_stars_earned': 0,
                'average_payment': 0,
                'most_popular_plan': 'N/A',
                'revenue_today': 0
            }
            
        except Exception as e:
            logger.error(f"❌ Get payment statistics error: {e}")
            return None
    
    def validate_pre_checkout(self, pre_checkout_data):
        """Валідація pre-checkout запиту"""
        try:
            # Перевірка валюти
            if pre_checkout_data.get('currency') != 'XTR':
                logger.error(f"❌ Invalid currency: {pre_checkout_data.get('currency')}")
                return False, "Invalid currency"
            
            # Перевірка суми
            total_amount = pre_checkout_data.get('total_amount')
            if not isinstance(total_amount, int) or total_amount < 1 or total_amount > 5:
                logger.error(f"❌ Invalid amount in pre-checkout: {total_amount}")
                return False, "Invalid amount"
            
            # Перевірка payload
            payload = pre_checkout_data.get('invoice_payload', '')
            if not payload.startswith('weather_'):
                logger.error(f"❌ Invalid payload in pre-checkout: {payload}")
                return False, "Invalid order"
            
            logger.info(f"✅ Pre-checkout validation successful")
            return True, None
            
        except Exception as e:
            logger.error(f"❌ Pre-checkout validation error: {e}")
            return False, "Validation error"
    
    def log_payment_attempt(self, user_id, stars_amount, status="attempt"):
        """Логування спроби платежу"""
        try:
            log_entry = {
                'user_id': user_id,
                'stars_amount': stars_amount,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"📝 Payment {status}: {stars_amount} stars for user {user_id}")
            return log_entry
            
        except Exception as e:
            logger.error(f"❌ Log payment attempt error: {e}")
            return None
