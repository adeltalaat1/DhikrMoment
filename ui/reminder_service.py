import os
from datetime import datetime
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QSystemTrayIcon, QMessageBox
from PyQt5.QtGui import QIcon

class ReminderService:
    def __init__(self, settings_manager, localization_manager, adhkar_manager, prayer_times_manager, base_path):
        self.settings_manager = settings_manager
        self.lm = localization_manager
        self.adhkar_manager = adhkar_manager
        self.prayer_times_manager = prayer_times_manager
        self.base_path = base_path
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_reminders)
        self.timer.start(60000)  # تحقق كل دقيقة
        self.last_dhikr_time = None
        self.last_prayer_time = None
        print("INFO: ReminderService initialized.")

    def check_reminders(self):
        print("INFO: Checking reminders...")
        self.check_dhikr_reminder()
        self.check_prayer_reminder()

    def check_dhikr_reminder(self):
        if not self.settings_manager.get("adhkar_active"):
            print("INFO: Adhkar reminders are disabled.")
            return

        interval = self.settings_manager.get("adhkar_interval", 60)
        now = datetime.now()

        if self.last_dhikr_time is None or (now - self.last_dhikr_time).total_seconds() >= interval * 60:
            print(f"INFO: Time for new dhikr reminder (interval: {interval} minutes).")
            dhikr = self.adhkar_manager.get_random_dhikr()
            if dhikr:
                print("INFO: Showing dhikr notification.")
                self.show_dhikr_notification(dhikr)
                self.last_dhikr_time = now
            else:
                print("WARN: No dhikr available for reminder.")

    def check_prayer_reminder(self):
        if not self.settings_manager.get("prayer_times_active"):
            print("INFO: Prayer time reminders are disabled.")
            return

        next_prayer = self.prayer_times_manager.get_next_prayer()
        if not next_prayer:
            print("WARN: Could not determine next prayer time.")
            return

        now = datetime.now()
        current_time = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        if today in self.prayer_times_manager.prayer_times:
            prayer_time = self.prayer_times_manager.prayer_times[today][next_prayer]
            if current_time == prayer_time and (self.last_prayer_time is None or self.last_prayer_time != prayer_time):
                print(f"INFO: Time for {next_prayer} prayer at {prayer_time}.")
                self.show_prayer_notification(next_prayer)
                self.last_prayer_time = prayer_time

    def show_dhikr_notification(self, dhikr):
        if not isinstance(dhikr, dict) or 'text' not in dhikr:
            print("WARN: Invalid dhikr format for notification.")
            return

        print("INFO: Creating dhikr notification.")
        notification = QSystemTrayIcon()
        notification.setIcon(QIcon(os.path.join(self.base_path, "assets", "icon.png")))
        notification.show()
        notification.showMessage(
            self.lm.get_string("dhikr_reminder", "تذكير بالأذكار"),
            dhikr['text'],
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )

    def show_prayer_notification(self, prayer):
        print(f"INFO: Creating prayer notification for {prayer}.")
        notification = QSystemTrayIcon()
        notification.setIcon(QIcon(os.path.join(self.base_path, "assets", "icon.png")))
        notification.show()
        notification.showMessage(
            self.lm.get_string("prayer_time", "حان وقت الصلاة"),
            self.lm.get_string(f"prayer_{prayer}", prayer),
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )

    def schedule_prayer_alerts(self):
        if not self.settings_manager.get("prayer_times_active"):
            print("INFO: Prayer time alerts are disabled.")
            return

        print("INFO: Fetching prayer times for alerts.")
        self.prayer_times_manager.fetch_prayer_times_for_date()
        if not self.prayer_times_manager.last_fetch_success:
            print("WARN: Failed to fetch prayer times for alerts.")
            return

        next_prayer = self.prayer_times_manager.get_next_prayer()
        if next_prayer:
            print(f"INFO: Scheduling alert for next prayer: {next_prayer}")
            self.show_prayer_notification(next_prayer) 