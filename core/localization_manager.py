import json
import os
from PyQt6.QtWidgets import QMessageBox # Keep for critical errors

class LocalizationManager:
    DEFAULT_TRANSLATIONS = {
        "en": {
            "app_name": "Zakir",
            "settings": "Settings",
            "language": "Language",
            "start_with_windows": "Start with Windows",
            "reminder_type": "Reminder Type",
            "text_notification": "Text Notification",
            "sound_notification": "Sound Notification",
            "random_notification": "Random (Text/Sound)",
            "general": "General",
            "reminders": "Reminders",
            "apply": "Apply",
            "ok": "OK",
            "cancel": "Cancel",
            "app_tooltip": "Zakir App",
            "toggle_reminders_active": "Pause Reminders",
            "toggle_reminders_paused": "Resume Reminders",
            "exit_app": "Exit",
            "language_changed_title": "Language Changed",
            "language_change_restart_note": "Please restart the application for all changes to take full effect.",
            "error": "Error",
            "settings_load_error": "Could not load settings. Using defaults.",
            "settings_save_error": "Could not save settings.",
            "content_tab_title": "Content",
            "text_adhkar_display": "Textual Adhkar (Display Only):",
            "audio_files_select": "Audio Files (Select Favorites):",
            "audio_folder_created": "Audio folder created. Place your audio files there.",
            "no_audio_files_found": "No audio files found in the 'resources/audio' directory.",
            "reminder_interval_minutes": "Interval (minutes):",
            "minutes_suffix": "min",
            "notification_position": "Notification Position:",
            "notification_duration_seconds": "Duration (seconds):",
            "seconds_suffix": "sec",
            "pos_top_left": "Top Left", "pos_top_center": "Top Center", "pos_top_right": "Top Right",
            "pos_center_left": "Center Left", "pos_center": "Center", "pos_center_right": "Center Right",
            "pos_bottom_left": "Bottom Left", "pos_bottom_center": "Bottom Center", "pos_bottom_right": "Bottom Right",
            "adhkar_load_error_display": "Error loading Adhkar data.",
            "no_adhkar_to_display": "No Adhkar to display for the current language.",
            "adhkar_category_format_error": "Error in Adhkar category format.",
            "adhkar_item_format_error": "Error in Adhkar item format.",
            "no_dhikr_available": "No dhikr available.",
            "startup_error_message": "A critical error occurred during startup: {error}",
            "audio_playback_error_title": "Audio Error",
            "audio_playback_error_message": "Could not play audio reminder.",
            "audio_reminder_error_title": "Sound Reminder Issue",
            "no_audio_files_selected_message": "No audio files are selected for sound reminders.",
            "audio_file_missing_title": "Audio File Missing",
            "audio_file_missing_message": "Selected audio file '{filename}' not found.",
            "prayer_times_tab_title": "Prayer Times",
            "enable_prayer_times": "Enable Prayer Times Display",
            "location_method": "Location Method:",
            "location_method_auto_ip": "Automatic (via IP)",
            "location_method_city_country": "City & Country",
            "location_method_coordinates": "Latitude & Longitude",
            "city": "City:",
            "country": "Country:",
            "latitude": "Latitude:",
            "longitude": "Longitude:",
            "calculation_method": "Calculation Method:",
            "asr_method": "Asr Juristic Method:",
            "asr_method_standard": "Shafii/Maliki/Hanbali (Standard)",
            "asr_method_hanafi": "Hanafi",
            "midnight_mode": "Midnight Mode:",
            "midnight_mode_standard": "Standard (Mid Sunset to Sunrise)",
            "midnight_mode_jafari": "Jafari (Mid Sunset to Fajr)", # أو ترجمة أخرى مناسبة
            "latitude_adjustment_method": "High Latitude Adjustment:",
            "lat_adj_middle_of_night": "Middle of the Night",
            "lat_adj_one_seventh": "One Seventh of the Night",
            "lat_adj_angle_based": "Angle Based",
            "prayer_time_tune": "Prayer Time Adjustments (minutes):",
            "fajr_tune": "Fajr:", "sunrise_tune": "Sunrise:", "dhuhr_tune": "Dhuhr:",
            "asr_tune": "Asr:", "sunset_tune": "Sunset:", "maghrib_tune": "Maghrib:",
            "isha_tune": "Isha:", "imsak_tune": "Imsak:",
            "tune_help_text": "Enter comma-separated values in order: Fajr, Sunrise, Dhuhr, Asr, Sunset, Maghrib, Isha, Imsak.",
            "fetch_prayer_times_button": "Fetch/Update Prayer Times",
            "prayer_times_fetched_success": "Successfully fetched prayer times for: {date}",
            "prayer_times_fetched_fail": "Failed to fetch prayer times: {error}",
            "prayer_times_not_active_message": "Prayer times feature is not active.",
            "location_settings_group": "Location Settings",
            "calculation_settings_group": "Calculation Settings",
            "prayer_time_tune_group": "Time Adjustments (Tune)",
            "prayer_times_menu_title": "Prayer Times",
            "prayer_name_fajr": "Fajr", "prayer_name_sunrise": "Sunrise",
            "prayer_name_dhuhr": "Dhuhr", "prayer_name_asr": "Asr",
            "prayer_name_maghrib": "Maghrib", "prayer_name_isha": "Isha",
            "next_prayer_label": "Next: {prayer_name} at {time} (in: {remaining})",
            "no_prayer_times_data": "No prayer times data available",
            "fetching_prayer_times": "Fetching prayer times...",
            "update_prayer_times_action": "Update Prayer Times",
            "calc_method_0": "Shia Ithna-Ansari", "calc_method_1": "University of Islamic Sciences, Karachi",
            "calc_method_2": "Islamic Society of North America (ISNA)", "calc_method_3": "Muslim World League (MWL)",
            "calc_method_4": "Umm al-Qura University, Makkah", "calc_method_5": "Egyptian General Authority of Survey",
            "calc_method_7": "Institute of Geophysics, University of Tehran", "calc_method_8": "Gulf Region",
            "calc_method_9": "Kuwait", "calc_method_10": "Qatar", "calc_method_11": "Singapore",
            "calc_method_12": "France - Angle 12°", "calc_method_13": "France - Angle 15°",
            "calc_method_14": "France - Angle 18°", "calc_method_15": "Russia",
            "calc_method_16": "Moonsighting Committee Worldwide (MCW)"
        },
        "ar": {
            "app_name": "ذاكر",
            "settings": "الإعدادات",
            "language": "اللغة",
            "start_with_windows": "البدء مع ويندوز",
            "reminder_type": "نوع التذكير",
            "text_notification": "إشعار نصي",
            "sound_notification": "إشعار صوتي",
            "random_notification": "عشوائي (نص/صوت)",
            "general": "عام",
            "reminders": "التذكيرات",
            "apply": "تطبيق",
            "ok": "موافق",
            "cancel": "إلغاء",
            "app_tooltip": "تطبيق ذاكر",
            "toggle_reminders_active": "إيقاف التذكيرات مؤقتًا",
            "toggle_reminders_paused": "استئناف التذكيرات",
            "exit_app": "خروج",
            "language_changed_title": "تم تغيير اللغة",
            "language_change_restart_note": "يرجى إعادة تشغيل التطبيق لتطبيق كافة التغييرات بشكل كامل.",
            "error": "خطأ",
            "settings_load_error": "تعذر تحميل الإعدادات. سيتم استخدام الإعدادات الافتراضية.",
            "settings_save_error": "تعذر حفظ الإعدادات.",
            "content_tab_title": "المحتوى",
            "text_adhkar_display": "الأذكار النصية (للعرض فقط):",
            "audio_files_select": "الملفات الصوتية (اختر المفضلة):",
            "audio_folder_created": "تم إنشاء مجلد الصوتيات. ضع ملفاتك الصوتية فيه.",
            "no_audio_files_found": "لم يتم العثور على ملفات صوتية في مجلد 'resources/audio'.",
            "reminder_interval_minutes": "الفاصل الزمني (دقائق):",
            "minutes_suffix": "دقيقة",
            "notification_position": "موضع الإشعار:",
            "notification_duration_seconds": "مدة الظهور (ثواني):",
            "seconds_suffix": "ثانية",
            "pos_top_left": "أعلى اليسار", "pos_top_center": "أعلى الوسط", "pos_top_right": "أعلى اليمين",
            "pos_center_left": "وسط اليسار", "pos_center": "الوسط", "pos_center_right": "وسط اليمين",
            "pos_bottom_left": "أسفل اليسار", "pos_bottom_center": "أسفل الوسط", "pos_bottom_right": "أسفل اليمين",
            "adhkar_load_error_display": "خطأ في تحميل بيانات الأذكار.",
            "no_adhkar_to_display": "لا توجد أذكار لعرضها باللغة الحالية.",
            "adhkar_category_format_error": "خطأ في تنسيق فئة الأذكار.",
            "adhkar_item_format_error": "خطأ في تنسيق عنصر الذكر.",
            "no_dhikr_available": "لا يوجد ذكر متاح.",
            "startup_error_message": "حدث خطأ حرج أثناء بدء التشغيل: {error}",
            "audio_playback_error_title": "خطأ في تشغيل الصوت",
            "audio_playback_error_message": "تعذر تشغيل التذكير الصوتي.",
            "audio_reminder_error_title": "مشكلة في التذكير الصوتي",
            "no_audio_files_selected_message": "لم يتم تحديد ملفات صوتية للتذكيرات الصوتية.",
            "audio_file_missing_title": "ملف صوتي مفقود",
            "audio_file_missing_message": "الملف الصوتي المحدد '{filename}' غير موجود.",
            "prayer_times_tab_title": "مواقيت الصلاة",
            "enable_prayer_times": "تفعيل عرض مواقيت الصلاة",
            "location_method": "طريقة تحديد الموقع:",
            "location_method_auto_ip": "تلقائي (عبر IP)",
            "location_method_city_country": "المدينة والدولة",
            "location_method_coordinates": "خطوط الطول والعرض",
            "city": "المدينة:",
            "country": "الدولة:",
            "latitude": "خط العرض:",
            "longitude": "خط الطول:",
            "calculation_method": "طريقة الحساب:",
            "asr_method": "مذهب العصر:",
            "asr_method_standard": "شافعي/مالكي/حنبلي (قياسي)",
            "asr_method_hanafi": "حنفي",
            "midnight_mode": "حساب منتصف الليل:",
            "midnight_mode_standard": "قياسي",
            "midnight_mode_jafari": "جعفري (فلكي)",
            "latitude_adjustment_method": "تعديل خطوط العرض العليا:",
            "lat_adj_middle_of_night": "منتصف الليل",
            "lat_adj_one_seventh": "سُبع الليل",
            "lat_adj_angle_based": "مبني على الزاوية",
            "prayer_time_tune": "تعديل أوقات الصلاة (دقائق):",
            "fajr_tune": "الفجر:", "sunrise_tune": "الشروق:", "dhuhr_tune": "الظهر:",
            "asr_tune": "العصر:", "sunset_tune": "الغروب:", "maghrib_tune": "المغرب:",
            "isha_tune": "العشاء:", "imsak_tune": "الإمساك:",
            "tune_help_text": "أدخل القيم مفصولة بفواصل بالترتيب: فجر, شروق, ظهر, عصر, غروب, مغرب, عشاء, إمساك.",
            "fetch_prayer_times_button": "جلب/تحديث مواقيت الصلاة",
            "prayer_times_fetched_success": "تم جلب مواقيت الصلاة بنجاح لليوم: {date}",
            "prayer_times_fetched_fail": "فشل جلب مواقيت الصلاة: {error}",
            "prayer_times_not_active_message": "ميزة مواقيت الصلاة غير مفعلة.",
            "location_settings_group": "إعدادات الموقع",
            "calculation_settings_group": "إعدادات الحساب",
            "prayer_time_tune_group": "تعديل الأوقات",
            "prayer_times_menu_title": "مواقيت الصلاة",
            "prayer_name_fajr": "الفجر", "prayer_name_sunrise": "الشروق",
            "prayer_name_dhuhr": "الظهر", "prayer_name_asr": "العصر",
            "prayer_name_maghrib": "المغرب", "prayer_name_isha": "العشاء",
            "next_prayer_label": "الصلاة القادمة: {prayer_name} في {time} (متبقي: {remaining})",
            "no_prayer_times_data": "لا توجد بيانات لمواقيت الصلاة",
            "fetching_prayer_times": "جاري جلب مواقيت الصلاة...",
            "update_prayer_times_action": "تحديث مواقيت الصلاة",
            "calc_method_0": "الشيعة الاثنا عشرية", "calc_method_1": "جامعة العلوم الإسلامية، كراتشي",
            "calc_method_2": "الجمعية الإسلامية لأمريكا الشمالية (ISNA)", "calc_method_3": "رابطة العالم الإسلامي (MWL)",
            "calc_method_4": "جامعة أم القرى، مكة المكرمة", "calc_method_5": "الهيئة المصرية العامة للمساحة",
            "calc_method_7": "معهد الجيوفيزياء، جامعة طهران", "calc_method_8": "منطقة الخليج",
            "calc_method_9": "الكويت", "calc_method_10": "قطر", "calc_method_11": "سنغافورة",
            "calc_method_12": "فرنسا - زاوية 12°", "calc_method_13": "فرنسا - زاوية 15°",
            "calc_method_14": "فرنسا - زاوية 18°", "calc_method_15": "روسيا",
            "calc_method_16": "لجنة رؤية الهلال العالمية (MCW)"
        }
    }

    def __init__(self, base_path="."):
        self.base_path = base_path
        self.translations = {}
        self.current_language = "en" 

    def _get_locale_path(self, lang_code):
        return os.path.join(self.base_path, "resources", "locale", f"{lang_code}.json")

    def load_language(self, lang_code="en"):
        self.current_language = lang_code
        filepath = self._get_locale_path(lang_code)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            print(f"INFO: Loaded language file: {filepath} for language {lang_code}")
        except FileNotFoundError:
            print(f"WARN: Language file for '{lang_code}' not found at {filepath}. Using default translations for this language.")
            self.translations = self.DEFAULT_TRANSLATIONS.get(lang_code, self.DEFAULT_TRANSLATIONS["en"].copy())
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.translations, f, indent=4, ensure_ascii=False)
                print(f"INFO: Created placeholder language file for '{lang_code}' at {filepath}")
            except Exception as e_write:
                print(f"ERROR: Could not write placeholder language file for '{lang_code}' at {filepath}: {e_write}")
        except json.JSONDecodeError as e:
            print(f"ERROR: Could not decode language file '{filepath}' for language '{lang_code}': {e}. Using defaults.")
            self.translations = self.DEFAULT_TRANSLATIONS.get(lang_code, self.DEFAULT_TRANSLATIONS["en"].copy())
        except Exception as e:
            print(f"ERROR: Unexpected error loading language file '{filepath}' for language '{lang_code}': {e}. Using defaults.")
            self.translations = self.DEFAULT_TRANSLATIONS.get(lang_code, self.DEFAULT_TRANSLATIONS["en"].copy())

    def get_string(self, key, default_text=None, **kwargs):
        # Ensure translations for the current language are loaded or defaulted
        translation_found = False
        translation = None

        if self.translations and key in self.translations:
            translation = self.translations.get(key)
            translation_found = True
        
        if not translation_found:
            default_lang_translations = self.DEFAULT_TRANSLATIONS.get(self.current_language, {})
            translation = default_lang_translations.get(key)
            if translation is not None:
                translation_found = True
            
        if not translation_found: # If still not found, try English defaults
            english_translations = self.DEFAULT_TRANSLATIONS.get("en", {})
            translation = english_translations.get(key)
            if translation is not None:
                translation_found = True

        if not translation_found:
             return default_text if default_text is not None else key
            
        try:
            return translation.format(**kwargs) if kwargs else translation
        except KeyError as e_format: 
            print(f"WARN: Formatting error for key '{key}' with value '{translation}'. Missing placeholder: {e_format}")
            return translation 
        except Exception as e_general_format:
            print(f"ERROR: General formatting error for key '{key}': {e_general_format}. Value: '{translation}', Args: {kwargs}")
            return translation

    def get_current_language(self):
        return self.current_language