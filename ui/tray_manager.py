import os
import traceback
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QDialog, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtGui import QIcon, QAction, QFont
from PyQt6.QtCore import QLocale, Qt, QTimer

from core.prayer_times_manager import PrayerTimesManager
from ui.settings_window import SettingsWindow

class TrayManager:
    def __init__(self, app, settings_manager, localization_manager, adhkar_manager, prayer_times_manager, base_path):
        self.app = app
        self.settings_manager = settings_manager
        self.lm = localization_manager
        self.adhkar_manager = adhkar_manager
        self.prayer_times_manager = prayer_times_manager
        self.base_path = base_path
        self.settings_window_instance = None

        # تحميل أيقونة النظام
        self.icon_path = os.path.join(self.base_path, "assets", "icon.png")
        if not os.path.exists(self.icon_path):
            QMessageBox.critical(None, "Error", f"Icon file not found at: {self.icon_path}")
            sys.exit(1)

        # إنشاء أيقونة النظام
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(QIcon(self.icon_path))
        self.tray_icon.setVisible(True)

        # إنشاء قائمة النظام
        self.tray_menu = QMenu()
        self.setup_tray_menu()
        self.tray_icon.setContextMenu(self.tray_menu)

        # ربط الإشارات
        self.tray_icon.activated.connect(self.handle_tray_activation)

    def setup_tray_menu(self):
        # إضافة عناصر القائمة
        settings_action = QAction(self.lm.get_string("settings", "الإعدادات"), self.tray_menu)
        settings_action.setIcon(QIcon(os.path.join(self.base_path, "assets", "settings.png")))
        self.tray_menu.addAction(settings_action)
        settings_action.triggered.connect(self.open_settings)

        self.tray_menu.addSeparator()

        # إضافة قائمة فرعية للأذكار
        adhkar_menu = QMenu(self.lm.get_string("adhkar", "الأذكار"), self.tray_menu)
        morning_action = QAction(self.lm.get_string("morning_adhkar", "أذكار الصباح"), adhkar_menu)
        evening_action = QAction(self.lm.get_string("evening_adhkar", "أذكار المساء"), adhkar_menu)
        sleep_action = QAction(self.lm.get_string("sleep_adhkar", "أذكار النوم"), adhkar_menu)
        
        adhkar_menu.addAction(morning_action)
        adhkar_menu.addAction(evening_action)
        adhkar_menu.addAction(sleep_action)
        
        morning_action.triggered.connect(lambda: self.show_adhkar("morning"))
        evening_action.triggered.connect(lambda: self.show_adhkar("evening"))
        sleep_action.triggered.connect(lambda: self.show_adhkar("sleep"))
        
        self.tray_menu.addMenu(adhkar_menu)

        self.tray_menu.addSeparator()

        # إضافة زر مواقيت الصلاة
        prayer_times_action = QAction(self.lm.get_string("prayer_times", "مواقيت الصلاة"), self.tray_menu)
        prayer_times_action.setIcon(QIcon(os.path.join(self.base_path, "assets", "prayer.png")))
        self.tray_menu.addAction(prayer_times_action)
        prayer_times_action.triggered.connect(self.show_prayer_times)

        self.tray_menu.addSeparator()

        exit_action = QAction(self.lm.get_string("exit", "خروج"), self.tray_menu)
        exit_action.setIcon(QIcon(os.path.join(self.base_path, "assets", "exit.png")))
        self.tray_menu.addAction(exit_action)
        exit_action.triggered.connect(self.app.quit)

    def handle_tray_activation(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            try:
                self.open_settings()
            except Exception as e:
                print(f"ERROR: Failed to handle tray activation: {str(e)}")
                QMessageBox.critical(None, "Error", f"Failed to open settings: {e}")

    def force_fetch_prayer_times(self):
        if self.prayer_times_manager:
            self.prayer_times_manager.clear_cached_auto_location_data()
            self.prayer_times_manager.fetch_prayer_times_for_date()
            if self.prayer_times_manager.last_fetch_success:
                QMessageBox.information(None, "Success", self.lm.get_string("prayer_times_updated", "تم تحديث مواقيت الصلاة بنجاح"))
            else:
                QMessageBox.warning(None, "Warning", self.lm.get_string("prayer_times_update_failed", "فشل تحديث مواقيت الصلاة"))

    def open_settings(self):
        try:
            if not self.settings_window_instance or not self.settings_window_instance.isVisible():
                self.settings_window_instance = SettingsWindow(
                    settings_manager=self.settings_manager,
                    localization_manager=self.lm,
                    adhkar_manager=self.adhkar_manager,
                    base_path=self.base_path
                )
                self.settings_window_instance.finished.connect(self.handle_settings_dialog_finished)
                self.settings_window_instance.setWindowFlags(
                    self.settings_window_instance.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
                )
                self.settings_window_instance.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
            
            # تحديث حالة النافذة
            if self.settings_window_instance.isMinimized():
                self.settings_window_instance.showNormal()
            
            self.settings_window_instance.show()
            self.settings_window_instance.raise_()
            self.settings_window_instance.activateWindow()
            
            # إضافة تأخير قصير للتأكد من أن النافذة تظهر بشكل صحيح
            QTimer.singleShot(100, lambda: self.settings_window_instance.activateWindow())
            
        except Exception as e:
            print(f"ERROR: Failed to open settings window: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(None, "Error", f"Could not open SettingsWindow: {e}")

    def handle_settings_dialog_finished(self, result):
        try:
            if result == QDialog.DialogCode.Accepted:
                self.handle_settings_accepted()
            # لا نقوم بحذف النافذة، فقط نخفيها
            if self.settings_window_instance:
                self.settings_window_instance.hide()
        except Exception as e:
            print(f"ERROR: Failed to handle settings dialog finished: {str(e)}")
            QMessageBox.critical(None, "Error", f"Error handling settings: {e}")

    def handle_settings_accepted(self):
        try:
            # تحديث اللغة إذا تم تغييرها
            new_lang = self.settings_manager.get("language", "ar")
            if new_lang != self.lm.get_current_language():
                self.handle_language_change(new_lang)
            
            # تحديث حالة النافذة
            if self.settings_window_instance:
                self.settings_window_instance.hide()
        except Exception as e:
            print(f"ERROR: Failed to handle settings accepted: {str(e)}")
            QMessageBox.critical(None, "Error", f"Error applying settings: {e}")

    def handle_language_change(self, lang_code):
        if self.lm:
            self.lm.load_language(lang_code)
            self.app.set_application_language_direction(lang_code)
            self.update_tray_menu_texts()

    def update_tray_menu_texts(self):
        # تحديث نصوص قائمة النظام
        for action in self.tray_menu.actions():
            if action.text() == self.lm.get_string("settings", "الإعدادات"):
                action.setText(self.lm.get_string("settings", "الإعدادات"))
            elif action.text() == self.lm.get_string("exit", "خروج"):
                action.setText(self.lm.get_string("exit", "خروج"))

    def show_adhkar(self, category):
        if self.adhkar_manager:
            adhkar = self.adhkar_manager.get_adhkar(category)
            if adhkar:
                # إنشاء نافذة منبثقة لعرض الأذكار
                dialog = QDialog()
                dialog.setWindowTitle(self.lm.get_string(f"{category}_adhkar", f"أذكار {category}"))
                layout = QVBoxLayout(dialog)
                
                text_edit = QTextEdit()
                text_edit.setReadOnly(True)
                text_edit.setHtml(adhkar)
                layout.addWidget(text_edit)
                
                close_button = QPushButton(self.lm.get_string("close", "إغلاق"))
                close_button.clicked.connect(dialog.accept)
                layout.addWidget(close_button)
                
                dialog.exec()

    def show_prayer_times(self):
        if self.prayer_times_manager:
            prayer_times = self.prayer_times_manager.get_prayer_times()
            if prayer_times:
                dialog = QDialog()
                dialog.setWindowTitle(self.lm.get_string("prayer_times", "مواقيت الصلاة"))
                dialog.setStyleSheet("""
                    QDialog {
                        background: transparent;
                    }
                    QWidget {
                        background: rgba(40, 42, 48, 235);
                        border-radius: 15px;
                        border: 1px solid rgba(70, 75, 85, 180);
                    }
                    QLabel {
                        color: #ffffff;
                        font-size: 14px;
                        padding: 5px;
                    }
                    QPushButton {
                        background: rgba(66, 153, 225, 0.8);
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 8px;
                    }
                    QPushButton:hover {
                        background: rgba(66, 153, 225, 0.9);
                    }
                """)
                layout = QVBoxLayout(dialog)
                
                text_edit = QTextEdit()
                text_edit.setReadOnly(True)
                text_edit.setHtml(self.format_prayer_times(prayer_times))
                text_edit.setStyleSheet("""
                    QTextEdit {
                        background: rgba(255, 255, 255, 0.1);
                        border: none;
                        border-radius: 10px;
                        color: #ffffff;
                        font-size: 14px;
                        padding: 10px;
                    }
                """)
                layout.addWidget(text_edit)
                
                close_button = QPushButton(self.lm.get_string("close", "إغلاق"))
                close_button.clicked.connect(dialog.accept)
                layout.addWidget(close_button)
                
                dialog.exec()

    def format_prayer_times(self, prayer_times):
        html = """
        <div style='font-family: Arial; font-size: 14px; line-height: 1.6; background-color: rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 10px;'>
            <h2 style='color: #ffffff; text-align: center; margin-bottom: 20px;'>مواقيت الصلاة</h2>
        """
        
        for prayer, time in prayer_times.items():
            html += f"""
            <div style='margin-bottom: 15px; padding: 10px; background-color: rgba(255, 255, 255, 0.1); border-radius: 8px;'>
                <p style='font-size: 18px; color: #ffffff; text-align: right;'>
                    <span style='font-weight: bold;'>{self.lm.get_string(prayer, prayer)}:</span> {time}
                </p>
            </div>
            """
        
        html += "</div>"
        return html