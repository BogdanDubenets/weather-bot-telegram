import requests
import logging
import math
from datetime import datetime

logger = logging.getLogger(__name__)

class WeatherService:
    """Сервіс для роботи з Weather API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    def get_forecast(self, lat, lon):
        """Отримання прогнозу погоди та якості повітря"""
        try:
            logger.info(f"🌤️ Getting weather forecast for coordinates: {lat}, {lon}")
            
            # Отримання прогнозу погоди
            forecast_data = self._get_weather_forecast(lat, lon)
            if not forecast_data:
                return None
            
            # Отримання якості повітря
            air_quality_data = self._get_air_quality(lat, lon)
            if not air_quality_data:
                return None
            
            logger.info("✅ Weather data retrieved successfully")
            return {
                'forecast': forecast_data,
                'air_quality': air_quality_data
            }
            
        except Exception as e:
            logger.error(f"❌ Weather service exception: {e}")
            return None
    
    def _get_weather_forecast(self, lat, lon):
        """Отримання 5-денного прогнозу"""
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'units': 'metric',
                'lang': 'uk',
                'appid': self.api_key
            }
            
            logger.info(f"📡 Making forecast API request to: {url}")
            logger.info(f"🔑 Using API key: {self.api_key[:10]}..." if self.api_key else "❌ No API key")
            
            response = requests.get(url, params=params, timeout=15)
            logger.info(f"📡 Forecast API response status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Forecast API error: {response.status_code}")
                logger.error(f"❌ Forecast API response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Forecast API exception: {e}")
            return None
    
    def _get_air_quality(self, lat, lon):
        """Отримання якості повітря"""
        try:
            url = f"{self.base_url}/air_pollution"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key
            }
            
            logger.info(f"📡 Making air quality API request")
            response = requests.get(url, params=params, timeout=15)
            logger.info(f"📡 Air quality API response status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Air quality API error: {response.status_code}")
                logger.error(f"❌ Air quality API response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Air quality API exception: {e}")
            return None
    
    def get_moon_phase(self):
        """Розрахунок фази місяця"""
        try:
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
                
        except Exception as e:
            logger.error(f"❌ Moon phase calculation error: {e}")
            return {"phase": "Невідома", "icon": "🌙"}
    
    def create_weather_messages(self, weather_data, stars_count, config):
        """Створення повідомлень з прогнозом погоды"""
        try:
            logger.info(f"📊 Creating weather messages for {stars_count} stars")
            messages = []
            
            forecast_data = weather_data['forecast']
            air_data = weather_data['air_quality']
            
            # Основна інформація
            city_name = forecast_data['city']['name']
            timezone_offset = forecast_data['city']['timezone'] // 3600
            moon_info = self.get_moon_phase()
            
            # Якість повітря
            air_quality = air_data['list'][0]
            aqi_status = config.AQI_LABELS.get(air_quality['main']['aqi'], 'Невідома')
            
            # Час сходу/заходу сонця
            sunrise_timestamp = forecast_data['city']['sunrise'] + forecast_data['city']['timezone']
            sunset_timestamp = forecast_data['city']['sunset'] + forecast_data['city']['timezone']
            
            sunrise_time = datetime.fromtimestamp(sunrise_timestamp).strftime('%H:%M')
            sunset_time = datetime.fromtimestamp(sunset_timestamp).strftime('%H:%M')
            
            # Заголовне повідомлення
            header_message = self._create_header_message(
                city_name, timezone_offset, moon_info, aqi_status, 
                air_quality, sunrise_time, sunset_time, config
            )
            messages.append(header_message)
            
            # Повідомлення по днях
            plan = config.get_pricing_plan(stars_count)
            days_to_show = plan['days'] if plan else 2
            
            daily_messages = self._create_daily_messages(
                forecast_data, air_quality, aqi_status, moon_info, 
                days_to_show, config
            )
            messages.extend(daily_messages)
            
            # Завершальне повідомлення
            final_message = self._create_final_message(city_name, days_to_show)
            messages.append(final_message)
            
            logger.info(f"✅ Created {len(messages)} weather messages")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error creating weather messages: {e}")
            return []
    
    def _create_header_message(self, city_name, timezone_offset, moon_info, aqi_status, air_quality, sunrise_time, sunset_time, config):
        """Створення заголовного повідомлення"""
        return f"""🌤️ ПРОГНОЗ ПОГОДИ ОТРИМАНО!

📍 Локація: {city_name}, Україна
🕐 Часовий пояс: UTC{'+' if timezone_offset >= 0 else ''}{timezone_offset}
{moon_info['icon']} Фаза місяця: {moon_info['phase']}

🌬️ ЯКІСТЬ ПОВІТРЯ: {aqi_status}
✅ PM2.5: {air_quality['components']['pm2_5']} мкг/м³
✅ O3: {air_quality['components']['o3']} мкг/м³

🌅 Схід: {sunrise_time} | 🌇 Захід: {sunset_time}

📊 Детальний прогноз надходить окремими повідомленнями...

🔗 Хочете такий же прогноз? {config.BOT_USERNAME}"""
    
    def _create_daily_messages(self, forecast_data, air_quality, aqi_status, moon_info, days_to_show, config):
        """Створення щоденних повідомлень прогнозу"""
        messages = []
        
        for day_index in range(min(days_to_show, len(config.DAY_NAMES))):
            day_name = config.DAY_NAMES[day_index]
            
            # Беремо дані з прогнозу (кожні 8 записів = 1 день)
            forecast_index = day_index * 8
            if forecast_index < len(forecast_data['list']):
                forecast_item = forecast_data['list'][forecast_index]
                
                temp = round(forecast_item['main']['temp'])
                feels_like = round(forecast_item['main']['feels_like'])
                description = forecast_item['weather'][0]['description']
                humidity = forecast_item['main']['humidity']
                wind_speed = forecast_item['wind']['speed']
                pressure = forecast_item['main']['pressure']
                
                # Додаткові дані
                temp_min = round(forecast_item['main']['temp_min'])
                temp_max = round(forecast_item['main']['temp_max'])
                clouds = forecast_item['clouds']['all']
                
                # Call-to-action для цього дня
                cta = config.CALL_TO_ACTIONS[day_index % len(config.CALL_TO_ACTIONS)]
                
                day_message = f"""📅 {day_name}
{moon_info['icon']} Фаза місяця: {moon_info['phase']}

🌬️ ЯКІСТЬ ПОВІТРЯ: {aqi_status}
✅ PM2.5: {air_quality['components']['pm2_5']} мкг/м³
✅ O3: {air_quality['components']['o3']} мкг/м³

🌡️ ТЕМПЕРАТУРА: {temp}°C (відчув. {feels_like}°C)
   📈 Мін: {temp_min}°C | Макс: {temp_max}°C
   {description}

💧 Вологість: {humidity}%
💨 Вітер: {wind_speed} м/с
🔽 Тиск: {pressure} гПа
☁️ Хмарність: {clouds}%

{cta}"""
                
                messages.append(day_message)
        
        return messages
    
    def _create_final_message(self, city_name, days_count):
        """Створення завершального повідомлення"""
        return f"""✅ ПРОГНОЗ ПОГОДИ ЗАВЕРШЕНО!

🎯 Ви отримали детальний прогноз на {days_count} днів для:
📍 {city_name}, Україна

💡 ХОЧЕТЕ НОВИЙ ПРОГНОЗ?

🔄 Якщо ви залишаєтесь у тому ж місці:
• У вас уже є актуальний прогноз на найближчі дні
• Рекомендуємо замовляти новий прогноз через 2-3 дні

🌍 Якщо ви змінили локацію:
• Можете замовити прогноз для нового місця прямо зараз

🛍️ Готові замовити новий прогноз?"""
    
    def validate_coordinates(self, lat, lon):
        """Валідація координат"""
        try:
            lat = float(lat)
            lon = float(lon)
            
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return True, lat, lon
            else:
                return False, None, None
        except (ValueError, TypeError):
            return False, None, None
    
    def get_weather_summary(self, weather_data):
        """Короткий огляд погоди для статистики"""
        try:
            forecast = weather_data['forecast']
            current = forecast['list'][0]
            
            return {
                'city': forecast['city']['name'],
                'temperature': round(current['main']['temp']),
                'description': current['weather'][0]['description'],
                'humidity': current['main']['humidity'],
                'wind_speed': current['wind']['speed']
            }
        except Exception as e:
            logger.error(f"❌ Error creating weather summary: {e}")
            return None
