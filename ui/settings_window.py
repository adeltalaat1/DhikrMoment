import sys
import os
from datetime import date 

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QComboBox,
                             QPushButton, QCheckBox, QSpacerItem, QSizePolicy,
                             QDialog, QDialogButtonBox, QMessageBox, QFrame,
                             QListWidget, QListWidgetItem, QSpinBox, QScrollArea, QApplication,
                             QLineEdit, QGroupBox, QFormLayout, QGraphicsBlurEffect, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QLocale, QRectF, pyqtSignal, QTimer 
from PyQt6.QtGui import (QIcon, QPainter, QPainterPath, QColor, 
                         QPen, QBrush, QMouseEvent, QPalette, QLinearGradient)

from core.settings_manager import SettingsManager
from ui.adhan_download_manager import AdhanDownloadWidget


class GlassFrame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.glass_color = QColor(40, 42, 48, 235)  # لون زجاجي داكن افتراضي
        self.border_color = QColor(70, 75, 85, 180)  # لون الحدود
        self.border_radius = 15  # نصف قطر الزوايا
        self.border_width = 1    # سمك الحدود
        self.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # إنشاء مسار للخلفية الزجاجية
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.border_radius, self.border_radius)
        
        # رسم الخلفية الزجاجية مع تأثير الضبابية
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(40, 42, 48, 235))
        gradient.setColorAt(1, QColor(30, 32, 38, 245))
        
        # إضافة تأثير الضبابية
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(10)
        self.setGraphicsEffect(blur_effect)
        
        painter.fillPath(path, QBrush(gradient))
        
        # رسم الحدود مع تأثير التوهج
        pen = QPen(self.border_color, self.border_width)
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # إضافة تأثير التوهج
        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(15)
        glow_effect.setColor(QColor(70, 75, 85, 100))
        glow_effect.setOffset(0, 0)
        self.setGraphicsEffect(glow_effect)

    def set_glass_color(self, color):
        self.glass_color = color
        self.update()

    def set_border_color(self, color):
        self.border_color = color
        self.update()

    def set_border_radius(self, radius):
        self.border_radius = radius
        self.update()

    def set_border_width(self, width):
        self.border_width = width
        self.update()

class SettingsWindow(QDialog):
    language_changed_signal = pyqtSignal(str)

    def __init__(self, settings_manager, localization_manager, adhkar_manager, base_path):
        super().__init__()
        self.settings_manager = settings_manager
        self.lm = localization_manager
        self.adhkar_manager = adhkar_manager
        self.base_path = base_path
        self.init_ui()

    def init_ui(self):
        dialog_main_layout = QVBoxLayout(self)
        dialog_main_layout.setContentsMargins(0, 0, 0, 0)

        self.content_frame = GlassFrame(self)
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(20, 15, 20, 15)

        title_bar_layout = QHBoxLayout()
        self.title_label = QLabel(self.lm.get_string("settings", "Settings"), self.content_frame)
        self.title_label.setObjectName("title_label") 
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14pt; background: transparent; padding: 5px;")
        
        close_button = QPushButton("✕", self.content_frame)
        close_button.setFixedSize(32, 32)
        close_button.setStyleSheet("""
            QPushButton { font-size: 11pt; font-weight: bold; color: #c0c0c0; background-color: transparent; border: none; border-radius: 16px;}
            QPushButton:hover { background-color: rgba(255,255,255,0.07); color: #dddddd; }
            QPushButton:pressed { background-color: rgba(255,255,255,0.1); }
        """)
        close_button.clicked.connect(self.reject)

        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(close_button)
        content_layout.addLayout(title_bar_layout)
        content_layout.addSpacing(10)

        self.tabs = QTabWidget(self.content_frame)
        
        # --- Tab 1: General Settings ---
        self.general_tab = QWidget()
        general_layout = QVBoxLayout(self.general_tab)
        general_layout.setContentsMargins(8, 12, 8, 8)
        lang_layout = QHBoxLayout()
        self.lang_label = QLabel(self.lm.get_string("language", "Language") + ":")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("العربية", "ar")
        lang_layout.addWidget(self.lang_label); lang_layout.addWidget(self.lang_combo); lang_layout.addStretch()
        general_layout.addLayout(lang_layout)
        general_layout.addSpacing(10)
        self.start_with_windows_checkbox = QCheckBox(self.lm.get_string("start_with_windows", "Start with Windows"))
        general_layout.addWidget(self.start_with_windows_checkbox)
        general_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.tabs.addTab(self.general_tab, self.lm.get_string("general", "General"))
        
        # --- Tab 2: Reminder Settings ---
        self.reminder_settings_tab = QWidget()
        reminder_settings_layout = QVBoxLayout(self.reminder_settings_tab)
        reminder_settings_layout.setContentsMargins(8,12,8,8)
        rtype_layout = QHBoxLayout()
        self.rtype_label = QLabel(self.lm.get_string("reminder_type", "Reminder Type:"))
        self.rtype_combo = QComboBox()
        self.rtype_combo.addItem(self.lm.get_string("text_notification", "Text Notification"), "text")
        self.rtype_combo.addItem(self.lm.get_string("sound_notification", "Sound Notification"), "sound")
        self.rtype_combo.addItem(self.lm.get_string("random_notification", "Random (Text/Sound)"), "random")
        rtype_layout.addWidget(self.rtype_label); rtype_layout.addWidget(self.rtype_combo); rtype_layout.addStretch()
        reminder_settings_layout.addLayout(rtype_layout)
        reminder_settings_layout.addSpacing(15)
        interval_layout = QHBoxLayout()
        self.interval_label = QLabel(self.lm.get_string("reminder_interval_minutes", "Interval (minutes):"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(1); self.interval_spinbox.setMaximum(120)
        self.interval_spinbox.setSuffix(f" {self.lm.get_string('minutes_suffix', 'min')}")
        interval_layout.addWidget(self.interval_label); interval_layout.addWidget(self.interval_spinbox); interval_layout.addStretch()
        reminder_settings_layout.addLayout(interval_layout)
        reminder_settings_layout.addSpacing(15)
        self.text_notification_group = QWidget()
        text_notif_layout = QVBoxLayout(self.text_notification_group)
        text_notif_layout.setContentsMargins(0,0,0,0)
        pos_layout = QHBoxLayout()
        self.pos_label = QLabel(self.lm.get_string("notification_position", "Notification Position:"))
        self.pos_combo = QComboBox()
        positions = { "top-left": "Top Left", "top-center": "Top Center", "top-right": "Top Right", "center-left": "Center Left", "center": "Center", "center-right": "Center Right", "bottom-left": "Bottom Left", "bottom-center": "Bottom Center", "bottom-right": "Bottom Right" }
        for key, val_en in positions.items(): self.pos_combo.addItem(self.lm.get_string(f"pos_{key.replace('-', '_')}", default_text=val_en), key)
        pos_layout.addWidget(self.pos_label); pos_layout.addWidget(self.pos_combo); pos_layout.addStretch()
        text_notif_layout.addLayout(pos_layout)
        text_notif_layout.addSpacing(10)
        duration_layout = QHBoxLayout()
        self.duration_label = QLabel(self.lm.get_string("notification_duration_seconds", "Duration (seconds):"))
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setMinimum(1); self.duration_spinbox.setMaximum(60)
        self.duration_spinbox.setSuffix(f" {self.lm.get_string('seconds_suffix', 'sec')}")
        duration_layout.addWidget(self.duration_label); duration_layout.addWidget(self.duration_spinbox); duration_layout.addStretch()
        text_notif_layout.addLayout(duration_layout)
        reminder_settings_layout.addWidget(self.text_notification_group)
        self.rtype_combo.currentTextChanged.connect(self.toggle_text_notification_settings_visibility)
        reminder_settings_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.tabs.addTab(self.reminder_settings_tab, self.lm.get_string("reminders", "Reminders"))

        # --- Tab 3: Content ---
        self.content_tab = QWidget()
        content_tab_layout = QVBoxLayout(self.content_tab)
        content_tab_layout.setContentsMargins(8,12,8,8)
        content_tab_layout.addWidget(QLabel(self.lm.get_string("text_adhkar_display", "Textual Adhkar (Display Only):")))
        self.adhkar_text_area = QScrollArea(); self.adhkar_text_area.setWidgetResizable(True)
        self.adhkar_text_widget = QWidget(); self.adhkar_text_layout = QVBoxLayout(self.adhkar_text_widget)
        self.adhkar_text_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.adhkar_text_area.setWidget(self.adhkar_text_widget)
        content_tab_layout.addWidget(self.adhkar_text_area)
        self.adhkar_text_area.setFixedHeight(150)
        content_tab_layout.addSpacing(15)
        content_tab_layout.addWidget(QLabel(self.lm.get_string("audio_files_select", "Audio Files (Select Favorites):")))
        self.audio_files_listwidget = QListWidget()
        self.audio_files_listwidget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        content_tab_layout.addWidget(self.audio_files_listwidget)
        self.audio_files_listwidget.setFixedHeight(120)
        content_tab_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.tabs.addTab(self.content_tab, self.lm.get_string("content_tab_title", "Content"))

        # --- Tab 4: Prayer Times Settings ---
        self.prayer_times_tab = QWidget()
        pt_main_scroll_area = QScrollArea(self.prayer_times_tab) 
        pt_main_scroll_area.setWidgetResizable(True)
        pt_scroll_content_widget = QWidget()
        pt_layout = QVBoxLayout(pt_scroll_content_widget) 
        pt_layout.setContentsMargins(8, 12, 8, 8)
        pt_main_scroll_area.setWidget(pt_scroll_content_widget)

        self.pt_enable_checkbox = QCheckBox(self.lm.get_string("enable_prayer_times"))
        pt_layout.addWidget(self.pt_enable_checkbox)
        pt_layout.addSpacing(10)

        self.pt_location_group = QGroupBox(self.lm.get_string("location_settings_group", "Location Settings"))
        location_group_layout = QVBoxLayout(self.pt_location_group)
        self.pt_loc_method_label = QLabel(self.lm.get_string("location_method"))
        self.pt_loc_method_combo = QComboBox()
        self.pt_loc_method_combo.addItem(self.lm.get_string("location_method_auto_ip", "Automatic (via IP)"), "auto_ip")
        self.pt_loc_method_combo.addItem(self.lm.get_string("location_method_city_country"), "manual_city")
        self.pt_loc_method_combo.addItem(self.lm.get_string("location_method_coordinates"), "manual_coords")
        
        pt_loc_method_layout = QHBoxLayout()
        pt_loc_method_layout.addWidget(self.pt_loc_method_label)
        pt_loc_method_layout.addWidget(self.pt_loc_method_combo)
        pt_loc_method_layout.addStretch()
        
        location_group_layout.addLayout(pt_loc_method_layout)
        self.pt_city_country_widget = QWidget()
        city_country_form_layout = QFormLayout(self.pt_city_country_widget)
        self.pt_city_label = QLabel(self.lm.get_string("city")); self.pt_city_edit = QLineEdit()
        self.pt_country_label = QLabel(self.lm.get_string("country")); self.pt_country_edit = QLineEdit()
        city_country_form_layout.addRow(self.pt_city_label, self.pt_city_edit)
        city_country_form_layout.addRow(self.pt_country_label, self.pt_country_edit)
        location_group_layout.addWidget(self.pt_city_country_widget)
        self.pt_coords_widget = QWidget()
        coords_form_layout = QFormLayout(self.pt_coords_widget)
        self.pt_latitude_label = QLabel(self.lm.get_string("latitude")); self.pt_latitude_edit = QLineEdit()
        self.pt_longitude_label = QLabel(self.lm.get_string("longitude")); self.pt_longitude_edit = QLineEdit()
        coords_form_layout.addRow(self.pt_latitude_label, self.pt_latitude_edit)
        coords_form_layout.addRow(self.pt_longitude_label, self.pt_longitude_edit)
        location_group_layout.addWidget(self.pt_coords_widget)
        self.pt_loc_method_combo.currentTextChanged.connect(self.toggle_location_input_widgets)
        pt_layout.addWidget(self.pt_location_group)
        pt_layout.addSpacing(10)

        self.pt_calculation_group = QGroupBox(self.lm.get_string("calculation_settings_group", "Calculation Settings"))
        calculation_group_layout = QFormLayout(self.pt_calculation_group)
        self.pt_calc_method_label = QLabel(self.lm.get_string("calculation_method")); self.pt_method_combo = QComboBox()
        calculation_methods = { "0": "Shia Ithna-Ansari", "1": "UoIS, Karachi", "2": "ISNA", "3": "MWL", "4": "Umm al-Qura, Makkah", "5": "Egyptian General Auth.", "7": "UoT, Tehran", "8": "Gulf Region", "9": "Kuwait", "10": "Qatar", "11": "Singapore", "12": "France 12°", "13": "France 15°", "14": "France 18°", "15": "Russia", "16": "MCW" }
        for api_id, name_en in calculation_methods.items(): self.pt_method_combo.addItem(self.lm.get_string(f"calc_method_{api_id}", default_text=name_en), api_id)
        calculation_group_layout.addRow(self.pt_calc_method_label, self.pt_method_combo)
        self.pt_asr_method_label = QLabel(self.lm.get_string("asr_method")); self.pt_asr_method_combo = QComboBox()
        self.pt_asr_method_combo.addItem(self.lm.get_string("asr_method_standard"), "0"); self.pt_asr_method_combo.addItem(self.lm.get_string("asr_method_hanafi"), "1")
        calculation_group_layout.addRow(self.pt_asr_method_label, self.pt_asr_method_combo)
        self.pt_midnight_mode_label = QLabel(self.lm.get_string("midnight_mode")); self.pt_midnight_mode_combo = QComboBox()
        self.pt_midnight_mode_combo.addItem(self.lm.get_string("midnight_mode_standard"), "0"); self.pt_midnight_mode_combo.addItem(self.lm.get_string("midnight_mode_jafari"), "1")
        calculation_group_layout.addRow(self.pt_midnight_mode_label, self.pt_midnight_mode_combo)
        self.pt_lat_adj_label = QLabel(self.lm.get_string("latitude_adjustment_method")); self.pt_lat_adj_combo = QComboBox()
        self.pt_lat_adj_combo.addItem(self.lm.get_string("lat_adj_middle_of_night", "Mid Night"), "0"); self.pt_lat_adj_combo.addItem(self.lm.get_string("lat_adj_one_seventh", "1/7 Night"), "1"); self.pt_lat_adj_combo.addItem(self.lm.get_string("lat_adj_angle_based", "Angle Based"), "3")
        calculation_group_layout.addRow(self.pt_lat_adj_label, self.pt_lat_adj_combo)
        pt_layout.addWidget(self.pt_calculation_group)
        pt_layout.addSpacing(10)
        
        self.pt_tune_group = QGroupBox(self.lm.get_string("prayer_time_tune_group", "Time Adjustments (Tune)"))
        tune_group_layout = QVBoxLayout(self.pt_tune_group)
        self.pt_tune_label_main = QLabel(self.lm.get_string("prayer_time_tune")); self.pt_tune_edit = QLineEdit()
        self.pt_tune_edit.setPlaceholderText("0,0,0,0,0,0,0,0")
        self.pt_tune_help_label = QLabel(self.lm.get_string("tune_help_text")); self.pt_tune_help_label.setWordWrap(True)
        tune_group_layout.addWidget(self.pt_tune_label_main); tune_group_layout.addWidget(self.pt_tune_edit); tune_group_layout.addWidget(self.pt_tune_help_label)
        pt_layout.addWidget(self.pt_tune_group)
        pt_layout.addSpacing(15)

        self.pt_alerts_group = QGroupBox(self.lm.get_string("prayer_alerts_group", "Prayer Alerts"))
        alerts_group_layout = QFormLayout(self.pt_alerts_group)
        self.pt_pre_adhan_alert_checkbox = QCheckBox(self.lm.get_string("enable_pre_adhan_alert", "Enable Pre-Adhan Alert"))
        alerts_group_layout.addRow(self.pt_pre_adhan_alert_checkbox)
        self.pt_pre_adhan_minutes_label = QLabel(self.lm.get_string("pre_adhan_minutes_label", "Minutes before Adhan:"))
        self.pt_pre_adhan_minutes_spinbox = QSpinBox(); self.pt_pre_adhan_minutes_spinbox.setRange(1, 60)
        alerts_group_layout.addRow(self.pt_pre_adhan_minutes_label, self.pt_pre_adhan_minutes_spinbox)

        self.pt_pre_adhan_sound_label = QLabel(self.lm.get_string("pre_adhan_sound_label", "Pre-Adhan Sound:"));
        self.pt_pre_adhan_sound_combo = QComboBox()
        alerts_group_layout.addRow(self.pt_pre_adhan_sound_label, self.pt_pre_adhan_sound_combo)
        
        
        separator1 = QFrame(); separator1.setFrameShape(QFrame.Shape.HLine); 
        separator1.setFrameShadow(QFrame.Shadow.Sunken); alerts_group_layout.addRow(separator1)
        self.pt_post_adhan_alert_checkbox = QCheckBox(self.lm.get_string("enable_post_adhan_alert", "Enable Post-Adhan (Iqama) Alert"))
        alerts_group_layout.addRow(self.pt_post_adhan_alert_checkbox)
        self.pt_post_adhan_minutes_label = QLabel(self.lm.get_string("post_adhan_minutes_label", "Minutes after Adhan for Iqama:"))
        self.pt_post_adhan_minutes_spinbox = QSpinBox(); self.pt_post_adhan_minutes_spinbox.setRange(1, 60)
        alerts_group_layout.addRow(self.pt_post_adhan_minutes_label, self.pt_post_adhan_minutes_spinbox)
        
        
        self.pt_post_adhan_sound_label = QLabel(self.lm.get_string("post_adhan_sound_label", "Post-Adhan (Iqama) Sound:")); self.pt_post_adhan_sound_combo = QComboBox()
        alerts_group_layout.addRow(self.pt_post_adhan_sound_label, self.pt_post_adhan_sound_combo)
        pt_layout.addWidget(self.pt_alerts_group)
        pt_layout.addSpacing(10)

        self.adhan_sounds_group = QGroupBox(self.lm.get_string("adhan_sounds_group", "Adhan Sounds"))
        adhan_sounds_layout = QFormLayout(self.adhan_sounds_group)
        self.use_unified_adhan_checkbox = QCheckBox(self.lm.get_string("use_unified_adhan", "Use Unified Adhan Sound"))
        adhan_sounds_layout.addRow(self.use_unified_adhan_checkbox)
        self.unified_adhan_sound_label = QLabel(self.lm.get_string("unified_adhan_sound", "Unified Adhan File:")); self.unified_adhan_sound_combo = QComboBox()
        adhan_sounds_layout.addRow(self.unified_adhan_sound_label, self.unified_adhan_sound_combo)
        self.specific_adhan_sounds_widget = QWidget()
        specific_adhan_layout = QFormLayout(self.specific_adhan_sounds_widget)
        self.adhan_fajr_label = QLabel(self.lm.get_string("adhan_fajr", "Fajr Adhan:")); self.adhan_fajr_combo = QComboBox()
        specific_adhan_layout.addRow(self.adhan_fajr_label, self.adhan_fajr_combo)
        
        
        self.adhan_dhuhr_label = QLabel(self.lm.get_string("adhan_dhuhr", "Dhuhr Adhan:"));
        self.adhan_dhuhr_combo = QComboBox()
        specific_adhan_layout.addRow(self.adhan_dhuhr_label, self.adhan_dhuhr_combo)
        
        
        self.adhan_asr_label = QLabel(self.lm.get_string("adhan_asr", "Asr Adhan:"))
        self.adhan_asr_combo = QComboBox()
        self.adhan_asr_combo.setObjectName("asrAdhanCombo")
        specific_adhan_layout.addRow(self.adhan_asr_label, self.adhan_asr_combo)
        
        
        self.adhan_maghrib_label = QLabel(self.lm.get_string("adhan_maghrib", "Maghrib Adhan:"));
        self.adhan_maghrib_combo = QComboBox()
        specific_adhan_layout.addRow(self.adhan_maghrib_label, self.adhan_maghrib_combo)
        
        
        self.adhan_isha_label = QLabel(self.lm.get_string("adhan_isha", "Isha Adhan:")); self.adhan_isha_combo = QComboBox()
        specific_adhan_layout.addRow(self.adhan_isha_label, self.adhan_isha_combo)
        adhan_sounds_layout.addWidget(self.specific_adhan_sounds_widget)
        self.use_unified_adhan_checkbox.toggled.connect(self.toggle_adhan_sound_inputs)
        pt_layout.addWidget(self.adhan_sounds_group)
        
        pt_layout.addStretch()
        prayer_times_tab_outer_layout = QVBoxLayout(self.prayer_times_tab)
        prayer_times_tab_outer_layout.addWidget(pt_main_scroll_area)
        self.tabs.addTab(self.prayer_times_tab, self.lm.get_string("prayer_times_tab_title"))
        
        content_layout.addWidget(self.tabs)
        self.button_box = QDialogButtonBox(self.content_frame)
        self.apply_button = self.button_box.addButton(self.lm.get_string("apply", "Apply"), QDialogButtonBox.ButtonRole.ApplyRole)
        self.ok_button = self.button_box.addButton(self.lm.get_string("ok", "OK"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_button = self.button_box.addButton(self.lm.get_string("cancel", "Cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        content_layout.addWidget(self.button_box)
        dialog_main_layout.addWidget(self.content_frame)
        self.ok_button.clicked.connect(self.accept_settings)
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button.clicked.connect(self.apply_settings)
        self.ok_button.setObjectName("OkButton"); self.apply_button.setObjectName("ApplyButton")


        self.adhan_download_tab = AdhanDownloadWidget(settings_window=self)
        self.tabs.addTab(self.adhan_download_tab, "تحميل الأذان")

    def update_layout_direction(self, lang_code):
        if lang_code == "ar":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    def display_text_adhkar(self):
        if not hasattr(self, 'adhkar_text_layout'):
            return
        if not hasattr(self, 'adhkar_text_widget'):
            return
        if not hasattr(self, 'adhkar_text_area'):
            return

        self.adhkar_text_area.clear()
        for category_key in self.adhkar_manager.get_categories():
            adhkar_list = self.adhkar_manager.get_adhkar_for_category(category_key)
            if not isinstance(adhkar_list, list):
                continue
            if not adhkar_list:
                continue

            self.adhkar_text_area.append(f"\n{self.lm.get_string(category_key)}:\n")
            for dhikr_item in adhkar_list:
                if isinstance(dhikr_item, dict) and 'text' in dhikr_item:
                    self.adhkar_text_area.append(f"{dhikr_item['text']}\n")

    def toggle_text_notification_settings_visibility(self):
        if hasattr(self, 'rtype_combo') and hasattr(self, 'text_notification_group'):
            self.text_notification_group.setVisible(self.rtype_combo.currentData() in ["text", "random"])

    def toggle_location_input_widgets(self):
        selected_method = self.pt_loc_method_combo.currentText()
        if selected_method == self.lm.get_string("manual_location"):
            self.pt_manual_location_widget.setVisible(True)
            self.pt_auto_location_widget.setVisible(False)
        else:
            self.pt_manual_location_widget.setVisible(False)
            self.pt_auto_location_widget.setVisible(True)

    def toggle_adhan_sound_inputs(self, checked):
        if hasattr(self, 'unified_adhan_sound_label') and hasattr(self, 'unified_adhan_sound_combo'):
            self.unified_adhan_sound_label.setVisible(checked); self.unified_adhan_sound_combo.setVisible(checked)
        if hasattr(self, 'specific_adhan_sounds_widget'): self.specific_adhan_sounds_widget.setVisible(not checked)

    def populate_audio_combobox(self, combobox, audio_type):
        if combobox is None:
            return

        audio_dir = os.path.join(self.base_path, "audio", audio_type)
        if not os.path.exists(audio_dir):
            try:
                os.makedirs(audio_dir)
            except Exception as e:
                return

        try:
            all_files = os.listdir(audio_dir)
            audio_files = [f for f in all_files if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
            if not audio_files:
                return

            current_selection = combobox.currentText()
            combobox.clear()
            combobox.addItem(self.lm.get_string("none", "لا شيء"))

            initial_index_to_select = 0
            for filename in audio_files:
                combobox.addItem(filename)
                if filename == current_selection:
                    initial_index_to_select = combobox.count() - 1

            combobox.setCurrentIndex(initial_index_to_select)
        except Exception:
            return

    def apply_settings(self):
        # حفظ إعدادات الأذكار
        self.settings_manager.set("adhkar_active", self.adhkar_active_checkbox.isChecked())
        self.settings_manager.set("adhkar_interval", self.adhkar_interval_spinbox.value())

        # حفظ إعدادات مواقيت الصلاة
        self.settings_manager.set("prayer_times_active", self.pt_active_checkbox.isChecked())
        self.settings_manager.set("prayer_location_method", self.pt_loc_method_combo.currentText())
        
        if self.pt_loc_method_combo.currentText() == self.lm.get_string("manual_location"):
            self.settings_manager.set("prayer_location", self.pt_manual_location_input.text())
        else:
            self.settings_manager.set("prayer_location", None)

        # حفظ إعدادات الأذان
        self.settings_manager.set("adhan_active", self.adhan_active_checkbox.isChecked())
        self.settings_manager.set("adhan_fajr", self.adhan_fajr_combo.currentText())
        self.settings_manager.set("adhan_dhuhr", self.adhan_dhuhr_combo.currentText())
        self.settings_manager.set("adhan_asr", self.adhan_asr_combo.currentText())
        self.settings_manager.set("adhan_maghrib", self.adhan_maghrib_combo.currentText())
        self.settings_manager.set("adhan_isha", self.adhan_isha_combo.currentText())

        # تحديث مواقيت الصلاة
        if self.settings_manager.get("prayer_times_active"):
            QTimer.singleShot(0, self.fetch_prayer_times)

    def fetch_prayer_times(self):
        self.prayer_times_manager.clear_cached_auto_location_data()
        self.prayer_times_manager.fetch_prayer_times_for_date()
        if self.prayer_times_manager.last_fetch_success:
            QTimer.singleShot(0, self.schedule_prayer_alerts)

    def schedule_prayer_alerts(self):
        if hasattr(self.app, 'reminder_service'):
            self.app.reminder_service.schedule_prayer_alerts()

    def accept_settings(self):
        self.apply_settings()
        super().accept()

    def update_ui_texts(self):
        self.setWindowTitle(self.lm.get_string("settings", "الإعدادات"))
        # ... تحديث باقي النصوص ...

    def language_preference_changed(self, lang_code):
        self.update_ui_texts()
        self.update_layout_direction(lang_code)

    def reapply_stylesheet_for_theme(self, theme):
        self.setStyleSheet(self.generate_settings_stylesheet(theme))

    def generate_settings_stylesheet(self, theme):
        if theme == "dark":
            return """
                QDialog {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QComboBox {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QLineEdit {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QSpinBox {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QPushButton {
                    background-color: #0d47a1;
                    color: #ffffff;
                    border: none;
                    padding: 5px 15px;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QPushButton:pressed {
                    background-color: #0a3d91;
                }
            """
        return ""