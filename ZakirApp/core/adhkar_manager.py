# core/adhkar_manager.py
import json
import os
import random
import traceback # For more detailed error logging

class AdhkarManager:
    def __init__(self, base_path, language_code="ar"): # Takes base_path and initial lang_code
        self.base_path = base_path
        self.language_code = language_code
        self.adhkar_data = {}
        self.lm = None # For potential localized messages from AdhkarManager itself
        
        print(f"DEBUG: AdhkarManager initializing with base_path: {self.base_path}, lang: {self.language_code}")
        self._load_adhkar()

    def set_localization_manager(self, lm):
        """Optional: For localized error messages or default texts."""
        self.lm = lm
        print("DEBUG: AdhkarManager - LocalizationManager set.")

    def _get_adhkar_file_path(self):
        # Ensure lang_code is a simple string like "en" or "ar"
        lang_code_safe = "".join(filter(str.isalnum, self.language_code))
        filepath = os.path.join(self.base_path, "resources", "adhkar", f"{lang_code_safe}.json")
        print(f"DEBUG: AdhkarManager - Adhkar file path determined: {filepath}")
        return filepath
    
    def _load_adhkar(self):
        filepath = self._get_adhkar_file_path()
        print(f"DEBUG: AdhkarManager - Attempting to load Adhkar from: {filepath}")
        
        try:
            if not os.path.exists(filepath):
                print(f"ERROR: AdhkarManager - Adhkar file DOES NOT EXIST at: {filepath}")
                self.adhkar_data = {} # Ensure data is empty
                return

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip(): # Check if file is empty or only whitespace
                    print(f"ERROR: AdhkarManager - Adhkar file is EMPTY: {filepath}")
                    self.adhkar_data = {}
                    return
                
                f.seek(0) # Rewind to beginning of file for json.load
                self.adhkar_data = json.load(f)
            
            print(f"INFO: AdhkarManager - Adhkar loaded successfully for language: {self.language_code} from {filepath}")
            
            # Basic validation of loaded data structure
            if isinstance(self.adhkar_data, dict) and self.adhkar_data:
                print(f"DEBUG: AdhkarManager - Loaded data keys: {list(self.adhkar_data.keys())}")
                if "general" in self.adhkar_data and isinstance(self.adhkar_data["general"], list):
                    print(f"DEBUG: AdhkarManager - 'general' category has {len(self.adhkar_data['general'])} items.")
                elif "general" in self.adhkar_data:
                     print(f"WARN: AdhkarManager - 'general' category is present but not a list: {type(self.adhkar_data['general'])}")
            elif not self.adhkar_data: # e.g. file contained only "{}" or "[]"
                print(f"WARN: AdhkarManager - Loaded Adhkar data is empty (e.g., file was '{{}}' or '[]'). Lang: {self.language_code}")
            else: # Not a dict
                 print(f"ERROR: AdhkarManager - Loaded Adhkar data is not a dictionary. Type: {type(self.adhkar_data)}. Lang: {self.language_code}")
                 self.adhkar_data = {}


        except json.JSONDecodeError as e:
            print(f"ERROR: AdhkarManager - Could not decode Adhkar JSON from: {filepath}. Error: {e.msg} at line {e.lineno} col {e.colno}")
            self.adhkar_data = {}
        except IOError as e:
            print(f"ERROR: AdhkarManager - IOError while reading Adhkar file: {filepath}. Error: {e}")
            self.adhkar_data = {}
        except Exception as e_load:
            print(f"ERROR: AdhkarManager - Unexpected error loading Adhkar file: {filepath}. Error: {e_load}")
            traceback.print_exc()
            self.adhkar_data = {}
            
    def set_language(self, language_code):
        if self.language_code != language_code:
            print(f"INFO: AdhkarManager - Changing language from '{self.language_code}' to '{language_code}'")
            self.language_code = language_code
            self._load_adhkar() # Reload data for the new language
        else:
            print(f"INFO: AdhkarManager - Language already set to '{language_code}'. No change.")

    def get_adhkar_by_category(self, category_key):
        """
        Returns a list of adhkar items (dictionaries) for a given category.
        Each item is expected to be a dict, e.g., {"id": "...", "text": "...", ...}.
        """
        if not isinstance(self.adhkar_data, dict):
            print(f"WARN: AdhkarManager.get_adhkar_by_category - Adhkar data is not a dictionary. Category: {category_key}")
            return []
            
        category_data = self.adhkar_data.get(category_key, [])
        if not isinstance(category_data, list):
            print(f"WARN: AdhkarManager.get_adhkar_by_category - Data for category '{category_key}' is not a list. Type: {type(category_data)}")
            return []
        
        # Further validation can be added here if needed to check item structure
        # For now, we return the list as is, assuming items are dicts.
        return category_data # Returns list of dicts

    def get_adhkar_texts_by_category(self, category_key):
        """Returns a list of just the adhkar texts for a given category."""
        items = self.get_adhkar_by_category(category_key)
        texts = []
        for item in items:
            if isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                texts.append(item["text"])
            else:
                print(f"WARN: AdhkarManager.get_adhkar_texts_by_category - Malformed item in category '{category_key}': {item}")
        return texts

    def get_all_adhkar_structured(self):
        """Returns a copy of the entire structured adhkar data."""
        if not isinstance(self.adhkar_data, dict):
            print(f"WARN: AdhkarManager.get_all_adhkar_structured - Adhkar data is not a dictionary. Returning empty dict.")
            return {}
        return self.adhkar_data.copy() # Return a copy to prevent external modification
    
    def get_random_dhikr(self, category_key="general"):
        """Gets a random dhikr text from a specific category, falling back to 'general'."""
        
        # Ensure adhkar_data is a dictionary
        if not isinstance(self.adhkar_data, dict):
            print(f"ERROR: AdhkarManager.get_random_dhikr - Adhkar data is not a dictionary. Cannot get random dhikr.")
            return self._get_no_dhikr_message()

        adhkar_texts_in_category = self.get_adhkar_texts_by_category(category_key)

        if adhkar_texts_in_category:
            return random.choice(adhkar_texts_in_category)
        
        # Fallback if specified category is empty, not found, or malformed
        if category_key != "general":
            print(f"WARN: AdhkarManager.get_random_dhikr - Category '{category_key}' empty or invalid. Falling back to 'general'.")
            general_adhkar_texts = self.get_adhkar_texts_by_category("general")
            if general_adhkar_texts:
                return random.choice(general_adhkar_texts)
        
        # If 'general' is also empty/invalid, or if the initial category was 'general' and it was empty
        print(f"WARN: AdhkarManager.get_random_dhikr - No valid dhikr found in category '{category_key}' or fallback 'general'.")
        return self._get_no_dhikr_message()

    def _get_no_dhikr_message(self):
        default_message = "No dhikr available." # Hardcoded English default
        if self.lm:
            # Try to get localized message, fallback to the English default_message
            return self.lm.get_string("no_dhikr_available", default_text=default_message)
        else:
            # print("WARN: AdhkarManager - LocalizationManager not set, using hardcoded default for 'no_dhikr_available'.")
            return default_message

    def get_categories(self):
        """Returns a list of available Adhkar category keys."""
        if not isinstance(self.adhkar_data, dict):
            return []
        return list(self.adhkar_data.keys())