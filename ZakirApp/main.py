# main.py
import sys
import os
import traceback
import platform 

from PyQt6.QtWidgets import QApplication, QMessageBox, QStyleFactory
from PyQt6.QtCore import QLocale, Qt, QTimer
from PyQt6.QtGui import QPalette, QColor

# Core components
from core.settings_manager import SettingsManager
from core.localization_manager import LocalizationManager
from core.adhkar_manager import AdhkarManager
from core.prayer_times_manager import PrayerTimesManager
from core.reminder_service import ReminderService

# UI components
from ui.tray_manager import TrayManager
# SettingsWindow is managed by TrayManager, so direct import here might not be needed
# from ui.settings_window import SettingsWindow 

class ZakirApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        print("INFO: ZakirApp.__init__ started.")
        self.setQuitOnLastWindowClosed(False) # Keep app running with only tray icon
        print("INFO: ZakirApp - setQuitOnLastWindowClosed(False) is active.")

        # Determine base_path for resources
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running in a PyInstaller bundle
            self.base_path = sys._MEIPASS
        else:
            # Running in a normal Python environment
            self.base_path = os.path.dirname(os.path.abspath(__file__))
        print(f"INFO: ZakirApp - Application base path: {self.base_path}")

        # Initialize core components
        self.lm = None
        self.settings_mngr = None
        self.adhkar_mngr = None
        self.prayer_times_mngr = None
        self.reminder_service = None # Will hold ReminderService instance
        self.tray_manager = None     # Will hold TrayManager instance

        try:
            # 1. Localization Manager (no dependencies for basic init)
            self.lm = LocalizationManager(base_path=self.base_path)
            print("INFO: ZakirApp - LocalizationManager initialized.")

            # 2. Settings Manager (depends on lm for error messages)
            self.settings_mngr = SettingsManager(app_name="ZakirApp", lm=self.lm) # Pass app_name
            print("INFO: ZakirApp - SettingsManager initialized.")
            if not self.settings_mngr: # Should not happen if constructor doesn't raise
                raise RuntimeError("SettingsManager failed to initialize.")

            # 3. Load initial language from settings and apply
            initial_lang = self.settings_mngr.get("language", "ar") # Default to 'ar'
            self.lm.load_language(initial_lang)
            self.set_application_language_direction(initial_lang)
            print(f"INFO: ZakirApp - Initial language '{initial_lang}' loaded and applied.")

            # 4. Adhkar Manager (depends on base_path, initial_lang, lm for specific messages)
            self.adhkar_mngr = AdhkarManager(base_path=self.base_path, language_code=initial_lang)
            self.adhkar_mngr.set_localization_manager(self.lm) # For "no_dhikr_available"
            print("INFO: ZakirApp - AdhkarManager initialized.")

            # 5. Prayer Times Manager (depends on settings_mngr, lm)
            self.prayer_times_mngr = PrayerTimesManager(settings_manager=self.settings_mngr, lm=self.lm)
            print("INFO: ZakirApp - PrayerTimesManager initialized.")

            # 6. Tray Manager (depends on many core components and self.app)
            self.tray_manager = TrayManager(
                app=self, 
                settings_manager=self.settings_mngr,
                localization_manager=self.lm,
                adhkar_manager=self.adhkar_mngr,
                prayer_times_manager=self.prayer_times_mngr,
                base_path=self.base_path
            )
            print("INFO: ZakirApp - TrayManager initialized.")
            if not self.tray_manager.tray_icon: # Critical if tray icon failed
                 raise RuntimeError("TrayManager failed to initialize tray icon.")

            # 7. Reminder Service (depends on settings, adhkar, tray_icon, base_path, lm)
            self.reminder_service = ReminderService(
                settings_manager=self.settings_mngr,
                adhkar_manager=self.adhkar_mngr,
                tray_icon=self.tray_manager.tray_icon, # Pass the actual QSystemTrayIcon
                base_path=self.base_path,
                lm=self.lm
            )
            print("INFO: ZakirApp - ReminderService initialized.")

            # 8. Apply initial theme
            initial_theme = self.settings_mngr.get("theme", "system")
            self.apply_theme_preference(initial_theme)
            print(f"INFO: ZakirApp - Initial theme '{initial_theme}' applied.")
            
            # Initial fetch for prayer times is now handled within PrayerTimesManager's __init__
            # if the feature is active in settings.

        except Exception as e_init:
            critical_error_title = "Initialization Error"
            critical_error_message = f"A critical error occurred during application startup: {e_init}\n\nThe application will now exit."
            if self.lm and hasattr(self.lm, 'get_string'): # Use lm if available
                critical_error_title = self.lm.get_string("error", critical_error_title)
                critical_error_message = self.lm.get_string("startup_error_message", "{error}").format(error=critical_error_message)
            
            print(f"FATAL ERROR during ZakirApp initialization: {e_init}")
            traceback.print_exc()
            
            # Ensure a message box can be shown even if GUI elements failed
            # Create a temporary QApplication if self (the app instance) might be broken
            temp_app_for_msgbox = QApplication.instance() if QApplication.instance() else QApplication(sys.argv)
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle(critical_error_title)
            msg_box.setText(critical_error_message)
            msg_box.exec()
            sys.exit(1) # Exit if critical initialization fails

        print("INFO: ZakirApp - Initialization sequence finished successfully.")

    def set_application_language_direction(self, lang_code):
        print(f"INFO: ZakirApp - Setting application layout direction for language: {lang_code}")
        if lang_code == "ar":
            QLocale.setDefault(QLocale(QLocale.Language.Arabic, QLocale.Country.SaudiArabia)) # Example country
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else: # Default to LTR for English and other languages
            QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        
        # If settings window exists and is visible, tell it to update its direction
        if self.tray_manager and self.tray_manager.settings_window_instance and \
           self.tray_manager.settings_window_instance.isVisible():
            print(f"INFO: ZakirApp - Notifying visible SettingsWindow to update layout for lang {lang_code}")
            self.tray_manager.settings_window_instance.update_ui_texts_and_direction()


    def apply_theme_preference(self, theme_key):
        print(f"INFO: ZakirApp - Applying theme preference: '{theme_key}'")
        if theme_key == "dark":
            self.setStyle(QStyleFactory.create("Fusion")) # Fusion style works well with dark palettes
            dark_palette = QPalette()
            # Define colors for dark theme (example from a common dark theme)
            dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
            dark_palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42)) # Text input backgrounds
            dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66)) # Used in some views
            dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25,25,25)) # Darker tooltip
            dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
            dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
            dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
            dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red) # For very important text (e.g., errors)
            dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218)) # Blue for links
            dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218)) # Selection highlight
            dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
            
            # Disabled states
            disabled_text_color = QColor(127, 127, 127)
            dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_text_color)
            dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_text_color)
            dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_text_color)
            dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(80,80,80))

            self.setPalette(dark_palette)
            # For GlassFrame, it has its own theme handling via its paintEvent
            # but we might need to tell it to repaint if its colors depend on app theme.
            # SettingsWindow now handles its own stylesheet for more granular control.

        elif theme_key == "light":
            self.setStyle(QStyleFactory.create("Fusion")) # Or "Windows", "macOS" depending on platform
            light_palette = QPalette() # Create a default light palette
            # Define colors for light theme (Qt's default is often good enough)
            # You can customize this further if needed.
            # Example:
            # light_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
            # light_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
            # ... and so on for other roles
            self.setPalette(QApplication.style().standardPalette()) # Reset to default style's palette

        else: # "system" or unknown
            # For "system", we don't apply a custom palette. Qt will use the OS's theme.
            # On some systems, Fusion style might look out of place if OS is light.
            # You might want to use platform-specific styles:
            # if platform.system() == "Windows": self.setStyle("WindowsVista") # or "Windows"
            # elif platform.system() == "Darwin": self.setStyle("macOS") 
            # else: self.setStyle(QStyleFactory.create("Fusion")) # Fallback
            self.setStyle(QStyleFactory.keys()[0] if QStyleFactory.keys() else "Fusion") # Use first available or Fusion
            self.setPalette(QApplication.style().standardPalette()) # Reset to default

        # Update all widgets to reflect palette changes
        for widget in self.allWidgets():
            widget.setPalette(self.palette()) # Apply the app's palette
            widget.update()
            
        # Specifically tell SettingsWindow to re-evaluate its custom stylesheet if it exists
        if self.tray_manager and self.tray_manager.settings_window_instance:
            if hasattr(self.tray_manager.settings_window_instance, 'reapply_stylesheet_for_theme'):
                self.tray_manager.settings_window_instance.reapply_stylesheet_for_theme(theme_key)


    def quit(self):
        print("INFO: ZakirApp - quit() called.")
        if hasattr(self, 'reminder_service') and self.reminder_service:
            print("INFO: ZakirApp - Stopping ReminderService...")
            self.reminder_service.stop_service()
        
        # Add cleanup for other services if needed (e.g., stopping timers in PrayerTimesManager)
        if hasattr(self, 'prayer_times_mngr') and self.prayer_times_mngr:
            if hasattr(self.prayer_times_mngr, 'data_refresh_timer'): self.prayer_times_mngr.data_refresh_timer.stop()
            if hasattr(self.prayer_times_mngr, 'next_prayer_check_timer'): self.prayer_times_mngr.next_prayer_check_timer.stop()

        print("INFO: ZakirApp - Calling super().quit().")
        super().quit()


if __name__ == '__main__':
    print("--- ZakirApp Main: Application Start ---")
    # High DPI scaling attribute (set before QApplication instantiation)
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    QApplication.setApplicationName("Zakir")
    QApplication.setOrganizationName("ZakirAppOrg") # Optional

    app_instance = ZakirApp(sys.argv)
    
    print("--- ZakirApp Main: Entering app_instance.exec() ---")
    exit_code = app_instance.exec()
    print(f"--- ZakirApp Main: Application exited with code: {exit_code} ---")
    sys.exit(exit_code)