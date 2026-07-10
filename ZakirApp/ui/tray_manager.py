# ui/tray_manager.py
import os
import sys
import traceback
from PyQt6.QtWidgets import (
    QSystemTrayIcon, QMenu, QMessageBox, QDialog, QVBoxLayout, QTextEdit, 
    QPushButton, QApplication, QScrollArea, QWidget, QLabel
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, QTimer, QLocale

# Import your modules - adjust paths if structure is different
# from core.prayer_times_manager import PrayerTimesManager (already passed in __init__)
from ui.settings_window import SettingsWindow # Assuming SettingsWindow is in ui directory

class TrayManager:
    def __init__(self, app, settings_manager, localization_manager, adhkar_manager, prayer_times_manager, base_path):
        self.app = app # QApplication instance
        self.settings_mngr = settings_manager
        self.lm = localization_manager
        self.adhkar_mngr = adhkar_manager
        self.prayer_times_mngr = prayer_times_manager
        self.base_path = base_path
        
        self.settings_window_instance = None # To hold the single instance of SettingsWindow
        self.adhkar_dialog_instance = None   # For Adhkar display
        self.prayer_times_dialog_instance = None # For Prayer Times display

        # Icon paths (ensure these exist in your resources/assets folder)
        self.app_icon_path = os.path.join(self.base_path, "resources", "assets", "icon.png")
        self.settings_icon_path = os.path.join(self.base_path, "resources", "assets", "settings.png")
        self.exit_icon_path = os.path.join(self.base_path, "resources", "assets", "exit.png")
        self.prayer_icon_path = os.path.join(self.base_path, "resources", "assets", "prayer.png") # Example
        self.adhkar_icon_path = os.path.join(self.base_path, "resources", "assets", "adhkar.png") # Example
        self.update_icon_path = os.path.join(self.base_path, "resources", "assets", "update.png") # Example
        self.toggle_on_icon_path = os.path.join(self.base_path, "resources", "assets", "toggle_on.png") # Example
        self.toggle_off_icon_path = os.path.join(self.base_path, "resources", "assets", "toggle_off.png") # Example


        if not os.path.exists(self.app_icon_path):
            print(f"CRITICAL: App icon not found at: {self.app_icon_path}")
            # Fallback or error handling
            # For now, let it proceed, QIcon will handle missing file gracefully (shows blank)
        
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(QIcon(self.app_icon_path))
        self.tray_icon.setToolTip(self.lm.get_string("app_tooltip", "Zakir App"))
        self.tray_icon.setVisible(True)

        self.tray_menu = QMenu()
        self._setup_tray_menu_actions() # Method to create/update actions

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._handle_tray_activation)

        # Connect to PrayerTimesManager signals
        if self.prayer_times_mngr:
            self.prayer_times_mngr.next_prayer_updated.connect(self.update_tray_tooltip_with_next_prayer)
            self.prayer_times_mngr.prayer_times_updated.connect(self.update_prayer_times_submenu)
            # Initial update for prayer times submenu if data is already available
            self.update_prayer_times_submenu(self.prayer_times_mngr.get_todays_timings_dict())


    def _setup_tray_menu_actions(self):
        self.tray_menu.clear() # Clear previous actions if re-building

        # Settings Action
        settings_action = QAction(QIcon(self.settings_icon_path), self.lm.get_string("settings"), self.tray_menu)
        settings_action.triggered.connect(self.open_settings_window)
        self.tray_menu.addAction(settings_action)

        self.tray_menu.addSeparator()

        # Adhkar Submenu
        adhkar_main_menu = QMenu(self.lm.get_string("adhkar"), self.tray_menu)
        if os.path.exists(self.adhkar_icon_path): adhkar_main_menu.setIcon(QIcon(self.adhkar_icon_path))
        
        morning_action = QAction(self.lm.get_string("morning_adhkar"), adhkar_main_menu)
        morning_action.triggered.connect(lambda: self.show_adhkar_dialog("morning"))
        adhkar_main_menu.addAction(morning_action)

        evening_action = QAction(self.lm.get_string("evening_adhkar"), adhkar_main_menu)
        evening_action.triggered.connect(lambda: self.show_adhkar_dialog("evening"))
        adhkar_main_menu.addAction(evening_action)

        sleep_action = QAction(self.lm.get_string("sleep_adhkar"), adhkar_main_menu)
        sleep_action.triggered.connect(lambda: self.show_adhkar_dialog("sleep"))
        adhkar_main_menu.addAction(sleep_action)
        self.tray_menu.addMenu(adhkar_main_menu)

        self.tray_menu.addSeparator()

        # Prayer Times Actions
        self.prayer_times_main_menu = QMenu(self.lm.get_string("prayer_times_menu_title"), self.tray_menu)
        if os.path.exists(self.prayer_icon_path): self.prayer_times_main_menu.setIcon(QIcon(self.prayer_icon_path))
        
        show_pt_action = QAction(self.lm.get_string("show_prayer_times_action", "Show Today's Prayer Times"), self.prayer_times_main_menu)
        show_pt_action.triggered.connect(self.show_prayer_times_dialog)
        self.prayer_times_main_menu.addAction(show_pt_action)

        update_pt_action = QAction(QIcon(self.update_icon_path), self.lm.get_string("update_prayer_times_action"), self.prayer_times_main_menu)
        update_pt_action.triggered.connect(self.force_fetch_prayer_times)
        self.prayer_times_main_menu.addAction(update_pt_action)
        
        self.prayer_times_submenu_dynamic = QMenu(self.lm.get_string("todays_times_submenu", "Today's Times"), self.prayer_times_main_menu)
        self.prayer_times_main_menu.addMenu(self.prayer_times_submenu_dynamic)
        self.update_prayer_times_submenu({}) # Initial empty state

        self.tray_menu.addMenu(self.prayer_times_main_menu)

        self.tray_menu.addSeparator()

        # Toggle Reminders Action
        self.toggle_reminders_action = QAction(self.tray_menu) # Icon set dynamically
        self.toggle_reminders_action.triggered.connect(self.toggle_reminder_service_status)
        self.update_toggle_reminders_action_text() # Set initial text and icon
        self.tray_menu.addAction(self.toggle_reminders_action)

        # Exit Action
        exit_action = QAction(QIcon(self.exit_icon_path), self.lm.get_string("exit_app"), self.tray_menu)
        exit_action.triggered.connect(self.app.quit) # QApplication.quit()
        self.tray_menu.addAction(exit_action)

    def _handle_tray_activation(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger: # Single click
            # Could open a quick summary window or settings
            self.open_settings_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings_window()
        # ContextMenu (right-click) is handled by self.tray_icon.setContextMenu()

    def open_settings_window(self):
        try:
            if self.settings_window_instance is None:
                print("DEBUG: TrayManager - Creating new SettingsWindow instance.")
                self.settings_window_instance = SettingsWindow(
                    settings_manager=self.settings_mngr,
                    localization_manager=self.lm,
                    adhkar_manager=self.adhkar_mngr,
                    base_path=self.base_path
                )
                # Connect signals from SettingsWindow
                self.settings_window_instance.language_changed_signal.connect(self.handle_language_change_from_settings)
                self.settings_window_instance.theme_changed_signal.connect(self.handle_theme_change_from_settings)
                self.settings_window_instance.settings_applied_signal.connect(self.handle_settings_applied_app_wide)
                self.settings_window_instance.finished.connect(self._on_settings_window_finished)

            if self.settings_window_instance.isHidden():
                print("DEBUG: TrayManager - SettingsWindow was hidden, showing.")
                self.settings_window_instance.show()
            
            self.settings_window_instance.raise_() # Bring to front
            self.settings_window_instance.activateWindow() # Ensure it has focus
            
            # Force a repaint or update if using custom drawing like GlassFrame
            QTimer.singleShot(50, lambda: self.settings_window_instance.update() if self.settings_window_instance else None)


        except Exception as e:
            print(f"ERROR: TrayManager - Failed to open SettingsWindow: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(None, self.lm.get_string("error"), 
                                 f"Could not open SettingsWindow: {e}")

    def _on_settings_window_finished(self, result_code):
        # This is connected to QDialog.finished signal
        print(f"DEBUG: TrayManager - SettingsWindow finished with result: {result_code}")
        # No need to delete instance if WA_DeleteOnClose is False (default for QDialog unless set otherwise)
        # SettingsWindow is hidden by its own accept/reject or custom close.
        # self.settings_window_instance = None # Only if you want to recreate it every time

    def handle_language_change_from_settings(self, new_lang_code):
        print(f"INFO: TrayManager - Language change to '{new_lang_code}' initiated from settings.")
        if self.lm.get_current_language() != new_lang_code:
            self.lm.load_language(new_lang_code)
            QApplication.setLayoutDirection(Qt.LayoutDirection.RightToLeft if new_lang_code == "ar" else Qt.LayoutDirection.LeftToRight)
            self.update_tray_menu_texts() # Update menu item texts
            self.tray_icon.setToolTip(self.lm.get_string("app_tooltip", "Zakir App"))
            # Notify AdhkarManager to reload its data for the new language
            if self.adhkar_mngr: self.adhkar_mngr.set_language(new_lang_code)
            # Potentially inform other parts of the app
            print(f"INFO: TrayManager - Application language and direction updated to {new_lang_code}.")
            # Show restart note
            QMessageBox.information(self.settings_window_instance, # Parent to settings window if open
                                    self.lm.get_string("language_changed_title"),
                                    self.lm.get_string("language_change_restart_note"))


    def handle_theme_change_from_settings(self, new_theme_key):
        print(f"INFO: TrayManager - Theme change to '{new_theme_key}' initiated from settings.")
        # The actual theme application (palette, stylesheet) should be handled by the main app class
        if hasattr(self.app, 'apply_theme_preference'):
            self.app.apply_theme_preference(new_theme_key)
        else:
            print("WARN: TrayManager - Main app does not have 'apply_theme_preference' method.")

    def handle_settings_applied_app_wide(self):
        """Called when settings are applied (OK or Apply in SettingsWindow)."""
        print("INFO: TrayManager - App-wide settings changes are being applied.")
        # Reminder Service update
        if hasattr(self.app, 'reminder_service') and self.app.reminder_service:
            self.app.reminder_service.update_timer_interval()
            is_active = self.settings_mngr.get("reminders_active", True)
            self.app.reminder_service.toggle_reminders(active=is_active) # Will also update persisted setting
        self.update_toggle_reminders_action_text()

        # Prayer Times Service update (e.g., re-fetch if location changed, re-schedule alerts)
        if self.prayer_times_mngr:
            if self.settings_mngr.get("prayer_times_active", False):
                self.prayer_times_mngr.clear_cached_ip_location() # Clear if method might have changed
                self.prayer_times_mngr.fetch_prayer_times_for_date() # This will emit signals
            else: # If prayer times became inactive
                self.prayer_times_mngr.daily_prayer_times_data = {}
                self.prayer_times_mngr.last_fetched_date = None
                self.prayer_times_mngr.prayer_times_updated.emit({})
                self.prayer_times_mngr.next_prayer_updated.emit(self.lm.get_string("prayer_times_not_active_message"),"","")
                
        # Re-schedule prayer alerts if ReminderService handles them
        if hasattr(self.app, 'reminder_service') and \
           hasattr(self.app.reminder_service, 'schedule_prayer_related_alerts'):
            self.app.reminder_service.schedule_prayer_related_alerts()


    def update_tray_menu_texts(self):
        # This rebuilds the menu, simpler than finding and updating each action.
        self._setup_tray_menu_actions()
        self.tray_icon.setContextMenu(self.tray_menu) # Re-assign the updated menu
        print("INFO: TrayManager - Tray menu texts updated for new language.")


    def _create_basic_dialog(self, title_key, default_title):
        dialog = QDialog(self.settings_window_instance) # Parent to settings window if open, else None
        dialog.setWindowTitle(self.lm.get_string(title_key, default_title))
        # Apply some basic styling if needed, or let it inherit app style
        dialog.setMinimumWidth(350)
        dialog.setMinimumHeight(250)
        
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        # Basic text edit styling
        text_edit.setStyleSheet("QTextEdit { background-color: #f0f0f0; color: #333; border: 1px solid #ccc; border-radius: 4px; font-size: 10pt; }")
        
        scroll_area = QScrollArea() # Ensure content is scrollable
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(text_edit)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        layout.addWidget(scroll_area)
        
        close_button = QPushButton(self.lm.get_string("close", "Close"))
        close_button.clicked.connect(dialog.accept)
        close_button.setStyleSheet("QPushButton { padding: 5px 15px; font-size: 9pt; }") # Basic button style
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        return dialog, text_edit

    def show_adhkar_dialog(self, category_key):
        if self.adhkar_mngr:
            # Use AdhkarManager's method that prepares HTML (assuming it exists)
            # Or, format it here. For now, let's assume AdhkarManager has:
            # adhkar_html = self.adhkar_mngr.get_adhkar_html_for_category(category_key)
            
            # Manual HTML formatting here:
            adhkar_items = self.adhkar_mngr.get_adhkar_by_category(category_key) # Gets list of dicts
            if not adhkar_items:
                QMessageBox.information(None, self.lm.get_string(f"{category_key}_adhkar", category_key.capitalize()),
                                        self.lm.get_string("no_adhkar_for_category", "No Adhkar found for this category."))
                return

            html_output = f"<h2 style='color: #337ab7;'>{self.lm.get_string(f'{category_key}_adhkar', category_key.capitalize())}</h2><ul>"
            for item in adhkar_items:
                text = item.get("text", "N/A")
                count = item.get("count", "")
                benefit = item.get("benefit", "")
                html_output += f"<li style='margin-bottom: 10px;'><strong>{text}</strong>"
                if count and count != -1: html_output += f" <em style='color: #5cb85c;'>({self.lm.get_string('count_prefix','Count')}: {count})</em>"
                if benefit: html_output += f"<br><small style='color: #777;'>{benefit}</small>"
                html_output += "</li>"
            html_output += "</ul>"

            if not html_output:
                html_output = f"<p>{self.lm.get_string('no_adhkar_to_display')}</p>"

            if self.adhkar_dialog_instance is None or not self.adhkar_dialog_instance.isVisible():
                self.adhkar_dialog_instance, text_edit = self._create_basic_dialog(
                    f"{category_key}_adhkar", f"{category_key.capitalize()} Adhkar"
                )
            else: # Dialog exists, just update content
                text_edit = self.adhkar_dialog_instance.findChild(QTextEdit)
                self.adhkar_dialog_instance.setWindowTitle(self.lm.get_string(f"{category_key}_adhkar", f"{category_key.capitalize()} Adhkar"))


            if text_edit: text_edit.setHtml(html_output)
            self.adhkar_dialog_instance.show()
            self.adhkar_dialog_instance.activateWindow()


    def show_prayer_times_dialog(self):
        if self.prayer_times_mngr:
            if not self.settings_mngr.get("prayer_times_active", False):
                QMessageBox.information(None, self.lm.get_string("prayer_times_menu_title"), 
                                        self.lm.get_string("prayer_times_not_active_message"))
                return

            timings_list = self.prayer_times_mngr.get_formatted_daily_timings_for_display() # List of (name, time)
            
            if not timings_list:
                QMessageBox.information(None, self.lm.get_string("prayer_times_menu_title"), 
                                        self.lm.get_string("no_prayer_times_data"))
                return

            current_date_str = self.prayer_times_mngr.last_fetched_date.strftime("%Y-%m-%d") if self.prayer_times_mngr.last_fetched_date else "N/A"
            timezone_str = self.prayer_times_mngr.get_current_timezone_name()

            html_output = f"<h2 style='color: #337ab7; text-align:center;'>{self.lm.get_string('prayer_times_menu_title')}</h2>"
            html_output += f"<p style='text-align:center; color: #555;'>{self.lm.get_string('date_label', 'Date')}: {current_date_str} ({timezone_str})</p>"
            html_output += "<table width='100%' style='border-collapse: collapse; margin-top:10px;'>"
            html_output += "<tr><th style='text-align:left; padding: 8px; border-bottom: 1px solid #ddd; background-color: #f9f9f9;'>{prayer_col}</th><th style='text-align:right; padding: 8px; border-bottom: 1px solid #ddd; background-color: #f9f9f9;'>{time_col}</th></tr>".format(
                prayer_col=self.lm.get_string("prayer_col_header", "Prayer"),
                time_col=self.lm.get_string("time_col_header", "Time")
            )

            for name, time in timings_list:
                html_output += f"<tr><td style='padding: 6px; border-bottom: 1px solid #eee;'>{name}</td><td style='text-align:right; padding: 6px; border-bottom: 1px solid #eee;'>{time}</td></tr>"
            html_output += "</table>"

            if self.prayer_times_dialog_instance is None or not self.prayer_times_dialog_instance.isVisible():
                self.prayer_times_dialog_instance, text_edit = self._create_basic_dialog(
                     "prayer_times_menu_title", "Prayer Times"
                )
            else:
                text_edit = self.prayer_times_dialog_instance.findChild(QTextEdit)
                self.prayer_times_dialog_instance.setWindowTitle(self.lm.get_string("prayer_times_menu_title"))


            if text_edit: text_edit.setHtml(html_output)
            self.prayer_times_dialog_instance.show()
            self.prayer_times_dialog_instance.activateWindow()


    def force_fetch_prayer_times(self):
        if self.prayer_times_mngr:
            if not self.settings_mngr.get("prayer_times_active", False):
                QMessageBox.information(None, self.lm.get_string("update_prayer_times_action"), 
                                        self.lm.get_string("prayer_times_not_active_message"))
                return

            print("INFO: TrayManager - Force fetching prayer times...")
            self.prayer_times_mngr.clear_cached_ip_location() # Clear IP cache if method is auto_ip
            # Fetching will emit signals that update UI (tooltip, submenu, and potentially main window if open)
            # and show success/failure via the fetch_error signal if connected.
            # For now, just show a message box from here.
            if self.prayer_times_mngr.fetch_prayer_times_for_date(): # Pass today's date
                 QMessageBox.information(None, self.lm.get_string("success_title", "Success"), 
                                         self.lm.get_string("prayer_times_updated"))
            else:
                 QMessageBox.warning(None, self.lm.get_string("error"), 
                                       self.lm.get_string("prayer_times_update_failed_manual", "Failed to update prayer times. Check settings or network."))


    def update_toggle_reminders_action_text(self):
        if not hasattr(self, 'toggle_reminders_action'): return

        is_active = self.settings_mngr.get("reminders_active", True)
        if is_active:
            self.toggle_reminders_action.setText(self.lm.get_string("toggle_reminders_active")) # Text for "Pause Reminders"
            if os.path.exists(self.toggle_off_icon_path): self.toggle_reminders_action.setIcon(QIcon(self.toggle_off_icon_path))
        else:
            self.toggle_reminders_action.setText(self.lm.get_string("toggle_reminders_paused")) # Text for "Resume Reminders"
            if os.path.exists(self.toggle_on_icon_path): self.toggle_reminders_action.setIcon(QIcon(self.toggle_on_icon_path))

    def toggle_reminder_service_status(self):
        current_status = self.settings_mngr.get("reminders_active", True)
        new_status = not current_status
        
        # Persist the new status first
        self.settings_mngr.set("reminders_active", new_status) 
        
        # Then toggle the service if it exists in the app
        if hasattr(self.app, 'reminder_service') and self.app.reminder_service:
            self.app.reminder_service.toggle_reminders(active=new_status)
        else:
            print("WARN: TrayManager - ReminderService not found in app instance.")
            
        self.update_toggle_reminders_action_text() # Update menu item text/icon

    def update_tray_tooltip_with_next_prayer(self, prayer_name, prayer_time_str, time_remaining_str):
        if not self.settings_mngr.get("prayer_times_active", False):
            self.tray_icon.setToolTip(self.lm.get_string("app_tooltip"))
            return

        if prayer_name and prayer_time_str:
            tooltip_text = self.lm.get_string("next_prayer_label_short", "{prayer_name} at {time} (in {remaining})").format(
                prayer_name=prayer_name, 
                time=prayer_time_str, 
                remaining=time_remaining_str
            )
            self.tray_icon.setToolTip(tooltip_text)
        elif prayer_name == self.lm.get_string("prayer_times_not_active_message") or \
             prayer_name == self.lm.get_string("no_prayer_times_data"):
            self.tray_icon.setToolTip(f"{self.lm.get_string('app_tooltip')} - {prayer_name}")
        else: # Fallback
            self.tray_icon.setToolTip(self.lm.get_string("app_tooltip"))

    def update_prayer_times_submenu(self, timings_dict): # timings_dict is {InternalKey: "HH:MM"}
        self.prayer_times_submenu_dynamic.clear()
        if not self.settings_mngr.get("prayer_times_active", False) or not timings_dict:
            no_data_action = QAction(self.lm.get_string("no_prayer_times_data_short", "No Data"), self.prayer_times_submenu_dynamic)
            no_data_action.setEnabled(False)
            self.prayer_times_submenu_dynamic.addAction(no_data_action)
            return

        for prayer_key_internal in PrayerTimesManager.PRAYER_ORDER: # Use PRAYER_ORDER for consistency
            time_str = timings_dict.get(prayer_key_internal)
            if time_str:
                display_name = self.lm.get_string(f"prayer_name_{prayer_key_internal.lower()}", prayer_key_internal)
                action_text = f"{display_name}: {time_str}"
                action = QAction(action_text, self.prayer_times_submenu_dynamic)
                action.setEnabled(False) # Just for display
                self.prayer_times_submenu_dynamic.addAction(action)