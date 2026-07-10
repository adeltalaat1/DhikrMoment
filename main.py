import sys
import os
import traceback 
import platform 

from PyQt6.QtWidgets import QApplication, QMessageBox, QStyleFactory, QWidget
from PyQt6.QtCore import QLocale, Qt, QTimer 
from PyQt6.QtGui import QPalette, QColor, QAction

from core.settings_manager import SettingsManager
from core.localization_manager import LocalizationManager
from core.adhkar_manager import AdhkarManager
from ui.tray_manager import TrayManager # تأكد أن هذا المسار صحيح
from core.reminder_service import ReminderService # تأكد أن هذا المسار صحيح
from ui.settings_window import GlassFrame, SettingsWindow # تأكد أن هذا المسار صحيح
from core.prayer_times_manager import PrayerTimesManager # تأكد أن هذا المسار صحيح

class ZakirApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        print("INFO: ZakirApp.__init__ started.")
        self.setQuitOnLastWindowClosed(False)
        print("INFO: setQuitOnLastWindowClosed(False) is ACTIVE.")

        # --- تعريف base_path يجب أن يكون هنا في البداية ---
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self.base_path = sys._MEIPASS
        else: 
            self.base_path = os.path.dirname(os.path.abspath(__file__))
        print(f"INFO: Application base path: {self.base_path}")
        # --- نهاية تعريف base_path ---

        self.lm = None
        self.settings_manager = None
        self.adhkar_manager = None
        self.tray_manager = None
        self.reminder_service = None
        self.prayer_times_manager = None 

        try:
            self.lm = LocalizationManager(base_path=self.base_path)
            print(f"DEBUG: LocalizationManager instance: {self.lm}")
            self.settings_manager = SettingsManager(app_name="ZakirApp", lm=self.lm)
            print(f"DEBUG: SettingsManager instance after init: {self.settings_manager}")

            if not self.settings_manager or not hasattr(self.settings_manager, 'get'):
                print("FATAL ERROR: SettingsManager was not initialized correctly or is None.")
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Startup Error")
                msg_box.setText("Settings Manager failed to initialize.\nApplication will exit.")
                msg_box.exec()
                sys.exit(1)

            initial_lang = self.settings_manager.get("language", "ar")
            self.lm.load_language(initial_lang)
            print(f"INFO: LocalizationManager loaded language: {initial_lang} from settings.")
            self.set_application_language_direction(initial_lang)

            self.adhkar_manager = AdhkarManager(base_path=self.base_path, language_code=initial_lang)
            self.adhkar_manager.set_localization_manager(self.lm)
            print(f"INFO: AdhkarManager initialized for language: {initial_lang}")

            self.prayer_times_manager = PrayerTimesManager(self.settings_manager, self.lm)
            print("INFO: PrayerTimesManager initialized.")

            self.tray_manager = TrayManager(
                app=self, settings_manager=self.settings_manager, 
                localization_manager=self.lm, adhkar_manager=self.adhkar_manager,
                prayer_times_manager=self.prayer_times_manager, 
                base_path=self.base_path
            )
            print("INFO: TrayManager initialized.")

            self.reminder_service = ReminderService(
                settings_manager=self.settings_manager, adhkar_manager=self.adhkar_manager,
                tray_icon=self.tray_manager.tray_icon, base_path=self.base_path, lm=self.lm
            )
            print("INFO: ReminderService initialized.")
            self.apply_dark_theme_permanently() 

            if self.settings_manager: 
                if self.settings_manager.get("prayer_times_active", False):
                    print("INFO: Initial fetch for prayer times as feature is active (main)...")
                    if self.prayer_times_manager: 
                        QTimer.singleShot(1500, self.prayer_times_manager.fetch_prayer_times_for_date) 
                    else:
                        print("WARN: PrayerTimesManager is None, cannot schedule initial fetch.")
                else:
                    print("INFO: Prayer times feature is not active, skipping initial fetch.")
            else:
                print("ERROR: SettingsManager is None before checking prayer_times_active for initial fetch (should not happen here).")

            self.settings_window_instance = SettingsWindow(
                settings_manager=self.settings_manager,
                localization_manager=self.lm,
                adhkar_manager=self.adhkar_manager,
                base_path=self.base_path
            )

        except Exception as e_init:
            print(f"FATAL ERROR during initialization sequence: {e_init}")
            traceback.print_exc()
            error_title = "Initialization Error"; error_message = f"A critical error occurred during startup: {e_init}"
            if self.lm and hasattr(self.lm, 'get_string'):
                error_title = self.lm.get_string("error", error_title)
                error_message = self.lm.get_string("startup_error_message", default_text=error_message).format(error=e_init)
            msg_box_error = QMessageBox(); msg_box_error.setIcon(QMessageBox.Icon.Critical)
            msg_box_error.setWindowTitle(error_title); msg_box_error.setText(error_message); msg_box_error.exec()
            sys.exit(1) 
        print("INFO: ZakirApp.__init__ finished successfully.")

    def apply_dark_theme_permanently(self):
        print("INFO: Applying permanent DARK theme.")
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
        dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
        dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127,127,127))
        self.setPalette(dark_palette)
        self.update_glass_frames_theme(is_dark=True)
        if hasattr(self, 'tray_manager') and self.tray_manager:
            if self.tray_manager.settings_window_instance and \
               self.tray_manager.settings_window_instance.isVisible():
                self.tray_manager.settings_window_instance.reapply_stylesheet_for_theme("dark")
        for widget in self.allWidgets():
            widget.update()

    def update_glass_frames_theme(self, is_dark):
        print(f"DEBUG: Updating GlassFrames for {'dark' if is_dark else 'light'} mode.")
        for widget in self.allWidgets():
            if isinstance(widget, GlassFrame):
                widget_name = widget.objectName() if widget.objectName() else str(widget)
                print(f"DEBUG: Updating GlassFrame: {widget_name}")
                if is_dark:
                    widget.glass_color = QColor(40, 42, 48, 235) 
                    widget.border_color = QColor(70, 75, 85, 180)
                else: 
                    widget.glass_color = QColor(250, 250, 255, 220)
                    widget.border_color = QColor(180, 195, 235, 120)
                widget.update()

    def set_application_language_direction(self, lang_code):
        print(f"INFO: Setting application layout direction for language: {lang_code}")
        if lang_code == "ar":
            QLocale.setDefault(QLocale(QLocale.Language.Arabic, QLocale.Country.SaudiArabia))
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        if hasattr(self, 'tray_manager') and self.tray_manager:
            if self.tray_manager.settings_window_instance and \
               self.tray_manager.settings_window_instance.isVisible():
                print(f"INFO: Notifying visible SettingsWindow to update layout direction for lang {lang_code}")
                self.tray_manager.settings_window_instance.update_layout_direction(lang_code)

    def quit(self):
        print("INFO: ZakirApp received quit signal.")
        if hasattr(self, 'reminder_service') and self.reminder_service:
            self.reminder_service.stop_service()
        super().quit()

if __name__ == '__main__':
    print("--- MAIN: Application Start ---")
    QApplication.setApplicationName("Zakir")
    QApplication.setOrganizationName("ZakirAppOrg") 
    app = ZakirApp(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion")) 
    print("--- MAIN: Entering app.exec() ---")
    exit_code = app.exec()
    print(f"--- MAIN: Application exited with code: {exit_code} ---")
    sys.exit(exit_code)