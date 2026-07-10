import os
import re
import time
import urllib.parse # قد نحتاجها لتحليل روابط معقدة، لكن ليس بالضرورة لـ Assabile
import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QProgressBar, QAbstractItemView, QMessageBox, QApplication, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import pygame
from bs4 import BeautifulSoup

# --- إعدادات ---
# تم التعليق على إعدادات IslamWeb لأننا نركز على Assabile الآن
# ISLAMWEB_BASE_URL = "https://audio.islamweb.net"
# ISLAMWEB_AUDIO_GROUP_URL = f"{ISLAMWEB_BASE_URL}/audio/index.php?Gtype=1&page=AudioGroup"

ASSABILE_ADHAN_URL = "https://ar.assabile.com/adhan-call-prayer" # الرابط الجديد لمصدر الأذانات
ADHAN_DIR = os.path.join(os.getcwd(), "resources", "audio", "adhan_assabile") # مجلد منفصل لأذانات Assabile
print(f"INFO: Adhan directory set to: {ADHAN_DIR}")


# --- دوال مساعدة ---
def sanitize_filename(name):
    print(f"DEBUG: Sanitizing filename: '{name}'")
    original_name = name
    # إزالة " - " و " ," واستبدالها بـ "_" قبل إزالة الأحرف الأخرى
    name = name.replace(" - ", "_").replace(" ,", "_").replace(",", "_")
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.replace(" ", "_")
    # إزالة الشرطات السفلية المتتالية
    name = re.sub(r'_+', '_', name)
    name = name.strip("._ ")
    if not name:
        name = "untitled_adhan"
        print(f"WARN: Original filename '{original_name}' resulted in empty, using '{name}'")
    if not name.lower().endswith(".mp3"):
        name += ".mp3"
    print(f"DEBUG: Sanitized filename: '{name}'")
    return name

# --- ويدجت عنصر الأذان المحلي ---
class LocalAdhanItemWidget(QWidget):
    play_clicked = pyqtSignal(str)
    stop_clicked = pyqtSignal(str)
    delete_clicked = pyqtSignal(str)

    def __init__(self, filename, is_playing=False, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.is_playing = is_playing

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        self.label = QLabel(os.path.basename(filename))
        self.label.setStyleSheet("color: #e0e0e0; font-size: 10pt;")

        self.play_button = QPushButton("تشغيل" if not is_playing else "إيقاف")
        self.play_button.setStyleSheet("QPushButton { background-color: #4299e1; border: 1px solid #2b6cb0; color: white; padding: 5px 10px; border-radius: 4px; font-size: 9pt; } QPushButton:hover { background-color: #3182ce; }")

        self.delete_button = QPushButton("حذف")
        self.delete_button.setStyleSheet("QPushButton { background-color: #e53e3e; border: 1px solid #c53030; color: white; padding: 5px 10px; border-radius: 4px; font-size: 9pt; } QPushButton:hover { background-color: #c53030; }")

        layout.addWidget(self.label)
        layout.addStretch(1)
        layout.addWidget(self.play_button)
        layout.addWidget(self.delete_button)

        self.play_button.clicked.connect(self.toggle_play)
        self.delete_button.clicked.connect(lambda: self.delete_clicked.emit(self.filename))

    def toggle_play(self):
        if self.is_playing:
            self.stop_clicked.emit(self.filename)
        else:
            self.play_clicked.emit(self.filename)

    def set_playing(self, is_playing):
        self.is_playing = is_playing
        self.play_button.setText("إيقاف" if is_playing else "تشغيل")

# --- خيط جلب قائمة الأذانات (مُعد لـ Assabile.com) ---
class AdhanListFetcher(QThread):
    fetched = pyqtSignal(list, str)
    progress_update = pyqtSignal(str)

    def run(self):
        print("INFO: AdhanListFetcher thread started (for Assabile.com).")
        adhan_list_result = []
        error_message = ""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://ar.assabile.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        try:
            self.progress_update.emit(f"جاري تحميل قائمة الأذانات من {ASSABILE_ADHAN_URL}...")
            print(f"INFO: Fetching Adhan list from URL: {ASSABILE_ADHAN_URL}")
            
            # إضافة timeout و verify=False للتعامل مع مشاكل SSL
            response = requests.get(
                ASSABILE_ADHAN_URL, 
                headers=headers, 
                timeout=30,
                verify=False
            )
            
            print(f"INFO: Main list page status code: {response.status_code} for Assabile")
            response.raise_for_status()
            
            # التحقق من نوع المحتوى
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                error_message = f"تم استلام نوع محتوى غير متوقع: {content_type}"
                print(f"ERROR: {error_message}")
                self.fetched.emit([], error_message)
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            adhan_items_li = soup.find_all("li", class_="adane")
            
            if not adhan_items_li:
                error_message = "لم يتم العثور على عناصر الأذان. قد يكون هيكل الموقع قد تغير."
                print(f"ERROR: {error_message}")
                self.fetched.emit([], error_message)
                return

            self.progress_update.emit(f"تم العثور على {len(adhan_items_li)} عنصر أذان. جاري استخراج التفاصيل...")
            
            for i, item_li in enumerate(adhan_items_li):
                try:
                    link_media_tag = item_li.find("a", class_="link-media")
                    if not link_media_tag or not link_media_tag.has_attr('href'):
                        continue

                    mp3_url = link_media_tag['href']
                    if not mp3_url.startswith(('http://', 'https://')):
                        mp3_url = 'https://ar.assabile.com' + mp3_url

                    name_span = link_media_tag.find("span", class_="sorting")
                    adhan_name_raw = name_span.text.strip() if name_span else "أذان غير مسمى"

                    if mp3_url and adhan_name_raw:
                        adhan_list_result.append({
                            'name': adhan_name_raw,
                            'url': mp3_url
                        })
                        self.progress_update.emit(f"تمت إضافة: {adhan_name_raw[:30]}...")
                except Exception as e:
                    print(f"WARN: Error processing item {i+1}: {str(e)}")
                    continue

            if not adhan_list_result:
                error_message = "لم يتم العثور على أي أذانات صالحة."
            else:
                error_message = ""

            self.fetched.emit(adhan_list_result, error_message)

        except requests.exceptions.Timeout:
            error_message = "انتهت مهلة الاتصال بالخادم. يرجى المحاولة مرة أخرى."
            print(f"ERROR: {error_message}")
            self.fetched.emit([], error_message)
        except requests.exceptions.RequestException as e:
            error_message = f"خطأ في الاتصال بالخادم: {str(e)}"
            print(f"ERROR: {error_message}")
            self.fetched.emit([], error_message)
        except Exception as e:
            error_message = f"خطأ غير متوقع: {str(e)}"
            print(f"ERROR: {error_message}")
            import traceback
            traceback.print_exc()
            self.fetched.emit([], error_message)
        finally:
            self.progress_update.emit("")
            print("INFO: AdhanListFetcher thread finished execution.")

# --- خيط تحميل الأذان ---
class AdhanDownloader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str, str)

    def __init__(self, url, filename_to_save_as):
        super().__init__()
        self.url = url
        self.filename_to_save_as = filename_to_save_as
        print(f"INFO: AdhanDownloader initialized for URL: '{self.url}', Filename: '{self.filename_to_save_as}'")

    def run(self):
        print(f"INFO: AdhanDownloader thread started for '{self.filename_to_save_as}'.")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://ar.assabile.com/' # من الجيد وضع Referer مناسب للمصدر
            }
        filepath = os.path.join(ADHAN_DIR, self.filename_to_save_as)
        error_msg_download = ""
        
        try:
            print(f"INFO: Attempting to download from: {self.url}")
            response = requests.get(self.url, stream=True, headers=headers, timeout=90)
            print(f"INFO: Download request status code: {response.status_code} for '{self.filename_to_save_as}'")
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            print(f"INFO: Actual Content-Type from GET request: '{content_type}' for '{self.filename_to_save_as}'")
            
            # التحقق من نوع المحتوى (أكثر تساهلاً مع Assabile لأن روابطهم مباشرة عادة)
            if not ('audio' in content_type or 'octet-stream' in content_type or content_type == ''):
                # إذا كان حجم الملف صغيرًا جدًا وكان النوع html، فهذه مشكلة
                content_length = int(response.headers.get('content-length', 0))
                if content_length < 5120 and 'html' in content_type: # أقل من 5KB
                    error_msg_download = f"تم تحميل محتوى HTML ({content_length} bytes) بدلاً من ملف صوتي. تحقق من الرابط: {self.url}"
                    print(f"ERROR: {error_msg_download}")
                    self.finished.emit(self.filename_to_save_as, error_msg_download)
                    return
                elif content_length > 0 : # إذا كان هناك حجم ولكن النوع ليس صوتيًا، نحذر
                    print(f"WARN: Content-Type for '{self.filename_to_save_as}' is '{content_type}', but proceeding with download as content_length is {content_length}.")


            total_size = int(response.headers.get('content-length', 0))
            print(f"INFO: Total download size: {total_size} bytes for '{self.filename_to_save_as}'")
            block_size = 8192
            downloaded = 0

            os.makedirs(ADHAN_DIR, exist_ok=True)
            print(f"INFO: Writing downloaded file to: {filepath}")
            
            with open(filepath, 'wb') as f:
                for data_chunk in response.iter_content(block_size):
                    if data_chunk:
                        downloaded += len(data_chunk)
                        f.write(data_chunk)
                        if total_size > 0:
                            progress_val = int((downloaded / total_size) * 100)
                            self.progress.emit(progress_val)
                        else:
                            self.progress.emit(-1)
            
            print(f"INFO: Finished writing {downloaded} bytes to '{filepath}'")
            if total_size == 0 and downloaded > 0:
                self.progress.emit(100)
            elif downloaded < total_size and total_size > 0: # تحقق إذا كان التحميل غير مكتمل
                 print(f"WARN: Download for '{self.filename_to_save_as}' might be incomplete. Downloaded: {downloaded}, Total: {total_size}")

            self.finished.emit(self.filename_to_save_as, "")
        except requests.exceptions.Timeout:
            error_msg_download = f"انتهت مهلة الاتصال بالخادم أثناء تحميل '{self.filename_to_save_as}'."
            print(f"ERROR: {error_msg_download}")
            self.finished.emit(self.filename_to_save_as, error_msg_download)
        except requests.exceptions.RequestException as e_req:
            error_msg_download = f"خطأ في الشبكة أثناء تحميل '{self.filename_to_save_as}': {e_req}"
            print(f"ERROR: {error_msg_download}")
            self.finished.emit(self.filename_to_save_as, error_msg_download)
        except IOError as e_io:
            error_msg_download = f"خطأ في الكتابة إلى الملف '{filepath}': {e_io}"
            print(f"ERROR: {error_msg_download}")
            self.finished.emit(self.filename_to_save_as, error_msg_download)
        except Exception as e:
            error_msg_download = f"خطأ غير متوقع أثناء تحميل '{self.filename_to_save_as}': {type(e).__name__} - {str(e)}"
            print(f"ERROR: {error_msg_download}")
            import traceback
            traceback.print_exc()
            self.finished.emit(self.filename_to_save_as, error_msg_download)
        finally:
            print(f"INFO: AdhanDownloader thread finished execution for '{self.filename_to_save_as}'.")

# --- الويدجت الرئيسي ---
class AdhanDownloadWidget(QWidget):
    def __init__(self, settings_window=None, parent=None):
        super().__init__(parent)
        print("INFO: AdhanDownloadWidget initializing...")
        self.settings_window = settings_window
        self.currently_playing_filename = None
        self.currently_playing_widget = None
        self.fetcher = None
        self.downloader = None
        self._all_online_items_data = [] # لتخزين جميع العناصر الأصلية للبحث

        try:
            pygame.mixer.init()
            print("INFO: Pygame mixer initialized successfully.")
        except pygame.error as pg_err:
            print(f"CRITICAL: Failed to initialize Pygame Mixer: {pg_err}")
            QMessageBox.critical(self, "خطأ Pygame", f"فشل في تهيئة Pygame Mixer: {pg_err}\nلن يعمل تشغيل الصوت.")
        
        self.init_ui()
        self.load_local_adhans()
        self.fetch_online_adhans()
        print("INFO: AdhanDownloadWidget initialization complete.")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        online_group_widget = QWidget()
        online_layout = QVBoxLayout(online_group_widget)
        online_layout.addWidget(QLabel("الأذان المتاحة للتحميل (من Assabile.com):")) # تم تحديث النص

        self.search_lineedit = QLineEdit()
        self.search_lineedit.setPlaceholderText("ابحث عن اسم الأذان أو القارئ...")
        self.search_button = QPushButton("بحث") # يمكن إزالته إذا كان الفلتر ديناميكيًا
        self.search_button.setStyleSheet("QPushButton { background-color: #4299e1; color: white; border-radius: 4px; padding: 4px 10px; } QPushButton:hover { background-color: #3182ce; }")
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_lineedit)
        # search_layout.addWidget(self.search_button) # زر البحث اختياري مع الفلترة الديناميكية
        online_layout.addLayout(search_layout)

        self.online_list_widget = QListWidget()
        self.online_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        online_layout.addWidget(self.online_list_widget)

        online_buttons_layout = QHBoxLayout()
        self.refresh_button = QPushButton("🔄 تحديث القائمة")
        self.download_button = QPushButton("⬇️ تحميل المحدد")
        self.refresh_button.setStyleSheet("QPushButton { background-color: #4299e1; border: 1px solid #2b6cb0; color: white; padding: 8px 12px; border-radius: 4px; } QPushButton:hover { background-color: #3182ce; } QPushButton:disabled { background-color: #a0aec0; }")
        self.download_button.setStyleSheet("QPushButton { background-color: #48bb78; border: 1px solid #2f855a; color: white; padding: 8px 12px; border-radius: 4px; } QPushButton:hover { background-color: #38a169; } QPushButton:disabled { background-color: #a0aec0; }")
        online_buttons_layout.addWidget(self.refresh_button)
        online_buttons_layout.addWidget(self.download_button)
        online_layout.addLayout(online_buttons_layout)

        self.fetch_status_label = QLabel("")
        self.fetch_status_label.setStyleSheet("color: #a0aec0; font-style: italic;")
        online_layout.addWidget(self.fetch_status_label)

        self.download_progress_bar = QProgressBar()
        self.download_progress_bar.setStyleSheet("QProgressBar { border: 1px solid #718096; border-radius: 4px; text-align: center; background-color: #4a5568; color: white; } QProgressBar::chunk { background-color: #4299e1; border-radius: 3px; }")
        self.download_progress_bar.setValue(0)
        self.download_progress_bar.setFixedHeight(20)
        online_layout.addWidget(self.download_progress_bar)

        local_group_widget = QWidget()
        local_layout = QVBoxLayout(local_group_widget)
        local_layout.addWidget(QLabel("الأذان المحملة محلياً:"))
        self.local_list_widget = QListWidget()
        local_layout.addWidget(self.local_list_widget)

        main_layout.addWidget(online_group_widget)
        main_layout.addWidget(local_group_widget)

        self.refresh_button.clicked.connect(self.fetch_online_adhans)
        self.download_button.clicked.connect(self.download_selected_adhan)
        # self.search_button.clicked.connect(self.filter_online_adhans) # إذا كنت تريد زرًا
        self.search_lineedit.textChanged.connect(self.filter_online_adhans) # فلترة ديناميكية

        self.download_button.setEnabled(False)
        self.online_list_widget.itemSelectionChanged.connect(
            lambda: self.download_button.setEnabled(bool(self.online_list_widget.selectedItems()))
        )

    def fetch_online_adhans(self):
        print("INFO: fetch_online_adhans called.")
        if self.fetcher and self.fetcher.isRunning():
            print("WARN: Fetcher is already running.")
            QMessageBox.information(self, "جاري الجلب", "عملية جلب قائمة الأذانات جارية بالفعل.")
            return
        self.download_progress_bar.setValue(0)
        self.online_list_widget.clear()
        self._all_online_items_data = [] # مسح القائمة المخزنة للبحث
        self.online_list_widget.addItem(QListWidgetItem("⏳ جاري تحميل قائمة الأذان، يرجى الانتظار..."))
        self.refresh_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.fetch_status_label.setText("بدء جلب القائمة...")
        self.fetcher = AdhanListFetcher()
        self.fetcher.fetched.connect(self.on_adhans_fetched)
        self.fetcher.progress_update.connect(self.update_fetch_status)
        self.fetcher.finished.connect(lambda: (self.refresh_button.setEnabled(True), print("INFO: Fetcher finished, refresh button re-enabled.")))
        self.fetcher.start()

    def update_fetch_status(self, message):
        self.fetch_status_label.setText(message)
        if not message: QApplication.processEvents()

    def on_adhans_fetched(self, adhan_list, error_msg):
        print(f"INFO: on_adhans_fetched called. Received {len(adhan_list)} adhans. Error: '{error_msg}'")
        self.online_list_widget.clear() # مسح العناصر القديمة أو رسالة الانتظار
        self._all_online_items_data = [] # مسح البيانات المخزنة للبحث
        self.refresh_button.setEnabled(True)

        if error_msg:
            QMessageBox.warning(self, "خطأ في جلب القائمة", f"فشل في جلب قائمة الأذان: {error_msg}")
            self.online_list_widget.addItem(QListWidgetItem(f"خطأ: {error_msg}"))
            return
        if not adhan_list:
            self.online_list_widget.addItem(QListWidgetItem("لم يتم العثور على أذانات متاحة للتحميل."))
            return

        self._all_online_items_data = adhan_list # تخزين جميع البيانات
        self.display_filtered_adhans("") # عرض كل شيء في البداية

        self.fetch_status_label.setText(f"تم جلب {len(adhan_list)} أذان بنجاح.")
        # QMessageBox.information(self, "اكتمل الجلب", f"تم تحميل قائمة بـ {len(adhan_list)} أذان.") # يمكن إزالتها لتجنب كثرة الرسائل

    def display_filtered_adhans(self, filter_text):
        self.online_list_widget.clear() # مسح القائمة المعروضة
        filter_text_lower = filter_text.lower()
        count = 0
        for adhan_data in self._all_online_items_data:
            if filter_text_lower in adhan_data['name'].lower():
                item = QListWidgetItem(f"{adhan_data['name']}")
                item.setData(Qt.ItemDataRole.UserRole, adhan_data)
                self.online_list_widget.addItem(item)
                count +=1
        if count == 0 and self._all_online_items_data: # إذا كانت هناك بيانات أصلية ولكن لا شيء يطابق الفلتر
            self.online_list_widget.addItem(QListWidgetItem("لا توجد نتائج تطابق بحثك."))
        elif not self._all_online_items_data and not self.fetcher.isRunning(): # إذا لم يكن هناك بيانات أصلية ولم يكن هناك خطأ
             self.online_list_widget.addItem(QListWidgetItem("لم يتم العثور على أذانات متاحة للتحميل."))


    def filter_online_adhans(self):
        text_to_filter = self.search_lineedit.text().strip()
        self.display_filtered_adhans(text_to_filter)


    def load_local_adhans(self):
        # ... (نفس الكود كما هو، لا تغييرات هنا) ...
        print("INFO: load_local_adhans called.")
        self.local_list_widget.clear()
        if not os.path.exists(ADHAN_DIR):
            print(f"INFO: Adhan directory '{ADHAN_DIR}' does not exist. Creating.")
            try:
                os.makedirs(ADHAN_DIR)
            except OSError as e:
                print(f"CRITICAL: Failed to create adhan directory: {ADHAN_DIR}\n{e}")
                QMessageBox.critical(self, "خطأ", f"فشل في إنشاء مجلد الأذان: {ADHAN_DIR}\n{e}")
                return
        adhans_found = False
        for filename_with_ext in os.listdir(ADHAN_DIR):
            if filename_with_ext.lower().endswith('.mp3'):
                adhans_found = True
                full_path = os.path.join(ADHAN_DIR, filename_with_ext)
                # print(f"DEBUG: Loading local adhan: {full_path}") # يمكن إلغاء التعليق
                list_item = QListWidgetItem(self.local_list_widget)
                item_widget = LocalAdhanItemWidget(full_path)
                item_widget.play_clicked.connect(self.play_local_adhan)
                item_widget.stop_clicked.connect(self.stop_current_adhan)
                item_widget.delete_clicked.connect(self.delete_local_adhan)
                list_item.setSizeHint(item_widget.sizeHint())
                self.local_list_widget.addItem(list_item)
                self.local_list_widget.setItemWidget(list_item, item_widget)
        if not adhans_found:
            print("INFO: No local adhans found.")
            placeholder_item = QListWidgetItem("لا يوجد أذانات محملة حالياً.")
            placeholder_item.setFlags(placeholder_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.local_list_widget.addItem(placeholder_item)

    def play_local_adhan(self, filepath):
        # ... (نفس الكود كما هو، لا تغييرات هنا) ...
        print(f"INFO: play_local_adhan called for: {filepath}")
        if not pygame.mixer.get_init():
            print("ERROR: Pygame mixer not initialized, cannot play.")
            QMessageBox.warning(self, "خطأ", "لم يتم تهيئة مشغل الصوت (Pygame Mixer).")
            return
        if self.currently_playing_filename and self.currently_playing_filename != filepath:
            # print(f"INFO: Stopping previously playing adhan: {self.currently_playing_filename}") # يمكن إلغاء التعليق
            self.stop_current_adhan(self.currently_playing_filename)
        try:
            print(f"DEBUG: pygame.mixer.music.load('{filepath}')")
            pygame.mixer.music.load(filepath)
            print("DEBUG: pygame.mixer.music.play()")
            pygame.mixer.music.play()
            self.currently_playing_filename = filepath
            for i in range(self.local_list_widget.count()):
                list_item = self.local_list_widget.item(i)
                widget = self.local_list_widget.itemWidget(list_item)
                if isinstance(widget, LocalAdhanItemWidget):
                    is_current = widget.filename == filepath
                    widget.set_playing(is_current)
                    if is_current: self.currently_playing_widget = widget
        except pygame.error as e:
            print(f"ERROR: Pygame error playing '{os.path.basename(filepath)}': {str(e)}")
            QMessageBox.warning(self, "خطأ في التشغيل", f"فشل في تشغيل الأذان '{os.path.basename(filepath)}':\n{str(e)}")
            self.currently_playing_filename = None
            self.currently_playing_widget = None


    def stop_current_adhan(self, filepath_to_stop=None):
        # ... (نفس الكود كما هو، لا تغييرات هنا) ...
        if not pygame.mixer.get_init(): return
        if filepath_to_stop is None or self.currently_playing_filename == filepath_to_stop:
            pygame.mixer.music.stop()
            current_playing_filename_before_stop = self.currently_playing_filename
            self.currently_playing_filename = None
            if self.currently_playing_widget and self.currently_playing_widget.filename == current_playing_filename_before_stop:
                self.currently_playing_widget.set_playing(False)
                self.currently_playing_widget = None


    def delete_local_adhan(self, filepath_to_delete):
        # ... (نفس الكود كما هو، لا تغييرات هنا) ...
        filename_only = os.path.basename(filepath_to_delete)
        print(f"INFO: delete_local_adhan called for: {filename_only}")
        reply = QMessageBox.question(self, "تأكيد الحذف", f"هل أنت متأكد من حذف: {filename_only}؟", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            print(f"INFO: User confirmed deletion for {filename_only}")
            try:
                if self.currently_playing_filename == filepath_to_delete: self.stop_current_adhan(filepath_to_delete)
                os.remove(filepath_to_delete)
                print(f"INFO: File {filepath_to_delete} removed successfully.")
                QMessageBox.information(self, "تم الحذف", f"تم حذف الملف {filename_only} بنجاح.")
                self.load_local_adhans()
                if self.settings_window and hasattr(self.settings_window, 'load_settings_to_ui'): self.settings_window.load_settings_to_ui()
            except OSError as e:
                print(f"ERROR: Failed to delete file {filepath_to_delete}: {str(e)}")
                QMessageBox.warning(self, "خطأ في الحذف", f"فشل في حذف الملف {filename_only}: {str(e)}")


    def download_selected_adhan(self):
        # ... (نفس الكود كما هو، لا تغييرات هنا) ...
        print("INFO: download_selected_adhan called.")
        selected_items = self.online_list_widget.selectedItems()
        if not selected_items:
            print("WARN: Download called with no item selected.")
            return
        if self.downloader and self.downloader.isRunning():
            print("WARN: Downloader is already running.")
            QMessageBox.information(self, "جاري التحميل", "عملية تحميل أخرى جارية بالفعل.")
            return
        item = selected_items[0]
        adhan_data = item.data(Qt.ItemDataRole.UserRole)
        url_to_download = adhan_data['url']
        original_name = adhan_data['name']
        print(f"INFO: Preparing to download: Name='{original_name}', URL='{url_to_download}'")
        safe_filename = sanitize_filename(original_name)
        filepath_to_save = os.path.join(ADHAN_DIR, safe_filename)
        if os.path.exists(filepath_to_save):
            print(f"WARN: File '{safe_filename}' already exists.")
            reply = QMessageBox.question(self, "ملف موجود", f"الملف '{safe_filename}' موجود بالفعل. هل تريد استبداله؟", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                print("INFO: User chose not to overwrite existing file.")
                self.download_progress_bar.setValue(0)
                return
        self.download_progress_bar.setValue(0)
        self.download_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.downloader = AdhanDownloader(url_to_download, safe_filename)
        self.downloader.progress.connect(self.update_download_progress)
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.finished.connect(lambda: (self.download_button.setEnabled(bool(self.online_list_widget.selectedItems())), self.refresh_button.setEnabled(True), print("INFO: Downloader finished, buttons re-enabled.")))
        self.downloader.start()


    def update_download_progress(self, value):
        # ... (نفس الكود كما هو، لا تغييرات هنا) ...
        if value == -1:
            self.download_progress_bar.setRange(0,0)
            self.download_progress_bar.setFormat("جاري التحميل...")
        else:
            self.download_progress_bar.setRange(0,100)
            self.download_progress_bar.setValue(value)
            self.download_progress_bar.setFormat(f"%p% - {value}%")


    def on_download_finished(self, downloaded_filename, error_msg):
        # ... (نفس الكود كما هو، لا تغييرات هنا) ...
        print(f"INFO: on_download_finished called for '{downloaded_filename}'. Error: '{error_msg}'")
        self.download_progress_bar.setRange(0,100)
        self.download_progress_bar.setValue(0 if error_msg else 100)
        self.download_progress_bar.setFormat("%p%")
        if error_msg:
            QMessageBox.warning(self, "خطأ في التحميل", f"فشل في تحميل الأذان '{downloaded_filename}': {error_msg}")
        else:
            QMessageBox.information(self, "اكتمل التحميل", f"تم تحميل الأذان بنجاح: {downloaded_filename}") # عرض رسالة نجاح
            self.load_local_adhans()
            if self.settings_window and hasattr(self.settings_window, 'load_settings_to_ui'): self.settings_window.load_settings_to_ui()


    def closeEvent(self, event):
        # ... (نفس الكود كما هو، لا تغييرات هنا) ...
        print("INFO: AdhanDownloadWidget closeEvent called.")
        if self.fetcher and self.fetcher.isRunning():
            print("INFO: Attempting to quit and wait for fetcher thread.")
            self.fetcher.quit()
            if not self.fetcher.wait(1000): print("WARN: Fetcher thread did not finish in time.")
        if self.downloader and self.downloader.isRunning():
            print("INFO: Downloader thread is running, attempting to disconnect signals.")
            try: self.downloader.finished.disconnect()
            except TypeError: pass
        if pygame.mixer.get_init():
            print("INFO: Stopping Pygame music and quitting mixer.")
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        super().closeEvent(event)

