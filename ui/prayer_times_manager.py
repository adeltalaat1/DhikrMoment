import os
import json
import requests
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox

class PrayerTimesManager:
    def __init__(self, settings_manager, localization_manager, base_path):
        self.settings_manager = settings_manager
        self.lm = localization_manager
        self.base_path = base_path
        self.prayer_times = {}
        self.last_fetch_success = False
        self.last_fetch_error = None
        self.auto_location_data = None
        self.cached_auto_location_data = None
        print("INFO: PrayerTimesManager initialized.")

    def get_prayer_times(self):
        return self.prayer_times

    def get_next_prayer(self):
        if not self.prayer_times:
            print("WARN: No prayer times available.")
            return None

        now = datetime.now()
        current_time = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        if today not in self.prayer_times:
            print(f"WARN: No prayer times for today ({today}).")
            return None

        prayers = self.prayer_times[today]
        for prayer, time in prayers.items():
            if time > current_time:
                print(f"INFO: Next prayer is {prayer} at {time}")
                return prayer
        print("INFO: All prayers for today have passed, returning to fajr.")
        return "fajr"

    def fetch_prayer_times_for_date(self):
        if not self.settings_manager.get("prayer_times_active"):
            print("INFO: Prayer times feature is disabled.")
            return

        location = self.settings_manager.get("prayer_location")
        if not location:
            print("WARN: No prayer location set.")
            return

        try:
            print(f"INFO: Fetching prayer times for location: {location}")
            today = datetime.now().strftime("%d-%m-%Y")
            url = f"http://api.aladhan.com/v1/timingsByCity?city={location}&country=SA&method=4&date={today}"
            response = requests.get(url)
            data = response.json()

            if data["code"] == 200:
                timings = data["data"]["timings"]
                date = data["data"]["date"]["gregorian"]["date"]
                self.prayer_times[date] = {
                    "fajr": timings["Fajr"],
                    "dhuhr": timings["Dhuhr"],
                    "asr": timings["Asr"],
                    "maghrib": timings["Maghrib"],
                    "isha": timings["Isha"]
                }
                self.last_fetch_success = True
                self.last_fetch_error = None
                print(f"INFO: Successfully fetched prayer times for {date}")
            else:
                self.last_fetch_success = False
                self.last_fetch_error = "API returned error"
                print(f"ERROR: API returned error code {data['code']}")
        except Exception as e:
            self.last_fetch_success = False
            self.last_fetch_error = str(e)
            print(f"ERROR: Failed to fetch prayer times: {e}")

    def get_auto_location(self):
        if self.cached_auto_location_data:
            print("INFO: Using cached auto location data.")
            return self.cached_auto_location_data

        try:
            print("INFO: Fetching auto location data.")
            response = requests.get("http://ip-api.com/json")
            data = response.json()
            if data["status"] == "success":
                self.cached_auto_location_data = {
                    "city": data["city"],
                    "country": data["country"]
                }
                print(f"INFO: Auto location data fetched: {self.cached_auto_location_data}")
                return self.cached_auto_location_data
        except Exception as e:
            print(f"ERROR: Failed to get auto location: {e}")
        return None

    def clear_cached_auto_location_data(self):
        print("INFO: Clearing cached auto location data.")
        self.cached_auto_location_data = None 