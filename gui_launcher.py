'''
A more modern way to launch games and applications.
Able to run just in the tray and such.
'''
import sys
import os
import subprocess
import threading
import queue
from pathlib import Path
import tkinter as tk
import customtkinter as ctk
import pystray
import ctypes
from PIL import Image, ImageTk

# Import custom files
import splash
import provision_card
import art_editor
from cmdline_launcher import display_menu

# Import existing logic directly from card_commands.py
from card_commands import load_game_cards, TomlCardLauncherObserver, CONFIG_FILE_PATH
from smartcard.CardMonitoring import CardMonitor

# Force standard output to handle UTF-8 characters
if sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")

class QueueRedirector:
    """Redirects writes to a queue for thread-safe GUI updates."""
    def __init__(self, log_queue):
        self.log_queue = log_queue

    def write(self, text):
        if text:
            self.log_queue.put(text)

    def flush(self):
        pass


class CrosynsCardLauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Crosyns Card Launcher")
        self.tray_icon = None
        self.provision_process = None

        # Calculate screen center for main launcher
        window_width = 520
        window_height = 580
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_coord = int((screen_width / 2) - (window_width / 2))
        y_coord = int((screen_height / 2) - (window_height / 2))
        
        self.geometry(f"{window_width}x{window_height}+{x_coord}+{y_coord}") 

        try:
            # 1. Tell Windows this is a unique app
            app_id = 'crosyn.nfc_launcher.gui.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            
            # 2. Apply window icon
            img = Image.open("assets/icon.png")
            img.save("assets/icon.ico", format="ICO")
            self.iconbitmap("assets/icon.ico")
        except Exception as e:
            print(f"Icon error: {e}")
        
        self.protocol('WM_DELETE_WINDOW', self.hide_window)

        # Thread-safe Log Queue
        self.log_queue = queue.Queue()

        # --- UI Elements ---
        self.header = ctk.CTkLabel(self, text="🎮 NFC Launcher Active", font=ctk.CTkFont(size=20, weight="bold"))
        self.header.pack(pady=(20, 5))

        self.status_label = ctk.CTkLabel(self, text="Status: Listening for cards...", text_color="#00FF00")
        self.status_label.pack(pady=5)

        # Button Frame
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)

        self.btn_pause = ctk.CTkButton(self.btn_frame, text="Pause Listener", command=self.toggle_pause, fg_color="#F57C00", hover_color="#EF6C00")
        self.btn_pause.grid(row=0, column=0, padx=10)

        self.btn_provision = ctk.CTkButton(self.btn_frame, text="Provision New Card", command=self.run_provisioner)
        self.btn_provision.grid(row=0, column=1, padx=10)

        # Console Log View
        self.console_label = ctk.CTkLabel(self, text="System Log:", font=ctk.CTkFont(size=12, weight="bold"))
        self.console_label.pack(anchor="w", padx=25, pady=(5, 0))

        self.console_box = ctk.CTkTextbox(
            self, width=470, height=220, state="disabled", 
            fg_color="#1E1E1E", text_color="#00FF00", 
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.console_box.pack(padx=20, pady=(5, 15))

        self.btn_exit = ctk.CTkButton(self, text="Quit Application", command=self.quit_app, fg_color="#C62828", hover_color="#B71C1C")
        self.btn_exit.pack(pady=(0, 20))

        # --- Redirect stdout & stderr to the log queue ---
        sys.stdout = QueueRedirector(self.log_queue)
        sys.stderr = QueueRedirector(self.log_queue)

        # Start checking the queue for log messages
        self.after(100, self.process_log_queue)

        # Single Subsystem Setup
        self.start_nfc_monitor()
        self.setup_tray_icon()

    def process_log_queue(self):
        """Polls the thread-safe queue and writes logs to the UI textbox."""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.console_box.configure(state="normal")
                self.console_box.insert("end", msg)
                self.console_box.see("end")
                self.console_box.configure(state="disabled")
            except queue.Empty:
                break
        
        self.after(100, self.process_log_queue)

    def start_nfc_monitor(self):
        active_card_map = load_game_cards(CONFIG_FILE_PATH)
        self.card_monitor = CardMonitor()
        self.card_observer = TomlCardLauncherObserver(active_card_map)
        self.card_monitor.addObserver(self.card_observer)

    def toggle_pause(self):
        if not getattr(self, '_is_paused', False):
            self._is_paused = True
            if hasattr(self, 'card_observer'):
                self.card_observer.paused = True
            try:
                self.card_monitor.deleteObserver(self.card_observer)
            except Exception:
                pass
            self.btn_pause.configure(text="Resume Listener")
            self.status_label.configure(text="Status: Listener Paused ⏸️", text_color="yellow")
            print("⏸️ Listener paused.\n")
        else:
            self._is_paused = False
            if hasattr(self, 'card_observer'):
                self.card_observer.paused = False
            self.card_monitor.addObserver(self.card_observer)
            self.btn_pause.configure(text="Pause Listener")
            self.status_label.configure(text="Status: Listening for cards...", text_color="#00FF00")
            print("▶️ Listener resumed.\n")

    def run_provisioner(self):
        self._is_paused = True
        if hasattr(self, 'card_observer'):
            self.card_observer.paused = True
        try:
            self.card_monitor.deleteObserver(self.card_observer)
        except Exception:
            pass
        
        self.btn_pause.configure(state="disabled") 
        self.btn_provision.configure(state="disabled")
        self.status_label.configure(text="Status: Provisioning Mode Active ⚙️", text_color="orange")
        print("⚙️ Launching provisioner... Background listener paused.\n")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        self.provision_process = subprocess.Popen(
            [sys.executable, "provision_card.py", "--gui"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            env=env
        )

        threading.Thread(target=self._stream_provisioner_output, daemon=True).start()
        self.check_provisioner_status()

    def _stream_provisioner_output(self):
        """Reads output from provision_card.py line by line and sends it to the queue."""
        if self.provision_process and self.provision_process.stdout:
            for line in iter(self.provision_process.stdout.readline, ''):
                if line:
                    self.log_queue.put(f"[Provisioner] {line}")
            self.provision_process.stdout.close()

    def check_provisioner_status(self):
        if self.provision_process and self.provision_process.poll() is None:
            self.after(500, self.check_provisioner_status)
        else:
            print("\n🔄 Provisioner closed. Reloading TOML configuration map...")
            self.card_observer.game_map = load_game_cards(CONFIG_FILE_PATH)

            self._is_paused = False
            if hasattr(self, 'card_observer'):
                self.card_observer.paused = False
            self.card_monitor.addObserver(self.card_observer)

            self.btn_pause.configure(state="normal", text="Pause Listener")
            self.btn_provision.configure(state="normal")
            self.status_label.configure(text="Status: Listening for cards...", text_color="#00FF00")
            print("▶️ System unpaused. Listening for card taps.\n")

    def setup_tray_icon(self):
        try:
            image = Image.open("assets/icon.png")
        except FileNotFoundError:
            image = Image.new('RGB', (64, 64), color=(73, 109, 137)) 

        menu = pystray.Menu(
            pystray.MenuItem('Show Dashboard', self.show_window, default=True),
            pystray.MenuItem('Quit', self.quit_app_from_tray)
        )
        
        self.tray_icon = pystray.Icon("NFC_Launcher", image, "NFC Smart Carts", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_window(self):
        self.withdraw()

    def show_window(self, icon=None, item=None):
        self.after(0, self.deiconify)

    def quit_app_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.quit_app)

    def quit_app(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        try:
            self.card_monitor.deleteObserver(self.card_observer)
        except Exception:
            pass
            
        if self.tray_icon:
            self.tray_icon.stop()
            
        self.destroy()
        sys.exit(0)

def ensure_single_instance():
    """Prevents multiple instances, alerts the user, and attempts to bring the existing app to the front."""
    mutex_name = "Global\\CrosynsCardLauncherAppMutex_UniqueLock"
    
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    
    if ctypes.windll.kernel32.GetLastError() == 183:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Crosyns Card Launcher")
        
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            
        sys.exit(0)
        
    return mutex

if __name__ == "__main__":
    # --- THE ROUTER ---
    # Check if the exe is being called with arguments by one of your subprocesses
    if len(sys.argv) > 1:
        script_target = sys.argv[1]
        
        if script_target == "splash.py":
            # sys.argv[2] is the cmd_id, sys.argv[3] is the game_name
            game_name = sys.argv[3] if len(sys.argv) > 3 else f"AppID: {sys.argv[2]}"
            splash.show_splash(sys.argv[2], game_name)
            sys.exit(0)
            
        elif script_target == "provision_card.py":
            # Pass the --gui flag logic manually
            if "--gui" in sys.argv:
                provision_card.run_gui()
            else:
                provision_card.run_cli()
            sys.exit(0)
            
        elif script_target == "art_editor.py":
            # Extract arguments for the art editor
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("script_name") # Catches 'art_editor.py'
            parser.add_argument("--id", required=True)
            parser.add_argument("--name", required=True)
            parser.add_argument("--cover", required=True)
            args, unknown = parser.parse_known_args()
            
            app = art_editor.ArtEditor(args.id, args.name, args.cover)
            app.mainloop()
            sys.exit(0)
            
        elif script_target == "cmdline_launcher.py":
            display_menu()
            sys.exit(0)

    # --- MAIN LAUNCHER ---
    # If no arguments are passed, run the normal GUI launcher
    app_mutex = ensure_single_instance()
    app = CrosynsCardLauncherApp()
    app.mainloop()