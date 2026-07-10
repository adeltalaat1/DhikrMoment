import os
import json
from PyQt5.QtWidgets import QMessageBox

class LocalizationManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.current_language = "ar"
        self.translations = {}
        self.load_translations()
        print("INFO: LocalizationManager initialized.")

    def load_translations(self):
        try:
            translations_file = os.path.join(self.base_path, "data", "translations.json")
            print(f"INFO: Loading translations from {translations_file}")
            with open(translations_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            print(f"INFO: Successfully loaded translations for {len(self.translations)} languages.")
        except Exception as e:
            print(f"ERROR: Failed to load translations: {e}")
            QMessageBox.critical(None, "Error", f"Failed to load translations: {e}")

    def get_string(self, key, default=None):
        if self.current_language in self.translations and key in self.translations[self.current_language]:
            return self.translations[self.current_language][key]
        print(f"WARN: Translation not found for key '{key}' in language '{self.current_language}'")
        return default if default is not None else key

    def get_current_language(self):
        print(f"INFO: Current language is '{self.current_language}'")
        return self.current_language

    def load_language(self, lang_code):
        if lang_code in self.translations:
            print(f"INFO: Switching language to '{lang_code}'")
            self.current_language = lang_code
            return True
        print(f"WARN: Language '{lang_code}' not found in translations")
        return False 