import random
import os
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QSystemTrayIcon

import pygame # استيراد pygame

class ReminderService:
    def __init__(self, settings_manager, adhkar_manager, tray_icon, base_path, lm):
        print("DEBUG: ReminderService __init__ called.")
        self.settings_mngr = settings_manager
        self.adhkar_mngr = adhkar_manager
        self.tray_icon = tray_icon
        self.base_path = base_path
        self.lm = lm

        self.timer = QTimer()
        self.timer.timeout.connect(self.trigger_reminder)

        self.is_pygame_mixer_initialized = False
        print("DEBUG: Calling _initialize_pygame_mixer...")
        self._initialize_pygame_mixer()

        self.update_timer_interval() # يجب أن تحتوي هذه الدالة على منطق
        initial_reminders_active = self.settings_mngr.get("reminders_active", True)
        self.toggle_reminders(initial_reminders_active, is_initial_call=True) # وهذه أيضًا

    def _initialize_pygame_mixer(self):
        print("DEBUG: _initialize_pygame_mixer entered.")
        try:
            pygame.mixer.init() 
            self.is_pygame_mixer_initialized = True
            print("INFO: pygame.mixer initialized successfully.")
        except pygame.error as e:
            self.is_pygame_mixer_initialized = False
            print(f"ERROR: Failed to initialize pygame.mixer: {e}")
            if self.tray_icon and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    self.lm.get_string("audio_playback_error_title", "Audio Error"),
                    f"Pygame audio system failed to init: {e}", # رسالة أوضح
                    QSystemTrayIcon.MessageIcon.Warning, # أيقونة صحيحة
                    5000
                )
        except Exception as ex: # التقاط أي استثناءات أخرى محتملة
            self.is_pygame_mixer_initialized = False
            print(f"ERROR: Unexpected error during pygame.mixer.init: {ex}")


    def update_timer_interval(self):
        interval_minutes = self.settings_mngr.get("interval_minutes", 15)
        if not isinstance(interval_minutes, (int, float)) or interval_minutes <= 0:
            print(f"WARN: Invalid interval_minutes value: {interval_minutes}. Defaulting to 15.")
            interval_minutes = 15
        self.timer.setInterval(int(interval_minutes * 60 * 1000)) # تأكد من أنه int
        print(f"INFO: Reminder interval set to {interval_minutes} minutes.")

    def toggle_reminders(self, active, is_initial_call=False):
        print(f"DEBUG: toggle_reminders called with active={active}, is_initial_call={is_initial_call}")
        current_setting = self.settings_mngr.get("reminders_active")
        
        # قم بتحديث الإعداد فقط إذا تغيرت الحالة المطلوبة عن الحالة الحالية
        if current_setting != active: 
            self.settings_mngr.set("reminders_active", active)
            print(f"INFO: Reminders active setting changed to {active}")
        
        if active:
            if not self.timer.isActive():
                self.timer.start()
                print("INFO: Reminder timer started by toggle_reminders.")
                # لا تقم بتشغيل تذكير فوري عند أول استدعاء (بدء تشغيل التطبيق)
                # ولكن قم بتشغيله إذا تم استئناف التذكيرات يدويًا
                if not is_initial_call:
                    print("DEBUG: Triggering immediate reminder due to manual resume/toggle.")
                    self.trigger_reminder() 
            else:
                print("DEBUG: Reminder timer already active.")
        else: # active is False
            if self.timer.isActive():
                self.timer.stop()
                print("INFO: Reminder timer stopped by toggle_reminders.")
            else:
                print("DEBUG: Reminder timer already stopped.")

    def trigger_reminder(self):
        print("DEBUG: trigger_reminder entered.")
        if not self.settings_mngr.get("reminders_active", True):
            print("DEBUG: Reminders are globally paused by setting, skipping trigger.")
            return

        print("INFO: Triggering reminder...")
        reminder_type = self.settings_mngr.get("reminder_type", "text")
        
        actual_type = reminder_type
        if reminder_type == "random":
            possible_choices = ["text"]
            selected_audio_files = self.settings_mngr.get("selected_audio_files", [])
            
            if self.is_pygame_mixer_initialized and selected_audio_files and isinstance(selected_audio_files, list) and any(selected_audio_files):
                possible_choices.append("sound")
            else:
                if not self.is_pygame_mixer_initialized:
                    print("DEBUG: pygame.mixer not initialized, 'sound' not added to random choices.")
                if not selected_audio_files or not isinstance(selected_audio_files, list) or not any(selected_audio_files):
                    print("DEBUG: No audio files selected/valid, 'sound' not added to random choices.")
            
            if not possible_choices : # عمليًا يجب أن تحتوي دائمًا على "text"
                 actual_type = "text" # احتياطي
                 print("WARN: No valid choices for random reminder, defaulting to text.")
            elif len(possible_choices) == 1 and possible_choices[0] == "text":
                actual_type = "text" # إذا كان النص هو الخيار الوحيد الممكن
            else:
                actual_type = random.choice(possible_choices)
            
            print(f"DEBUG: Random reminder. Possible choices: {possible_choices}. Chosen: {actual_type}")

        if actual_type == "text":
            self.show_text_reminder()
        elif actual_type == "sound":
            print("DEBUG: Attempting to play sound reminder using pygame.mixer...")
            self.play_sound_reminder()
        else:
            print(f"WARN: Unknown actual_type selected for reminder: {actual_type}")

    def show_text_reminder(self):
        # (الكود كما هو، يعمل بشكل جيد)
        if not self.tray_icon or not self.tray_icon.isVisible():
            print("WARN: Tray icon not available to show text reminder.")
            return
        dhikr_text = self.adhkar_mngr.get_random_dhikr()
        if dhikr_text:
            print(f"DEBUG: Showing text reminder (ORIGINAL TEXT): {dhikr_text}")
            duration_ms = self.settings_mngr.get("notification_duration_seconds", 7) * 1000
            title_text = self.lm.get_string("app_name", "Zakir Test")
            try:
                self.tray_icon.showMessage(
                    title_text,
                    dhikr_text,
                    QSystemTrayIcon.MessageIcon.Information, 
                    duration_ms
                )
                print(f"DEBUG: showMessage called successfully (ORIGINAL TEXT - '{dhikr_text[:30]}...').")
            except Exception as e_show_msg:
                print(f"ERROR during tray_icon.showMessage with original text: {e_show_msg}")
                import traceback
                traceback.print_exc()
        else:
            print("WARN: No dhikr text available to show (ORIGINAL TEXT ATTEMPT).")

    def play_sound_reminder(self):
        print("DEBUG: play_sound_reminder entered.")
        if not self.is_pygame_mixer_initialized:
            print("ERROR: pygame.mixer not initialized, cannot play sound reminder.")
            if self.tray_icon and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    self.lm.get_string("audio_playback_error_title"),
                    "Audio system (pygame) not ready.",
                    QSystemTrayIcon.MessageIcon.Warning,
                    3000
                )
            return

        selected_audios = self.settings_mngr.get("selected_audio_files", [])
        if not selected_audios or not isinstance(selected_audios, list) or not any(selected_audios):
            print("WARN: No audio files selected or 'selected_audio_files' is empty/invalid for sound reminder.")
            if self.settings_mngr.get("reminder_type") == "sound" or self.settings_mngr.get("reminder_type") == "random":
                 if self.tray_icon and self.tray_icon.isVisible():
                    self.tray_icon.showMessage(
                        self.lm.get_string("audio_reminder_error_title"),
                        self.lm.get_string("no_audio_files_selected_message"),
                        QSystemTrayIcon.MessageIcon.Warning,
                        3000
                    )
            return

        audio_file_name = random.choice(selected_audios)
        audio_file_path = os.path.join(self.base_path, "resources", "audio", "reminders", audio_file_name)

        if not os.path.exists(audio_file_path):
            print(f"ERROR: Audio file not found: {audio_file_path}")
            if self.tray_icon and self.tray_icon.isVisible():
                 self.tray_icon.showMessage(
                    self.lm.get_string("audio_file_missing_title"),
                    self.lm.get_string("audio_file_missing_message", filename=audio_file_name), # تأكد أن لديك هذا المفتاح في الترجمة
                    QSystemTrayIcon.MessageIcon.Warning,
                    3000
                )
            return

        print(f"DEBUG: Preparing to play sound with pygame.mixer: {audio_file_path}")
        
        try:
            if not pygame.mixer.get_init(): # تحقق إضافي إذا تم إلغاء تهيئته لسبب ما
                print("WARN: pygame.mixer was not initialized. Attempting to re-init.")
                self._initialize_pygame_mixer()
                if not self.is_pygame_mixer_initialized:
                    print("ERROR: Failed to re-initialize pygame.mixer. Cannot play sound.")
                    return

            if pygame.mixer.music.get_busy():
                print("DEBUG: Pygame mixer was busy, stopping current music.")
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()

            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play() 
            print(f"DEBUG: pygame.mixer.music.play() called for {audio_file_name}")
        except pygame.error as e:
            print(f"ERROR: pygame.error while trying to play {audio_file_name}: {e}")
            if self.tray_icon and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    self.lm.get_string("audio_playback_error_title"),
                    f"Error playing {audio_file_name}: {e}",
                    QSystemTrayIcon.MessageIcon.Warning,
                    3000
                )
        except Exception as e_general:
            print(f"ERROR: Unexpected error during pygame sound playback: {e_general}")
            import traceback
            traceback.print_exc()


    def stop_service(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.is_pygame_mixer_initialized and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            self.is_pygame_mixer_initialized = False # تحديث الحالة
            print("INFO: pygame.mixer stopped and quit.")
        print("INFO: ReminderService stopped.")

# --- END OF FILE core/reminder_service.py ---