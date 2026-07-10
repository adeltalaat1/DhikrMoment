import os
import json
from PyQt5.QtWidgets import QMessageBox

class SettingsManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.settings_file = os.path.join(base_path, "data", "settings.json")
        self.settings = self.load_settings()
        print("INFO: SettingsManager initialized.")

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                print(f"INFO: Loading settings from {self.settings_file}")
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                print("INFO: Settings loaded successfully.")
                return settings
            else:
                print("INFO: Settings file not found, creating default settings.")
                default_settings = self.get_default_settings()
                self.save_settings()  # حفظ الإعدادات الافتراضية
                return default_settings
        except Exception as e:
            print(f"ERROR: Failed to load settings: {e}")
            QMessageBox.critical(None, "Error", f"Failed to load settings: {e}")
            return self.get_default_settings()

    def get_default_settings(self):
        print("INFO: Returning default settings.")
        return {
            "language": "ar",
            "theme": "dark",
            "adhkar_active": True,
            "adhkar_interval": 60,
            "prayer_times_active": True,
            "prayer_location": None,
            "prayer_location_method": "auto",
            "adhan_active": True,
            "adhan_fajr": "none",
            "adhan_dhuhr": "none",
            "adhan_asr": "none",
            "adhan_maghrib": "none",
            "adhan_isha": "none"
        }

    def save_settings(self):
        try:
            print(f"INFO: Saving settings to {self.settings_file}")
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            print("INFO: Settings saved successfully.")
        except Exception as e:
            print(f"ERROR: Failed to save settings: {e}")
            QMessageBox.critical(None, "Error", f"Failed to save settings: {e}")

    def get(self, key, default=None):
        value = self.settings.get(key, default)
        print(f"INFO: Getting setting '{key}' = {value}")
        return value

    def set(self, key, value):
        print(f"INFO: Setting '{key}' = {value}")
        self.settings[key] = value
        self.save_settings()

    def get_all_settings(self):
        print("INFO: Returning all settings.")
        return self.settings.copy() 