# core/settings_manager.py
import json
import os
import sys
from PyQt6.QtWidgets import QMessageBox # Changed from PyQt5

class SettingsManager:
    DEFAULT_SETTINGS = {
        "language": "ar",
        "theme": "system", # Options: "light", "dark", "system"
        "start_with_windows": False, # Changed from True to False as a safer default
        "reminder_type": "text", # Options: "text", "sound", "random"
        "interval_minutes": 15,
        "notification_position": "bottom_right", # e.g., "top_left", "center", "bottom_right"
        "notification_duration_seconds": 7,
        "mute_on_fullscreen": True, # Functionality to be implemented
        "reminders_active": True,
        "selected_audio_files": [], # For general sound reminders

        # Prayer Times Settings
        "prayer_times_active": False,
        "prayer_location_method": "auto_ip", # Options: "auto_ip", "manual_city", "manual_coords"
        "prayer_city": "",
        "prayer_country": "",
        "prayer_latitude": "",
        "prayer_longitude": "",
        "prayer_calculation_method": "5", # Aladhan API method ID (e.g., "5" for Egyptian)
        "prayer_asr_method": "0",         # 0: Standard (Shafii, Maliki, Hanbali), 1: Hanafi
        "prayer_midnight_mode": "0",      # 0: Standard, 1: Jafari
        "prayer_tune_values": "0,0,0,0,0,0,0,0", # Comma-separated: Fajr,Sunrise,Dhuhr,Asr,Sunset,Maghrib,Isha,Imsak
        "prayer_latitude_adjustment_method": "3", # 0: Middle of Night, 1: One Seventh, 3: Angle Based

        # Prayer Alerts Settings
        "pre_adhan_alert_active": False,
        "pre_adhan_minutes": 10,
        "pre_adhan_sound_file": "", # Filename (e.g., "alert_tone.mp3") in resources/audio/adhan

        "post_adhan_iqama_alert_active": False,
        "post_adhan_iqama_minutes": 10,
        "post_adhan_iqama_sound_file": "", # Filename

        # Adhan Sounds Settings (specific to prayer times feature)
        "use_unified_adhan_sound": True,
        "unified_adhan_sound_file": "", # Filename (e.g., "adhan_makkah.mp3") in resources/audio/adhan
        "adhan_sound_fajr": "",
        "adhan_sound_dhuhr": "",
        "adhan_sound_asr": "",
        "adhan_sound_maghrib": "",
        "adhan_sound_isha": ""
    }

    def __init__(self, app_name="ZakirApp", lm=None):
        self.lm = lm # LocalizationManager instance
        self.app_name = app_name
        print(f"DEBUG: SettingsManager initializing for app: {self.app_name}")

        if sys.platform == "win32":
            self.config_dir = os.path.join(os.environ['APPDATA'], self.app_name)
        elif sys.platform == "darwin": # macOS
            self.config_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", self.app_name)
        else: # Linux and other Unix-like
            self.config_dir = os.path.join(os.path.expanduser("~"), ".config", self.app_name)
        
        print(f"DEBUG: Config directory set to: {self.config_dir}")
        os.makedirs(self.config_dir, exist_ok=True)
        self.settings_file = os.path.join(self.config_dir, "settings.json")
        print(f"DEBUG: Settings file path: {self.settings_file}")
        
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        print(f"INFO: Attempting to load settings from {self.settings_file}")
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                # Merge loaded settings with defaults: loaded takes precedence, defaults fill gaps.
                self.settings = {**self.DEFAULT_SETTINGS, **loaded_settings}
                print(f"INFO: Settings loaded successfully.")
                # Ensure all default keys are present and have correct types after loading
                needs_resave = False
                for key, default_value in self.DEFAULT_SETTINGS.items():
                    if key not in self.settings:
                        self.settings[key] = default_value
                        print(f"INFO: Added missing default setting: {key} = {default_value}")
                        needs_resave = True
                    # Type check for critical list setting
                    elif key == "selected_audio_files" and not isinstance(self.settings[key], list):
                        print(f"WARN: '{key}' was not a list. Resetting to default: {default_value}")
                        self.settings[key] = default_value
                        needs_resave = True
                if needs_resave:
                    print("INFO: Resaving settings due to added defaults or type corrections.")
                    self.save_settings() # Save if defaults were added or types corrected

            else:
                print("INFO: Settings file not found. Using default settings and creating the file.")
                self.settings = self.DEFAULT_SETTINGS.copy()
                self.save_settings()
        except json.JSONDecodeError:
            title = "Error"
            msg_default = "Settings file is corrupted. Using default settings and attempting to overwrite."
            msg = msg_default
            if self.lm:
                title = self.lm.get_string("error", title)
                msg = self.lm.get_string("settings_load_error_corrupted", msg_default) # Specific key for corrupted
            
            QMessageBox.warning(None, title, msg)
            print(f"ERROR: {msg_default} (File: {self.settings_file})")
            self.settings = self.DEFAULT_SETTINGS.copy()
            self.save_settings() # Attempt to save a fresh default file
        except Exception as e:
            title = "Error"
            msg_template_default = "Error loading settings: {error}. Using default settings."
            msg_template = msg_template_default
            if self.lm:
                title = self.lm.get_string("error", title)
                msg_template = self.lm.get_string("settings_load_error_generic", msg_template_default)
            
            msg = msg_template.format(error=str(e))
            QMessageBox.warning(None, title, msg)
            print(f"ERROR: {msg_template_default.format(error=str(e))} (File: {self.settings_file})")
            self.settings = self.DEFAULT_SETTINGS.copy()

    def save_settings(self):
        print(f"INFO: Attempting to save settings to {self.settings_file}")
        try:
            # Create directory if it doesn't exist (should be redundant if __init__ worked)
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            print(f"INFO: Settings saved successfully to {self.settings_file}")
        except PermissionError:
            title = "Error"
            msg_template_default = "No permission to write settings to {filepath}."
            msg_template = msg_template_default
            if self.lm:
                title = self.lm.get_string("error", title)
                msg_template = self.lm.get_string("settings_save_error_permission", msg_template_default)

            msg = msg_template.format(filepath=self.settings_file)
            QMessageBox.critical(None, title, msg)
            print(f"ERROR: {msg_template_default.format(filepath=self.settings_file)}")
        except Exception as e:
            title = "Error"
            msg_template_default = "Error saving settings: {error}."
            msg_template = msg_template_default
            if self.lm:
                title = self.lm.get_string("error", title)
                msg_template = self.lm.get_string("settings_save_error_generic", msg_template_default)
            
            msg = msg_template.format(error=str(e))
            QMessageBox.critical(None, title, msg)
            print(f"ERROR: {msg_template_default.format(error=str(e))} (File: {self.settings_file})")

    def get(self, key, default_override=None):
        """
        Retrieves a setting value.
        If default_override is provided, it's used if the key is not found.
        Otherwise, falls back to self.DEFAULT_SETTINGS.get(key).
        """
        if key in self.settings:
            return self.settings[key]
        
        if default_override is not None:
            # print(f"DEBUG: Key '{key}' not in settings, using provided default_override: {default_override}")
            return default_override
        
        # Fallback to DEFAULT_SETTINGS if key is not in self.settings and no default_override
        default_from_class = self.DEFAULT_SETTINGS.get(key)
        # print(f"DEBUG: Key '{key}' not in settings, using class default: {default_from_class}")
        return default_from_class


    def set(self, key, value):
        self.settings[key] = value
        self.save_settings() # Save immediately after setting a single value

    def set_bulk(self, settings_dict):
        """Applies multiple settings and saves once."""
        updated = False
        for key, value in settings_dict.items():
            if self.settings.get(key) != value: # Only update if value changed
                self.settings[key] = value
                updated = True
        
        if updated:
            self.save_settings()
            print(f"INFO: Bulk settings applied and saved. Keys: {list(settings_dict.keys())}")
        else:
            print(f"INFO: Bulk settings received, but no changes detected. Keys: {list(settings_dict.keys())}")


    def get_all_settings(self):
        """Returns a copy of all current settings, merged with defaults."""
        # Ensure all default keys are present in the returned dict
        return {**self.DEFAULT_SETTINGS, **self.settings}.copy()

    def get_config_dir(self):
        return self.config_dir

    def get_settings_file_path(self):
        return self.settings_file