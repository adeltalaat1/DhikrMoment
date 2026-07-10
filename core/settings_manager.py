# --- START OF FILE core/settings_manager.py ---
import json
import os
import sys
from PyQt6.QtWidgets import QMessageBox

class SettingsManager:
    DEFAULT_SETTINGS = {
        "language": "ar",
        "reminder_type": "text",
        "interval_minutes": 15,
        "notification_position": "bottom-right",
        "notification_duration_seconds": 7,
        "mute_on_fullscreen": True, # لم يتم تنفيذ وظيفتها بعد
        "auto_start_windows": True, # لم يتم تنفيذ وظيفتها بعد
        "reminders_active": True,
        "prayer_location_method": "auto_ip", # الخيارات الآن: "auto_ip", "manual_city", "manual_coords"


        # --- إعدادات تنبيهات الصلاة الجديدة ---
        "pre_adhan_alert_active": False,     # تفعيل التنبيه قبل الأذان
        "pre_adhan_minutes": 10,             # عدد الدقائق قبل الأذان للتنبيه
        "pre_adhan_sound_file": "",          # مسار الملف الصوتي للتنبيه قبل الأذان (أو اسم الملف في مجلد audio)

        "post_adhan_iqama_alert_active": False, # تفعيل تنبيه الإقامة بعد الأذان
        "post_adhan_iqama_minutes": 10,       # عدد الدقائق بعد الأذان لتنبيه الإقامة
        "post_adhan_iqama_sound_file": "",    # مسار الملف الصوتي لتنبيه الإقامة

        "adhan_sound_fajr": "",              # ملف أذان الفجر (إذا أردت تخصيص لكل صلاة)
        "adhan_sound_dhuhr": "",             # ملف أذان الظهر
        "adhan_sound_asr": "",               # ... وهكذا لباقي الصلوات
        "adhan_sound_maghrib": "",
        "adhan_sound_isha": "",
        "use_unified_adhan_sound": True,     # استخدام ملف أذان موحد إذا كان True
        "unified_adhan_sound_file": "",      # ملف الأذان الموحد
        
        # --- إعدادات مواقيت الصلاة الجديدة ---
        "prayer_times_active": False, # هل ميزة مواقيت الصلاة مفعلة؟
        "prayer_location_method": "manual_city", # الخيارات: "manual_city", "manual_coords" (مستقبلاً: "auto")
        "prayer_city": "",
        "prayer_country": "",
        "prayer_latitude": "",  # خط العرض (نص، سيتم تحويله إلى float)
        "prayer_longitude": "", # خط الطول (نص، سيتم تحويله إلى float)
        "prayer_calculation_method": "5", # الافتراضي: الهيئة المصرية العامة للمساحة (رقم 5)
        "prayer_asr_method": "0", # 0: شافعي/مالكي/حنبلي (قياسي), 1: حنفي
        "prayer_midnight_mode": "0", # 0: قياسي (منتصف الفترة بين المغرب والفجر), 1: فلكي (منتصف الفترة بين الغروب والشروق)
        "prayer_tune_values": "0,0,0,0,0,0,0,0", # تعديلات: فجر,شروق,ظهر,عصر,غروب,مغرب,عشاء,إمساك
        "prayer_latitude_adjustment_method": "3", # 3: طريقة الزاوية (Angle Based)
        # --- نهاية إعدادات مواقيت الصلاة ---

        "selected_audio_files": [] 
    }

    def __init__(self, app_name="ZakirApp", lm=None):
        self.lm = lm
        if sys.platform == "win32":
            self.config_dir = os.path.join(os.environ['APPDATA'], app_name)
        else:
            self.config_dir = os.path.join(os.path.expanduser("~"), f".{app_name.lower()}")
        
        os.makedirs(self.config_dir, exist_ok=True)
        self.settings_file = os.path.join(self.config_dir, "settings.json")
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                self.settings = {**self.DEFAULT_SETTINGS, **loaded_settings}
            else:
                self.settings = self.DEFAULT_SETTINGS.copy()
                self.save_settings()
            print(f"INFO: Settings loaded from {self.settings_file}")
            # ضمان وجود جميع المفاتيح الافتراضية بعد التحميل
            for key, value in self.DEFAULT_SETTINGS.items():
                if key not in self.settings:
                    self.settings[key] = value
                    print(f"INFO: Added missing default setting: {key} = {value}")
                # ضمان أن selected_audio_files هي قائمة
                if key == "selected_audio_files" and not isinstance(self.settings[key], list):
                    print(f"WARN: 'selected_audio_files' was not a list. Resetting to default.")
                    self.settings[key] = self.DEFAULT_SETTINGS[key]


        except json.JSONDecodeError:
            msg = "Settings file is corrupted. Using default settings and attempting to overwrite."
            print(f"ERROR: {msg}")
            if self.lm:
                QMessageBox.warning(None, self.lm.get_string("error", "Error"), self.lm.get_string("settings_load_error", msg))
            else:
                QMessageBox.warning(None, "Error", msg)
            self.settings = self.DEFAULT_SETTINGS.copy()
            self.save_settings()
        except Exception as e:
            msg = f"Error loading settings: {e}. Using default settings."
            print(f"ERROR: {msg}")
            if self.lm:
                QMessageBox.warning(None, self.lm.get_string("error", "Error"), self.lm.get_string("settings_load_error", msg))
            else:
                QMessageBox.warning(None, "Error", msg)
            self.settings = self.DEFAULT_SETTINGS.copy()

    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            print(f"INFO: Settings saved to {self.settings_file}")
        except PermissionError:
            msg = f"No permission to write to {self.settings_file}"
            print(f"ERROR: {msg}")
            if self.lm: QMessageBox.critical(None, self.lm.get_string("error", "Error"), self.lm.get_string("settings_save_error", msg))
            else: QMessageBox.critical(None, "Error", msg)
        except Exception as e:
            msg = f"Error saving settings: {e}"
            print(f"ERROR: {msg}")
            if self.lm: QMessageBox.critical(None, self.lm.get_string("error", "Error"), self.lm.get_string("settings_save_error", msg))
            else: QMessageBox.critical(None, "Error", msg)

    def get(self, key, default=None):
        if key in self.settings:
            return self.settings[key]
        # إذا لم يتم توفير قيمة افتراضية للمعامل، استخدم القيمة من DEFAULT_SETTINGS
        effective_default = default if default is not None else self.DEFAULT_SETTINGS.get(key)
        return effective_default

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()

    def set_bulk(self, settings_dict):
        for key, value in settings_dict.items():
            self.settings[key] = value
        self.save_settings()
        print(f"INFO: Bulk settings applied and saved. Keys: {list(settings_dict.keys())}")

    def get_all_settings(self):
        return {**self.DEFAULT_SETTINGS, **self.settings}.copy()

# --- END OF FILE core/settings_manager.py ---