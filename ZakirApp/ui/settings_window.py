# ui/settings_window.py
import sys
import os
from datetime import date 

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QComboBox,
    QPushButton, QCheckBox, QSpacerItem, QSizePolicy, QFrame,
    QListWidget, QListWidgetItem, QSpinBox, QScrollArea, QApplication,
    QLineEdit, QGroupBox, QFormLayout, QGraphicsBlurEffect, QGraphicsDropShadowEffect,
    QFileDialog # For selecting audio files (if needed for browsing)
)
from PyQt6.QtCore import Qt, QLocale, QRectF, pyqtSignal, QTimer, QPoint, QEvent
from PyQt6.QtGui import (
    QIcon, QPainter, QPainterPath, QColor, QPen, QBrush, QMouseEvent, QPalette, 
    QLinearGradient, QFontMetrics, QAction
)

# Import AdhanDownloadWidget locally if it's in the same directory or adjust path
from .adhan_download_manager import AdhanDownloadWidget 

# --- GlassFrame for custom window appearance ---
class GlassFrame(QFrame): # Changed from QWidget to QFrame for more styling options
    def __init__(self, parent=None, border_radius=15, title_bar_height=40):
        super().__init__(parent)
        self.border_radius = border_radius
        self.title_bar_height = title_bar_height
        self._is_dragging = False
        self._drag_start_position = QPoint()

        # Make the QDialog frameless and transparent
        if self.parent(): # Assuming parent is the QDialog
            self.parent().setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
            self.parent().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setAutoFillBackground(False) # We will handle all painting

        # Shadow effect for the entire frame
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 90))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.border_radius, self.border_radius)
        
        # Glassy background
        # Darker theme for glass
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0, QColor(45, 48, 55, 230)) # Slightly lighter top
        gradient.setColorAt(1, QColor(35, 38, 45, 245)) # Slightly darker bottom
        
        painter.fillPath(path, QBrush(gradient))

        # Subtle border
        border_color = QColor(80, 85, 95, 100)
        pen = QPen(border_color, 1.5) # Slightly thicker border
        painter.setPen(pen)
        painter.drawPath(path)
        
        super().paintEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if the press is within the custom title bar area
            if event.pos().y() < self.title_bar_height : # Assuming title_bar_height is defined
                self._is_dragging = True
                # Global position for window movement, local for offset calculation
                self._drag_start_position = event.globalPosition().toPoint() - self.parent().frameGeometry().topLeft()
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            # Move the parent QDialog window
            new_pos = event.globalPosition().toPoint() - self_drag_start_position
            self.parent().move(new_pos)
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()
        else:
            event.ignore()


class SettingsWindow(QDialog):
    language_changed_signal = pyqtSignal(str) # Emits new language code
    theme_changed_signal = pyqtSignal(str)    # Emits new theme key ("light", "dark", "system")
    settings_applied_signal = pyqtSignal()    # Emitted when Apply or OK is clicked

    def __init__(self, settings_manager, localization_manager, adhkar_manager, base_path):
        super().__init__()
        self.settings_mngr = settings_manager
        self.lm = localization_manager
        self.adhkar_mngr = adhkar_manager # For displaying Adhkar in content tab
        self.base_path = base_path

        self.ADHAN_AUDIO_DIR = os.path.join(self.base_path, "resources", "audio", "adhan")
        self.REMINDER_AUDIO_DIR = os.path.join(self.base_path, "resources", "audio", "reminders")
        os.makedirs(self.ADHAN_AUDIO_DIR, exist_ok=True)
        os.makedirs(self.REMINDER_AUDIO_DIR, exist_ok=True)
        
        self.setWindowTitle(self.lm.get_string("settings")) # Title for taskbar, etc.
        self.setMinimumSize(680, 550) # Adjusted minimum size

        # Main layout for the QDialog (will hold the GlassFrame)
        dialog_outer_layout = QVBoxLayout(self)
        dialog_outer_layout.setContentsMargins(0, 0, 0, 0) # Remove margins for frameless

        self.glass_content_frame = GlassFrame(self, border_radius=12, title_bar_height=45)
        dialog_outer_layout.addWidget(self.glass_content_frame)

        # Layout for content INSIDE the GlassFrame
        content_layout = QVBoxLayout(self.glass_content_frame)
        content_layout.setContentsMargins(20, 0, 20, 15) # Top margin handled by title bar

        self._init_custom_title_bar(content_layout) # Add title bar first
        self._init_ui_tabs(content_layout)          # Then tabs
        self._init_action_buttons(content_layout)   # Then action buttons

        self.load_settings_to_ui()
        self.update_ui_texts_and_direction() # Apply initial language and direction

        # Apply base stylesheet for the dialog (will be refined)
        self.setStyleSheet(self._get_base_stylesheet())


    def _get_base_stylesheet(self):
        # This stylesheet provides base styling for elements within the GlassFrame
        # It aims for a modern, dark, glassmorphism-compatible look
        return """
            QDialog { /* The main dialog window */
                background-color: transparent; /* Fully transparent as GlassFrame handles background */
            }
            QLabel {
                color: #D1D5DB; /* Light gray text */
                background-color: transparent;
                font-size: 9pt;
            }
            QCheckBox {
                color: #D1D5DB;
                background-color: transparent;
                font-size: 9pt;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #4B5563; /* Darker gray border */
                border-radius: 3px;
                background-color: #374151; /* Dark gray background */
            }
            QCheckBox::indicator:checked {
                background-color: #3B82F6; /* Blue when checked */
                border: 1px solid #2563EB;
                image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); /* Checkmark (example) */
            }
             QCheckBox::indicator:disabled {
                border: 1px solid #374151;
                background-color: #1F2937;
            }
            QComboBox {
                color: #E5E7EB; /* Lighter text for combobox */
                background-color: #374151; /* Dark input background */
                border: 1px solid #4B5563;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9pt;
                min-height: 20px;
            }
            QComboBox:disabled {
                color: #6B7280;
                background-color: #1F2937;
                border: 1px solid #374151;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left-width: 1px;
                border-left-color: #4B5563;
                border-left-style: solid;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }
            QComboBox::down-arrow {
                image: url(:/qt-project.org/styles/commonstyle/images/arrow-down-16.png); /* Example path */
            }
            QComboBox QAbstractItemView { /* Dropdown list style */
                background-color: #2c313a; /* Slightly lighter than combobox bg */
                color: #E5E7EB;
                border: 1px solid #4B5563;
                selection-background-color: #3B82F6; /* Blue for selection */
                selection-color: white;
                outline: 0px; /* Remove focus outline */
            }
            QLineEdit, QSpinBox {
                color: #E5E7EB;
                background-color: #374151;
                border: 1px solid #4B5563;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 9pt;
                min-height: 20px;
            }
            QLineEdit:disabled, QSpinBox:disabled {
                color: #6B7280;
                background-color: #1F2937;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border;
                width: 16px;
                border-left-width: 1px;
                border-left-color: #4B5563;
                border-left-style: solid;
                border-radius: 0px; /* Keep them square with main control */
            }
            QSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 3px;}
            QSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 3px;}
            QSpinBox::up-arrow { image: url(:/qt-project.org/styles/commonstyle/images/arrow-up-16.png); }
            QSpinBox::down-arrow { image: url(:/qt-project.org/styles/commonstyle/images/arrow-down-16.png); }

            QGroupBox {
                color: #9CA3AF; /* Subdued title color */
                background-color: transparent;
                border: 1px solid #374151; /* Subtle border */
                border-radius: 6px;
                margin-top: 8px; /* Space for title */
                font-size: 8.5pt;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center; /* Or top left, with padding */
                padding: 0 5px;
                left: 10px; /* Adjust if position is top left */
                background-color: transparent; /* Match GlassFrame's gradient near title */
            }

            QTabWidget::pane {
                border: 1px solid #374151;
                border-radius: 5px;
                background-color: transparent; /* Pane itself is transparent */
                padding: 8px;
            }
            QTabBar::tab {
                color: #9CA3AF; /* Default tab text color */
                background-color: transparent; /* Fully transparent by default */
                border: 1px solid transparent; /* No border by default */
                border-bottom-color: #374151; /* Underline for inactive tabs */
                padding: 8px 15px;
                margin-right: 2px; /* Space between tabs */
                font-size: 9pt;
                min-width: 80px; /* Minimum tab width */
            }
            QTabBar::tab:hover {
                color: #E5E7EB; /* Lighter text on hover */
                border-bottom-color: #4B5563;
            }
            QTabBar::tab:selected {
                color: #FFFFFF; /* White text for selected tab */
                background-color: rgba(59, 130, 246, 0.1); /* Very subtle blue highlight */
                border: 1px solid #3B82F6; /* Blue border for selected tab */
                border-bottom-color: #3B82F6; /* Stronger underline */
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:disabled {
                color: #4B5563;
            }
            /* Make the QScrollArea background transparent */
            QScrollArea {
                background-color: transparent;
                border: none; /* Or 1px solid #374151; if you want a border */
            }
            /* Style the QListWidget for audio files */
            QListWidget {
                background-color: #2d323b; /* Slightly different dark shade */
                border: 1px solid #4B5563;
                border-radius: 4px;
                color: #D1D5DB;
                font-size: 9pt;
                outline: 0px; /* Remove focus outline */
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #374151; /* Separator line */
            }
            QListWidget::item:last-child {
                border-bottom: none;
            }
            QListWidget::item:selected {
                background-color: #3B82F6; /* Blue selection */
                color: white;
            }
            QListWidget::item:hover:!selected { /* Hover but not selected */
                background-color: #374151;
            }
            /* Remove focus border from QTextEdit (adhkar display) */
            QTextEdit {
                 background-color: rgba(40, 42, 48, 0.7); /* Semi-transparent dark */
                 color: #D1D5DB;
                 border: 1px solid #4B5563;
                 border-radius: 4px;
                 font-size: 10pt;
                 padding: 8px;
            }
        """
    def _init_custom_title_bar(self, main_content_layout):
        title_bar_widget = QWidget(self.glass_content_frame) # Parent to glass frame
        title_bar_widget.setFixedHeight(45) # Fixed height for the title bar area
        title_bar_widget.setStyleSheet("background-color: transparent;")

        title_bar_layout = QHBoxLayout(title_bar_widget)
        title_bar_layout.setContentsMargins(10, 0, 5, 0) # Left, Top, Right, Bottom

        self.title_label = QLabel(self.lm.get_string("settings"))
        self.title_label.setStyleSheet("color: #E5E7EB; font-size: 11pt; font-weight: bold; background-color: transparent;")
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()

        # Minus, Max, Close buttons (Example, style them as needed)
        # For simplicity, only close button here
        self.close_button_custom = QPushButton("✕") # Unicode multiplication sign (X)
        self.close_button_custom.setFixedSize(30, 30)
        self.close_button_custom.setStyleSheet("""
            QPushButton { 
                font-family: "Lucida Console", Monaco, monospace;
                font-size: 12pt; 
                font-weight: bold; 
                color: #9CA3AF; 
                background-color: transparent; 
                border: none; 
                border-radius: 15px;
            }
            QPushButton:hover { background-color: rgba(239, 68, 68, 0.8); color: white; } /* Red hover */
            QPushButton:pressed { background-color: rgba(220, 38, 38, 0.9); }
        """)
        self.close_button_custom.clicked.connect(self.reject) # QDialog's reject slot
        title_bar_layout.addWidget(self.close_button_custom)
        
        main_content_layout.addWidget(title_bar_widget)


    def _init_ui_tabs(self, main_content_layout):
        self.tabs = QTabWidget(self.glass_content_frame) # Parent to glass frame
        
        # --- Tab 1: General Settings ---
        self.general_tab = QWidget()
        general_layout = QVBoxLayout(self.general_tab)
        general_layout.setContentsMargins(10, 15, 10, 10)
        general_layout.setSpacing(12)

        lang_group = QGroupBox(self.lm.get_string("language_settings_group", "Language & Theme"))
        lang_group_layout = QFormLayout(lang_group)
        lang_group_layout.setSpacing(8)

        self.lang_label = QLabel(self.lm.get_string("language") + ":")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("العربية", "ar")
        self.lang_combo.currentTextChanged.connect(self.language_preference_changed_in_settings)
        lang_group_layout.addRow(self.lang_label, self.lang_combo)

        self.theme_label = QLabel(self.lm.get_string("theme_setting") + ":")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.lm.get_string("theme_system", "System Default"), "system")
        self.theme_combo.addItem(self.lm.get_string("theme_light", "Light"), "light")
        self.theme_combo.addItem(self.lm.get_string("theme_dark", "Dark"), "dark")
        self.theme_combo.currentTextChanged.connect(self.theme_preference_changed)
        lang_group_layout.addRow(self.theme_label, self.theme_combo)
        general_layout.addWidget(lang_group)

        self.start_with_windows_checkbox = QCheckBox(self.lm.get_string("start_with_windows"))
        general_layout.addWidget(self.start_with_windows_checkbox)
        
        general_layout.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.tabs.addTab(self.general_tab, self.lm.get_string("general"))
        
        # --- Tab 2: Reminder Settings ---
        self.reminders_tab = QWidget()
        reminders_layout = QVBoxLayout(self.reminders_tab)
        reminders_layout.setContentsMargins(10,15,10,10)
        reminders_layout.setSpacing(12)

        rem_config_group = QGroupBox(self.lm.get_string("reminder_config_group", "Reminder Configuration"))
        rem_config_form_layout = QFormLayout(rem_config_group)
        
        self.rtype_label = QLabel(self.lm.get_string("reminder_type"))
        self.rtype_combo = QComboBox()
        self.rtype_combo.addItem(self.lm.get_string("text_notification"), "text")
        self.rtype_combo.addItem(self.lm.get_string("sound_notification"), "sound")
        self.rtype_combo.addItem(self.lm.get_string("random_notification"), "random")
        self.rtype_combo.currentTextChanged.connect(self._toggle_reminder_detail_widgets)
        rem_config_form_layout.addRow(self.rtype_label, self.rtype_combo)

        self.interval_label = QLabel(self.lm.get_string("reminder_interval_minutes"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(1); self.interval_spinbox.setMaximum(180) # Up to 3 hours
        self.interval_spinbox.setSuffix(f" {self.lm.get_string('minutes_suffix')}")
        rem_config_form_layout.addRow(self.interval_label, self.interval_spinbox)
        reminders_layout.addWidget(rem_config_group)

        # Text Notification Settings (Conditional)
        self.text_notification_settings_group = QGroupBox(self.lm.get_string("text_notification_settings_group", "Text Notification Settings"))
        text_notif_layout = QFormLayout(self.text_notification_settings_group)
        self.pos_label = QLabel(self.lm.get_string("notification_position"))
        self.pos_combo = QComboBox()
        positions = { "top_left": "Top Left", "top_center": "Top Center", "top_right": "Top Right", 
                      "center_left": "Center Left", "center": "Center", "center_right": "Center Right", 
                      "bottom_left": "Bottom Left", "bottom_center": "Bottom Center", "bottom_right": "Bottom Right" }
        for key, val_en in positions.items(): self.pos_combo.addItem(self.lm.get_string(f"pos_{key.replace('-', '_')}", default_text=val_en), key)
        text_notif_layout.addRow(self.pos_label, self.pos_combo)
        self.duration_label = QLabel(self.lm.get_string("notification_duration_seconds"))
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setMinimum(2); self.duration_spinbox.setMaximum(60)
        self.duration_spinbox.setSuffix(f" {self.lm.get_string('seconds_suffix')}")
        text_notif_layout.addRow(self.duration_label, self.duration_spinbox)
        reminders_layout.addWidget(self.text_notification_settings_group)

        # Sound Notification Settings (Conditional)
        self.sound_notification_settings_group = QGroupBox(self.lm.get_string("sound_notification_settings_group", "Sound Reminder Settings"))
        sound_notif_layout_main = QVBoxLayout(self.sound_notification_settings_group)
        sound_notif_layout_main.addWidget(QLabel(self.lm.get_string("audio_files_select")))
        self.reminder_audio_files_listwidget = QListWidget()
        self.reminder_audio_files_listwidget.setSelectionMode(QListWidget.SelectionMode.MultiSelection) # Allow multiple
        self.reminder_audio_files_listwidget.setFixedHeight(100)
        sound_notif_layout_main.addWidget(self.reminder_audio_files_listwidget)
        reminders_layout.addWidget(self.sound_notification_settings_group)
        
        reminders_layout.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.tabs.addTab(self.reminders_tab, self.lm.get_string("reminders"))

        # --- Tab 3: Content (Adhkar Display & Reminder Sounds) ---
        self.content_tab = QWidget()
        content_tab_main_layout = QVBoxLayout(self.content_tab)
        content_tab_main_layout.setContentsMargins(10,15,10,10)
        content_tab_main_layout.setSpacing(12)

        adhkar_display_group = QGroupBox(self.lm.get_string("text_adhkar_display"))
        adhkar_display_layout = QVBoxLayout(adhkar_display_group)
        self.adhkar_text_area_display = QTextEdit() # Changed from QScrollArea with custom widget
        self.adhkar_text_area_display.setReadOnly(True)
        self.adhkar_text_area_display.setMinimumHeight(150) # Good height for display
        adhkar_display_layout.addWidget(self.adhkar_text_area_display)
        content_tab_main_layout.addWidget(adhkar_display_group)
        
        content_tab_main_layout.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.tabs.addTab(self.content_tab, self.lm.get_string("content_tab_title"))

        # --- Tab 4: Prayer Times Settings ---
        self.prayer_times_tab = QWidget()
        pt_scroll_area = QScrollArea(self.prayer_times_tab) # Make the whole tab scrollable
        pt_scroll_area.setWidgetResizable(True)
        pt_scroll_area.setStyleSheet("background-color: transparent; border: none;")

        pt_scroll_content_widget = QWidget() # Content widget for scroll area
        pt_scroll_content_widget.setStyleSheet("background-color: transparent;")
        pt_layout = QVBoxLayout(pt_scroll_content_widget)
        pt_layout.setContentsMargins(5,5,5,5) # Margins for content inside scroll
        pt_layout.setSpacing(10)

        self.pt_enable_checkbox = QCheckBox(self.lm.get_string("enable_prayer_times"))
        self.pt_enable_checkbox.toggled.connect(self._toggle_prayer_times_widgets_enabled_state)
        pt_layout.addWidget(self.pt_enable_checkbox)

        # Location Settings Group
        self.pt_location_group = QGroupBox(self.lm.get_string("location_settings_group"))
        location_group_layout = QVBoxLayout(self.pt_location_group)
        loc_method_layout = QHBoxLayout()
        loc_method_layout.addWidget(QLabel(self.lm.get_string("location_method")))
        self.pt_loc_method_combo = QComboBox()
        self.pt_loc_method_combo.addItem(self.lm.get_string("location_method_auto_ip"), "auto_ip")
        self.pt_loc_method_combo.addItem(self.lm.get_string("location_method_city_country"), "manual_city")
        self.pt_loc_method_combo.addItem(self.lm.get_string("location_method_coordinates"), "manual_coords")
        self.pt_loc_method_combo.currentTextChanged.connect(self._toggle_location_input_widgets)
        loc_method_layout.addWidget(self.pt_loc_method_combo)
        loc_method_layout.addStretch()
        location_group_layout.addLayout(loc_method_layout)

        self.pt_city_country_widget = QWidget()
        city_country_form = QFormLayout(self.pt_city_country_widget)
        self.pt_city_edit = QLineEdit(); self.pt_country_edit = QLineEdit()
        city_country_form.addRow(self.lm.get_string("city"), self.pt_city_edit)
        city_country_form.addRow(self.lm.get_string("country"), self.pt_country_edit)
        location_group_layout.addWidget(self.pt_city_country_widget)

        self.pt_coords_widget = QWidget()
        coords_form = QFormLayout(self.pt_coords_widget)
        self.pt_latitude_edit = QLineEdit(); self.pt_longitude_edit = QLineEdit()
        coords_form.addRow(self.lm.get_string("latitude"), self.pt_latitude_edit)
        coords_form.addRow(self.lm.get_string("longitude"), self.pt_longitude_edit)
        location_group_layout.addWidget(self.pt_coords_widget)
        pt_layout.addWidget(self.pt_location_group)

        # Calculation Settings Group
        self.pt_calculation_group = QGroupBox(self.lm.get_string("calculation_settings_group"))
        calc_group_form = QFormLayout(self.pt_calculation_group)
        self.pt_method_combo = QComboBox() # Populate with calculation methods
        methods = {"0":"calc_method_0","1":"calc_method_1","2":"calc_method_2","3":"calc_method_3", "4":"calc_method_4","5":"calc_method_5", "7":"calc_method_7","8":"calc_method_8","9":"calc_method_9", "10":"calc_method_10","11":"calc_method_11","12":"calc_method_12", "13":"calc_method_13","14":"calc_method_14","15":"calc_method_15","16":"calc_method_16"}
        for val, key in methods.items(): self.pt_method_combo.addItem(self.lm.get_string(key), val)
        calc_group_form.addRow(self.lm.get_string("calculation_method"), self.pt_method_combo)
        
        self.pt_asr_method_combo = QComboBox()
        self.pt_asr_method_combo.addItem(self.lm.get_string("asr_method_standard"), "0")
        self.pt_asr_method_combo.addItem(self.lm.get_string("asr_method_hanafi"), "1")
        calc_group_form.addRow(self.lm.get_string("asr_method"), self.pt_asr_method_combo)

        self.pt_midnight_mode_combo = QComboBox()
        self.pt_midnight_mode_combo.addItem(self.lm.get_string("midnight_mode_standard"), "0")
        self.pt_midnight_mode_combo.addItem(self.lm.get_string("midnight_mode_jafari"), "1")
        calc_group_form.addRow(self.lm.get_string("midnight_mode"), self.pt_midnight_mode_combo)
        
        self.pt_lat_adj_combo = QComboBox() # High Latitude Adjustment
        self.pt_lat_adj_combo.addItem(self.lm.get_string("lat_adj_middle_of_night"), "0")
        self.pt_lat_adj_combo.addItem(self.lm.get_string("lat_adj_one_seventh"), "1")
        self.pt_lat_adj_combo.addItem(self.lm.get_string("lat_adj_angle_based"), "3") # API value for Angle Based
        calc_group_form.addRow(self.lm.get_string("latitude_adjustment_method"), self.pt_lat_adj_combo)
        pt_layout.addWidget(self.pt_calculation_group)

        # Tune Settings Group
        self.pt_tune_group = QGroupBox(self.lm.get_string("prayer_time_tune_group"))
        tune_group_layout = QVBoxLayout(self.pt_tune_group)
        tune_group_layout.addWidget(QLabel(self.lm.get_string("prayer_time_tune")))
        self.pt_tune_edit = QLineEdit(); self.pt_tune_edit.setPlaceholderText("0,0,0,0,0,0,0,0")
        tune_group_layout.addWidget(self.pt_tune_edit)
        tune_help = QLabel(self.lm.get_string("tune_help_text")); tune_help.setWordWrap(True)
        tune_group_layout.addWidget(tune_help)
        pt_layout.addWidget(self.pt_tune_group)

        # Prayer Alerts Group
        self.pt_alerts_group = QGroupBox(self.lm.get_string("prayer_alerts_group"))
        alerts_form_layout = QFormLayout(self.pt_alerts_group)
        self.pt_pre_adhan_alert_checkbox = QCheckBox(self.lm.get_string("enable_pre_adhan_alert"))
        self.pt_pre_adhan_alert_checkbox.toggled.connect(self._toggle_pre_adhan_widgets_enabled)
        alerts_form_layout.addRow(self.pt_pre_adhan_alert_checkbox)
        self.pt_pre_adhan_minutes_spinbox = QSpinBox(); self.pt_pre_adhan_minutes_spinbox.setRange(1, 60)
        alerts_form_layout.addRow(self.lm.get_string("pre_adhan_minutes_label"), self.pt_pre_adhan_minutes_spinbox)
        self.pt_pre_adhan_sound_combo = QComboBox()
        alerts_form_layout.addRow(self.lm.get_string("pre_adhan_sound_label"), self.pt_pre_adhan_sound_combo)

        alerts_form_layout.addRow(QFrame(frameShape=QFrame.Shape.HLine, frameShadow=QFrame.Shadow.Sunken)) # Separator

        self.pt_post_adhan_alert_checkbox = QCheckBox(self.lm.get_string("enable_post_adhan_alert"))
        self.pt_post_adhan_alert_checkbox.toggled.connect(self._toggle_post_adhan_widgets_enabled)
        alerts_form_layout.addRow(self.pt_post_adhan_alert_checkbox)
        self.pt_post_adhan_minutes_spinbox = QSpinBox(); self.pt_post_adhan_minutes_spinbox.setRange(1, 60)
        alerts_form_layout.addRow(self.lm.get_string("post_adhan_minutes_label"), self.pt_post_adhan_minutes_spinbox)
        self.pt_post_adhan_sound_combo = QComboBox()
        alerts_form_layout.addRow(self.lm.get_string("post_adhan_sound_label"), self.pt_post_adhan_sound_combo)
        pt_layout.addWidget(self.pt_alerts_group)

        # Adhan Sounds Group
        self.adhan_sounds_group = QGroupBox(self.lm.get_string("adhan_sounds_group"))
        adhan_sounds_main_layout = QVBoxLayout(self.adhan_sounds_group)
        self.use_unified_adhan_checkbox = QCheckBox(self.lm.get_string("use_unified_adhan"))
        self.use_unified_adhan_checkbox.toggled.connect(self._toggle_adhan_sound_inputs_visibility)
        adhan_sounds_main_layout.addWidget(self.use_unified_adhan_checkbox)
        
        self.unified_adhan_widget = QWidget()
        unified_form = QFormLayout(self.unified_adhan_widget)
        self.unified_adhan_sound_combo = QComboBox()
        unified_form.addRow(self.lm.get_string("unified_adhan_sound"), self.unified_adhan_sound_combo)
        adhan_sounds_main_layout.addWidget(self.unified_adhan_widget)

        self.specific_adhan_sounds_widget = QWidget()
        specific_form = QFormLayout(self.specific_adhan_sounds_widget)
        self.adhan_fajr_combo = QComboBox(); specific_form.addRow(self.lm.get_string("adhan_fajr"), self.adhan_fajr_combo)
        self.adhan_dhuhr_combo = QComboBox(); specific_form.addRow(self.lm.get_string("adhan_dhuhr"), self.adhan_dhuhr_combo)
        self.adhan_asr_combo = QComboBox(); specific_form.addRow(self.lm.get_string("adhan_asr"), self.adhan_asr_combo)
        self.adhan_maghrib_combo = QComboBox(); specific_form.addRow(self.lm.get_string("adhan_maghrib"), self.adhan_maghrib_combo)
        self.adhan_isha_combo = QComboBox(); specific_form.addRow(self.lm.get_string("adhan_isha"), self.adhan_isha_combo)
        adhan_sounds_main_layout.addWidget(self.specific_adhan_sounds_widget)
        pt_layout.addWidget(self.adhan_sounds_group)

        pt_layout.addStretch(1) # Pushes content up if it's short
        pt_scroll_area.setWidget(pt_scroll_content_widget) # Set content widget for scroll area
        
        # Layout for the tab itself, to hold the scroll area
        prayer_times_tab_outer_layout = QVBoxLayout(self.prayer_times_tab)
        prayer_times_tab_outer_layout.setContentsMargins(0,0,0,0) # Tab layout has no margins
        prayer_times_tab_outer_layout.addWidget(pt_scroll_area)
        self.tabs.addTab(self.prayer_times_tab, self.lm.get_string("prayer_times_tab_title"))


        # --- Tab 5: Download Adhan ---
        self.adhan_download_tab_widget = AdhanDownloadWidget(
            settings_manager=self.settings_mngr, 
            lm=self.lm, 
            base_path=self.base_path,
            parent_settings_window=self # Pass self as parent
        )
        self.adhan_download_tab_widget.local_adhans_changed.connect(self.populate_audio_comboboxes)
        self.tabs.addTab(self.adhan_download_tab_widget, self.lm.get_string("download_adhan_tab_title", "Download Adhan"))
        
        main_content_layout.addWidget(self.tabs)

    def _init_action_buttons(self, main_content_layout):
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1) # Push buttons to the right (or left in RTL)

        button_style = """
            QPushButton {{
                color: #E5E7EB;
                background-color: #3B82F6; /* Blue */
                border: none;
                padding: 8px 18px;
                font-size: 9pt;
                font-weight: bold;
                border-radius: 5px;
                min-width: 70px;
            }}
            QPushButton:hover {{ background-color: #2563EB; }}
            QPushButton:pressed {{ background-color: #1D4ED8; }}
            QPushButton:disabled {{ background-color: #4B5563; color: #9CA3AF; }}
            QPushButton#CancelButton {{ background-color: #4B5563; }} /* Gray for cancel */
            QPushButton#CancelButton:hover {{ background-color: #6B7280; }}
            QPushButton#CancelButton:pressed {{ background-color: #374151; }}
        """

        self.apply_button = QPushButton(self.lm.get_string("apply"))
        self.apply_button.setStyleSheet(button_style)
        self.apply_button.clicked.connect(self.apply_settings)
        buttons_layout.addWidget(self.apply_button)

        self.ok_button = QPushButton(self.lm.get_string("ok"))
        self.ok_button.setStyleSheet(button_style)
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept_settings)
        buttons_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton(self.lm.get_string("cancel"))
        self.cancel_button.setObjectName("CancelButton") # For specific styling
        self.cancel_button.setStyleSheet(button_style)
        self.cancel_button.clicked.connect(self.reject) # QDialog's reject slot
        buttons_layout.addWidget(self.cancel_button)
        
        main_content_layout.addLayout(buttons_layout)

    def load_settings_to_ui(self):
        print("DEBUG: SettingsWindow - Loading settings to UI...")
        # General Tab
        current_lang = self.settings_mngr.get("language", "ar")
        lang_index = self.lang_combo.findData(current_lang)
        if lang_index != -1: self.lang_combo.setCurrentIndex(lang_index)

        current_theme = self.settings_mngr.get("theme", "system")
        theme_index = self.theme_combo.findData(current_theme)
        if theme_index != -1: self.theme_combo.setCurrentIndex(theme_index)

        self.start_with_windows_checkbox.setChecked(self.settings_mngr.get("start_with_windows", False))

        # Reminders Tab
        rtype = self.settings_mngr.get("reminder_type", "text")
        rtype_idx = self.rtype_combo.findData(rtype)
        if rtype_idx != -1: self.rtype_combo.setCurrentIndex(rtype_idx)
        
        self.interval_spinbox.setValue(self.settings_mngr.get("interval_minutes", 15))
        
        pos = self.settings_mngr.get("notification_position", "bottom_right")
        pos_idx = self.pos_combo.findData(pos)
        if pos_idx != -1: self.pos_combo.setCurrentIndex(pos_idx)
        
        self.duration_spinbox.setValue(self.settings_mngr.get("notification_duration_seconds", 7))
        
        self.populate_reminder_audio_list() # Load and check selected reminder audios
        
        # Prayer Times Tab
        self.pt_enable_checkbox.setChecked(self.settings_mngr.get("prayer_times_active", False))
        
        loc_method = self.settings_mngr.get("prayer_location_method", "auto_ip")
        loc_method_idx = self.pt_loc_method_combo.findData(loc_method)
        if loc_method_idx != -1: self.pt_loc_method_combo.setCurrentIndex(loc_method_idx)
        
        self.pt_city_edit.setText(self.settings_mngr.get("prayer_city", ""))
        self.pt_country_edit.setText(self.settings_mngr.get("prayer_country", ""))
        self.pt_latitude_edit.setText(self.settings_mngr.get("prayer_latitude", ""))
        self.pt_longitude_edit.setText(self.settings_mngr.get("prayer_longitude", ""))
        
        calc_method_val = self.settings_mngr.get("prayer_calculation_method", "5")
        calc_method_idx = self.pt_method_combo.findData(calc_method_val)
        if calc_method_idx != -1: self.pt_method_combo.setCurrentIndex(calc_method_idx)

        asr_method_val = self.settings_mngr.get("prayer_asr_method", "0")
        asr_idx = self.pt_asr_method_combo.findData(asr_method_val)
        if asr_idx != -1: self.pt_asr_method_combo.setCurrentIndex(asr_idx)

        midnight_val = self.settings_mngr.get("prayer_midnight_mode", "0")
        midnight_idx = self.pt_midnight_mode_combo.findData(midnight_val)
        if midnight_idx != -1: self.pt_midnight_mode_combo.setCurrentIndex(midnight_idx)

        lat_adj_val = self.settings_mngr.get("prayer_latitude_adjustment_method", "3")
        lat_adj_idx = self.pt_lat_adj_combo.findData(lat_adj_val)
        if lat_adj_idx != -1: self.pt_lat_adj_combo.setCurrentIndex(lat_adj_idx)

        self.pt_tune_edit.setText(self.settings_mngr.get("prayer_tune_values", "0,0,0,0,0,0,0,0"))

        # Prayer Alerts
        self.pt_pre_adhan_alert_checkbox.setChecked(self.settings_mngr.get("pre_adhan_alert_active", False))
        self.pt_pre_adhan_minutes_spinbox.setValue(self.settings_mngr.get("pre_adhan_minutes", 10))
        # Sound combo for pre-adhan will be populated by populate_audio_comboboxes

        self.pt_post_adhan_alert_checkbox.setChecked(self.settings_mngr.get("post_adhan_iqama_alert_active", False))
        self.pt_post_adhan_minutes_spinbox.setValue(self.settings_mngr.get("post_adhan_iqama_minutes", 10))
        # Sound combo for post-adhan will be populated by populate_audio_comboboxes

        # Adhan Sounds
        self.use_unified_adhan_checkbox.setChecked(self.settings_mngr.get("use_unified_adhan_sound", True))
        # Unified and specific adhan sound combos will be populated by populate_audio_comboboxes
        
        self.populate_audio_comboboxes() # Crucial call after other UI elements are ready
        self.set_selected_combo_item(self.pt_pre_adhan_sound_combo, self.settings_mngr.get("pre_adhan_sound_file", ""))
        self.set_selected_combo_item(self.pt_post_adhan_sound_combo, self.settings_mngr.get("post_adhan_iqama_sound_file", ""))
        self.set_selected_combo_item(self.unified_adhan_sound_combo, self.settings_mngr.get("unified_adhan_sound_file", ""))
        self.set_selected_combo_item(self.adhan_fajr_combo, self.settings_mngr.get("adhan_sound_fajr", ""))
        self.set_selected_combo_item(self.adhan_dhuhr_combo, self.settings_mngr.get("adhan_sound_dhuhr", ""))
        self.set_selected_combo_item(self.adhan_asr_combo, self.settings_mngr.get("adhan_sound_asr", ""))
        self.set_selected_combo_item(self.adhan_maghrib_combo, self.settings_mngr.get("adhan_sound_maghrib", ""))
        self.set_selected_combo_item(self.adhan_isha_combo, self.settings_mngr.get("adhan_sound_isha", ""))


        # Update visibility of conditional sections
        self._toggle_reminder_detail_widgets()
        self._toggle_location_input_widgets()
        self._toggle_prayer_times_widgets_enabled_state(self.pt_enable_checkbox.isChecked())
        self._toggle_pre_adhan_widgets_enabled(self.pt_pre_adhan_alert_checkbox.isChecked())
        self._toggle_post_adhan_widgets_enabled(self.pt_post_adhan_alert_checkbox.isChecked())
        self._toggle_adhan_sound_inputs_visibility(self.use_unified_adhan_checkbox.isChecked())
        
        # Content Tab
        self.display_text_adhkar_in_tab()
        
        print("DEBUG: SettingsWindow - UI loaded with current settings.")

    def apply_settings(self):
        print("DEBUG: SettingsWindow - Applying settings...")
        settings_to_save = {
            "language": self.lang_combo.currentData(),
            "theme": self.theme_combo.currentData(),
            "start_with_windows": self.start_with_windows_checkbox.isChecked(),
            "reminder_type": self.rtype_combo.currentData(),
            "interval_minutes": self.interval_spinbox.value(),
            "notification_position": self.pos_combo.currentData(),
            "notification_duration_seconds": self.duration_spinbox.value(),
            
            "selected_audio_files": self.get_selected_reminder_audio_files(),

            "prayer_times_active": self.pt_enable_checkbox.isChecked(),
            "prayer_location_method": self.pt_loc_method_combo.currentData(),
            "prayer_city": self.pt_city_edit.text(),
            "prayer_country": self.pt_country_edit.text(),
            "prayer_latitude": self.pt_latitude_edit.text(),
            "prayer_longitude": self.pt_longitude_edit.text(),
            "prayer_calculation_method": self.pt_method_combo.currentData(),
            "prayer_asr_method": self.pt_asr_method_combo.currentData(),
            "prayer_midnight_mode": self.pt_midnight_mode_combo.currentData(),
            "prayer_latitude_adjustment_method": self.pt_lat_adj_combo.currentData(),
            "prayer_tune_values": self.pt_tune_edit.text(),

            "pre_adhan_alert_active": self.pt_pre_adhan_alert_checkbox.isChecked(),
            "pre_adhan_minutes": self.pt_pre_adhan_minutes_spinbox.value(),
            "pre_adhan_sound_file": self.pt_pre_adhan_sound_combo.currentData() if self.pt_pre_adhan_sound_combo.currentIndex() > 0 else "",

            "post_adhan_iqama_alert_active": self.pt_post_adhan_alert_checkbox.isChecked(),
            "post_adhan_iqama_minutes": self.pt_post_adhan_minutes_spinbox.value(),
            "post_adhan_iqama_sound_file": self.pt_post_adhan_sound_combo.currentData() if self.pt_post_adhan_sound_combo.currentIndex() > 0 else "",
            
            "use_unified_adhan_sound": self.use_unified_adhan_checkbox.isChecked(),
            "unified_adhan_sound_file": self.unified_adhan_sound_combo.currentData() if self.unified_adhan_sound_combo.currentIndex() > 0 else "",
            "adhan_sound_fajr": self.adhan_fajr_combo.currentData() if self.adhan_fajr_combo.currentIndex() > 0 else "",
            "adhan_sound_dhuhr": self.adhan_dhuhr_combo.currentData() if self.adhan_dhuhr_combo.currentIndex() > 0 else "",
            "adhan_sound_asr": self.adhan_asr_combo.currentData() if self.adhan_asr_combo.currentIndex() > 0 else "",
            "adhan_sound_maghrib": self.adhan_maghrib_combo.currentData() if self.adhan_maghrib_combo.currentIndex() > 0 else "",
            "adhan_sound_isha": self.adhan_isha_combo.currentData() if self.adhan_isha_combo.currentIndex() > 0 else ""
        }
        self.settings_mngr.set_bulk(settings_to_save)
        
        # Emit signals for changes that need immediate app-wide reaction
        if self.settings_mngr.get("language") != self.lang_combo.currentData():
             self.language_changed_signal.emit(self.lang_combo.currentData())
        if self.settings_mngr.get("theme") != self.theme_combo.currentData():
             self.theme_changed_signal.emit(self.theme_combo.currentData())

        self.settings_applied_signal.emit() # General signal that settings were applied
        print("INFO: SettingsWindow - Settings applied and saved.")
        # QMessageBox.information(self, self.lm.get_string("settings_applied_title", "Settings Applied"),
        #                         self.lm.get_string("settings_applied_message", "Settings have been applied."))

    def accept_settings(self):
        self.apply_settings()
        super().accept() # Closes the dialog with QDialog.DialogCode.Accepted

    def reject(self): # Overriding reject to ensure it always just closes
        super().reject() # Closes the dialog with QDialog.DialogCode.Rejected

    def language_preference_changed_in_settings(self):
        new_lang = self.lang_combo.currentData()
        if new_lang != self.lm.get_current_language():
            print(f"DEBUG: SettingsWindow - Language preference changed to {new_lang}. Emitting signal.")
            # self.language_changed_signal.emit(new_lang) # This will be handled by apply/ok
            # For immediate UI text update within settings window itself:
            self.lm.load_language(new_lang)
            self.update_ui_texts_and_direction()


    def theme_preference_changed(self):
        new_theme = self.theme_combo.currentData()
        print(f"DEBUG: SettingsWindow - Theme preference changed to {new_theme}.")
        # self.theme_changed_signal.emit(new_theme) # This will be handled by apply/ok
        # Actual theme application logic is in main.py or app class

    def update_ui_texts_and_direction(self):
        self.setWindowTitle(self.lm.get_string("settings"))
        if hasattr(self, 'title_label'): self.title_label.setText(self.lm.get_string("settings"))

        # Tab Titles
        if self.tabs.count() > 0: self.tabs.setTabText(0, self.lm.get_string("general"))
        if self.tabs.count() > 1: self.tabs.setTabText(1, self.lm.get_string("reminders"))
        if self.tabs.count() > 2: self.tabs.setTabText(2, self.lm.get_string("content_tab_title"))
        if self.tabs.count() > 3: self.tabs.setTabText(3, self.lm.get_string("prayer_times_tab_title"))
        if self.tabs.count() > 4: self.tabs.setTabText(4, self.lm.get_string("download_adhan_tab_title", "Download Adhan"))


        # General Tab
        self.lang_label.setText(self.lm.get_string("language") + ":")
        self.theme_label.setText(self.lm.get_string("theme_setting") + ":")
        # ComboBox items for lang/theme are set with fixed text + data, so they don't need re-translation of items.
        self.start_with_windows_checkbox.setText(self.lm.get_string("start_with_windows"))
        if hasattr(self, 'lang_group'): self.lang_group.setTitle(self.lm.get_string("language_settings_group", "Language & Theme"))


        # Reminders Tab
        if hasattr(self, 'rem_config_group'): self.rem_config_group.setTitle(self.lm.get_string("reminder_config_group", "Reminder Configuration"))
        self.rtype_label.setText(self.lm.get_string("reminder_type"))
        self.rtype_combo.setItemText(0, self.lm.get_string("text_notification"))
        self.rtype_combo.setItemText(1, self.lm.get_string("sound_notification"))
        self.rtype_combo.setItemText(2, self.lm.get_string("random_notification"))
        self.interval_label.setText(self.lm.get_string("reminder_interval_minutes"))
        self.interval_spinbox.setSuffix(f" {self.lm.get_string('minutes_suffix')}")
        
        if hasattr(self, 'text_notification_settings_group'): self.text_notification_settings_group.setTitle(self.lm.get_string("text_notification_settings_group", "Text Notification Settings"))
        self.pos_label.setText(self.lm.get_string("notification_position"))
        # Position combo items set with lm.get_string initially, should be fine.
        self.duration_label.setText(self.lm.get_string("notification_duration_seconds"))
        self.duration_spinbox.setSuffix(f" {self.lm.get_string('seconds_suffix')}")
        
        if hasattr(self, 'sound_notification_settings_group'):
            self.sound_notification_settings_group.setTitle(self.lm.get_string("sound_notification_settings_group", "Sound Reminder Settings"))
            # The label inside this group if any
            first_child = self.sound_notification_settings_group.layout().itemAt(0)
            if first_child and isinstance(first_child.widget(), QLabel):
                first_child.widget().setText(self.lm.get_string("audio_files_select"))


        # Content Tab
        if hasattr(self, 'adhkar_display_group'): self.adhkar_display_group.setTitle(self.lm.get_string("text_adhkar_display"))
        self.display_text_adhkar_in_tab() # Reload Adhkar with new lang if lm changed

        # Prayer Times Tab
        self.pt_enable_checkbox.setText(self.lm.get_string("enable_prayer_times"))
        self.pt_location_group.setTitle(self.lm.get_string("location_settings_group"))
        # ... and so on for all labels and group titles in Prayer Times tab
        # This part can be very verbose, ensure all static texts are updated.
        # Example for one combo in prayer times:
        self.pt_loc_method_combo.itemAt(0).widget().setText(self.lm.get_string("location_method_auto_ip")) # If item is a widget
        # Or if items are simple strings:
        # self.pt_loc_method_combo.setItemText(0, self.lm.get_string("location_method_auto_ip"))


        # Action Buttons
        self.apply_button.setText(self.lm.get_string("apply"))
        self.ok_button.setText(self.lm.get_string("ok"))
        self.cancel_button.setText(self.lm.get_string("cancel"))

        # Layout Direction
        if self.lm.get_current_language() == "ar":
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            for i in range(self.tabs.count()): # Also set direction for tab contents
                self.tabs.widget(i).setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            for i in range(self.tabs.count()):
                self.tabs.widget(i).setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        
        self.adjustSize()


    def _toggle_reminder_detail_widgets(self):
        rtype = self.rtype_combo.currentData()
        self.text_notification_settings_group.setVisible(rtype in ["text", "random"])
        self.sound_notification_settings_group.setVisible(rtype in ["sound", "random"])

    def _toggle_location_input_widgets(self):
        loc_method = self.pt_loc_method_combo.currentData()
        self.pt_city_country_widget.setVisible(loc_method == "manual_city")
        self.pt_coords_widget.setVisible(loc_method == "manual_coords")

    def _toggle_prayer_times_widgets_enabled_state(self, enabled):
        # Enable/disable all group boxes related to prayer times settings
        widgets_to_toggle = [
            self.pt_location_group, self.pt_calculation_group, self.pt_tune_group,
            self.pt_alerts_group, self.adhan_sounds_group
        ]
        for widget_group in widgets_to_toggle:
            widget_group.setEnabled(enabled)
        # Ensure conditional visibility is also reapplied if needed
        if enabled:
            self._toggle_location_input_widgets()
            self._toggle_pre_adhan_widgets_enabled(self.pt_pre_adhan_alert_checkbox.isChecked())
            self._toggle_post_adhan_widgets_enabled(self.pt_post_adhan_alert_checkbox.isChecked())
            self._toggle_adhan_sound_inputs_visibility(self.use_unified_adhan_checkbox.isChecked())

    def _toggle_pre_adhan_widgets_enabled(self, enabled):
        self.pt_pre_adhan_minutes_spinbox.setEnabled(enabled)
        self.pt_pre_adhan_sound_combo.setEnabled(enabled)

    def _toggle_post_adhan_widgets_enabled(self, enabled):
        self.pt_post_adhan_minutes_spinbox.setEnabled(enabled)
        self.pt_post_adhan_sound_combo.setEnabled(enabled)
        
    def _toggle_adhan_sound_inputs_visibility(self, use_unified_checked):
        self.unified_adhan_widget.setVisible(use_unified_checked)
        self.specific_adhan_sounds_widget.setVisible(not use_unified_checked)

    def populate_audio_comboboxes(self):
        print("DEBUG: SettingsWindow - Populating ALL audio comboboxes...")
        adhan_files = self._get_audio_files_from_dir(self.ADHAN_AUDIO_DIR)
        
        # Helper to populate one combobox
        def _populate_one_combo(combo, files, current_selection_value):
            combo.blockSignals(True) # Block signals during modification
            combo.clear()
            combo.addItem(self.lm.get_string("none", "None"), "") # "" as data for "None"
            selected_idx = 0 # Default to "None"
            for i, filename in enumerate(files):
                combo.addItem(filename, filename) # Text and data are the same (filename)
                if filename == current_selection_value:
                    selected_idx = i + 1 # +1 because of "None" item
            combo.setCurrentIndex(selected_idx)
            combo.blockSignals(False)

        # Prayer Alert Sounds
        _populate_one_combo(self.pt_pre_adhan_sound_combo, adhan_files, self.settings_mngr.get("pre_adhan_sound_file"))
        _populate_one_combo(self.pt_post_adhan_sound_combo, adhan_files, self.settings_mngr.get("post_adhan_iqama_sound_file"))

        # Adhan Sounds
        _populate_one_combo(self.unified_adhan_sound_combo, adhan_files, self.settings_mngr.get("unified_adhan_sound_file"))
        _populate_one_combo(self.adhan_fajr_combo, adhan_files, self.settings_mngr.get("adhan_sound_fajr"))
        _populate_one_combo(self.adhan_dhuhr_combo, adhan_files, self.settings_mngr.get("adhan_sound_dhuhr"))
        _populate_one_combo(self.adhan_asr_combo, adhan_files, self.settings_mngr.get("adhan_sound_asr"))
        _populate_one_combo(self.adhan_maghrib_combo, adhan_files, self.settings_mngr.get("adhan_sound_maghrib"))
        _populate_one_combo(self.adhan_isha_combo, adhan_files, self.settings_mngr.get("adhan_sound_isha"))
        print("DEBUG: SettingsWindow - Audio comboboxes populated.")

    def _get_audio_files_from_dir(self, directory):
        if not os.path.exists(directory):
            print(f"WARN: Audio directory not found: {directory}")
            return []
        try:
            all_entries = os.listdir(directory)
            audio_files = sorted([f for f in all_entries if f.lower().endswith(('.mp3', '.wav', '.ogg'))])
            return audio_files
        except Exception as e:
            print(f"ERROR: Failed to list audio files in {directory}: {e}")
            return []

    def populate_reminder_audio_list(self):
        print("DEBUG: SettingsWindow - Populating reminder audio list...")
        self.reminder_audio_files_listwidget.clear()
        reminder_audio_files = self._get_audio_files_from_dir(self.REMINDER_AUDIO_DIR)
        selected_files_from_settings = self.settings_mngr.get("selected_audio_files", [])

        if not reminder_audio_files:
            no_files_item = QListWidgetItem(self.lm.get_string("no_audio_files_found"))
            no_files_item.setFlags(no_files_item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled)
            self.reminder_audio_files_listwidget.addItem(no_files_item)
        else:
            for filename in reminder_audio_files:
                item = QListWidgetItem(filename)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable) # Make it checkable
                if filename in selected_files_from_settings:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.reminder_audio_files_listwidget.addItem(item)
        print("DEBUG: SettingsWindow - Reminder audio list populated.")


    def get_selected_reminder_audio_files(self):
        selected_files = []
        for i in range(self.reminder_audio_files_listwidget.count()):
            item = self.reminder_audio_files_listwidget.item(i)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable and item.checkState() == Qt.CheckState.Checked:
                selected_files.append(item.text())
        return selected_files

    def set_selected_combo_item(self, combobox, value_to_select):
        # Helper to select an item in a combobox by its data (or text if data is same as text)
        if not value_to_select: # If value is empty, select "None" (index 0)
            combobox.setCurrentIndex(0)
            return
        index = combobox.findData(value_to_select)
        if index != -1:
            combobox.setCurrentIndex(index)
        else: # Fallback to finding by text if data not found (e.g. "None" item has "" as data)
            index_text = combobox.findText(value_to_select)
            if index_text != -1:
                combobox.setCurrentIndex(index_text)
            else:
                combobox.setCurrentIndex(0) # Default to "None" if not found


    def display_text_adhkar_in_tab(self):
        if not hasattr(self, 'adhkar_text_area_display') or not self.adhkar_mngr:
            print("WARN: SettingsWindow - Adhkar display area or manager not ready.")
            return
        
        self.adhkar_text_area_display.clear()
        current_lang = self.lm.get_current_language()
        self.adhkar_mngr.set_language(current_lang) # Ensure AdhkarManager uses current UI lang

        all_adhkar = self.adhkar_mngr.get_all_adhkar_structured()
        if not all_adhkar:
            self.adhkar_text_area_display.setHtml(f"<p>{self.lm.get_string('no_adhkar_to_display')}</p>")
            return

        html_content = "<div style='font-family: Segoe UI, sans-serif;'>"
        categories_order = ["morning", "evening", "sleep", "general"] # Preferred order

        for category_key in categories_order:
            if category_key in all_adhkar:
                adhkar_list = all_adhkar[category_key]
                if isinstance(adhkar_list, list) and adhkar_list:
                    # Category Title - Use lm.get_string for category name if available
                    cat_name_key = f"{category_key}_adhkar_title" # e.g. morning_adhkar_title
                    cat_display_name = self.lm.get_string(cat_name_key, category_key.capitalize())
                    
                    html_content += f"<h3 style='color: #A5B4FC; margin-top: 15px; margin-bottom: 8px;'>{cat_display_name}</h3>"
                    html_content += "<ul style='list-style-type: none; padding-left: 0;'>"
                    for dhikr_item in adhkar_list:
                        if isinstance(dhikr_item, dict) and 'text' in dhikr_item:
                            text = dhikr_item['text']
                            # Optional: Display count and benefit if they exist
                            details = []
                            if "count" in dhikr_item and dhikr_item["count"] != -1 : # -1 might mean "as much as possible"
                                details.append(f"<span style='color: #60A5FA;'>({self.lm.get_string('count_prefix', 'Count')}: {dhikr_item['count']})</span>")
                            if "benefit" in dhikr_item and dhikr_item["benefit"]:
                                details.append(f"<em style='color: #818CF8;'>- {dhikr_item['benefit']}</em>")
                            
                            details_str = " ".join(details)
                            html_content += f"<li style='margin-bottom: 6px; padding: 5px; background-color: rgba(255,255,255,0.03); border-radius: 3px;'>{text} {details_str}</li>"
                    html_content += "</ul>"
        html_content += "</div>"
        self.adhkar_text_area_display.setHtml(html_content)


    # Override showEvent to load settings each time dialog is shown
    def showEvent(self, event):
        print("DEBUG: SettingsWindow - showEvent triggered. Reloading settings to UI.")
        self.load_settings_to_ui()
        # Ensure layout direction is correct based on current language
        self.update_ui_texts_and_direction() 
        super().showEvent(event)

    # Override closeEvent if needed for specific cleanup,
    # but QDialog's default closeEvent (connected to reject) is usually fine.
    # def closeEvent(self, event):
    #     super().closeEvent(event)