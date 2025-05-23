import os
import json
import requests
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3
import math

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфігурація
BOT_TOKEN = os.environ.get('BOT_TOKEN')
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

class WeatherBot:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.weather_api_key = OPENWEATHER_API_KEY
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.init_database()
    
    def init_database(self):
        """Ініціалізація бази даних"""
        conn = sqlite3.connect('weather_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_purchase_date TEXT,
                last_location_lat REAL,
                last_location_lon REAL,
                last_location_name TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stars_amount INTEGER,
                payload TEXT,
                payment_date TEXT,
                telegram_payment_id TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def send_message(self, chat_id, text, reply_markup=None, parse_mode='Markdown'):
        """Відправка повідомлення"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        
        try:
            logger.info(f"Sending message to {chat_id}: {text[:50]}...")
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Message sent successfully")
            else:
                logger.error(f"❌ Message send failed: {result}")
            return result
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return None
    
    def send_invoice(self, chat_id, title, description, payload, stars_amount):
        """Створення invoice для Telegram Stars"""
        url = f"{self.base_url}/sendInvoice"
        data = {
            'chat_id': chat_id,
            'title': title,
            'description': description,
            'payload': payload,
            'currency': 'XTR',
            'prices': json.dumps([{'label': title, 'amount': stars_amount}])
        }
        
        try:
            logger.info(f"Creating invoice: {title} - {stars_amount} stars")
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Invoice created successfully")
            else:
                logger.error(f"❌ Invoice creation failed: {result}")
            return result
        except Exception as e:
            logger.error(f"Send invoice error: {e}")
            return None
    
    def answer_pre_checkout_query(self, pre_checkout_query_id, ok=True):
        """Підтвердження pre-checkout"""
        url = f"{self.base_url}/answerPreCheckoutQuery"
        data = {
            'pre_checkout_query_id': pre_checkout_query_id,
            'ok': ok
        }
        
        try:
            logger.info(f"Answering pre-checkout query: {pre_checkout_query_id}")
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Pre-checkout answered successfully")
            else:
                logger.error(f"❌ Pre-checkout answer failed: {result}")
            return result
        except Exception as e:
            logger.error(f"Answer pre-checkout error: {e}")
            return None
    
    def get_weather_forecast(self, lat, lon):
        """Отримання прогнозу погоди"""
        try:
            logger.info(f"🌤️ Getting weather forecast for coordinates: {lat}, {lon}")
            
            # 5-денний прогноз
            forecast_url = f"https://api.openweathermap.org/data/2.5/forecast"
            forecast_params = {
                'lat': lat,
                'lon': lon,
                'units': 'metric',
                'lang': 'uk',
                'appid': self.weather_api_key
            }
            
            logger.info(f"📡 Making forecast API request to: {forecast_url}")
            logger.info(f"🔑 Using API key: {self.weather_api_key[:10]}..." if self.weather_api_key else "❌ No API key")
            
            forecast_response = requests.get(forecast_url, params=forecast_params, timeout=15)
            logger.info(f"📡 Forecast API response status: {forecast_response.status_code}")
            
            if forecast_response.status_code != 200:
                logger.error(f"❌ Forecast API error: {forecast_response.status_code}")
                logger.error(f"❌ Forecast API response: {forecast_response.text}")
                return None
            
            # Якість повітря
            air_url = f"https://api.openweathermap.org/data/2.5/air_pollution"
            air_params = {
                'lat': lat,
                'lon': lon,
                'appid': self.weather_api_key
            }
            
            logger.info(f"📡 Making air quality API request")
            air_response = requests.get(air_url, params=air_params, timeout=15)
            logger.info(f"📡 Air quality API response status: {air_response.status_code}")
            
            if air_response.status_code != 200:
                logger.error(f"❌ Air quality API error: {air_response.status_code}")
                logger.error(f"❌ Air quality API response: {air_response.text}")
                return None
            
            logger.info("✅ Weather data retrieved successfully")
            return {
                'forecast': forecast_response.json(),
                'air_quality': air_response.json()
            }
                
        except Exception as e:
            logger.error(f"❌ Weather API exception: {e}")
            return None
    
    def get_moon_phase(self):
        """Розрахунок фази місяця"""
        now = datetime.now()
        year = now.year
        month = now.month
        day = now.day
        
        # Спрощений алгоритм фази місяця
        c = math.floor((year - 1900) / 100)
        jd = 365.25 * (year - 1900) + math.floor(30.6 * month) + day - 694039.09
        age = jd * 1.5336 + 0.18
        phase = age - math.floor(age)
        
        if phase < 0.0625 or phase >= 0.9375:
            return {"phase": "Новий місяць", "icon": "🌑"}
        elif phase < 0.1875:
            return {"phase": "Молодий місяць", "icon": "🌒"}
        elif phase < 0.3125:
            return {"phase": "Перша чверть", "icon": "🌓"}
        elif phase < 0.4375:
            return {"phase": "Зростаючий місяць", "icon": "🌔"}
        elif phase < 0.5625:
            return {"phase": "Повний місяць", "icon": "🌕"}
        elif phase < 0.6875:
            return {"phase": "Спадаючий місяць", "icon": "🌖"}
        elif phase < 0.8125:
            return {"phase": "Остання чверть", "icon": "🌗"}
        else:
            return {"phase": "Старіючий місяць", "icon": "🌘"}
    
    def create_weather_messages(self, weather_data, stars_count):
        """Створення повідомлень з прогнозом"""
        try:
            logger.info(f"📊 Creating weather messages for {stars_count} stars")
            messages = []
            forecast_data = weather_data['forecast']
            air_data = weather_data['air_quality']
            
            # Заголовне повідомлення
            city_name = forecast_data['city']['name']
            timezone_offset = forecast_data['city']['timezone'] // 3600
            moon_info = self.get_moon_phase()
            
            air_quality = air_data['list'][0]
            aqi_labels = {1: 'Добра 🟢', 2: 'Задовільна 🟡', 3: 'Помірна 🟠', 4: 'Погана 🔴', 5: 'Дуже погана 🟣'}
            aqi_status = aqi_labels.get(air_quality['main']['aqi'], 'Невідома')
            
            # Час сходу/заходу сонця
            sunrise_timestamp = forecast_data['city']['sunrise'] + forecast_data['city']['timezone']
            sunset_timestamp = forecast_data['city']['sunset'] + forecast_data['city']['timezone']
            
            sunrise_time = datetime.fromtimestamp(sunrise_timestamp).strftime('%H:%M')
            sunset_time = datetime.fromtimestamp(sunset_timestamp).strftime('%H:%M')
            
            header_message = f"""🌤️ ПРОГНОЗ ПОГОДИ ОТРИМАНО!

📍 Локація: {city_name}, Україна
🕐 Часовий пояс: UTC{'+' if timezone_offset >= 0 else ''}{timezone_offset}
{moon_info['icon']} Фаза місяця: {moon_info['phase']}

🌬️ ЯКІСТЬ ПОВІТРЯ: {aqi_status}
✅ PM2.5: {air_quality['components']['pm2_5']} μg/m³
✅ O₃: {air_quality['components']['o3']} μg/m³

🌅 Схід: {sunrise_time} | 🌇 Захід: {sunset_time}

📊 Детальний прогноз надходить окремими повідомленнями...

🔗 Хочете такий же прогноз? @pogoda_bez_syurpryziv_bot"""
            
            messages.append(header_message)
            
            # Повідомлення по днях
            days_to_show = stars_count + 1
            day_names = ['СЬОГОДНІ', 'ЗАВТРА', 'ПІСЛЯЗАВТРА', 'ЧЕРЕЗ 3 ДНІ', 'ЧЕРЕЗ 4 ДНІ', 'ЧЕРЕЗ 5 ДНІВ']
            
            call_to_actions = [
                "🎯 Точні прогнози без сюрпризів! @pogoda_bez_syurpryziv_bot",
                "⭐ Детальна погода за зірки! @pogoda_bez_syurpryziv_bot",
                "🌤️ Професійні прогнози тут: @pogoda_bez_syurpryziv_bot",
                "💫 Погода без сюрпризів: @pogoda_bez_syurpryziv_bot",
                "🔮 Максимально детальні прогнози: @pogoda_bez_syurpryziv_bot",
                "🌟 Найточніші прогнози: @pogoda_bez_syurpryziv_bot"
            ]
            
            # Групування прогнозів по днях
            for day_index in range(min(days_to_show, len(day_names))):
                day_name = day_names[day_index]
                
                if day_index * 8 < len(forecast_data['list']):
                    forecast_item = forecast_data['list'][day_index * 8]
                    temp = round(forecast_item['main']['temp'])
                    feels_like = round(forecast_item['main']['feels_like'])
                    description = forecast_item['weather'][0]['description']
                    humidity = forecast_item['main']['humidity']
                    wind_speed = forecast_item['wind']['speed']
                    
                    day_message = f"""📅 {day_name}
{moon_info['icon']} Фаза місяця: {moon_info['phase']}

🌬️ ЯКІСТЬ ПОВІТРЯ: {aqi_status}
✅ PM2.5: {air_quality['components']['pm2_5']} μg/m³
✅ O₃: {air_quality['components']['o3']} μg/m³

☀️ ТЕМПЕРАТУРА: {temp}°C (відчув. {feels_like}°C)
   {description}
   💧 Вологість: {humidity}%
   💨 Вітер: {wind_speed} м/с

{call_to_actions[day_index % len(call_to_actions)]}"""
                    
                    messages.append(day_message)
            
            # Завершальне повідомлення
            final_message = f"""✅ ПРОГНОЗ ПОГОДИ ЗАВЕРШЕНО!

🎯 Ви отримали детальний прогноз на {days_to_show} днів для:
📍 {city_name}, Україна

💡 ХОЧЕТЕ НОВИЙ ПРОГНОЗ?

🔄 Якщо ви залишаєтесь у тому ж місці:
• У вас уже є актуальний прогноз на найближчі дні
• Рекомендуємо замовляти новий прогноз через 2-3 дні

🌍 Якщо ви змінили локацію:
• Можете замовити прогноз для нового місця прямо зараз

🛍️ Готові замовити новий прогноз?"""
            
            messages.append(final_message)
            logger.info(f"✅ Created {len(messages)} weather messages")
            return messages
        except Exception as e:
            logger.error(f"❌ Error creating weather messages: {e}")
            return []
    
    def save_user(self, user_data):
        """Збереження користувача в базу"""
        try:
            conn = sqlite3.connect('weather_bot.db', check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_purchase_date)
                VALUES (?, ?, ?, ?)
            ''', (
                user_data['id'],
                user_data.get('username'),
                user_data.get('first_name'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ User saved: {user_data.get('username', user_data['id'])}")
        except Exception as e:
            logger.error(f"Save user error: {e}")
    
    def save_payment(self, user_id, stars_amount, payload, telegram_payment_id):
        """Збереження платежу"""
        try:
            conn = sqlite3.connect('weather_bot.db', check_same_thread=False)
            cursor = conn.cursor()
            
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
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Payment saved: {stars_amount} stars for user {user_id}")
        except Exception as e:
            logger.error(f"Save payment error: {e}")
    
    def get_last_payment(self, user_id):
        """Отримання останнього платежу користувача"""
        try:
            conn = sqlite3.connect('weather_bot.db', check_same_thread=False)
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
            logger.error(f"Get last payment error: {e}")
            return None

# Ініціалізація бота
weather_bot = None
if BOT_TOKEN and OPENWEATHER_API_KEY:
    weather_bot = WeatherBot()
    logger.info("✅ WeatherBot initialized successfully")
else:
    logger.error("❌ Missing BOT_TOKEN or OPENWEATHER_API_KEY")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обробка webhook від Telegram"""
    if not weather_bot:
        logger.error("Weather bot not initialized")
        return jsonify({'status': 'error', 'message': 'Bot not initialized'})
    
    try:
        update = request.get_json()
        logger.info(f"Received update: {update}")
        
        if 'message' in update:
            if 'successful_payment' in update['message']:
                handle_successful_payment(update['message'])
            else:
                handle_message(update['message'])
        elif 'callback_query' in update:
            handle_callback_query(update['callback_query'])
        elif 'pre_checkout_query' in update:
            handle_pre_checkout(update['pre_checkout_query'])
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

def handle_message(message):
    """Обробка текстових повідомлень"""
    if not weather_bot:
        return
    
    chat_id = message['chat']['id']
    user = message['from']
    
    logger.info(f"📨 Processing message from user {user.get('username', user['id'])}")
    
    weather_bot.save_user(user)
    
    if 'text' in message:
        text = message['text']
        logger.info(f"📝 Text message: {text}")
        
        if text == '/start':
            handle_start_command(chat_id)
        elif text == '/weather':
            handle_weather_command(chat_id)
    
    elif 'location' in message:
        logger.info(f"📍 Location message received")
        handle_location(message)

def handle_start_command(chat_id):
    """Обробка команди /start"""
    logger.info(f"🚀 Handling /start command for chat {chat_id}")
    message = """🌤️ *Вітаємо в "Погода без сюрпризів"!*

🎯 *Наші можливості:*
• Точні прогнози погоди на 2-6 днів
• Детальна якість повітря з рекомендаціями
• Температура по частинах доби
• Фаза місяця та час сходу/заходу сонця

💫 *Тарифи:*
⭐ 1 зірка = 2 дні
⭐⭐ 2 зірки = 3 дні
⭐⭐⭐ 3 зірки = 4 дні
⭐⭐⭐⭐ 4 зірки = 5 днів
⭐⭐⭐⭐⭐ 5 зірок = 6 днів

🚀 Почніть з команди /weather"""
    
    weather_bot.send_message(chat_id, message)

def handle_weather_command(chat_id):
    """Обробка команди /weather"""
    logger.info(f"🌤️ Handling /weather command for chat {chat_id}")
    reply_markup = {
        'inline_keyboard': [
            [{'text': '⭐ 1 зірка', 'callback_data': 'weather_1_star'}],
            [{'text': '⭐⭐ 2 зірки', 'callback_data': 'weather_2_stars'}],
            [{'text': '⭐⭐⭐ 3 зірки', 'callback_data': 'weather_3_stars'}],
            [{'text': '⭐⭐⭐⭐ 4 зірки', 'callback_data': 'weather_4_stars'}],
            [{'text': '⭐⭐⭐⭐⭐ 5 зірок', 'callback_data': 'weather_5_stars'}]
        ]
    }
    
    message = """🌤️ *Оберіть тариф прогнозу погоди:*

⭐ 1 зірка = 2 дні (сьогодні + завтра)
⭐⭐ 2 зірки = 3 дні
⭐⭐⭐ 3 зірки = 4 дні
⭐⭐⭐⭐ 4 зірки = 5 днів
⭐⭐⭐⭐⭐ 5 зірок = 6 днів (МАКСИМУМ!)

🎯 Виберіть потрібний тариф:"""
    
    weather_bot.send_message(chat_id, message, reply_markup)

def handle_callback_query(callback_query):
    """Обробка натискань кнопок"""
    if not weather_bot:
        return
    
    chat_id = callback_query['message']['chat']['id']
    data = callback_query['data']
    
    logger.info(f"🔘 Handling callback query: {data}")
    
    if data.startswith('weather_'):
        if 'star' in data:
            stars_count = 1
        else:
            stars_count = int(data.split('_')[1])
        
        days_count = stars_count + 1
        
        title = f"Прогноз погоди на {days_count} днів"
        description = f"Детальний прогноз погоди на {days_count} днів з якістю повітря та фазою місяця"
        payload = f"weather_{days_count}_days"
        
        weather_bot.send_invoice(chat_id, title, description, payload, stars_count)
    
    elif data == 'new_forecast':
        handle_weather_command(chat_id)
    
    elif data == 'change_location':
        reply_markup = {
            'keyboard': [[{'text': '📍 Поділитися локацією', 'request_location': True}]],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        weather_bot.send_message(
            chat_id, 
            "📍 Надішліть нову геолокацію або напишіть назву міста:",
            reply_markup
        )

def handle_pre_checkout(pre_checkout_query):
    """Обробка pre-checkout запиту"""
    logger.info(f"💳 Handling pre-checkout query")
    if weather_bot:
        weather_bot.answer_pre_checkout_query(pre_checkout_query['id'], True)

def handle_successful_payment(message):
    """Обробка успішного платежу"""
    if not weather_bot:
        return
    
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    payment = message['successful_payment']
    
    logger.info(f"💰 Processing successful payment: {payment['total_amount']} stars")
    
    weather_bot.save_payment(
        user_id,
        payment['total_amount'],
        payment['invoice_payload'],
        payment['telegram_payment_charge_id']
    )
    
    reply_markup = {
        'keyboard': [[{'text': '📍 Поділитися локацією', 'request_location': True}]],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }
    
    stars_count = payment['total_amount']
    days_count = stars_count + 1
    
    message_text = f"""✅ Оплату {stars_count} зірок успішно проведено!

💫 Ви придбали прогноз погоди на {days_count} днів!

📍 Наступний крок: Надішліть вашу геолокацію або напишіть назву міста.

🎯 Ви отримаєте найдетальніший прогноз з усіма можливими даними!"""
    
    weather_bot.send_message(chat_id, message_text, reply_markup)

def handle_location(message):
    """Обробка геолокації"""
    if not weather_bot:
        logger.error("❌ Weather bot not initialized")
        return
    
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    location = message['location']
    
    lat = location['latitude']
    lon = location['longitude']
    
    logger.info(f"📍 Processing location: {lat}, {lon}")
    
    weather_bot.send_message(chat_id, "🔄 Обробляємо вашу геолокацію та отримуємо прогноз погоди...")
    
    stars_count = weather_bot.get_last_payment(user_id)
    
    if not stars_count:
        logger.error(f"❌ No payment found for user {user_id}")
        weather_bot.send_message(chat_id, "❌ Спочатку оплатіть прогноз командою /weather")
        return
    
    logger.info(f"💫 Found payment: {stars_count} stars for user {user_id}")
    
    weather_data = weather_bot.get_weather_forecast(lat, lon)
    
    if not weather_data:
        logger.error("❌ Failed to get weather data")
        weather_bot.send_message(chat_id, "❌ Помилка отримання даних про погоду. Спробуйте пізніше або зверніться до підтримки.")
        return
    
    logger.info("✅ Weather data retrieved, creating messages...")
    
    messages = weather_bot.create_weather_messages(weather_data, stars_count)
    
    if not messages:
        logger.error("❌ Failed to create weather messages")
        weather_bot.send_message(chat_id, "❌ Помилка створення прогнозу. Спробуйте пізніше.")
        return
    
    logger.info(f"📤 Sending {len(messages)} weather messages")
    
    for i, msg in enumerate(messages):
        logger.info(f"📤 Sending message {i+1}/{len(messages)}")
        weather_bot.send_message(chat_id, msg)
        
        if i == len(messages) - 1:
            final_markup = {
                'inline_keyboard': [
                    [{'text': '🌤️ Замовити новий прогноз', 'callback_data': 'new_forecast'}],
                    [{'text': '📍 Змінити локацію', 'callback_data': 'change_location'}]
                ]
            }
            weather_bot.send_message(chat_id, "🎉 Прогноз готовий! Оберіть наступну дію:", final_markup)
    
    logger.info("✅ Weather forecast process completed successfully")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'bot_initialized': weather_bot is not None,
        'has_bot_token': BOT_TOKEN is not None,
        'has_weather_key': OPENWEATHER_API_KEY is not None,
        'webhook_url': WEBHOOK_URL
    })

@app.route('/')
def index():
    """Головна сторінка"""
    return "🌤️ Погода без сюрпризів - Bot is running!"

@app.route('/test-weather')
def test_weather():
    """Тестовий endpoint для перевірки Weather API"""
    if not weather_bot:
        return jsonify({'error': 'Bot not initialized'})
    
    lat, lon = 50.4501, 30.5234
    
    try:
        weather_data = weather_bot.get_weather_forecast(lat, lon)
        if weather_data:
            return jsonify({
                'status': 'success',
                'city': weather_data['forecast']['city']['name'],
                'forecast_count': len(weather_data['forecast']['list']),
                'air_quality_aqi': weather_data['air_quality']['list'][0]['main']['aqi']
            })
        else:
            return jsonify({'status': 'error', 'message': 'Failed to get weather data'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def setup_webhook():
    """Встановлення webhook"""
    if WEBHOOK_URL and BOT_TOKEN:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        set_webhook_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        
        try:
            response = requests.post(set_webhook_url, data={'url': webhook_url}, timeout=10)
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Webhook setup successful: {webhook_url}")
            else:
                logger.error(f"❌ Webhook setup failed: {result}")
        except Exception as e:
            logger.error(f"❌ Webhook setup error: {e}")
    else:
        logger.warning("⚠️ WEBHOOK_URL or BOT_TOKEN not set - webhook not configured")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"🚀 Starting Flask app on port {port}")
    logger.info(f"📍 Bot Token present: {bool(BOT_TOKEN)}")
    logger.info(f"🌤️ Weather API Key present: {bool(OPENWEATHER_API_KEY)}")
    logger.info(f"🔗 Webhook URL: {WEBHOOK_URL or 'Not set'}")
    
    setup_webhook()
    
    app.run(host='0.0.0.0', port=port, debug=False)
