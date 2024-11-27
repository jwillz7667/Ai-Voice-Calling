import customtkinter as ctk
import threading
import asyncio
import sys
import os
import json
import logging
from datetime import datetime
import subprocess

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure CLI logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class VoiceSettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, current_settings):
        super().__init__(master)
        self.title("Advanced Voice AI Settings")
        self.geometry("500x700")
        
        # Store current settings
        self.current_settings = current_settings
        
        # Create settings widgets
        self.create_widgets()
    
    def create_widgets(self):
        # Scrollable frame for settings
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=450)
        self.scrollable_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Custom Prompt
        ctk.CTkLabel(self.scrollable_frame, text="Custom Prompt:", font=ctk.CTkFont(weight="bold")).pack(pady=(10,5))
        self.prompt_textbox = ctk.CTkTextbox(self.scrollable_frame, height=150)
        self.prompt_textbox.pack(padx=10, pady=(0,10), fill="x")
        self.prompt_textbox.insert("1.0", self.current_settings.get('prompt', 
            "You are a helpful and engaging AI assistant. Respond conversationally and be concise."))
        
        # Voice Selection
        ctk.CTkLabel(self.scrollable_frame, text="Voice:", font=ctk.CTkFont(weight="bold")).pack(pady=(10,5))
        self.voice_var = ctk.StringVar(value=self.current_settings.get('voice', 'alloy'))
        self.voice_menu = ctk.CTkOptionMenu(
            self.scrollable_frame,
            values=["alloy", "echo", "fable", "onyx", "nova"],
            variable=self.voice_var
        )
        self.voice_menu.pack(padx=10, pady=(0,10), fill="x")
        
        # Temperature (Creativity)
        ctk.CTkLabel(self.scrollable_frame, text="Creativity (Temperature):", font=ctk.CTkFont(weight="bold")).pack(pady=(10,5))
        self.temp_var = ctk.DoubleVar(value=float(self.current_settings.get('temperature', 0.7)))
        self.temp_slider = ctk.CTkSlider(
            self.scrollable_frame, 
            from_=0, 
            to=1, 
            number_of_steps=20,
            variable=self.temp_var
        )
        self.temp_slider.pack(padx=10, pady=(0,10), fill="x")
        self.temp_label = ctk.CTkLabel(self.scrollable_frame, 
            text=f"Current: {self.temp_var.get():.2f}")
        self.temp_label.pack()
        self.temp_slider.configure(command=self.update_temp_label)
        
        # Emotion/Tone Selection
        ctk.CTkLabel(self.scrollable_frame, text="Emotional Tone:", font=ctk.CTkFont(weight="bold")).pack(pady=(10,5))
        self.emotion_var = ctk.StringVar(value=self.current_settings.get('emotion', 'neutral'))
        self.emotion_menu = ctk.CTkOptionMenu(
            self.scrollable_frame,
            values=["neutral", "friendly", "professional", "enthusiastic", "empathetic", "playful"],
            variable=self.emotion_var
        )
        self.emotion_menu.pack(padx=10, pady=(0,10), fill="x")
        
        # Speech Rate
        ctk.CTkLabel(self.scrollable_frame, text="Speech Rate:", font=ctk.CTkFont(weight="bold")).pack(pady=(10,5))
        self.rate_var = ctk.DoubleVar(value=float(self.current_settings.get('speech_rate', 1.0)))
        self.rate_slider = ctk.CTkSlider(
            self.scrollable_frame, 
            from_=0.5, 
            to=2.0, 
            number_of_steps=15,
            variable=self.rate_var
        )
        self.rate_slider.pack(padx=10, pady=(0,10), fill="x")
        self.rate_label = ctk.CTkLabel(self.scrollable_frame, 
            text=f"Current: {self.rate_var.get():.2f}")
        self.rate_label.pack()
        self.rate_slider.configure(command=self.update_rate_label)
        
        # Volume
        ctk.CTkLabel(self.scrollable_frame, text="Volume:", font=ctk.CTkFont(weight="bold")).pack(pady=(10,5))
        self.volume_var = ctk.DoubleVar(value=float(self.current_settings.get('volume', 1.0)))
        self.volume_slider = ctk.CTkSlider(
            self.scrollable_frame, 
            from_=0, 
            to=2.0, 
            number_of_steps=20,
            variable=self.volume_var
        )
        self.volume_slider.pack(padx=10, pady=(0,10), fill="x")
        self.volume_label = ctk.CTkLabel(self.scrollable_frame, 
            text=f"Current: {self.volume_var.get():.2f}")
        self.volume_label.pack()
        self.volume_slider.configure(command=self.update_volume_label)
        
        # Save Button
        self.save_button = ctk.CTkButton(
            self.scrollable_frame, 
            text="Save Settings", 
            command=self.save_settings
        )
        self.save_button.pack(pady=20)
    
    def update_temp_label(self, value):
        self.temp_label.configure(text=f"Current: {value:.2f}")
    
    def update_rate_label(self, value):
        self.rate_label.configure(text=f"Current: {value:.2f}")
    
    def update_volume_label(self, value):
        self.volume_label.configure(text=f"Current: {value:.2f}")
    
    def save_settings(self):
        # Import here to avoid circular import
        from main import set_system_message, set_voice
        
        # Collect all settings
        settings = {
            'prompt': self.prompt_textbox.get("1.0", "end-1c"),
            'voice': self.voice_var.get(),
            'temperature': self.temp_var.get(),
            'emotion': self.emotion_var.get(),
            'speech_rate': self.rate_var.get(),
            'volume': self.volume_var.get()
        }
        
        # Update main.py parameters directly
        try:
            # Set system message and voice
            set_system_message(settings['prompt'])
            set_voice(settings['voice'])
            
            # Save to a JSON file in the user's home directory
            settings_path = os.path.join(os.path.expanduser('~'), '.ai_voice_call_settings.json')
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=4)
            
            # Update main window's settings and log
            self.master.update_voice_settings(settings)
            self.master.log_message("Voice settings saved successfully")
            
            # Close the settings window
            self.destroy()
        except Exception as e:
            self.master.log_message(f"Error saving settings: {str(e)}")

class VoiceCallApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Load existing settings
        self.load_settings()

        # Configure window
        self.title("AI Voice Call")
        self.geometry("800x600")
        
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Main content
        self.grid_rowconfigure(2, weight=0)  # Controls

        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Create widgets
        self.create_widgets()
        
        self.is_calling = False
        self.call_thread = None

    def create_widgets(self):
        # Header Frame
        self.header_frame = ctk.CTkFrame(self, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20,0))
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="AI Voice Call",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=10)

        # Main Content Frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Phone Number Entry
        self.phone_frame = ctk.CTkFrame(self.main_frame)
        self.phone_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        self.phone_label = ctk.CTkLabel(self.phone_frame, text="Phone Number:")
        self.phone_label.pack(side="left", padx=10)
        
        self.phone_entry = ctk.CTkEntry(
            self.phone_frame,
            placeholder_text="+1234567890"
        )
        self.phone_entry.pack(side="left", fill="x", expand=True, padx=10)

        # Call Log
        self.log_frame = ctk.CTkFrame(self.main_frame)
        self.log_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0,20))
        
        self.log_label = ctk.CTkLabel(self.log_frame, text="Call Log:")
        self.log_label.pack(anchor="w", padx=10, pady=5)
        
        self.log_text = ctk.CTkTextbox(self.log_frame, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0,10))

        # Controls Frame
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0,20))

        # Voice Selection
        self.voice_var = ctk.StringVar(value=self.voice_settings.get('voice', 'alloy'))
        self.voice_label = ctk.CTkLabel(self.controls_frame, text="Voice:")
        self.voice_label.pack(side="left", padx=10)
        
        self.voice_menu = ctk.CTkOptionMenu(
            self.controls_frame,
            values=["alloy", "echo", "fable", "onyx", "nova"],
            variable=self.voice_var
        )
        self.voice_menu.pack(side="left", padx=10)

        # Call Button
        self.call_button = ctk.CTkButton(
            self.controls_frame,
            text="Start Call",
            command=self.toggle_call
        )
        self.call_button.pack(side="right", padx=10)

        # Settings Button
        self.settings_button = ctk.CTkButton(
            self.controls_frame,
            text="Settings",
            command=self.show_settings
        )
        self.settings_button.pack(side="right", padx=10)

    def load_settings(self):
        # Default settings
        self.voice_settings = {
            'prompt': "You are a helpful and engaging AI assistant. Respond conversationally and be concise.",
            'voice': 'alloy',
            'temperature': 0.7,
            'emotion': 'neutral',
            'speech_rate': 1.0,
            'volume': 1.0
        }
        
        # Try to load from saved settings in user's home directory
        settings_path = os.path.join(os.path.expanduser('~'), '.ai_voice_call_settings.json')
        try:
            with open(settings_path, 'r') as f:
                saved_settings = json.load(f)
                self.voice_settings.update(saved_settings)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error loading settings: {e}")

    def update_voice_settings(self, new_settings):
        """Update voice settings from settings window"""
        self.voice_settings.update(new_settings)
        
        # Update voice menu to reflect current voice
        self.voice_var.set(self.voice_settings.get('voice', 'alloy'))

    def show_settings(self):
        # Open advanced settings window
        VoiceSettingsWindow(self, self.voice_settings)

    def toggle_call(self):
        # Import subprocess to launch main.py
        import subprocess
        import sys
        import os

        if not self.is_calling:
            phone_number = self.phone_entry.get()
            if not phone_number:
                logger.warning("No phone number entered")
                self.log_message("Please enter a phone number")
                return
            
            # Validate phone number format
            if not self._validate_phone_number(phone_number):
                logger.warning(f"Invalid phone number format: {phone_number}")
                self.log_message("Invalid phone number format")
                return
            
            self.is_calling = True
            self.call_button.configure(text="End Call", fg_color="red")
            
            # Log call initiation
            logger.info(f"Starting call to {phone_number}")
            self.log_message(f"Starting call to {phone_number}")
            
            # Prepare call configuration
            call_config = {
                'phone_number': phone_number,
                'prompt': self.voice_settings.get('prompt', ''),
                'voice': self.voice_settings.get('voice', 'alloy'),
                'temperature': self.voice_settings.get('temperature', 0.7),
                'emotion': self.voice_settings.get('emotion', 'neutral'),
                'speech_rate': self.voice_settings.get('speech_rate', 1.0),
                'volume': self.voice_settings.get('volume', 1.0)
            }
            
            # Save current configuration to a temporary file
            config_path = os.path.join(os.path.dirname(__file__), 'current_call_config.json')
            try:
                with open(config_path, 'w') as f:
                    json.dump(call_config, f, indent=4)
                
                # Launch main.py as a separate process with full arguments
                main_script_path = os.path.join(os.path.dirname(__file__), 'main.py')
                call_process = subprocess.Popen([
                    sys.executable, 
                    main_script_path, 
                    '--call', phone_number,
                    '--config', config_path
                ], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True)
                
                # Optional: Track the process and log its output
                def monitor_process():
                    while True:
                        output = call_process.stdout.readline()
                        if output == '' and call_process.poll() is not None:
                            break
                        if output:
                            self.log_message(output.strip())
                    
                    # Check for any errors
                    stderr_output = call_process.stderr.read()
                    if stderr_output:
                        self.log_message(f"Error: {stderr_output}")
                    
                    # Update UI when process ends
                    self.after(0, self.end_call)
                
                # Start monitoring in a separate thread
                threading.Thread(target=monitor_process, daemon=True).start()
                
                # Optional: Track the process
                self.call_process = call_process
                
            except Exception as e:
                logger.error(f"Error starting call: {e}")
                self.log_message(f"Error starting call: {e}")
                self.end_call()
        else:
            # Log call termination
            logger.info("Manually ending call")
            self.end_call()

    def _validate_phone_number(self, phone_number):
        """Basic phone number validation"""
        # Remove any spaces or dashes
        cleaned_number = ''.join(filter(str.isdigit, phone_number))
        
        # Check if number starts with + and has 10-15 digits
        return (phone_number.startswith('+') and 
                len(cleaned_number) >= 10 and 
                len(cleaned_number) <= 15)

    def end_call(self):
        # Terminate the call process if it exists
        if hasattr(self, 'call_process'):
            try:
                self.call_process.terminate()
            except Exception as e:
                logger.error(f"Error terminating call process: {e}")
        
        self.is_calling = False
        self.call_button.configure(text="Start Call", fg_color=["#3B8ED0", "#1F6AA5"])
        self.log_message("Call ended")

    def log_message(self, message):
        # Ensure logging happens on the main thread
        self.after(0, self._log_message, message)

    def _log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")

def main():
    app = VoiceCallApp()
    app.mainloop()

if __name__ == "__main__":
    main()