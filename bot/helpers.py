"""
Допоміжні функції для Weather Bot
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import hashlib
import json

logger = logging.getLogger(__name__)

def format_timestamp(timestamp: str, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """Форматування часової мітки"""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime(format_str)
    except Exception as e:
        logger.error(f"❌ Format timestamp error: {e}")
        return timestamp

def validate_coordinates(lat: float, lon: float) -> bool:
    """Валідація координат"""
    try:
        return -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180
    except (ValueError, TypeError):
        return False

def sanitize_text(text: str, max_length: int = 4000) -> str:
    """Очищення тексту для Telegram"""
    if not text:
        return ""
    
    # Видалення проблемних символів
    text = re.sub(r'[^\w\s\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]', '', text, flags=re.UNICODE)
    
    # Обмеження довжини
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    return text

def create_user_hash(user_id: int) -> str:
    """Створення хешу користувача для анонімізації"""
    try:
        return hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
    except Exception:
        return "unknown"

def parse_callback_data(callback_data: str) -> Dict[str, Any]:
    """Парсинг callback_data"""
    try:
        parts = callback_data.split('_')
        
        if len(parts) >= 3 and parts[0] == 'weather' and parts[1] == 'stars':
            return {
                'action': 'weather_order',
                'stars': int(parts[2]),
                'valid': True
            }
        
        return {
            'action': callback_data,
            'valid': False
        }
        
    except Exception as e:
        logger.error(f"❌ Parse callback data error: {e}")
        return {'action': callback_data, 'valid': False}

def calculate_time_ago(timestamp: str) -> str:
    """Розрахунок часу, що минув"""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} днів тому"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} годин тому"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} хвилин тому"
        else:
            return "щойно"
            
    except Exception as e:
        logger.error(f"❌ Calculate time ago error: {e}")
        return "невідомо"

def format_weather_emoji(weather_code: int, is_day: bool = True) -> str:
    """Форматування емодзі погоди за кодом"""
    weather_emojis = {
        # Ясно
        800: "☀️" if is_day else "🌙",
        # Хмари
        801: "🌤️" if is_day else "☁️",
        802: "⛅",
        803: "☁️",
        804: "☁️",
        # Дощ
        500: "🌦️",
        501: "🌧️",
        502: "🌧️",
        503: "⛈️",
        504: "⛈️",
        # Сніг
        600: "🌨️",
        601: "❄️",
        602: "❄️",
        # Туман
        701: "🌫️",
        # Гроза
        200: "⛈️",
        201: "⛈️",
        202: "⚡",
    }
    
    return weather_emojis.get(weather_code, "🌤️")

def format_currency(amount: int, currency: str = "stars") -> str:
    """Форматування валюти"""
    if currency == "stars":
        star_emoji = "⭐" * min(amount, 5)
        return f"{star_emoji} {amount}"
    return str(amount)

def truncate_text(text: str, max_length: int = 50) -> str:
    """Скорочення тексту з многоточием"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def validate_user_input(text: str, input_type: str = "general") -> Tuple[bool, str]:
    """Валідація введення користувача"""
    if not text or not text.strip():
        return False, "Порожнє введення"
    
    text = text.strip()
    
    if input_type == "city":
        # Перевірка назви міста
        if len(text) < 2 or len(text) > 50:
            return False, "Некоректна довжина назви міста"
        
        if not re.match(r'^[a-zA-Zа-яА-ЯіІїЇєЄґҐ\s\-\']+$', text):
            return False, "Некоректні символи в назві міста"
            
    elif input_type == "username":
        # Перевірка username
        if not re.match(r'^[a-zA-Z0-9_]{3,32}$', text):
            return False, "Некоректний формат username"
    
    return True, text

def create_error_report(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Створення звіту про помилку"""
    import traceback
    
    report = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.now().isoformat(),
        'stack_trace': traceback.format_exc()
    }
    
    if context:
        report['context'] = context
    
    return report

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Безпечне завантаження JSON"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """Безпечне серіалізування в JSON"""
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return default

def calculate_forecast_accuracy(predicted_temp: float, actual_temp: float) -> float:
    """Розрахунок точності прогнозу"""
    try:
        diff = abs(predicted_temp - actual_temp)
        accuracy = max(0, 100 - (diff * 10))  # 1°C різниця = -10% точності
        return round(accuracy, 2)
    except Exception:
        return 0.0

def generate_order_id(user_id: int, timestamp: str = None) -> str:
    """Генерація унікального ID замовлення"""
    if not timestamp:
        timestamp = datetime.now().isoformat()
    
    data = f"{user_id}_{timestamp}"
    return hashlib.md5(data.encode()).hexdigest()[:12].upper()

def parse_location_name(location_data: Dict[str, Any]) -> str:
    """Парсинг назви локації з даних"""
    try:
        if 'name' in location_data:
            return location_data['name']
        elif 'city' in location_data:
            return location_data['city']['name']
        elif 'address' in location_data:
            return location_data['address']
        else:
            return "Невідома локація"
    except Exception:
        return "Невідома локація"

def format_file_size(size_bytes: int) -> str:
    """Форматування розміру файлу"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Маскування чутливих даних"""
    if len(data) <= visible_chars * 2:
        return "*" * len(data)
    
    visible_start = data[:visible_chars]
    visible_end = data[-visible_chars:]
    masked_middle = "*" * (len(data) - visible_chars * 2)
    
    return f"{visible_start}{masked_middle}{visible_end}"

def is_business_hours(timezone_offset: int = 0) -> bool:
    """Перевірка робочих годин (9:00 - 18:00)"""
    try:
        now = datetime.now()
        # Врахування часового поясу
        local_time = now + timedelta(hours=timezone_offset)
        hour = local_time.hour
        
        return 9 <= hour < 18
    except Exception:
        return True  # За замовчуванням вважаємо робочими годинами

def create_debug_info() -> Dict[str, Any]:
    """Створення діагностичної інформації"""
    import sys
    import platform
    
    return {
        'python_version': sys.version,
        'platform': platform.platform(),
        'timestamp': datetime.now().isoformat(),
        'memory_usage': sys.getsizeof(globals())
    }
