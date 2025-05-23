import os

class Config:
    """Конфігурація бота"""
    
    def __init__(self):
        self.BOT_TOKEN = os.environ.get('BOT_TOKEN')
        self.OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
        self.WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
        
        # Налаштування бота
        self.BOT_NAME = "Погода без сюрпризів"
        self.BOT_USERNAME = "@pogoda_bez_syurpryziv_bot"
        
        # Тарифні плани
        self.PRICING_PLANS = {
            1: {'days': 2, 'name': '⭐ 1 зірка', 'description': '2 дні (сьогодні + завтра)'},
            2: {'days': 3, 'name': '⭐⭐ 2 зірки', 'description': '3 дні'},
            3: {'days': 4, 'name': '⭐⭐⭐ 3 зірки', 'description': '4 дні'},
            4: {'days': 5, 'name': '⭐⭐⭐⭐ 4 зірки', 'description': '5 днів'},
            5: {'days': 6, 'name': '⭐⭐⭐⭐⭐ 5 зірок', 'description': '6 днів (МАКСИМУМ!)'}
        }
        
        # Повідомлення
        self.MESSAGES = {
            'start': """🌤️ Вітаємо в "Погода без сюрпризів"!

🎯 Наші можливості:
• Точні прогнози погоди на 2-6 днів
• Детальна якість повітря з рекомендаціями
• Температура по частинах доби
• Фаза місяця та час сходу/заходу сонця

💫 Тарифи:
⭐ 1 зірка = 2 дні
⭐⭐ 2 зірки = 3 дні
⭐⭐⭐ 3 зірки = 4 дні
⭐⭐⭐⭐ 4 зірки = 5 днів
⭐⭐⭐⭐⭐ 5 зірок = 6 днів

🚀 Почніть з команди /weather""",
            
            'weather_menu': """🌤️ Оберіть тариф прогнозу погоди:

⭐ 1 зірка = 2 дні (сьогодні + завтра)
⭐⭐ 2 зірки = 3 дні
⭐⭐⭐ 3 зірки = 4 дні
⭐⭐⭐⭐ 4 зірки = 5 днів
⭐⭐⭐⭐⭐ 5 зірок = 6 днів (МАКСИМУМ!)

🎯 Виберіть потрібний тариф:""",
            
            'payment_success': "✅ Оплату {stars} зірок успішно проведено!\n\n💫 Ви придбали прогноз погоди на {days} днів!\n\n📍 Наступний крок: Надішліть вашу геолокацію або напишіть назву міста.\n\n🎯 Ви отримаєте найдетальніший прогноз з усіма можливими даними!",
            
            'processing': "🔄 Обробляємо вашу геолокацію та отримуємо прогноз погоди...",
            
            'no_payment': "❌ Спочатку оплатіть прогноз командою /weather",
            
            'weather_error': "❌ Помилка отримання даних про погоду. Спробуйте пізніше або зверніться до підтримки.",
            
            'forecast_ready': "🎉 Прогноз готовий! Оберіть наступну дію:"
        }
        
        # Call-to-action повідомлення
        self.CALL_TO_ACTIONS = [
            f"🎯 Точні прогнози без сюрпризів! {self.BOT_USERNAME}",
            f"⭐ Детальна погода за зірки! {self.BOT_USERNAME}",
            f"🌤️ Професійні прогнози тут: {self.BOT_USERNAME}",
            f"💫 Погода без сюрпризів: {self.BOT_USERNAME}",
            f"🔮 Максимально детальні прогнози: {self.BOT_USERNAME}",
            f"🌟 Найточніші прогнози: {self.BOT_USERNAME}"
        ]
        
        # Назви днів
        self.DAY_NAMES = ['СЬОГОДНІ', 'ЗАВТРА', 'ПІСЛЯЗАВТРА', 'ЧЕРЕЗ 3 ДНІ', 'ЧЕРЕЗ 4 ДНІ', 'ЧЕРЕЗ 5 ДНІВ']
        
        # Індекс якості повітря
        self.AQI_LABELS = {
            1: 'Добра 🟢',
            2: 'Задовільна 🟡', 
            3: 'Помірна 🟠',
            4: 'Погана 🔴',
            5: 'Дуже погана 🟣'
        }
    
    def get_pricing_plan(self, stars):
        """Отримання тарифного плану"""
        return self.PRICING_PLANS.get(stars)
    
    def validate_config(self):
        """Перевірка конфігурації"""
        errors = []
        
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN not set")
        
        if not self.OPENWEATHER_API_KEY:
            errors.append("OPENWEATHER_API_KEY not set")
            
        if not self.WEBHOOK_URL:
            errors.append("WEBHOOK_URL not set")
        
        return len(errors) == 0, errors
