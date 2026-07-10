import json
import os
import random

class AdhkarManager:
    def __init__(self, base_path=".", language_code="ar"):
        self.base_path = base_path
        self.language_code = language_code
        self.adhkar_data = {}
        self.lm = None # For potential localized messages from AdhkarManager itself
        self._load_adhkar()

    def set_localization_manager(self, lm): # Optional: for localized error messages
        self.lm = lm

    def _get_adhkar_file_path(self):
        # تأكد أن هذا المسار صحيح وأن language_code يتم تحديثه بشكل صحيح
        # عند تغيير اللغة في الإعدادات.
        filepath = os.path.join(self.base_path, "resources", "adhkar", f"{self.language_code}.json")
        print(f"DEBUG: AdhkarManager - Attempting to get adhkar file path: {filepath}")
        return filepath
    
    def _load_adhkar(self):
        filepath = self._get_adhkar_file_path()
        print(f"DEBUG: AdhkarManager - Attempting to load Adhkar from: {filepath}")
        try:
            # تحقق مما إذا كان الملف موجودًا قبل محاولة فتحه
            if not os.path.exists(filepath):
                print(f"ERROR: AdhkarManager - Adhkar file DOES NOT EXIST at: {filepath}")
                self.adhkar_data = {}
                return # اخرج إذا لم يكن الملف موجودًا

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read() # اقرأ المحتوى أولاً للتحقق
                print(f"DEBUG: AdhkarManager - File content (first 100 chars): {content[:100]}")
                if not content.strip(): # تحقق إذا كان الملف فارغًا أو يحتوي على مسافات فقط
                    print(f"ERROR: AdhkarManager - Adhkar file is EMPTY: {filepath}")
                    self.adhkar_data = {}
                    return
                
                # العودة إلى بداية الملف لإعادة القراءة بواسطة json.load
                f.seek(0) 
                self.adhkar_data = json.load(f)
            
            print(f"INFO: Adhkar loaded successfully for language: {self.language_code} from {filepath}")
            # اطبع بعض البيانات للتحقق
            if isinstance(self.adhkar_data, dict) and self.adhkar_data:
                print(f"DEBUG: AdhkarManager - Loaded data keys: {list(self.adhkar_data.keys())}")
                if "general" in self.adhkar_data:
                    print(f"DEBUG: AdhkarManager - 'general' category has {len(self.adhkar_data['general'])} items.")
            elif not self.adhkar_data:
                print("WARN: AdhkarManager - Loaded data is empty after successful JSON load (file might be valid JSON but empty like {} or []).")

        except FileNotFoundError: # يجب أن يتم التقاط هذا بواسطة os.path.exists الآن
            print(f"ERROR: AdhkarManager - Adhkar file not found (should have been caught by os.path.exists): {filepath}")
            self.adhkar_data = {} 
        except json.JSONDecodeError as e:
            print(f"ERROR: AdhkarManager - Could not decode Adhkar JSON file for language: {self.language_code} at {filepath}. Error: {e}")
            print(f"DEBUG: AdhkarManager - Error occurred at line {e.lineno}, column {e.colno}: {e.msg}")
            self.adhkar_data = {}
        except Exception as e_load: # لالتقاط أي أخطاء أخرى غير متوقعة
            print(f"ERROR: AdhkarManager - Unexpected error loading Adhkar file: {e_load}")
            import traceback
            traceback.print_exc()
            self.adhkar_data = {}
            

    def set_language(self, language_code):
        if self.language_code != language_code:
            print(f"INFO: AdhkarManager changing language from {self.language_code} to {language_code}")
            self.language_code = language_code
            self._load_adhkar()
        else:
            print(f"INFO: AdhkarManager language already set to {language_code}")


    def get_adhkar_by_category(self, category):
        """Returns a list of adhkar texts for a given category."""
        category_data = self.adhkar_data.get(category, [])
        if not isinstance(category_data, list):
            print(f"WARN: Adhkar category '{category}' data is not a list: {category_data}")
            return []
        
        texts = []
        for item in category_data:
            if isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                texts.append(item["text"])
            else:
                print(f"WARN: Malformed item in adhkar category '{category}': {item}")
        return texts

# core/adhkar_manager.py
    def get_all_adhkar_structured(self):
        print(f"DEBUG: AdhkarManager - get_all_adhkar_structured called. Data type: {type(self.adhkar_data)}, Is empty: {not bool(self.adhkar_data)}")
        if not isinstance(self.adhkar_data, dict):
            print(f"WARN: AdhkarManager - Adhkar data is not a dictionary in get_all_adhkar_structured. Returning empty. Data: {self.adhkar_data}")
            return {}
        return self.adhkar_data.copy() # تأكد من إرجاع نسخة
    
    def get_random_dhikr(self, category="general"):
        """Gets a random dhikr text from a specific category."""
        category_adhkar_raw = self.adhkar_data.get(category, [])
        
        valid_adhkar = []
        if isinstance(category_adhkar_raw, list):
            for item in category_adhkar_raw:
                if isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                    valid_adhkar.append(item["text"])
                else:
                    print(f"WARN: get_random_dhikr - Malformed item in category '{category}': {item}")
        else:
            print(f"WARN: get_random_dhikr - Category '{category}' data is not a list: {category_adhkar_raw}")

        if valid_adhkar:
            return random.choice(valid_adhkar)
        
        # Fallback if category is empty, not found, or malformed
        if category != "general": # Avoid issues if 'general' itself is problematic
            general_adhkar_raw = self.adhkar_data.get("general", [])
            valid_general_adhkar = []
            if isinstance(general_adhkar_raw, list):
                for item in general_adhkar_raw:
                    if isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                        valid_general_adhkar.append(item["text"])
                    else:
                        print(f"WARN: get_random_dhikr (fallback) - Malformed item in category 'general': {item}")
            else:
                print(f"WARN: get_random_dhikr (fallback) - Category 'general' data is not a list: {general_adhkar_raw}")

            if valid_general_adhkar:
                return random.choice(valid_general_adhkar)
        
        default_message = "No dhikr available."
        if self.lm: # Check if lm is set
            default_message = self.lm.get_string("no_dhikr_available", default_text=default_message)
        else: # Fallback if lm is not set
             print("WARN: LocalizationManager not set in AdhkarManager, using hardcoded default for 'no_dhikr_available'.")
        return default_message