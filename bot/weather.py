import requests
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class WeatherService:
    """Розширений сервіс для роботи з Weather API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    def get_comprehensive_forecast(self, lat: float, lon: float) -> Optional[Dict]:
        """Отримання повного прогнозу з усіх доступних API"""
        try:
            logger.info(f"🌤️ Getting comprehensive weather forecast for: {lat}, {lon}")
            
            # Паралельне отримання всіх даних
            current_weather = self._get_current_weather(lat, lon)
            forecast_5day = self._get_5day_forecast(lat, lon) 
            air_quality = self._get_air_quality(lat, lon)
            uv_index = self._get_uv_index(lat, lon)
            
            if not current_weather or not forecast_5day:
                logger.error("❌ Failed to get essential weather data")
                return None
            
            # Об'єднання всіх даних
            comprehensive_data = {
                'current': current_weather,
                'forecast': forecast_5day,
                'air_quality': air_quality,
                'uv_index': uv_index,
                'location_info': {
                    'lat': lat,
                    'lon': lon,
                    'city': forecast_5day.get('city', {}).get('name', 'Unknown'),
                    'country': forecast_5day.get('city', {}).get('country', 'Unknown')
                }
            }
            
            logger.info("✅ Comprehensive weather data retrieved successfully")
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"❌ Comprehensive forecast error: {e}")
            return None
    
    def _get_current_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """Отримання поточної погоди"""
        try:
            url = f"{self.base_url}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'units': 'metric',
                'lang': 'uk',
                'appid': self.api_key
            }
            
            logger.info("📡 Getting current weather data")
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Current weather API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Current weather exception: {e}")
            return None
    
    def _get_5day_forecast(self, lat: float, lon: float) -> Optional[Dict]:
        """Отримання 5-денного прогнозу з 3-годинними інтервалами"""
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'units': 'metric',
                'lang': 'uk',
                'appid': self.api_key
            }
            
            logger.info("📡 Getting 5-day forecast data")
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ 5-day forecast API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 5-day forecast exception: {e}")
            return None
    
    def _get_air_quality(self, lat: float, lon: float) -> Optional[Dict]:
        """Отримання даних якості повітря"""
        try:
            url = f"{self.base_url}/air_pollution"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key
            }
            
            logger.info("📡 Getting air quality data")
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Air quality API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Air quality exception: {e}")
            return None
    
    def _get_uv_index(self, lat: float, lon: float) -> Optional[Dict]:
        """Отримання УФ-індексу (з поточної погоди, оскільки окремий UV API платний)"""
        try:
            # УФ-індекс можна отримати з поточної погоди
            current = self._get_current_weather(lat, lon)
            if current and 'uvi' in current:
                return {'current': current['uvi']}
            return None
        except Exception as e:
            logger.error(f"❌ UV index exception: {e}")
            return None
    
    def create_detailed_weather_messages(self, weather_data: Dict, stars_count: int, config) -> List[str]:
        """Створення детальних повідомлень з прогнозом"""
        try:
            logger.info(f"📊 Creating detailed weather messages for {stars_count} stars")
            messages = []
            
            current = weather_data['current']
            forecast = weather_data['forecast']
            air_quality = weather_data.get('air_quality')
            location = weather_data['location_info']
            
            # Заголовне повідомлення з поточною погодою
            header_message = self._create_current_weather_message(current, location, air_quality, config)
            messages.append(header_message)
            
            # Детальні прогнози по днях з розбивкою на частини доби
            plan = config.get_pricing_plan(stars_count)
            days_to_show = plan['days'] if plan else 2
            
            daily_forecasts = self._create_detailed_daily_forecasts(
                forecast, air_quality, days_to_show, config
            )
            messages.extend(daily_forecasts)
            
            # Додаткова інформація (тільки для тарифів 3+ зірки)
            if stars_count >= 3:
                additional_info = self._create_additional_info_message(weather_data, config)
                if additional_info:
                    messages.append(additional_info)
            
            # Завершальне повідомлення
            final_message = self._create_comprehensive_final_message(location['city'], days_to_show, stars_count)
            messages.append(final_message)
            
            logger.info(f"✅ Created {len(messages)} detailed weather messages")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error creating detailed weather messages: {e}")
            return []
    
    def _create_current_weather_message(self, current: Dict, location: Dict, air_quality: Optional[Dict], config) -> str:
        """Створення повідомлення з поточною погодою"""
        try:
            city_name = location['city']
            country = location['country']
            
            # Поточна температура та відчуття
            temp = round(current['main']['temp'])
            feels_like = round(current['main']['feels_like'])
            temp_min = round(current['main']['temp_min'])
            temp_max = round(current['main']['temp_max'])
            
            # Опис погоди
            description = current['weather'][0]['description'].title()
            weather_icon = self._get_weather_emoji(current['weather'][0]['id'])
            
            # Додаткові параметри
            humidity = current['main']['humidity']
            pressure = current['main']['pressure']
            wind_speed = current['wind']['speed']
            wind_deg = current['wind'].get('deg', 0)
            wind_direction = self._get_wind_direction(wind_deg)
            visibility = current.get('visibility', 0) // 1000  # км
            cloudiness = current['clouds']['all']
            
            # Схід/захід сонця
            sunrise = datetime.fromtimestamp(current['sys']['sunrise']).strftime('%H:%M')
            sunset = datetime.fromtimestamp(current['sys']['sunset']).strftime('%H:%M')
            
            # Фаза місяця
            moon_info = self.get_moon_phase()
            
            # Якість повітря
            air_info = ""
            if air_quality:
                aqi = air_quality['list'][0]['main']['aqi']
                aqi_status = config.AQI_LABELS.get(aqi, 'Невідома')
                pm25 = air_quality['list'][0]['components']['pm2_5']
                pm10 = air_quality['list'][0]['components']['pm10']
                
                air_info = f"""
🌬️ ЯКІСТЬ ПОВІТРЯ: {aqi_status}
✅ PM2.5: {pm25} мкг/м³ | PM10: {pm10} мкг/м³"""
            
            return f"""{weather_icon} ПОТОЧНА ПОГОДА

📍 {city_name}, {country}
🕐 Станом на {datetime.now().strftime('%H:%M, %d.%m.%Y')}

🌡️ ТЕМПЕРАТУРА
   Зараз: {temp}°C (відчув. {feels_like}°C)
   Мін/Макс: {temp_min}°C / {temp_max}°C
   {description}

🌪️ ВІТЕР ТА АТМОСФЕРА
   💨 Швидкість: {wind_speed} м/с ({wind_direction})
   🔽 Тиск: {pressure} гПа
   💧 Вологість: {humidity}%
   👁️ Видимість: {visibility} км
   ☁️ Хмарність: {cloudiness}%{air_info}

🌅 СОНЦЕ ТА МІСЯЦЬ
   Схід: {sunrise} | Захід: {sunset}
   {moon_info['icon']} {moon_info['phase']}

📊 Детальний прогноз на кілька днів надходить..."""
            
        except Exception as e:
            logger.error(f"❌ Error creating current weather message: {e}")
            return "❌ Помилка створення повідомлення про поточну погоду"
    
    def _create_detailed_daily_forecasts(self, forecast: Dict, air_quality: Optional[Dict], days_to_show: int, config) -> List[str]:
        """Створення детальних щоденних прогнозів з розбивкою на частини доби"""
        messages = []
        
        try:
            # Групуємо прогнози по днях
            daily_forecasts = self._group_forecasts_by_day(forecast['list'])
            
            day_names = config.DAY_NAMES[:days_to_show]
            
            for day_index, day_name in enumerate(day_names):
                if day_index < len(daily_forecasts):
                    day_data = daily_forecasts[day_index]
                    
                    # Розбиваємо день на частини
                    periods = self._split_day_into_periods(day_data)
                    
                    # Створюємо повідомлення для дня
                    day_message = self._create_single_day_message(day_name, periods, air_quality, config, day_index)
                    messages.append(day_message)
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error creating daily forecasts: {e}")
            return []
    
    def _group_forecasts_by_day(self, forecast_list: List[Dict]) -> List[List[Dict]]:
        """Групування прогнозів по днях"""
        daily_forecasts = []
        current_day = None
        day_forecasts = []
        
        for forecast in forecast_list:
            forecast_date = datetime.fromtimestamp(forecast['dt']).date()
            
            if current_day != forecast_date:
                if day_forecasts:
                    daily_forecasts.append(day_forecasts)
                day_forecasts = [forecast]
                current_day = forecast_date
            else:
                day_forecasts.append(forecast)
        
        if day_forecasts:
            daily_forecasts.append(day_forecasts)
        
        return daily_forecasts
    
    def _split_day_into_periods(self, day_forecasts: List[Dict]) -> Dict[str, Dict]:
        """Розбиття дня на періоди: ніч, ранок, день, вечір"""
        periods = {
            'night': None,      # 00:00-06:00
            'morning': None,    # 06:00-12:00  
            'day': None,        # 12:00-18:00
            'evening': None     # 18:00-24:00
        }
        
        for forecast in day_forecasts:
            hour = datetime.fromtimestamp(forecast['dt']).hour
            
            if 0 <= hour < 6:
                if not periods['night']:
                    periods['night'] = forecast
            elif 6 <= hour < 12:
                if not periods['morning']:
                    periods['morning'] = forecast
            elif 12 <= hour < 18:
                if not periods['day']:
                    periods['day'] = forecast
            else:  # 18-24
                if not periods['evening']:
                    periods['evening'] = forecast
        
        return periods
    
    def _create_single_day_message(self, day_name: str, periods: Dict, air_quality: Optional[Dict], config, day_index: int) -> str:
        """Створення повідомлення для одного дня з розбивкою на періоди"""
        try:
            # Загальна інформація про день
            day_temps = []
            descriptions = []
            
            for period_name, period_data in periods.items():
                if period_data:
                    day_temps.append(period_data['main']['temp'])
                    descriptions.append(period_data['weather'][0]['description'])
            
            if not day_temps:
                return f"📅 {day_name}\n❌ Немає даних для цього дня"
            
            min_temp = round(min(day_temps))
            max_temp = round(max(day_temps))
            main_description = max(set(descriptions), key=descriptions.count).title()
            
            # Детальна розбивка по періодам
            period_details = []
            period_names = {
                'night': '🌙 Ніч (00-06)',
                'morning': '🌅 Ранок (06-12)', 
                'day': '☀️ День (12-18)',
                'evening': '🌆 Вечір (18-24)'
            }
            
            for period_key, period_name in period_names.items():
                period_data = periods.get(period_key)
                if period_data:
                    temp = round(period_data['main']['temp'])
                    feels_like = round(period_data['main']['feels_like'])
                    humidity = period_data['main']['humidity']
                    wind_speed = period_data['wind']['speed']
                    description = period_data['weather'][0]['description']
                    
                    # Опади
                    rain_info = ""
                    if 'rain' in period_data:
                        rain_3h = period_data['rain'].get('3h', 0)
                        if rain_3h > 0:
                            rain_info = f" 🌧️ {rain_3h}мм"
                    
                    snow_info = ""
                    if 'snow' in period_data:
                        snow_3h = period_data['snow'].get('3h', 0)
                        if snow_3h > 0:
                            snow_info = f" ❄️ {snow_3h}мм"
                    
                    period_detail = f"""   {period_name}: {temp}°C (відчув. {feels_like}°C)
      {description}, вологість {humidity}%, вітер {wind_speed} м/с{rain_info}{snow_info}"""
                    
                    period_details.append(period_detail)
            
            # Якість повітря для дня
            air_info = ""
            if air_quality:
                aqi = air_quality['list'][0]['main']['aqi']
                aqi_status = config.AQI_LABELS.get(aqi, 'Невідома')
                air_info = f"\n🌬️ Якість повітря: {aqi_status}"
            
            # Call-to-action
            cta = config.CALL_TO_ACTIONS[day_index % len(config.CALL_TO_ACTIONS)]
            
            return f"""📅 {day_name.upper()}
🌡️ {min_temp}°C — {max_temp}°C | {main_description}{air_info}

🕐 ДЕТАЛЬНО ПО ПЕРІОДАХ:
{chr(10).join(period_details)}

{cta}"""
            
        except Exception as e:
            logger.error(f"❌ Error creating single day message: {e}")
            return f"📅 {day_name}\n❌ Помилка створення прогнозу"
    
    def _create_additional_info_message(self, weather_data: Dict, config) -> Optional[str]:
        """Створення додаткової інформації (для преміум тарифів)"""
        try:
            current = weather_data['current']
            location = weather_data['location_info']
            
            # Розрахунок додаткових параметрів
            dew_point = self._calculate_dew_point(
                current['main']['temp'], 
                current['main']['humidity']
            )
            
            heat_index = self._calculate_heat_index(
                current['main']['temp'],
                current['main']['humidity']
            )
            
            # Рекомендації
            recommendations = self._generate_weather_recommendations(current, weather_data.get('air_quality'))
            
            return f"""📊 ДОДАТКОВА ІНФОРМАЦІЯ

🧮 РОЗРАХУНКОВІ ПАРАМЕТРИ:
   🌡️ Точка роси: {dew_point:.1f}°C
   🔥 Індекс спеки: {heat_index:.1f}°C
   
💡 РЕКОМЕНДАЦІЇ:
{recommendations}

📈 ТЕНДЕНЦІЇ:
   Погода поступово змінюється протягом наступних днів.
   Стежте за оновленнями прогнозу.

🔬 Дані надані OpenWeatherMap API
📱 Детальніші прогнози: {config.BOT_USERNAME}"""
            
        except Exception as e:
            logger.error(f"❌ Error creating additional info: {e}")
            return None
    
    def _create_comprehensive_final_message(self, city_name: str, days_count: int, stars_count: int) -> str:
        """Створення завершального повідомлення"""
        return f"""✅ ПОВНИЙ ПРОГНОЗ ЗАВЕРШЕНО!

🎯 Ви отримали максимально детальний прогноз:
📍 Локація: {city_name}
📅 Період: {days_count} днів
⭐ Тариф: {stars_count} зірок
🕐 Розбивка: по періодах доби (ніч/ранок/день/вечір)

💡 КОРИСНІ ПОРАДИ:
🔄 Для того ж місця рекомендуємо оновлювати прогноз кожні 2-3 дні
🌍 Для іншої локації можете замовити новий прогноз
📱 Зберігайте повідомлення для офлайн-перегляду

🌟 Дякуємо за довіру до нашого сервісу!"""
    
    def _get_weather_emoji(self, weather_code: int) -> str:
        """Отримання емодзі за кодом погоди"""
        weather_emojis = {
            # Ясно
            800: "☀️",
            # Хмари
            801: "🌤️", 802: "⛅", 803: "☁️", 804: "☁️",
            # Дощ
            500: "🌦️", 501: "🌧️", 502: "🌧️", 503: "⛈️", 504: "⛈️",
            520: "🌦️", 521: "🌧️", 522: "🌧️", 531: "🌧️",
            # Дрібний дощ
            300: "🌦️", 301: "🌦️", 302: "🌧️", 310: "🌦️", 311: "🌧️", 312: "🌧️",
            # Сніг
            600: "🌨️", 601: "❄️", 602: "❄️", 611: "🌨️", 612: "🌨️", 613: "🌨️",
            615: "🌨️", 616: "🌨️", 620: "🌨️", 621: "❄️", 622: "❄️",
            # Туман
            701: "🌫️", 711: "🌫️", 721: "🌫️", 731: "🌫️", 741: "🌫️", 751: "🌫️", 761: "🌫️", 762: "🌋", 771: "💨", 781: "🌪️",
            # Гроза
            200: "⛈️", 201: "⛈️", 202: "⚡", 210: "🌩️", 211: "⛈️", 212: "⚡", 221: "⛈️", 230: "⛈️", 231: "⛈️", 232: "⚡"
        }
        return weather_emojis.get(weather_code, "🌤️")
    
    def _get_wind_direction(self, degrees: int) -> str:
        """Визначення напрямку вітру"""
        directions = [
            "Півн", "ПнПнСх", "ПнСх", "СхПнСх", 
            "Сх", "СхПдСх", "ПдСх", "ПдПдСх",
            "Пд", "ПдПдЗх", "ПдЗх", "ЗхПдЗх", 
            "Зх", "ЗхПнЗх", "ПнЗх", "ПнПнЗх"
        ]
        index = round(degrees / 22.5) % 16
        return directions[index]
    
    def _calculate_dew_point(self, temp: float, humidity: int) -> float:
        """Розрахунок точки роси"""
        try:
            a = 17.27
            b = 237.7
            alpha = ((a * temp) / (b + temp)) + math.log(humidity / 100.0)
            return (b * alpha) / (a - alpha)
        except Exception:
            return temp - 10  # Приблизна оцінка
    
    def _calculate_heat_index(self, temp: float, humidity: int) -> float:
        """Розрахунок індексу спеки"""
        try:
            if temp < 27:  # Індекс спеки актуальний тільки при високих температурах
                return temp
            
            # Спрощена формула індексу спеки
            hi = temp + 0.5 * (temp - 20) * (humidity / 100)
            return max(temp, hi)
        except Exception:
            return temp
    
    def _generate_weather_recommendations(self, current: Dict, air_quality: Optional[Dict]) -> str:
        """Генерація рекомендацій на основі погодних умов"""
        recommendations = []
        
        temp = current['main']['temp']
        humidity = current['main']['humidity']
        wind_speed = current['wind']['speed']
        
        # Температурні рекомендації
        if temp < 0:
            recommendations.append("🧥 Одягайтесь тепло, ризик обмороження")
        elif temp < 10:
            recommendations.append("🧥 Рекомендуємо теплий одяг")
        elif temp > 30:
            recommendations.append("🌡️ Спекотно, пийте більше води")
        
        # Вологість
        if humidity > 80:
            recommendations.append("💧 Висока вологість, можливе відчуття духоти")
        elif humidity < 30:
            recommendations.append("🏜️ Низька вологість, зволожуйте повітря")
        
        # Вітер
        if wind_speed > 10:
            recommendations.append("💨 Сильний вітер, будьте обережні")
        
        # Якість повітря
        if air_quality:
            aqi = air_quality['list'][0]['main']['aqi']
            if aqi >= 4:
                recommendations.append("😷 Погана якість повітря, носіть маску")
            elif aqi >= 3:
                recommendations.append("🌬️ Помірна якість повітря, обмежте активність на вулиці")
        
        return "\n   ".join(recommendations) if recommendations else "✅ Погодні умови сприятливі"
    
    def get_moon_phase(self) -> Dict[str, str]:
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
