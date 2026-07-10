# core/reminder_service.py
import random
import os
import pygame # For audio playback
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QSystemTrayIcon # For showing messages

class ReminderService:
    def __init__(self, settings_manager, adhkar_manager, tray_icon, base_path, lm):
        print("DEBUG: ReminderService __init__ called.")
        self.settings_mngr = settings_manager
        self.adhkar_mngr = adhkar_manager # This should be an instance of AdhkarManager
        self.tray_icon = tray_icon # This is the QSystemTrayIcon instance itself
        self.base_path = base_path
        self.lm = lm # LocalizationManager instance

        self.timer = QTimer()
        self.timer.timeout.connect(self.trigger_reminder)

        self.is_pygame_mixer_initialized = False
        self._initialize_pygame_mixer() # Initialize Pygame mixer

        self.update_timer_interval() # Set initial timer interval based on settings
        
        # Start or stop the timer based on the initial "reminders_active" setting
        initial_reminders_active = self.settings_mngr.get("reminders_active", True)
        self.toggle_reminders(active=initial_reminders_active, is_initial_call=True)
        print(f"DEBUG: ReminderService initialized. Reminders active: {initial_reminders_active}")

    def _initialize_pygame_mixer(self):
        print("DEBUG: ReminderService - _initialize_pygame_mixer entered.")
        try:
            pygame.mixer.init()
            self.is_pygame_mixer_initialized = True
            print("INFO: ReminderService - pygame.mixer initialized successfully.")
        except pygame.error as e:
            self.is_pygame_mixer_initialized = False
            error_title_default = "Audio Error"
            error_msg_key = "audio_playback_init_error_message" # For specific init error
            error_msg_default_template = "Pygame audio system failed to initialize: {error_detail}"
            
            error_title = self.lm.get_string("audio_playback_error_title", error_title_default)
            error_message = self.lm.get_string(error_msg_key, error_msg_default_template).format(error_detail=str(e))
            
            print(f"ERROR: ReminderService - Failed to initialize pygame.mixer: {e}")
            if self.tray_icon and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    error_title,
                    error_message,
                    QSystemTrayIcon.MessageIcon.Warning,
                    5000 # milliseconds
                )
        except Exception as ex:
            self.is_pygame_mixer_initialized = False
            print(f"ERROR: ReminderService - Unexpected error during pygame.mixer.init: {ex}")
            # Potentially show a generic error message here too if desired

    def update_timer_interval(self):
        interval_minutes_val = self.settings_mngr.get("interval_minutes", 15)
        try:
            interval_minutes = int(interval_minutes_val)
            if interval_minutes <= 0:
                print(f"WARN: ReminderService - Invalid interval_minutes value: {interval_minutes_val}. Defaulting to 15.")
                interval_minutes = 15
        except (ValueError, TypeError):
            print(f"WARN: ReminderService - interval_minutes value '{interval_minutes_val}' is not a valid number. Defaulting to 15.")
            interval_minutes = 15
            
        self.timer.setInterval(interval_minutes * 60 * 1000)
        print(f"INFO: ReminderService - Reminder interval set to {interval_minutes} minutes.")

    def toggle_reminders(self, active, is_initial_call=False):
        print(f"DEBUG: ReminderService - toggle_reminders called with active={active}, is_initial_call={is_initial_call}")
        
        # Update the setting if it's different from the requested state
        # This handles calls from UI where user changes the "reminders_active" checkbox
        current_setting = self.settings_mngr.get("reminders_active")
        if current_setting != active:
            self.settings_mngr.set("reminders_active", active)
            print(f"INFO: ReminderService - Reminders active setting persisted: {active}")

        if active:
            if not self.timer.isActive():
                self.timer.start()
                print("INFO: ReminderService - Reminder timer started.")
                # Trigger an immediate reminder if manually resumed, but not on initial app start
                if not is_initial_call:
                    print("DEBUG: ReminderService - Triggering immediate reminder due to manual resume.")
                    self.trigger_reminder() 
            else:
                print("DEBUG: ReminderService - Reminder timer already active.")
        else: # active is False
            if self.timer.isActive():
                self.timer.stop()
                print("INFO: ReminderService - Reminder timer stopped.")
            else:
                print("DEBUG: ReminderService - Reminder timer already stopped.")

    def trigger_reminder(self):
        print("DEBUG: ReminderService - trigger_reminder entered.")
        if not self.settings_mngr.get("reminders_active", True): # Double check the persisted setting
            print("DEBUG: ReminderService - Reminders are globally paused by setting, skipping trigger.")
            return

        print("INFO: ReminderService - Triggering reminder...")
        reminder_type_setting = self.settings_mngr.get("reminder_type", "text")
        
        actual_type_to_show = reminder_type_setting
        if reminder_type_setting == "random":
            possible_choices = ["text"] # Text is always a possibility
            
            selected_audio_files = self.settings_mngr.get("selected_audio_files", [])
            # Ensure selected_audio_files is a list and has content
            is_audio_possible = (
                self.is_pygame_mixer_initialized and
                isinstance(selected_audio_files, list) and
                any(selected_audio_files) # Checks if list is not empty
            )

            if is_audio_possible:
                possible_choices.append("sound")
            else:
                if not self.is_pygame_mixer_initialized:
                    print("DEBUG: ReminderService - Pygame mixer not initialized, 'sound' reminder not possible for random.")
                if not isinstance(selected_audio_files, list) or not any(selected_audio_files):
                    print("DEBUG: ReminderService - No audio files selected or list is invalid, 'sound' reminder not possible for random.")
            
            if not possible_choices: # Should not happen as "text" is always there
                 actual_type_to_show = "text" 
                 print("WARN: ReminderService - No valid choices for random reminder (this is unexpected). Defaulting to text.")
            else:
                actual_type_to_show = random.choice(possible_choices)
            
            print(f"DEBUG: ReminderService - Random reminder chosen. Possible: {possible_choices}. Selected: {actual_type_to_show}")

        if actual_type_to_show == "text":
            self.show_text_reminder()
        elif actual_type_to_show == "sound":
            print("DEBUG: ReminderService - Attempting to play sound reminder via pygame.mixer.")
            self.play_sound_reminder()
        else: # Should not happen with current logic
            print(f"WARN: ReminderService - Unknown actual_type_to_show '{actual_type_to_show}'. Defaulting to text reminder.")
            self.show_text_reminder()


    def show_text_reminder(self):
        if not self.tray_icon or not self.tray_icon.isVisible():
            print("WARN: ReminderService - Tray icon not available to show text reminder.")
            return

        # Get a random dhikr text using AdhkarManager
        dhikr_text = self.adhkar_mngr.get_random_dhikr() # Default category is "general"
        
        if dhikr_text: # dhikr_text could be the "no_dhikr_available" message
            print(f"DEBUG: ReminderService - Showing text reminder: '{dhikr_text[:50]}...'")
            duration_ms = self.settings_mngr.get("notification_duration_seconds", 7) * 1000
            title_text = self.lm.get_string("app_name", "Zakir Reminder") # Localized app name or default
            
            try:
                self.tray_icon.showMessage(
                    title_text,
                    dhikr_text,
                    QSystemTrayIcon.MessageIcon.Information, 
                    duration_ms
                )
                print(f"DEBUG: ReminderService - tray_icon.showMessage called successfully for text.")
            except Exception as e_show_msg:
                print(f"ERROR: ReminderService - Exception during tray_icon.showMessage: {e_show_msg}")
                import traceback
                traceback.print_exc()
        else:
            # This case should ideally be handled by adhkar_mngr returning a default message.
            print("WARN: ReminderService - No dhikr text available to show (get_random_dhikr returned None or empty).")

    def play_sound_reminder(self):
        print("DEBUG: ReminderService - play_sound_reminder entered.")
        if not self.is_pygame_mixer_initialized:
            print("ERROR: ReminderService - pygame.mixer not initialized, cannot play sound reminder.")
            if self.tray_icon and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    self.lm.get_string("audio_playback_error_title"),
                    self.lm.get_string("audio_playback_not_ready_message"),
                    QSystemTrayIcon.MessageIcon.Warning,
                    3000
                )
            return

        selected_audios = self.settings_mngr.get("selected_audio_files", [])
        if not isinstance(selected_audios, list) or not any(selected_audios): # Ensure it's a non-empty list
            print("WARN: ReminderService - No audio files selected or 'selected_audio_files' is empty/invalid.")
            # Show message only if reminder_type is explicitly "sound" or was chosen as "sound" in "random"
            current_reminder_type = self.settings_mngr.get("reminder_type")
            if current_reminder_type == "sound" or (current_reminder_type == "random" and self.is_pygame_mixer_initialized): # Avoid showing if it was random and text was chosen
                 if self.tray_icon and self.tray_icon.isVisible():
                    self.tray_icon.showMessage(
                        self.lm.get_string("audio_reminder_error_title"),
                        self.lm.get_string("no_audio_files_selected_message"),
                        QSystemTrayIcon.MessageIcon.Warning,
                        3000
                    )
            return

        chosen_audio_filename = random.choice(selected_audios)
        # Path for general reminder audio files
        audio_file_path = os.path.join(self.base_path, "resources", "audio", "reminders", chosen_audio_filename)

        if not os.path.exists(audio_file_path):
            print(f"ERROR: ReminderService - Audio file not found: {audio_file_path}")
            if self.tray_icon and self.tray_icon.isVisible():
                 self.tray_icon.showMessage(
                    self.lm.get_string("audio_file_missing_title"),
                    self.lm.get_string("audio_file_missing_message", filename=chosen_audio_filename),
                    QSystemTrayIcon.MessageIcon.Warning,
                    3000
                )
            return

        print(f"DEBUG: ReminderService - Preparing to play sound with pygame.mixer: {audio_file_path}")
        
        try:
            # Double-check mixer initialization (it might have been quit externally or failed silently)
            if not pygame.mixer.get_init():
                print("WARN: ReminderService - pygame.mixer was not initialized. Attempting to re-init.")
                self._initialize_pygame_mixer() # Try to re-initialize
                if not self.is_pygame_mixer_initialized:
                    print("ERROR: ReminderService - Failed to re-initialize pygame.mixer. Cannot play sound.")
                    return # Exit if re-initialization fails

            # Stop any currently playing music and unload it before loading new
            if pygame.mixer.music.get_busy():
                print("DEBUG: ReminderService - Pygame mixer was busy, stopping current music.")
                pygame.mixer.music.stop()
                pygame.mixer.music.unload() # Important to unload before loading new

            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play() 
            print(f"DEBUG: ReminderService - pygame.mixer.music.play() called for {chosen_audio_filename}")

        except pygame.error as e:
            print(f"ERROR: ReminderService - pygame.error while trying to play {chosen_audio_filename}: {e}")
            if self.tray_icon and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    self.lm.get_string("audio_playback_error_title"),
                    self.lm.get_string("audio_playback_error_message"), # Generic message for playback error
                    QSystemTrayIcon.MessageIcon.Warning,
                    3000
                )
        except Exception as e_general: # Catch any other unexpected errors
            print(f"ERROR: ReminderService - Unexpected error during pygame sound playback: {e_general}")
            import traceback
            traceback.print_exc()
            # Optionally, show a generic error message to the user

    def stop_service(self):
        print("INFO: ReminderService - stop_service called.")
        if self.timer.isActive():
            self.timer.stop()
            print("INFO: ReminderService - Reminder timer stopped.")
        
        if self.is_pygame_mixer_initialized and pygame.mixer.get_init(): # Check if initialized before quitting
            try:
                pygame.mixer.music.stop() # Stop any playing music
                pygame.mixer.quit()       # Quit the mixer
                self.is_pygame_mixer_initialized = False # Update status
                print("INFO: ReminderService - pygame.mixer stopped and quit.")
            except Exception as e_quit:
                print(f"ERROR: ReminderService - Error during pygame.mixer.quit(): {e_quit}")
        else:
            print("INFO: ReminderService - pygame.mixer was not initialized or already quit.")
            
        print("INFO: ReminderService stopped.")