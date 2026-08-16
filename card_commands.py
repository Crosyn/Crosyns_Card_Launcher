"""
Script that monitors nfc card scanning/removal to run various applications.
"""

import subprocess
import sys
import threading
from pathlib import Path
from time import sleep
import winreg
from smartcard.CardMonitoring import CardMonitor, CardObserver

try:
    import tomllib
except ImportError:
    import pip._vendor.tomli as tomllib

CONFIG_FILE_PATH = Path("card_config.toml")

# Initialize a standard threading gate event
shutdown_event = threading.Event()

def is_steam_game_running() -> bool:
    """Checks the Windows Registry to see if Steam currently has a game running."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            running_app_id, _ = winreg.QueryValueEx(key, "RunningAppId")
            # If RunningAppId is not 0, a game is actively running
            return running_app_id != 0
    except Exception:
        # If the key is missing or inaccessible, assume no game is running
        return False

def load_game_cards(config_path: Path) -> dict:
    """Parses config.toml and returns a flat runtime dictionary mapping
    UIDs to their corresponding launch commands/IDs.
    """
    if not config_path.exists():
        print(f"❌ Error: Configuration file not found at {config_path}")
        print("Please ensure your config.toml exists in the same directory.")
        sys.exit(1)

    try:
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)

        # Build a rapid lookup dictionary: { "UID": "CMD" }
        runtime_map = {}

        # Safely traverse the [[cards]] array of tables
        cards_list = config_data.get("cards", [])
        for card in cards_list:
            uid = card.get("uid")
            cmd = card.get("cmd")
            name = card.get("name", "Unknown Game")

            if uid and cmd:
                # Force uppercase to guarantee casing matching regardless of TOML input
                runtime_map[uid.strip().upper()] = {
                    "cmd": str(cmd).strip(),
                    "name": name,
                    "type": card.get("type", "Steam"),
                }

        print(f"⚙️ Successfully loaded {len(runtime_map)} games from configuration file.")
        return runtime_map

    except Exception as e:
        print(f"❌ Failed parsing {CONFIG_FILE_PATH} layout: {e}")
        sys.exit(1)

class TomlCardLauncherObserver(CardObserver):
    """An observer that detects tapped cards,
    extracts their unique hardware UIDs, and launches corresponding games
    defined inside config.toml.
    """

    def __init__(self, game_map: dict):
        super().__init__()
        self.game_map = game_map
        self.paused = False  # Add this flag

    def update(self, observable, handlers):
        # Immediately exit the function if the system is paused
        if self.paused:
            return
        added_cards, removed_cards = handlers

        for card in added_cards:
            try:
                # 1. Establish connection to the tapped card
                connection = card.createConnection()
                connection.connect()

                # 2. Transmit the standard PC/SC command to retrieve the unique hardware UID
                GET_UID_COMMAND = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                data, sw1, sw2 = connection.transmit(GET_UID_COMMAND)

                if sw1 == 0x90 and sw2 == 0x00:
                    # Format the UID with dashes (e.g., "04-83-D5-1E-46-02-89")
                    uid_string = "-".join(f"{b:02X}" for b in data)
                    print(f"\n🎯 Card Detected! UID: {uid_string}")

                    # --- NEW: Check if a game is already running before proceeding ---
                    if is_steam_game_running():
                        print("🚫 Launch blocked: A Steam game is currently running!")
                        continue # Skip launching for this card tap

                    # 3. Match the UID against our TOML-derived configuration map
                    if uid_string in self.game_map:
                        card_info = self.game_map[uid_string]
                        card_name = card_info["name"]
                        card_cmd = card_info["cmd"]
                        card_type = card_info["type"]

                        print(f"🎮 Target Identified: {card_name} ({card_type})")
                        print(f"🚀 Executing launch trigger code: {card_cmd}")

                        if card_type.lower() == "steam":
                            self.steam_card(card_name, card_cmd)
                        else:
                            print(f"⚠️ Unsupported type '{card_type}' specified in config.")
                    else:
                        print(f"⚠️ Unmapped tag. Add UID '{uid_string}' to your config.toml.")
                else:
                    print(f"❌ Failed to extract hardware UID. Status code: {hex(sw1)} {hex(sw2)}")

            except Exception as e:
                print(f"⚠️ Connection dropped or read interrupted: {e}")

        for card in removed_cards:
            print("👋 Card removed from reader surface.")

    def steam_card(self, card_name, card_cmd):
        # Fire off the splash screen script asynchronously 
        subprocess.Popen([sys.executable, "splash.py", str(card_cmd)])
        
        # Triggers the Windows default URI handler for Steam
        subprocess.run(
            ["cmd", "/c", f"start steam://run/{card_cmd}"],
            shell=True,
        )

if __name__ == "__main__":
    print("==================================================")
    print(" 🎮 SMART CARTS SYSTEM RUNNING ")
    print("==================================================")

    # Load file values on initialization path
    active_card_map = load_game_cards(CONFIG_FILE_PATH)

    print("\n🛰️  System online! Tap an NFC card to run its macro.")
    print("--------------------------------------------------")

    # Initialize the background system monitor loop
    card_monitor = CardMonitor()
    card_observer = TomlCardLauncherObserver(active_card_map)
    card_monitor.addObserver(card_observer)

    while True:
        print("⌨️  Press '1' and Enter at any time to exit the program safely.")
        user_input = input("👉 Enter command: ").strip()

        if user_input == "1":
            print("\nShutting down card monitor threads...")
            break
        else:
            print("⚠️  Unknown command. The system is still listening for card taps.")
            print("--------------------------------------------------")

    # Cleanup so the operating system thread loop finishes gracefully
    card_monitor.deleteObserver(card_observer)
    print("👋 Stopping Smart Cart System ")
    sys.exit(0)