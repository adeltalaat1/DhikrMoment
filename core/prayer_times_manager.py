import os
import pygame
import requests
import json
from datetime import datetime, date, timedelta, time as time_obj 
from PyQt6.QtCore import Qt, QLocale, QRectF, pyqtSignal, QTimer # <<<--- إضافة QTimer هنا


class PrayerTimesManager:
    API_BASE_URL = "http://api.aladhan.com/v1"
    IP_GEOLOCATION_API_URL = "http://ip-api.com/json/"

    PRAYER_ORDER = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]
    # API_PRAYER_NAMES maps our internal keys to keys expected/returned by Aladhan API
    # This is useful if Aladhan API changes its keys slightly in the future.
    # For now, they are mostly the same.
    API_PRAYER_NAMES = { 
        "Fajr": "Fajr", "Sunrise": "Sunrise", "Dhuhr": "Dhuhr", "Asr": "Asr",
        "Sunset": "Sunset", "Maghrib": "Maghrib", "Isha": "Isha", "Imsak": "Imsak",
        "Midnight": "Midnight" 
    }

    def __init__(self, settings_manager, lm):
        self.settings_mngr = settings_manager
        self.lm = lm 
        self.daily_prayer_times_data = {} 
        self.last_fetched_date = None
        self.auto_location_data = None 
        print("DEBUG: PrayerTimesManager initialized.")
        self.prayer_alert_timers = {} # لتخزين مؤقتات التنبيهات النشطة
        self.adhan_timers = {} # لتخزين مؤقتات الأذان
        
        
    def schedule_prayer_related_alerts(self):
        if not self.settings_mngr.get("prayer_times_active", False):
            self.cancel_all_scheduled_alerts()
            return

        timings = self.get_todays_timings_dict()
        if not timings:
            return

        now = datetime.now()
        today_date = now.date()

        # إلغاء أي مؤقتات مجدولة سابقة
        self.cancel_all_scheduled_alerts()

        for prayer_key in self.PRAYER_ORDER: # Fajr, Dhuhr, Asr, Maghrib, Isha
            time_str_raw = timings.get(prayer_key)
            if not time_str_raw:
                continue

            try:
                time_str = time_str_raw.split(" ")[0]
                prayer_time_obj = datetime.strptime(time_str, "%H:%M").time()
                prayer_datetime = datetime.combine(today_date, prayer_time_obj)

                # 1. جدولة الأذان
                if prayer_datetime > now:
                    adhan_sound_file = self._get_adhan_sound_for_prayer(prayer_key)
                    if adhan_sound_file:
                        ms_until_adhan = int((prayer_datetime - now).total_seconds() * 1000)
                        if ms_until_adhan > 0:
                            timer_id = f"adhan_{prayer_key}"
                            self.adhan_timers[timer_id] = QTimer()
                            self.adhan_timers[timer_id].setSingleShot(True)
                            # ربط المؤقت بدالة تقوم بتشغيل الأذان
                            self.adhan_timers[timer_id].timeout.connect(
                                lambda p=prayer_key, snd=adhan_sound_file: self.play_adhan_alert(p, snd)
                            )
                            self.adhan_timers[timer_id].start(ms_until_adhan)
                            print(f"DEBUG: Scheduled Adhan for {prayer_key} in {ms_until_adhan / 1000 / 60:.1f} minutes.")

                # 2. جدولة التنبيه قبل الأذان
                if self.settings_mngr.get("pre_adhan_alert_active", False):
                    pre_minutes = self.settings_mngr.get("pre_adhan_minutes", 10)
                    pre_alert_datetime = prayer_datetime - timedelta(minutes=pre_minutes)
                    if pre_alert_datetime > now:
                        pre_sound_file = self.settings_mngr.get("pre_adhan_sound_file", "")
                        ms_until_pre_alert = int((pre_alert_datetime - now).total_seconds() * 1000)
                        if ms_until_pre_alert > 0:
                            timer_id = f"pre_adhan_{prayer_key}"
                            self.prayer_alert_timers[timer_id] = QTimer()
                            self.prayer_alert_timers[timer_id].setSingleShot(True)
                            self.prayer_alert_timers[timer_id].timeout.connect(
                                lambda p=prayer_key, snd=pre_sound_file: self.play_pre_post_alert("pre_adhan", p, snd)
                            )
                            self.prayer_alert_timers[timer_id].start(ms_until_pre_alert)
                            print(f"DEBUG: Scheduled Pre-Adhan alert for {prayer_key} in {ms_until_pre_alert / 1000 / 60:.1f} minutes.")
                
                # 3. جدولة تنبيه الإقامة بعد الأذان
                if self.settings_mngr.get("post_adhan_iqama_alert_active", False):
                    post_minutes = self.settings_mngr.get("post_adhan_iqama_minutes", 10)
                    post_alert_datetime = prayer_datetime + timedelta(minutes=post_minutes)
                    if post_alert_datetime > now: # يجب أن يكون أيضًا أقل من الصلاة التالية (أكثر تعقيدًا)
                        post_sound_file = self.settings_mngr.get("post_adhan_iqama_sound_file", "")
                        ms_until_post_alert = int((post_alert_datetime - now).total_seconds() * 1000)
                        if ms_until_post_alert > 0:
                            timer_id = f"post_adhan_{prayer_key}"
                            self.prayer_alert_timers[timer_id] = QTimer()
                            self.prayer_alert_timers[timer_id].setSingleShot(True)
                            self.prayer_alert_timers[timer_id].timeout.connect(
                                lambda p=prayer_key, snd=post_sound_file: self.play_pre_post_alert("post_adhan", p, snd)
                            )
                            self.prayer_alert_timers[timer_id].start(ms_until_post_alert)
                            print(f"DEBUG: Scheduled Post-Adhan alert for {prayer_key} in {ms_until_post_alert / 1000 / 60:.1f} minutes.")
            
            except ValueError:
                print(f"WARN: Could not parse time for scheduling alert for {prayer_key} ('{time_str_raw}')")
                continue

    def _get_adhan_sound_for_prayer(self, prayer_key):
        if self.settings_mngr.get("use_unified_adhan_sound", True):
            return self.settings_mngr.get("unified_adhan_sound_file", "")
        else:
            return self.settings_mngr.get(f"adhan_sound_{prayer_key.lower()}", "")

    def play_adhan_alert(self, prayer_name, sound_file):
        print(f"INFO: Playing Adhan for {prayer_name} using {sound_file}")
        # استخدم pygame.mixer لتشغيل sound_file
        # (نفس منطق play_sound_reminder ولكن بالملف المحدد)
        self._play_sound_with_pygame(sound_file, alert_type=f"Adhan for {prayer_name}")

    def play_pre_post_alert(self, alert_type_str, prayer_name, sound_file):
        print(f"INFO: Playing {alert_type_str} alert for {prayer_name} using {sound_file}")
        # استخدم pygame.mixer لتشغيل sound_file
        self._play_sound_with_pygame(sound_file, alert_type=f"{alert_type_str} for {prayer_name}")
        # يمكنك أيضًا إظهار إشعار نصي هنا
        # self.app.tray_manager.tray_icon.showMessage(...)

    def _play_sound_with_pygame(self, sound_file_name, alert_type="Generic Alert"):
        # دالة مساعدة لتشغيل الصوت باستخدام pygame (مشابهة لـ play_sound_reminder)
        if not self.is_pygame_mixer_initialized: # افترض أن لديك is_pygame_mixer_initialized
            print(f"ERROR: Pygame mixer not ready for {alert_type}.")
            return
        if not sound_file_name:
            print(f"INFO: No sound file specified for {alert_type}.")
            return

        audio_file_path = os.path.join(self.base_path, "resources", "audio", "adhan", sound_file_name)
        if not os.path.exists(audio_file_path):
            print(f"ERROR: Sound file not found for {alert_type}: {audio_file_path}")
            return
        try:
            if pygame.mixer.music.get_busy(): pygame.mixer.music.stop(); pygame.mixer.music.unload()
            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play()
            print(f"DEBUG: Playing {alert_type} sound: {sound_file_name}")
        except pygame.error as e:
            print(f"ERROR: Pygame error playing {alert_type} sound ({sound_file_name}): {e}")


    def cancel_all_scheduled_alerts(self):
        for timer_id, timer in self.prayer_alert_timers.items():
            timer.stop()
            print(f"DEBUG: Cancelled pre/post alert timer: {timer_id}")
        self.prayer_alert_timers.clear()

        for timer_id, timer in self.adhan_timers.items():
            timer.stop()
            print(f"DEBUG: Cancelled Adhan timer: {timer_id}")
        self.adhan_timers.clear()
        
    def _get_location_from_ip(self):
        if self.auto_location_data and self.auto_location_data.get("latitude") is not None: # Check if valid data exists
            print("INFO: PrayerTimes - Using cached IP geolocation data.")
            return self.auto_location_data
        
        print("INFO: PrayerTimes - Attempting to fetch location via IP geolocation...")
        try:
            response = requests.get(self.IP_GEOLOCATION_API_URL, params={'fields': 'status,message,country,city,lat,lon,timezone'}, timeout=7) 
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                self.auto_location_data = {
                    "city": data.get("city"),
                    "country": data.get("country"),
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                    "timezone": data.get("timezone")
                }
                print(f"INFO: PrayerTimes - IP Geolocation successful: {self.auto_location_data}")
                return self.auto_location_data
            else:
                print(f"ERROR: PrayerTimes - IP Geolocation API error: {data.get('message', 'Unknown error')}")
                self.auto_location_data = {} # Clear invalid cache
                return None
        except requests.exceptions.RequestException as e:
            print(f"ERROR: PrayerTimes - Network error during IP geolocation: {e}")
            self.auto_location_data = {}
            return None
        except json.JSONDecodeError:
            print("ERROR: PrayerTimes - Could not decode JSON response from IP Geolocation API.")
            self.auto_location_data = {}
            return None
        except Exception as e_gen_ip:
            print(f"ERROR: PrayerTimes - Unexpected error during IP geolocation: {e_gen_ip}")
            self.auto_location_data = {}
            return None

    def _get_api_params(self):
        params = {}
        loc_method_raw = self.settings_mngr.get("prayer_location_method", "auto_ip")
        loc_method = loc_method_raw.strip() if isinstance(loc_method_raw, str) else loc_method_raw
            
        print(f"DEBUG: PrayerTimes - _get_api_params - loc_method from settings (raw): '{loc_method_raw}', (stripped): '{loc_method}'")

        if loc_method == "auto_ip":
            print("DEBUG: PrayerTimes - loc_method IS 'auto_ip'. Attempting IP geolocation.")
            location_data = self._get_location_from_ip()
            if location_data and location_data.get("latitude") is not None and location_data.get("longitude") is not None:
                params["latitude"] = location_data["latitude"]
                params["longitude"] = location_data["longitude"]
            elif location_data and location_data.get("city") and location_data.get("country"):
                 print("WARN: PrayerTimes - Lat/Lon not directly available from IP-API, using City/Country as fallback for Aladhan API.")
                 params["city"] = location_data["city"]
                 params["country"] = location_data["country"]
            else:
                print("ERROR: PrayerTimes - Failed to get valid location data (lat/lon or city/country) from IP geolocation for Aladhan API.")
                return None

        elif loc_method == "manual_city":
            print("DEBUG: PrayerTimes - loc_method IS 'manual_city'.")
            city = self.settings_mngr.get("prayer_city", "").strip()
            country = self.settings_mngr.get("prayer_country", "").strip()
            if not city or not country:
                print("WARN: PrayerTimes - City or Country not set for 'manual_city' method.")
                return None
            params["city"] = city
            params["country"] = country
        elif loc_method == "manual_coords":
            print("DEBUG: PrayerTimes - loc_method IS 'manual_coords'.")
            lat_str = self.settings_mngr.get("prayer_latitude", "").strip()
            lon_str = self.settings_mngr.get("prayer_longitude", "").strip()
            if not lat_str or not lon_str:
                print("WARN: PrayerTimes - Latitude or Longitude not set for 'manual_coords' method.")
                return None
            try:
                params["latitude"] = float(lat_str)
                params["longitude"] = float(lon_str)
            except ValueError:
                print(f"ERROR: PrayerTimes - Invalid latitude/longitude format: '{lat_str}', '{lon_str}'")
                return None
        else:
            print(f"ERROR: PrayerTimes - Unknown or unhandled location method encountered: '{loc_method}'")
            return None

        params["method"] = self.settings_mngr.get("prayer_calculation_method", "5")
        params["school"] = self.settings_mngr.get("prayer_asr_method", "0")
        params["midnightMode"] = self.settings_mngr.get("prayer_midnight_mode", "0")
        tune_values = self.settings_mngr.get("prayer_tune_values", "0,0,0,0,0,0,0,0")
        
        try:
            if isinstance(tune_values, str) and len(tune_values.split(',')) == 8 and \
               all(val.strip().lstrip('-+').isdigit() for val in tune_values.split(',')):
                params["tune"] = tune_values
            else:
                raise ValueError("Invalid tune format")
        except ValueError:
            print(f"WARN: PrayerTimes - Invalid tune_values format: '{tune_values}'. Using default '0,0,0,0,0,0,0,0'.")
            params["tune"] = "0,0,0,0,0,0,0,0"


        params["latitudeAdjustmentMethod"] = self.settings_mngr.get("prayer_latitude_adjustment_method", "3")
        
        if not (("city" in params and "country" in params) or ("latitude" in params and "longitude" in params)):
            print("ERROR: PrayerTimes - No valid location parameters (city/country or lat/lon) were set after processing loc_method.")
            return None

        return params

    def fetch_prayer_times_for_date(self, target_date=None):
        # ... (الكود كما هو في الرد السابق، مع التأكد من أن api_params إذا كان None يتم الخروج) ...
        if target_date is None: target_date = date.today()
        if not self.settings_mngr.get("prayer_times_active", False):
            self.daily_prayer_times_data = {}; self.last_fetched_date = None; return False
        if self.last_fetched_date == target_date and self.daily_prayer_times_data.get("timings"): return True
        api_params = self._get_api_params()
        if not api_params: self.daily_prayer_times_data = {}; return False
        date_str = target_date.strftime('%d-%m-%Y'); endpoint = f"{self.API_BASE_URL}/timings/{date_str}"
        print(f"INFO: PrayerTimes - Fetching times for {target_date} from {endpoint}")
        try:
            response = requests.get(endpoint, params=api_params, timeout=15)
            response.raise_for_status(); data = response.json()
            if data.get("code") == 200 and "data" in data and "timings" in data["data"]:
                self.daily_prayer_times_data = data["data"]; self.last_fetched_date = target_date
                print(f"INFO: PrayerTimes - Successfully fetched for {target_date}.")
                return True
            else:
                error_message = data.get("status", data.get("data", "Unknown API error"))
                if isinstance(error_message, dict): error_message = str(error_message)
                print(f"ERROR: PrayerTimes - API error: {error_message} (Code: {data.get('code')})")
                self.daily_prayer_times_data = {}; return False
        except requests.exceptions.Timeout: print(f"ERROR: PrayerTimes - Request timed out for {target_date}."); self.daily_prayer_times_data = {}; return False
        except requests.exceptions.RequestException as e: print(f"ERROR: PrayerTimes - Network/HTTP error for {target_date}: {e}"); self.daily_prayer_times_data = {}; return False
        except json.JSONDecodeError: print(f"ERROR: PrayerTimes - JSON decode error for {target_date}."); self.daily_prayer_times_data = {}; return False
        except Exception as e_general: print(f"ERROR: PrayerTimes - Unexpected fetch error for {target_date}: {e_general}"); import traceback; traceback.print_exc(); self.daily_prayer_times_data = {}; return False


    def get_formatted_daily_timings(self):
        timings = self.get_todays_timings_dict() # This will fetch if necessary
        if not timings:
            return []
        formatted_list = []
        for prayer_key in self.PRAYER_ORDER: # Use our defined order
            time_str = timings.get(prayer_key)
            if time_str:
                display_name = self.lm.get_string(f"prayer_name_{prayer_key.lower()}", prayer_key)
                # API might return time with timezone like "05:00 (EET)", take only HH:MM
                actual_time_str = time_str.split(" ")[0]
                formatted_list.append((display_name, actual_time_str))
        return formatted_list

    def get_todays_timings_dict(self):
        today = date.today()
        if self.last_fetched_date != today or not self.daily_prayer_times_data.get("timings"):
            print(f"DEBUG: PrayerTimes - Timings for {today} not cached or outdated. Fetching...")
            if not self.fetch_prayer_times_for_date(today):
                return {}
        timings_raw = self.daily_prayer_times_data.get("timings", {})
        filtered_timings = {}
        for prayer_key_internal, api_prayer_name in self.API_PRAYER_NAMES.items():
            if api_prayer_name in timings_raw:
                 filtered_timings[prayer_key_internal] = timings_raw[api_prayer_name]
        return filtered_timings

    def get_next_prayer(self):
        # ... (الكود كما هو في الرد السابق، مع التأكد من استخدام get_formatted_daily_timings أو get_todays_timings_dict بشكل صحيح)
        timings_dict = self.get_todays_timings_dict() # الحصول على قاموس الأوقات الخام
        if not timings_dict:
            return None, None, None 

        now = datetime.now()
        next_prayer_name_found = None
        next_prayer_datetime_found = None

        for prayer_name_key in self.PRAYER_ORDER:
            time_str_raw = timings_dict.get(prayer_name_key)
            if time_str_raw:
                try:
                    time_str = time_str_raw.split(" ")[0] # "HH:MM (TZ)" -> "HH:MM"
                    prayer_hour, prayer_minute = map(int, time_str.split(':'))
                    prayer_datetime_today = now.replace(hour=prayer_hour, minute=prayer_minute, second=0, microsecond=0)
                    
                    if prayer_datetime_today > now:
                        next_prayer_name_found = prayer_name_key
                        next_prayer_datetime_found = prayer_datetime_today
                        break 
                except ValueError:
                    print(f"WARN: PrayerTimes - Could not parse time string '{time_str_raw}' for {prayer_name_key}")
                    continue
        
        if not next_prayer_name_found: # All prayers for today passed
            print("INFO: PrayerTimes - All prayers for today passed. Looking for Fajr tomorrow.")
            tomorrow = date.today() + timedelta(days=1)
            if self.last_fetched_date != tomorrow : # Only fetch if not already tomorrow's data
                if not self.fetch_prayer_times_for_date(tomorrow):
                    print("WARN: PrayerTimes - Could not fetch prayer times for tomorrow.")
                    return None, None, None 

            timings_tomorrow_raw = self.daily_prayer_times_data.get("timings", {})
            fajr_tomorrow_str_raw = timings_tomorrow_raw.get(self.API_PRAYER_NAMES["Fajr"])
            if fajr_tomorrow_str_raw:
                try:
                    fajr_tomorrow_str = fajr_tomorrow_str_raw.split(" ")[0]
                    fajr_hour, fajr_minute = map(int, fajr_tomorrow_str.split(':'))
                    next_prayer_name_found = "Fajr"
                    next_prayer_datetime_found = datetime(tomorrow.year, tomorrow.month, tomorrow.day, fajr_hour, fajr_minute, 0, 0)
                except ValueError:
                    print(f"WARN: PrayerTimes - Could not parse Fajr time string '{fajr_tomorrow_str_raw}' for tomorrow.")
            else:
                print("WARN: PrayerTimes - Fajr time for tomorrow not found in fetched data.")

        if next_prayer_name_found and next_prayer_datetime_found:
            time_until_next = next_prayer_datetime_found - now
            # ترجمة اسم الصلاة قبل إرجاعه
            display_prayer_name = self.lm.get_string(f"prayer_name_{next_prayer_name_found.lower()}", next_prayer_name_found)
            return display_prayer_name, next_prayer_datetime_found.strftime("%H:%M"), time_until_next
        
        print("WARN: PrayerTimes - Could not determine the next prayer after all checks.")
        return None, None, None