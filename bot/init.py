"""
Weather Bot Package

Модульний Telegram бот для прогнозу погоди з системою платежів Telegram Stars.

Модулі:
- handlers: Обробка Telegram оновлень
- weather: Робота з Weather API
- payments: Обробка платежів
- database: Робота з базою даних
"""

from .handlers import TelegramHandlers
from .weather import WeatherService
from .payments import PaymentService
from .database import DatabaseService

__version__ = "1.0.0"
__author__ = "Weather Bot Team"

# Експорт основних класів
__all__ = [
    'TelegramHandlers',
    'WeatherService', 
    'PaymentService',
    'DatabaseService'
]
