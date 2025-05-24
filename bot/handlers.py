import json
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramHandlers:
    """Обробка Telegram оновлень з розширеним прогнозом погоди"""
    
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
        
        # Логування дії користувача
        self.db_service.log_user_action(user['id'], 'message_received', {
            'message_type': 'text' if 'text' in message else 'location',
            'chat_type': message['chat']['type']
        })
        
        if 'text' in message:
            text = message['text']
            logger.info(f"📝 Text message: {text}")
            
            if text == '/start':
                return self.handle_start_command(chat_id)
            elif text == '/weather':
                return self.handle_weather_command(chat_id)
            elif text == '/help':
                return self.handle_help_command(chat_id)
            elif text == '/stats' and self._is_admin_user(user['id']):
                return self.handle_stats_command(chat_id)
            else:
                # Якщо це не команда, просто нагадуємо про команди
                return self.send_message(chat_id, "🌤️ Для замовлення прогнозу погоди використовуйте команду /weather")
        
        elif 'location' in message:
            logger.info(f"📍 Location message received")
            return self.handle_location(message)
        
        return True
    
    def handle_start_command(self, chat_id):
        """Обробка команди /start"""
        logger.info(f"🚀 Handling /start command for chat {chat_id}")
        return self.send_message(chat_id, self.config.MESSAGES['start'])
    
    def handle_help_command(self, chat_id):
        """Обробка команди /help"""
        help_message = """🆘 ДОВІДКА ПО БОТУ

🌤️ **Основні команди:**
/start - Почати роботу з ботом
/weather - Замовити прогноз погоди  
/help - Показати цю довідку

💫 **Тарифні плани:**
⭐ 1 зірка = 2 дні (базовий прогноз)
⭐⭐ 2 зірки = 3 дні (розширений)
⭐⭐⭐ 3 зірки = 4 дні (детальний + рекомендації)
⭐⭐⭐⭐ 4 зірки = 5 днів (професійний)
⭐⭐⭐⭐⭐ 5 зірок = 6 днів (максимальний)

🎯 **Що ви отримуєте:**
📊 Поточна погода з усіма параметрами
🕐 Прогноз по періодах доби (ніч/ранок/день/вечір)
🌡️ Детальні температури та відчуття
🌬️ Якість повітря та рекомендації
🌙 Фази місяця та астрономічні дані
💡 Корисні поради та рекомендації

❓ **Як користуватися:**
1. Натисніть /weather
2. Оберіть потрібний тариф
3. Оплатіть Telegram Stars  
4. Надішліть геолокацію
5. Отримайте детальний прогноз!

🔄 **Підтримка:** Прогнози оновлюються кожні 3 години"""
        
        return self.send_message(chat_id, help_message)
    
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
    
    def handle_stats_command(self, chat_id):
        """Обробка команди /stats (тільки для адміністраторів)"""
        try:
            stats = self.db_service.get_bot_stats()
            if stats:
                stats_message = f"""📊 СТАТИСТИКА БОТА

👥 **Користувачі:**
   Всього: {stats['total_users']}
   Активні (30д): {stats['active_users_30d']}
   
💰 **Платежі:**
   Всього: {stats['total_payments']}
   Зірок зароблено: {stats['total_stars']}
   Середній чек: {stats['avg_payment']} зірок
   
📈 **Доходи:**
   За сьогодні: {stats['revenue_today']} зірок
   За тиждень: {stats['revenue_week']} зірок
   
🎯 **Конверсія:** {stats['conversion_rate']}%
🏆 **Популярний тариф:** {stats['most_popular_plan']}"""
                
                return self.send_message(chat_id, stats_message)
            else:
                return self.send_message(chat_id, "❌ Помилка отримання статистики")
        except Exception as e:
            logger.error(f"❌ Stats command error: {e}")
            return self.send_message(chat_id, "❌ Помилка отримання статистики")
    
    def handle_callback_query(self, callback_query):
        """Обробка натискань кнопок"""
        chat_id = callback_query['message']['chat']['id']
        user_id = callback_query['from']['id']
        data = callback_query['data']
        
        logger.info(f"🔘 Handling callback query: {data}")
        
        # Логування дії
        self.db_service.log_user_action(user_id, 'button_clicked', {'callback_data': data})
        
        if data.startswith('weather_stars_'):
            try:
                stars_count = int(data.split('_')[-1])
                logger.info(f"⭐ Selected {stars_count} stars")
                
                plan = self.config.get_pricing_plan(stars_count)
                if not plan:
                    logger.error(f"❌ Invalid pricing plan: {stars_count}")
                    return False
                
                title = f"Прогноз погоди на {plan['days']} днів"
                description = f"Максимально детальний прогноз на {plan['days']} днів з розбивкою по періодах доби"
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
                "📍 Надішліть вашу геолокацію:",
                reply_markup
            )
        
        return True
    
    def handle_pre_checkout(self, pre_checkout_query):
        """Обробка pre-checkout запиту"""
        logger.info(f"💳 Handling pre-checkout query")
        
        # Валідація pre-checkout
        is_valid, error_msg = self.payment_service.validate_pre_checkout(pre_checkout_query)
        
        return self.payment_service.answer_pre_checkout_query(
            pre_checkout_query['id'], 
            is_valid, 
            error_msg
        )
    
    def handle_successful_payment(self, message):
        """Обробка успішного платежу"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        payment = message['successful_payment']
        
        stars_count = payment['total_amount']
        plan = self.config.get_pricing_plan(stars_count)
        
        logger.info(f"💰 Processing successful payment: {stars_count} stars for {plan['days']} days")
        
        # Логування платежу
        self.db_service.log_user_action(user_id, 'payment_successful', {
            'stars_amount': stars_count,
            'plan_days': plan['days'],
            'payload': payment['invoice_payload']
        })
        
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
        """Обробка геолокації з розширеним прогнозом"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        location = message['location']
        
        lat = location['latitude']
        lon = location['longitude']
        
        logger.info(f"📍 Processing location: {lat}, {lon}")
        
        # Логування використання локації
        self.db_service.log_user_action(user_id, 'location_shared', {
            'lat': lat,
            'lon': lon
        })
        
        # Оновлення локації користувача
        self.db_service.update_location(user_id, lat, lon)
        
        # Повідомлення про обробку
        self.send_message(chat_id, self.config.MESSAGES['processing'])
        
        # Перевірка останнього платежу
        stars_count = self.db_service.get_last_payment(user_id)
        
        if not stars_count:
            logger.error(f"❌ No payment found for user {user_id}")
            return self.send_message(chat_id, self.config.MESSAGES['no_payment'])
        
        logger.info(f"💫 Found payment: {stars_count} stars for user {user_id}")
        
        # Отримання РОЗШИРЕНОГО прогнозу погоди
        weather_data = self.weather_service.get_comprehensive_forecast(lat, lon)
        
        if not weather_data:
            logger.error("❌ Failed to get comprehensive weather data")
            self.db_service.log_error(user_id, 'weather_api_error', 'Failed to get weather data')
            return self.send_message(chat_id, self.config.MESSAGES['weather_error'])
        
        logger.info("✅ Comprehensive weather data retrieved, creating detailed messages...")
        
        # Створення ДЕТАЛЬНИХ повідомлень з розбивкою по періодах доби
        messages = self.weather_service.create_detailed_weather_messages(
            weather_data, 
            stars_count, 
            self.config
        )
        
        if not messages:
            logger.error("❌ Failed to create detailed weather messages")
            self.db_service.log_error(user_id, 'message_creation_error', 'Failed to create weather messages')
            return self.send_message(chat_id, "❌ Помилка створення детального прогнозу. Спробуйте пізніше.")
        
        logger.info(f"📤 Sending {len(messages)} detailed weather messages")
        
        # Відправка всіх повідомлень
        success_count = 0
        for i, msg in enumerate(messages):
            logger.info(f"📤 Sending detailed message {i+1}/{len(messages)}")
            if self.send_message(chat_id, msg):
                success_count += 1
            else:
                logger.error(f"❌ Failed to send message {i+1}")
        
        # Фінальне повідомлення з кнопками
        final_markup = {
            'inline_keyboard': [
                [{'text': '🌤️ Замовити новий прогноз', 'callback_data': 'new_forecast'}],
                [{'text': '📍 Змінити локацію', 'callback_data': 'change_location'}]
            ]
        }
        
        self.send_message(chat_id, self.config.MESSAGES['forecast_ready'], final_markup)
        
        # Логування успішного завершення
        self.db_service.log_user_action(user_id, 'forecast_delivered', {
            'messages_sent': success_count,
            'total_messages': len(messages),
            'stars_used': stars_count,
            'location': f"{lat},{lon}"
        })
        
        logger.info("✅ Detailed weather forecast process completed successfully")
        return success_count == len(messages)
    
    def _is_admin_user(self, user_id: int) -> bool:
        """Перевірка чи є користувач адміністратором"""
        # Додайте сюди ID адміністраторів
        admin_ids = [5648307936]  # Замініть на реальні ID
        return user_id in admin_ids
        # Додайте сюди ID адміністраторів
        admin_ids = [5648307936]  # Замініть на реальні ID
        return user_id in admin_ids
