import json
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramHandlers:
    """Обробка Telegram оновлень"""
    
    def __init__(self, bot_token, weather_service, payment_service, db_service):
        self.bot_token = bot_token
        self.weather_service = weather_service
        self.payment_service = payment_service
        self.db_service = db_service
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Імпорт конфігурації
        from config.settings import Config
        self.config = Config()
    
    def process_update(self, update):
        """Головна функція обробки оновлень"""
        try:
            if 'message' in update:
                if 'successful_payment' in update['message']:
                    return self.handle_successful_payment(update['message'])
                else:
                    return self.handle_message(update['message'])
            
            elif 'callback_query' in update:
                return self.handle_callback_query(update['callback_query'])
            
            elif 'pre_checkout_query' in update:
                return self.handle_pre_checkout(update['pre_checkout_query'])
            
            return True
        except Exception as e:
            logger.error(f"Process update error: {e}")
            return False
    
    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        """Відправка повідомлення"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        if parse_mode:
            data['parse_mode'] = parse_mode
        
        try:
            logger.info(f"Sending message to {chat_id}: {text[:50]}...")
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"✅ Message sent successfully")
                return True
            else:
                logger.error(f"❌ Message send failed: {result}")
                return False
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return False
    
    def setup_webhook(self, webhook_url):
        """Встановлення webhook"""
        url = f"{self.base_url}/setWebhook"
        webhook_endpoint = f"{webhook_url}/webhook"
        
        try:
            response = requests.post(url, data={'url': webhook_endpoint}, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"✅ Webhook setup successful: {webhook_endpoint}")
                return True
            else:
                logger.error(f"❌ Webhook setup failed: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Webhook setup error: {e}")
            return False
    
    def handle_message(self, message):
        """Обробка текстових повідомлень"""
        chat_id = message['chat']['id']
        user = message['from']
        
        logger.info(f"📨 Processing message from user {user.get('username', user['id'])}")
        
        # Збереження користувача
        self.db_service.save_user(user)
        
        if 'text' in message:
            text = message['text']
            logger.info(f"📝 Text message: {text}")
            
            if text == '/start':
                return self.handle_start_command(chat_id)
            elif text == '/weather':
                return self.handle_weather_command(chat_id)
        
        elif 'location' in message:
            logger.info(f"📍 Location message received")
            return self.handle_location(message)
        
        return True
    
    def handle_start_command(self, chat_id):
        """Обробка команди /start"""
        logger.info(f"🚀 Handling /start command for chat {chat_id}")
        return self.send_message(chat_id, self.config.MESSAGES['start'])
    
    def handle_weather_command(self, chat_id):
        """Обробка команди /weather"""
        logger.info(f"🌤️ Handling /weather command for chat {chat_id}")
        
        # Створення інлайн клавіатури з правильними callback_data
        reply_markup = {
            'inline_keyboard': [
                [{'text': self.config.PRICING_PLANS[1]['name'], 'callback_data': 'weather_stars_1'}],
                [{'text': self.config.PRICING_PLANS[2]['name'], 'callback_data': 'weather_stars_2'}],
                [{'text': self.config.PRICING_PLANS[3]['name'], 'callback_data': 'weather_stars_3'}],
                [{'text': self.config.PRICING_PLANS[4]['name'], 'callback_data': 'weather_stars_4'}],
                [{'text': self.config.PRICING_PLANS[5]['name'], 'callback_data': 'weather_stars_5'}]
            ]
        }
        
        return self.send_message(chat_id, self.config.MESSAGES['weather_menu'], reply_markup)
    
    def handle_callback_query(self, callback_query):
        """Обробка натискань кнопок"""
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        logger.info(f"🔘 Handling callback query: {data}")
        
        if data.startswith('weather_stars_'):
            # ВИПРАВЛЕНА ЛОГІКА: правильний парсинг кількості зірок
            try:
                stars_count = int(data.split('_')[-1])  # Останній елемент після розділення
                logger.info(f"⭐ Selected {stars_count} stars")
                
                plan = self.config.get_pricing_plan(stars_count)
                if not plan:
                    logger.error(f"❌ Invalid pricing plan: {stars_count}")
                    return False
                
                title = f"Прогноз погоди на {plan['days']} днів"
                description = f"Детальний прогноз погоди на {plan['days']} днів з якістю повітря та фазою місяця"
                payload = f"weather_{plan['days']}_days"
                
                return self.payment_service.send_invoice(chat_id, title, description, payload, stars_count)
                
            except (ValueError, IndexError) as e:
                logger.error(f"❌ Error parsing callback data {data}: {e}")
                return False
        
        elif data == 'new_forecast':
            return self.handle_weather_command(chat_id)
        
        elif data == 'change_location':
            reply_markup = {
                'keyboard': [[{'text': '📍 Поділитися локацією', 'request_location': True}]],
                'resize_keyboard': True,
                'one_time_keyboard': True
            }
            
            return self.send_message(
                chat_id, 
                "📍 Надішліть нову геолокацію або напишіть назву міста:",
                reply_markup
            )
        
        return True
    
    def handle_pre_checkout(self, pre_checkout_query):
        """Обробка pre-checkout запиту"""
        logger.info(f"💳 Handling pre-checkout query")
        return self.payment_service.answer_pre_checkout_query(pre_checkout_query['id'], True)
    
    def handle_successful_payment(self, message):
        """Обробка успішного платежу"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        payment = message['successful_payment']
        
        stars_count = payment['total_amount']
        plan = self.config.get_pricing_plan(stars_count)
        
        logger.info(f"💰 Processing successful payment: {stars_count} stars for {plan['days']} days")
        
        # Збереження платежу
        self.db_service.save_payment(
            user_id,
            stars_count,
            payment['invoice_payload'],
            payment['telegram_payment_charge_id']
        )
        
        # Запит геолокації
        reply_markup = {
            'keyboard': [[{'text': '📍 Поділитися локацією', 'request_location': True}]],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        message_text = self.config.MESSAGES['payment_success'].format(
            stars=stars_count, 
            days=plan['days']
        )
        
        return self.send_message(chat_id, message_text, reply_markup)
    
    def handle_location(self, message):
        """Обробка геолокації"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        location = message['location']
        
        lat = location['latitude']
        lon = location['longitude']
        
        logger.info(f"📍 Processing location: {lat}, {lon}")
        
        # Повідомлення про обробку
        self.send_message(chat_id, self.config.MESSAGES['processing'])
        
        # Перевірка останнього платежу
        stars_count = self.db_service.get_last_payment(user_id)
        
        if not stars_count:
            logger.error(f"❌ No payment found for user {user_id}")
            return self.send_message(chat_id, self.config.MESSAGES['no_payment'])
        
        logger.info(f"💫 Found payment: {stars_count} stars for user {user_id}")
        
        # Отримання прогнозу погоди
        weather_data = self.weather_service.get_forecast(lat, lon)
        
        if not weather_data:
            logger.error("❌ Failed to get weather data")
            return self.send_message(chat_id, self.config.MESSAGES['weather_error'])
        
        logger.info("✅ Weather data retrieved, creating messages...")
        
        # Створення повідомлень
        messages = self.weather_service.create_weather_messages(weather_data, stars_count, self.config)
        
        if not messages:
            logger.error("❌ Failed to create weather messages")
            return self.send_message(chat_id, "❌ Помилка створення прогнозу. Спробуйте пізніше.")
        
        logger.info(f"📤 Sending {len(messages)} weather messages")
        
        # Відправка всіх повідомлень
        success = True
        for i, msg in enumerate(messages):
            logger.info(f"📤 Sending message {i+1}/{len(messages)}")
            if not self.send_message(chat_id, msg):
                success = False
        
        # Фінальне повідомлення з кнопками
        final_markup = {
            'inline_keyboard': [
                [{'text': '🌤️ Замовити новий прогноз', 'callback_data': 'new_forecast'}],
                [{'text': '📍 Змінити локацію', 'callback_data': 'change_location'}]
            ]
        }
        
        self.send_message(chat_id, self.config.MESSAGES['forecast_ready'], final_markup)
        
        logger.info("✅ Weather forecast process completed successfully")
        return success
