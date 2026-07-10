# ui/adhan_download_manager.py
import os
import re
import time
import urllib.parse
import requests # For web requests
from bs4 import BeautifulSoup # For parsing HTML
import pygame # For playing audio previews

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QProgressBar, QAbstractItemView, QMessageBox, QApplication, QLineEdit,
    QScrollArea # Added for potential future use if list gets very long
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# ADHAN_DIR should point to where Adhan files are stored and selected from in SettingsWindow
# This path assumes it's relative to the application's base_path
# ADHAN_DIR will be base_path + /resources/audio/adhan/
# We get base_path from the constructor.


ASSABILE_ADHAN_URL = "https://ar.assabile.com/adhan-call-prayer"

def sanitize_filename(name_str):
    # print(f"DEBUG: Sanitizing filename: '{name_str}'")
    original_name = name_str
    # Replace common problematic patterns first
    name_str = name_str.replace(" - ", "_").replace(" ,", "_").replace(",", "_")
    # Remove or replace characters invalid in filenames
    name_str = re.sub(r'[\\/*?:"<>|]', "", name_str) # Keep Arabic characters
    name_str = name_str.replace(" ", "_") # Replace spaces with underscores
    # Remove multiple underscores
    name_str = re.sub(r'_+', '_', name_str)
    name_str = name_str.strip("._ ") # Remove leading/trailing problematic chars

    if not name_str: # If name becomes empty
        name_str = f"untitled_adhan_{int(time.time())}" # Add timestamp for uniqueness
        print(f"WARN: Original filename '{original_name}' resulted in empty, using '{name_str}'")
    
    if not name_str.lower().endswith(".mp3"):
        name_str += ".mp3"
    # print(f"DEBUG: Sanitized filename: '{name_str}'")
    return name_str

class LocalAdhanItemWidget(QWidget):
    play_clicked = pyqtSignal(str)       # emits filepath
    stop_clicked = pyqtSignal(str)       # emits filepath
    delete_clicked = pyqtSignal(str)     # emits filepath

    def __init__(self, filename_path, lm, is_playing=False, parent=None):
        super().__init__(parent)
        self.filepath = filename_path
        self.lm = lm
        self.is_playing = is_playing

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3) # Adjusted margins

        self.label = QLabel(os.path.basename(filename_path))
        self.label.setStyleSheet("color: #e0e0e0; font-size: 9pt;") # Adjusted font size

        self.play_button = QPushButton(self.lm.get_string("stop_playback", "Stop") if is_playing else self.lm.get_string("play_playback", "Play"))
        self.play_button.setStyleSheet("QPushButton { background-color: #4299e1; border: none; color: white; padding: 4px 8px; border-radius: 3px; font-size: 8pt; } QPushButton:hover { background-color: #3182ce; }")
        self.play_button.setFixedHeight(24)


        self.delete_button = QPushButton(self.lm.get_string("delete", "Delete"))
        self.delete_button.setStyleSheet("QPushButton { background-color: #e53e3e; border: none; color: white; padding: 4px 8px; border-radius: 3px; font-size: 8pt; } QPushButton:hover { background-color: #c53030; }")
        self.delete_button.setFixedHeight(24)

        layout.addWidget(self.label, 1) # Add stretch factor
        # layout.addStretch(1)
        layout.addWidget(self.play_button)
        layout.addWidget(self.delete_button)

        self.play_button.clicked.connect(self.toggle_play_stop)
        self.delete_button.clicked.connect(lambda: self.delete_clicked.emit(self.filepath))

    def toggle_play_stop(self):
        if self.is_playing:
            self.stop_clicked.emit(self.filepath)
        else:
            self.play_clicked.emit(self.filepath)

    def set_playing_state(self, is_playing_now):
        self.is_playing = is_playing_now
        self.play_button.setText(self.lm.get_string("stop_playback", "Stop") if is_playing_now else self.lm.get_string("play_playback", "Play"))

class AdhanListFetcher(QThread):
    fetched_list = pyqtSignal(list, str) # list of dicts, error message string
    progress_message = pyqtSignal(str)   # for status updates

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        print(f"INFO: AdhanListFetcher - Thread started for URL: {self.url}")
        adhan_results = []
        error_str = ""
        headers = { # More comprehensive headers
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Referer': 'https://www.google.com/', # Generic referer
            'DNT': '1', # Do Not Track
            'Upgrade-Insecure-Requests': '1'
        }

        try:
            self.progress_message.emit(f"Fetching Adhan list from Assabile...") # Localized later
            
            # Using verify=False is a security risk. Only use if you trust the source
            # and cannot resolve SSL certificate issues otherwise.
            response = requests.get(self.url, headers=headers, timeout=45, verify=False) # Increased timeout
            
            print(f"INFO: AdhanListFetcher - Assabile main page status: {response.status_code}")
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                error_str = f"Unexpected content type from Assabile: {content_type}"
                print(f"ERROR: AdhanListFetcher - {error_str}")
                self.fetched_list.emit([], error_str)
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            # Targeting <li class="adane"> which contains the <a class="link-media">
            adhan_li_elements = soup.find_all("li", class_="adane")
            
            if not adhan_li_elements:
                error_str = "No Adhan list items found on Assabile page. Structure might have changed."
                print(f"ERROR: AdhanListFetcher - {error_str}")
                self.fetched_list.emit([], error_str)
                return

            self.progress_message.emit(f"Found {len(adhan_li_elements)} potential Adhans. Processing...")

            for idx, li_tag in enumerate(adhan_li_elements):
                link_tag = li_tag.find("a", class_="link-media")
                if link_tag and link_tag.has_attr('href'):
                    mp3_url_path = link_tag['href']
                    # Ensure URL is absolute
                    if mp3_url_path.startswith('/'):
                        mp3_url = urllib.parse.urljoin("https://ar.assabile.com", mp3_url_path)
                    elif not mp3_url_path.startswith(('http://', 'https://')):
                        # This case might not be needed if Assabile always uses absolute or root-relative paths
                        mp3_url = "https://ar.assabile.com/" + mp3_url_path 
                    else:
                        mp3_url = mp3_url_path
                    
                    # Get the name, usually from a span inside the link
                    name_span = link_tag.find("span", class_="sorting") # Or other relevant class/tag
                    adhan_title = name_span.text.strip() if name_span else f"Adhan {idx+1}"
                    adhan_title = re.sub(r'\s+', ' ', adhan_title).strip() # Clean up whitespace

                    if mp3_url and adhan_title:
                        adhan_results.append({'name': adhan_title, 'url': mp3_url})
                        # self.progress_message.emit(f"Processed: {adhan_title[:40]}...")
                # time.sleep(0.05) # Small delay to be polite to server

            if not adhan_results:
                error_str = "No valid Adhan MP3 links found after parsing."
            
            self.fetched_list.emit(adhan_results, error_str)

        except requests.exceptions.Timeout:
            error_str = "Connection to Assabile timed out."
            print(f"ERROR: AdhanListFetcher - {error_str}")
        except requests.exceptions.RequestException as e_req:
            error_str = f"Network error fetching Assabile list: {e_req}"
            print(f"ERROR: AdhanListFetcher - {error_str}")
        except Exception as e_main:
            error_str = f"Unexpected error fetching Adhan list: {e_main}"
            print(f"ERROR: AdhanListFetcher - {error_str}")
            import traceback
            traceback.print_exc()
        finally:
            if error_str and not adhan_results: # Ensure error is emitted if list is empty due to error
                 self.fetched_list.emit([], error_str)
            self.progress_message.emit("") # Clear progress message
            print("INFO: AdhanListFetcher - Thread finished.")


class AdhanDownloader(QThread):
    download_progress = pyqtSignal(int) # Percentage
    download_finished = pyqtSignal(str, str) # filename, error_message (empty if success)

    def __init__(self, url, save_filename, adhan_dir_path, parent=None):
        super().__init__(parent)
        self.url = url
        self.save_filename = save_filename # Just the filename, not full path
        self.adhan_dir_path = adhan_dir_path # Full path to Adhan directory
        print(f"INFO: AdhanDownloader initialized for URL: '{self.url}', Filename: '{self.save_filename}'")

    def run(self):
        print(f"INFO: AdhanDownloader - Thread started for '{self.save_filename}'.")
        full_save_path = os.path.join(self.adhan_dir_path, self.save_filename)
        error_msg = ""
        headers = { # Headers for download request
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
            'Referer': ASSABILE_ADHAN_URL # Referer can be important
        }
        
        try:
            print(f"INFO: AdhanDownloader - Attempting to download from: {self.url} to {full_save_path}")
            # Stream download
            response = requests.get(self.url, stream=True, headers=headers, timeout=120, verify=False) # Long timeout for download
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            print(f"INFO: AdhanDownloader - Total download size: {total_size} bytes for '{self.save_filename}'")
            
            os.makedirs(self.adhan_dir_path, exist_ok=True) # Ensure directory exists
            
            downloaded_size = 0
            with open(full_save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): # 8KB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.download_progress.emit(progress)
                        else:
                            self.download_progress.emit(-1) # Indeterminate progress
            
            if total_size == 0 and downloaded_size > 0: # Content-Length was 0 but we got data
                self.download_progress.emit(100) # Assume complete
            elif downloaded_size < total_size:
                print(f"WARN: AdhanDownloader - Download for '{self.save_filename}' might be incomplete. Downloaded: {downloaded_size}, Total: {total_size}")
                # Potentially set error_msg here if incomplete is critical
            
            print(f"INFO: AdhanDownloader - Finished writing {downloaded_size} bytes to '{full_save_path}'")

        except requests.exceptions.Timeout:
            error_msg = f"Download timeout for '{self.save_filename}'."
            print(f"ERROR: AdhanDownloader - {error_msg}")
        except requests.exceptions.RequestException as e_req:
            error_msg = f"Network error downloading '{self.save_filename}': {e_req}"
            print(f"ERROR: AdhanDownloader - {error_msg}")
        except IOError as e_io:
            error_msg = f"File write error for '{full_save_path}': {e_io}"
            print(f"ERROR: AdhanDownloader - {error_msg}")
        except Exception as e:
            error_msg = f"Unexpected error downloading '{self.save_filename}': {type(e).__name__} - {str(e)}"
            print(f"ERROR: AdhanDownloader - {error_msg}")
            import traceback
            traceback.print_exc()
        finally:
            self.download_finished.emit(self.save_filename, error_msg)
            print(f"INFO: AdhanDownloader - Thread finished for '{self.save_filename}'. Error: '{error_msg if error_msg else 'None'}'")


class AdhanDownloadWidget(QWidget):
    # Signal to notify settings window that local adhans might have changed
    local_adhans_changed = pyqtSignal() 

    def __init__(self, settings_manager, lm, base_path, parent_settings_window=None):
        super().__init__(parent_settings_window) # Pass parent if available
        print("INFO: AdhanDownloadWidget initializing...")
        self.settings_mngr = settings_manager
        self.lm = lm
        self.base_path = base_path
        self.parent_settings_window = parent_settings_window # Store reference if needed

        self.ADHAN_STORAGE_DIR = os.path.join(self.base_path, "resources", "audio", "adhan")
        print(f"INFO: AdhanDownloadWidget - Adhan storage directory: {self.ADHAN_STORAGE_DIR}")

        self.currently_playing_filepath = None
        self.currently_playing_widget_ref = None # Reference to the LocalAdhanItemWidget playing

        self.fetch_thread = None
        self.download_thread = None
        self._all_fetched_adhans_data = [] # To store full list for filtering

        try:
            pygame.mixer.init()
            print("INFO: AdhanDownloadWidget - Pygame mixer initialized successfully.")
            self._is_pygame_mixer_init = True
        except pygame.error as pg_err:
            self._is_pygame_mixer_init = False
            print(f"CRITICAL: AdhanDownloadWidget - Failed to initialize Pygame Mixer: {pg_err}")
            QMessageBox.critical(self, 
                                 self.lm.get_string("audio_playback_error_title"), 
                                 self.lm.get_string("audio_playback_init_error_message", error_detail=str(pg_err)))
        
        self.init_ui()
        self.load_local_adhans_list()
        self.trigger_fetch_online_adhans() # Initial fetch
        print("INFO: AdhanDownloadWidget initialization complete.")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5,5,5,5) # Reduced margins

        # --- Online Adhans Section ---
        online_group_label = QLabel(self.lm.get_string("online_adhans_label", "Adhans Available for Download (from Assabile.com):"))
        main_layout.addWidget(online_group_label)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.lm.get_string("search_adhan_placeholder", "Search Adhan name..."))
        self.search_input.textChanged.connect(self.filter_displayed_online_adhans)
        search_layout.addWidget(self.search_input)
        # Optional: Add a clear search button
        main_layout.addLayout(search_layout)

        self.online_adhans_listwidget = QListWidget()
        self.online_adhans_listwidget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.online_adhans_listwidget.itemSelectionChanged.connect(self._update_download_button_state)
        self.online_adhans_listwidget.setMinimumHeight(150) # Ensure it's visible
        main_layout.addWidget(self.online_adhans_listwidget)

        online_buttons_layout = QHBoxLayout()
        self.refresh_list_button = QPushButton(f"🔄 {self.lm.get_string('refresh_list_button', 'Refresh List')}")
        self.refresh_list_button.clicked.connect(self.trigger_fetch_online_adhans)
        self.download_selected_button = QPushButton(f"⬇️ {self.lm.get_string('download_selected_button', 'Download Selected')}")
        self.download_selected_button.clicked.connect(self.trigger_download_selected_adhan)
        self.download_selected_button.setEnabled(False) # Disabled initially
        online_buttons_layout.addWidget(self.refresh_list_button)
        online_buttons_layout.addWidget(self.download_selected_button)
        main_layout.addLayout(online_buttons_layout)

        self.fetch_status_label = QLabel(self.lm.get_string("status_idle", "Status: Idle"))
        self.fetch_status_label.setStyleSheet("color: #a0aec0; font-style: italic; font-size: 8pt;")
        main_layout.addWidget(self.fetch_status_label)

        self.download_progressbar = QProgressBar()
        self.download_progressbar.setValue(0)
        self.download_progressbar.setFixedHeight(18) # Slightly smaller
        self.download_progressbar.setTextVisible(True) # Show percentage
        self.download_progressbar.setFormat("%p%")
        main_layout.addWidget(self.download_progressbar)

        # --- Local Adhans Section ---
        local_group_label = QLabel(self.lm.get_string("local_adhans_label", "Locally Downloaded Adhans:"))
        main_layout.addWidget(local_group_label)
        
        self.local_adhans_listwidget = QListWidget()
        self.local_adhans_listwidget.setMinimumHeight(120)
        # Using QScrollArea for local adhans if many exist and custom widgets are complex
        # scroll_area_local = QScrollArea()
        # scroll_area_local.setWidgetResizable(True)
        # scroll_area_local.setWidget(self.local_adhans_listwidget)
        # main_layout.addWidget(scroll_area_local)
        main_layout.addWidget(self.local_adhans_listwidget)


    def trigger_fetch_online_adhans(self):
        print("INFO: AdhanDownloadWidget - trigger_fetch_online_adhans called.")
        if self.fetch_thread and self.fetch_thread.isRunning():
            print("WARN: AdhanDownloadWidget - Fetcher thread is already running.")
            # QMessageBox.information(self, self.lm.get_string("fetch_in_progress_title", "Fetch in Progress"), 
            #                         self.lm.get_string("fetch_in_progress_message", "Adhan list fetching is already in progress."))
            self.fetch_status_label.setText(self.lm.get_string("status_fetch_busy", "Status: Fetching already in progress..."))
            return
        
        self.download_progressbar.setValue(0)
        self.download_progressbar.setFormat("%p%")
        self.online_adhans_listwidget.clear()
        self._all_fetched_adhans_data = [] # Clear previous full list
        self.online_adhans_listwidget.addItem(QListWidgetItem(self.lm.get_string("fetching_adhan_list_placeholder", "⏳ Fetching Adhan list, please wait...")))
        self.refresh_list_button.setEnabled(False)
        self.download_selected_button.setEnabled(False)
        self.fetch_status_label.setText(self.lm.get_string("status_fetching", "Status: Fetching list..."))
        
        self.fetch_thread = AdhanListFetcher(ASSABILE_ADHAN_URL)
        self.fetch_thread.fetched_list.connect(self.handle_fetched_adhans_list)
        self.fetch_thread.progress_message.connect(lambda msg: self.fetch_status_label.setText(f"{self.lm.get_string('status_prefix', 'Status: ')}{msg}"))
        self.fetch_thread.finished.connect(lambda: (self.refresh_list_button.setEnabled(True), print("INFO: AdhanDownloadWidget - Fetcher thread finished.")))
        self.fetch_thread.start()

    def handle_fetched_adhans_list(self, adhan_data_list, error_msg):
        print(f"INFO: AdhanDownloadWidget - handle_fetched_adhans_list. Received {len(adhan_data_list)} adhans. Error: '{error_msg}'")
        self.online_adhans_listwidget.clear() # Clear placeholder or old items
        self.refresh_list_button.setEnabled(True) # Re-enable refresh button

        if error_msg:
            QMessageBox.warning(self, self.lm.get_string("fetch_list_error_title", "Error Fetching List"), 
                                f"{self.lm.get_string('fetch_list_error_message', 'Failed to fetch Adhan list')}: {error_msg}")
            self.online_adhans_listwidget.addItem(QListWidgetItem(f"{self.lm.get_string('error_prefix', 'Error')}: {error_msg}"))
            self.fetch_status_label.setText(self.lm.get_string("status_fetch_failed", "Status: Fetch failed."))
            return

        if not adhan_data_list:
            self.online_adhans_listwidget.addItem(QListWidgetItem(self.lm.get_string("no_adhans_found_online", "No Adhans found available for download.")))
            self.fetch_status_label.setText(self.lm.get_string("status_fetch_empty", "Status: Fetched list is empty."))
            return

        self._all_fetched_adhans_data = adhan_data_list # Store the full list
        self.filter_displayed_online_adhans(self.search_input.text()) # Display, possibly filtered
        
        self.fetch_status_label.setText(self.lm.get_string("status_fetch_success", "Status: List fetched ({count} items).").format(count=len(adhan_data_list)))

    def filter_displayed_online_adhans(self, filter_text=""):
        self.online_adhans_listwidget.clear()
        filter_text_lower = filter_text.lower().strip()
        
        displayed_count = 0
        for adhan_item_data in self._all_fetched_adhans_data:
            if filter_text_lower in adhan_item_data['name'].lower():
                list_widget_item = QListWidgetItem(f"{adhan_item_data['name']}")
                list_widget_item.setData(Qt.ItemDataRole.UserRole, adhan_item_data) # Store full data dict
                self.online_adhans_listwidget.addItem(list_widget_item)
                displayed_count += 1
        
        if displayed_count == 0:
            if self._all_fetched_adhans_data: # If there was data, but filter found none
                self.online_adhans_listwidget.addItem(QListWidgetItem(self.lm.get_string("no_search_results", "No results match your search.")))
            # If _all_fetched_adhans_data is empty, the message from handle_fetched_adhans_list remains.
        self._update_download_button_state()


    def _update_download_button_state(self):
        # Enable download button only if an item is selected and no download is in progress
        can_download = bool(self.online_adhans_listwidget.selectedItems())
        is_downloader_active = self.download_thread and self.download_thread.isRunning()
        self.download_selected_button.setEnabled(can_download and not is_downloader_active)


    def load_local_adhans_list(self):
        print("INFO: AdhanDownloadWidget - load_local_adhans_list called.")
        self.local_adhans_listwidget.clear()
        
        if not os.path.exists(self.ADHAN_STORAGE_DIR):
            print(f"INFO: AdhanDownloadWidget - Adhan storage directory '{self.ADHAN_STORAGE_DIR}' does not exist. Attempting to create.")
            try:
                os.makedirs(self.ADHAN_STORAGE_DIR, exist_ok=True)
            except OSError as e:
                print(f"CRITICAL: AdhanDownloadWidget - Failed to create adhan directory: {self.ADHAN_STORAGE_DIR}\n{e}")
                QMessageBox.critical(self, self.lm.get_string("error"), 
                                     self.lm.get_string("error_create_adhan_dir", "Failed to create Adhan directory: {path}\n{error_detail}").format(path=self.ADHAN_STORAGE_DIR, error_detail=str(e)))
                return # Cannot proceed if directory cannot be made

        adhans_found_count = 0
        try:
            for filename in os.listdir(self.ADHAN_STORAGE_DIR):
                if filename.lower().endswith('.mp3'):
                    full_path = os.path.join(self.ADHAN_STORAGE_DIR, filename)
                    
                    list_item = QListWidgetItem(self.local_adhans_listwidget) # Parent it to the list
                    item_widget = LocalAdhanItemWidget(full_path, self.lm) # Pass lm
                    item_widget.play_clicked.connect(self.play_selected_local_adhan)
                    item_widget.stop_clicked.connect(self.stop_current_local_adhan_playback)
                    item_widget.delete_clicked.connect(self.delete_selected_local_adhan)
                    
                    list_item.setSizeHint(item_widget.sizeHint())
                    # self.local_adhans_listwidget.addItem(list_item) # Already parented
                    self.local_adhans_listwidget.setItemWidget(list_item, item_widget)
                    adhans_found_count += 1
        except Exception as e_list_dir:
            print(f"ERROR: AdhanDownloadWidget - Error listing local adhan directory: {e_list_dir}")
            QMessageBox.warning(self, self.lm.get_string("error"), self.lm.get_string("error_listing_adhan_dir", "Error listing local Adhans."))


        if adhans_found_count == 0:
            print("INFO: AdhanDownloadWidget - No local adhans found.")
            placeholder = QListWidgetItem(self.lm.get_string("no_local_adhans_placeholder", "No Adhans currently downloaded."))
            placeholder.setFlags(placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable) # Not selectable
            self.local_adhans_listwidget.addItem(placeholder)
        
        self.local_adhans_changed.emit() # Notify parent (SettingsWindow)

    def play_selected_local_adhan(self, filepath_to_play):
        print(f"INFO: AdhanDownloadWidget - play_selected_local_adhan: {filepath_to_play}")
        if not self._is_pygame_mixer_init or not pygame.mixer.get_init():
            print("ERROR: AdhanDownloadWidget - Pygame mixer not initialized, cannot play.")
            QMessageBox.warning(self, self.lm.get_string("audio_playback_error_title"), 
                                self.lm.get_string("audio_playback_not_ready_message"))
            return

        # Stop currently playing adhan if it's different
        if self.currently_playing_filepath and self.currently_playing_filepath != filepath_to_play:
            self.stop_current_local_adhan_playback(self.currently_playing_filepath)
        
        try:
            pygame.mixer.music.load(filepath_to_play)
            pygame.mixer.music.play()
            self.currently_playing_filepath = filepath_to_play
            
            # Update UI for the playing item
            for i in range(self.local_adhans_listwidget.count()):
                list_item = self.local_adhans_listwidget.item(i)
                widget = self.local_adhans_listwidget.itemWidget(list_item)
                if isinstance(widget, LocalAdhanItemWidget):
                    is_this_one_playing = (widget.filepath == filepath_to_play)
                    widget.set_playing_state(is_this_one_playing)
                    if is_this_one_playing:
                        self.currently_playing_widget_ref = widget
        except pygame.error as e_play:
            print(f"ERROR: AdhanDownloadWidget - Pygame error playing '{os.path.basename(filepath_to_play)}': {str(e_play)}")
            QMessageBox.warning(self, self.lm.get_string("audio_playback_error_title"), 
                                self.lm.get_string("audio_file_playback_error", "Failed to play Adhan '{filename}':\n{error_detail}").format(filename=os.path.basename(filepath_to_play), error_detail=str(e_play)))
            self.currently_playing_filepath = None
            self.currently_playing_widget_ref = None


    def stop_current_local_adhan_playback(self, filepath_being_stopped=None):
        # filepath_being_stopped is passed by the widget that was clicked
        if not self._is_pygame_mixer_init or not pygame.mixer.get_init(): return

        print(f"INFO: AdhanDownloadWidget - stop_current_local_adhan_playback. Current: {self.currently_playing_filepath}, Requested stop for: {filepath_being_stopped}")
        
        # Stop only if the requested file to stop is actually playing, or if no specific file is given (general stop)
        if filepath_being_stopped is None or self.currently_playing_filepath == filepath_being_stopped:
            pygame.mixer.music.stop()
            
            if self.currently_playing_widget_ref and \
               (filepath_being_stopped is None or self.currently_playing_widget_ref.filepath == filepath_being_stopped) :
                self.currently_playing_widget_ref.set_playing_state(False)
            
            self.currently_playing_filepath = None
            self.currently_playing_widget_ref = None


    def delete_selected_local_adhan(self, filepath_to_delete):
        filename_short = os.path.basename(filepath_to_delete)
        print(f"INFO: AdhanDownloadWidget - delete_selected_local_adhan: {filename_short}")
        
        reply = QMessageBox.question(self, 
                                     self.lm.get_string("confirm_delete_title", "Confirm Deletion"), 
                                     self.lm.get_string("confirm_delete_message", "Are you sure you want to delete: {filename}?").format(filename=filename_short),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            print(f"INFO: AdhanDownloadWidget - User confirmed deletion for {filename_short}")
            try:
                if self.currently_playing_filepath == filepath_to_delete:
                    self.stop_current_local_adhan_playback(filepath_to_delete)
                
                os.remove(filepath_to_delete)
                print(f"INFO: AdhanDownloadWidget - File {filepath_to_delete} removed successfully.")
                # QMessageBox.information(self, self.lm.get_string("delete_success_title", "Deletion Successful"), 
                #                         self.lm.get_string("delete_success_message", "File {filename} deleted successfully.").format(filename=filename_short))
                self.load_local_adhans_list() # Refresh the list of local adhans
                # self.local_adhans_changed.emit() # Emitted by load_local_adhans_list
            except OSError as e_os_del:
                print(f"ERROR: AdhanDownloadWidget - Failed to delete file {filepath_to_delete}: {str(e_os_del)}")
                QMessageBox.warning(self, self.lm.get_string("delete_error_title", "Deletion Error"), 
                                    self.lm.get_string("delete_error_message", "Failed to delete file {filename}: {error_detail}").format(filename=filename_short, error_detail=str(e_os_del)))

    def trigger_download_selected_adhan(self):
        print("INFO: AdhanDownloadWidget - trigger_download_selected_adhan called.")
        selected_qlist_items = self.online_adhans_listwidget.selectedItems()
        if not selected_qlist_items:
            print("WARN: AdhanDownloadWidget - Download triggered with no item selected.")
            # This should not happen if button state is managed correctly
            return

        if self.download_thread and self.download_thread.isRunning():
            print("WARN: AdhanDownloadWidget - Downloader thread is already running.")
            QMessageBox.information(self, self.lm.get_string("download_in_progress_title", "Download in Progress"), 
                                    self.lm.get_string("download_in_progress_message", "Another download is already in progress."))
            return

        selected_adhan_data = selected_qlist_items[0].data(Qt.ItemDataRole.UserRole) # Get stored dict
        url = selected_adhan_data['url']
        original_name = selected_adhan_data['name']
        
        print(f"INFO: AdhanDownloadWidget - Preparing to download: Name='{original_name}', URL='{url}'")
        
        safe_filename_to_save = sanitize_filename(original_name)
        full_path_to_save = os.path.join(self.ADHAN_STORAGE_DIR, safe_filename_to_save)

        if os.path.exists(full_path_to_save):
            print(f"WARN: AdhanDownloadWidget - File '{safe_filename_to_save}' already exists.")
            reply = QMessageBox.question(self, self.lm.get_string("file_exists_title", "File Exists"), 
                                         self.lm.get_string("file_exists_overwrite_message", "File '{filename}' already exists. Overwrite?").format(filename=safe_filename_to_save),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                print("INFO: AdhanDownloadWidget - User chose not to overwrite.")
                self.download_progressbar.setValue(0)
                self.download_progressbar.setFormat("%p%")
                return
        
        self.download_progressbar.setValue(0)
        self.download_progressbar.setFormat(self.lm.get_string("download_starting_format", "Starting..."))
        self.download_selected_button.setEnabled(False) # Disable while downloading
        self.refresh_list_button.setEnabled(False)    # Also disable refresh

        self.download_thread = AdhanDownloader(url, safe_filename_to_save, self.ADHAN_STORAGE_DIR)
        self.download_thread.download_progress.connect(self.update_gui_download_progress)
        self.download_thread.download_finished.connect(self.handle_download_completion)
        # Re-enable buttons after thread finishes, regardless of outcome
        self.download_thread.finished.connect(lambda: (self._update_download_button_state(), self.refresh_list_button.setEnabled(True), print("INFO: AdhanDownloadWidget - Downloader thread finished, buttons state updated.")))
        self.download_thread.start()

    def update_gui_download_progress(self, percentage):
        if percentage == -1: # Indeterminate
            self.download_progressbar.setRange(0,0) # Makes it show busy indicator
            self.download_progressbar.setFormat(self.lm.get_string("downloading_format_busy", "Downloading..."))
        else:
            self.download_progressbar.setRange(0,100)
            self.download_progressbar.setValue(percentage)
            self.download_progressbar.setFormat(f"{percentage}%")

    def handle_download_completion(self, downloaded_filename, error_msg_str):
        print(f"INFO: AdhanDownloadWidget - handle_download_completion for '{downloaded_filename}'. Error: '{error_msg_str}'")
        self.download_progressbar.setRange(0,100) # Ensure range is normal for final value
        
        if error_msg_str:
            self.download_progressbar.setValue(0) # Reset progress on error
            self.download_progressbar.setFormat(self.lm.get_string("download_failed_format", "Failed"))
            QMessageBox.warning(self, self.lm.get_string("download_error_title", "Download Error"), 
                                self.lm.get_string("download_error_message", "Failed to download Adhan '{filename}': {error_detail}").format(filename=downloaded_filename, error_detail=error_msg_str))
        else:
            self.download_progressbar.setValue(100)
            self.download_progressbar.setFormat(self.lm.get_string("download_complete_format", "Complete!"))
            # QMessageBox.information(self, self.lm.get_string("download_success_title", "Download Successful"), 
            #                         self.lm.get_string("download_success_message", "Adhan '{filename}' downloaded successfully.").format(filename=downloaded_filename))
            self.load_local_adhans_list() # Refresh local list
            # self.local_adhans_changed.emit() # Emitted by load_local_adhans_list
        
        # Buttons state is handled by download_thread.finished connection

    def closeEvent(self, event):
        print("INFO: AdhanDownloadWidget - closeEvent called.")
        # Stop threads if they are running
        if self.fetch_thread and self.fetch_thread.isRunning():
            print("INFO: AdhanDownloadWidget - Terminating fetcher thread.")
            self.fetch_thread.quit() # Request quit
            if not self.fetch_thread.wait(1500): # Wait a bit
                print("WARN: AdhanDownloadWidget - Fetcher thread did not finish in time, terminating.")
                self.fetch_thread.terminate() # Force terminate if necessary

        if self.download_thread and self.download_thread.isRunning():
            print("INFO: AdhanDownloadWidget - Terminating downloader thread.")
            # For downloads, it's often better to let them finish or cancel gracefully if possible.
            # Terminating might leave partial files. For simplicity here, we'll quit/terminate.
            self.download_thread.quit()
            if not self.download_thread.wait(1500):
                print("WARN: AdhanDownloadWidget - Downloader thread did not finish in time, terminating.")
                self.download_thread.terminate()
        
        # Stop any local adhan playback
        self.stop_current_local_adhan_playback()

        # Quit pygame.mixer if it was initialized by this widget
        if self._is_pygame_mixer_init and pygame.mixer.get_init():
            print("INFO: AdhanDownloadWidget - Quitting Pygame mixer.")
            pygame.mixer.quit()
            self._is_pygame_mixer_init = False # Mark as quit
        
        super().closeEvent(event)