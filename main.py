import os
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Імпорти модулів бота
from bot.handlers import TelegramHandlers
from bot.weather import WeatherService
from bot.payments import PaymentService
from bot.database import DatabaseService
from config.settings import Config

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Ініціалізація сервісів
config = Config()
db_service = DatabaseService()
weather_service = WeatherService(config.OPENWEATHER_API_KEY)
payment_service = PaymentService(config.BOT_TOKEN)
telegram_handlers = TelegramHandlers(config.BOT_TOKEN, weather_service, payment_service, db_service)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Головний webhook роутер"""
    try:
        update = request.get_json()
        logger.info(f"Received update: {update}")
        
        # Делегування обробки до handlers
        result = telegram_handlers.process_update(update)
        
        return jsonify({'status': 'ok', 'processed': result})
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'bot_token': bool(config.BOT_TOKEN),
            'weather_api': bool(config.OPENWEATHER_API_KEY),
            'webhook_url': bool(config.WEBHOOK_URL),
            'database': db_service.check_connection()
        }
    })

@app.route('/')
def index():
    """Головна сторінка"""
    return "🌤️ Погода без сюрпризів - Bot is running!"

@app.route('/test-weather')
def test_weather():
    """Тестування Weather API"""
    try:
        # Тестові координати Києва
        lat, lon = 50.4501, 30.5234
        weather_data = weather_service.get_forecast(lat, lon)
        
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

@app.route('/stats')
def stats():
    """Статистика бота"""
    try:
        stats = db_service.get_bot_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def setup_webhook():
    """Встановлення webhook"""
    if config.WEBHOOK_URL and config.BOT_TOKEN:
        result = telegram_handlers.setup_webhook(config.WEBHOOK_URL)
        if result:
            logger.info(f"✅ Webhook setup successful")
        else:
            logger.error(f"❌ Webhook setup failed")
    else:
        logger.warning("⚠️ WEBHOOK_URL or BOT_TOKEN not set")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"🚀 Starting Weather Bot on port {port}")
    logger.info(f"📍 Bot Token: {'✅' if config.BOT_TOKEN else '❌'}")
    logger.info(f"🌤️ Weather API: {'✅' if config.OPENWEATHER_API_KEY else '❌'}")
    logger.info(f"🔗 Webhook URL: {config.WEBHOOK_URL or 'Not set'}")
    
    # Ініціалізація бази даних
    db_service.init_database()
    
    # Встановлення webhook
    setup_webhook()
    
    # Запуск Flask
    app.run(host='0.0.0.0', port=port, debug=False)
