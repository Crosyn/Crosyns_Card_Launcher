'''
Handles card provisioning to map a NFC card's UUID to launch commands locally
via a toml configuration file. Also launches the editor to create card art.
'''
import os
import re
import subprocess
import shutil
import sys
import argparse
import urllib.request
from time import sleep
from pathlib import Path
import winreg
import ctypes
from PIL import Image, ImageTk, ImageChops
import tkinter as tk
import customtkinter as ctk
from smartcard.CardMonitoring import CardMonitor, CardObserver

try:
    import tomllib
except ImportError:
    import pip._vendor.tomli as tomllib

# Force standard output to handle UTF-8 characters (like emojis)
if sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')

CONFIG_FILE_PATH = Path("card_config.toml")
IGNORE_FILE_PATH = Path("steam_ignore.toml")
COVERS_DIR_PATH = Path("card_covers")

def load_ignored_games(file_path: Path) -> dict:
    """Reads the ignore list and returns a dictionary of {id: name}."""
    if file_path.exists() and file_path.stat().st_size > 0:
        try:
            with open(file_path, "rb") as f:
                parsed_data = tomllib.load(f)
                ignored_list = parsed_data.get("ignored", [])
                return {str(item["id"]): item.get("name", "Unknown") for item in ignored_list}
        except Exception as e:
            print(f"⚠️  Failed to read ignore list: {e}")
    return {}

def append_to_ignore_list(game_id: str, game_name: str, file_path: Path):
    """Appends a new game to the ignore list and saves it."""
    ignored = load_ignored_games(file_path)
    
    if game_id not in ignored:
        ignored[game_id] = game_name
        
        toml_output_buffer = []
        for gid, gname in ignored.items():
            toml_output_buffer.append(
                f"[[ignored]]\n"
                f'id = "{gid}"\n'
                f'name = "{gname}"\n'
            )
        file_path.write_text("\n".join(toml_output_buffer), encoding="utf-8")
        print(f"🚫 Added '{game_name}' to ignore list -> {file_path}")

def remove_from_ignore_list(game_id: str, file_path: Path):
    """Removes a game from the ignore list and saves it."""
    ignored = load_ignored_games(file_path)
    if game_id in ignored:
        del ignored[game_id]
        toml_output_buffer = []
        for gid, gname in ignored.items():
            toml_output_buffer.append(
                f"[[ignored]]\n"
                f'id = "{gid}"\n'
                f'name = "{gname}"\n'
            )
        file_path.write_text("\n".join(toml_output_buffer), encoding="utf-8")
        print(f"✅ Removed from ignore list -> {file_path}")

def load_existing_cards(file_path: Path) -> list:
    if file_path.exists() and file_path.stat().st_size > 0:
        try:
            with open(file_path, "rb") as f:
                parsed_data = tomllib.load(f)
                return parsed_data.get("cards", [])
        except Exception as e:
            print(f"⚠️  Failed to read current config file layout: {e}")
            sys.exit(1)
    return []

def get_steam_root() -> Path:
    """Finds the main Steam installation directory via the Windows Registry."""
    try:
        # Try 64-bit registry path
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
            path, _ = winreg.QueryValueEx(key, "InstallPath")
            return Path(path)
    except FileNotFoundError:
        try:
            # Try 32-bit registry path
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam") as key:
                path, _ = winreg.QueryValueEx(key, "InstallPath")
                return Path(path)
        except FileNotFoundError:
            # Absolute fallback
            return Path(r"C:\Program Files (x86)\Steam")

def get_all_steam_libraries() -> list:
    """Reads Steam's libraryfolders.vdf to find all game installation drives."""
    steam_root = get_steam_root()
    libraries = [steam_root / "steamapps"] # Always include the default drive
    
    vdf_path = steam_root / "steamapps" / "libraryfolders.vdf"
    if vdf_path.exists():
        try:
            with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            # Use Regex to extract paths from the VDF (e.g., "path"  "D:\\SteamLibrary")
            paths = re.findall(r'"path"\s+"([^"]+)"', content, re.IGNORECASE)
            for p in paths:
                # VDF files double-escape backslashes; we need to clean them up
                clean_path = Path(p.replace(r'\\', '\\')) / "steamapps"
                if clean_path not in libraries and clean_path.exists():
                    libraries.append(clean_path)
        except Exception as e:
            print(f"⚠️ Failed to parse libraryfolders.vdf: {e}")
            
    return libraries

def scan_installed_steam_games(filter_ignored=True) -> list:
    installed_games = []
    library_folders = get_all_steam_libraries()
    ignored_games = load_ignored_games(IGNORE_FILE_PATH)

    for steamapps_path in library_folders:
        if not steamapps_path.exists():
            continue

        for file_path in steamapps_path.glob("appmanifest_*.acf"):
            try:
                match = re.search(r"appmanifest_(\d+)\.acf", file_path.name)
                if not match: continue
                game_id = match.group(1)

                if filter_ignored and game_id in ignored_games:
                    continue 

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                name_match = re.search(r'"name"\s+"([^"]+)"', content, re.IGNORECASE)
                game_name = name_match.group(1) if name_match else "Unknown Game"
                
                # Prevent duplicates if a game appears in multiple libraries
                if not any(g['id'] == game_id for g in installed_games):
                    installed_games.append({"name": game_name, "id": game_id})
            except Exception:
                pass

    return sorted(installed_games, key=lambda x: x["name"].lower())

def download_cover_art(game_id: str, game_name: str, target_dir: Path):
    """Attempts to copy the cover art from Steam's local cache first, 
    falling back to the CDN if the file is missing."""
    target_dir.mkdir(parents=True, exist_ok=True)
    destination_file = target_dir / f"{game_id}.jpg"

    # Grab the true root directly from the registry
    steam_root = get_steam_root()
    local_cache_folder = steam_root / "appcache" / "librarycache" / f"{game_id}"
    local_cache_file = local_cache_folder / "library_600x900.jpg"

    # 2. Try the local cache first
    if not local_cache_file.exists():
        # Search recursively inside local_cache_folder for specific files
        found_600x900 = list(local_cache_folder.rglob("library_600x900.jpg"))
        found_capsule = list(local_cache_folder.rglob("library_capsule.jpg"))

        if found_600x900:
            local_cache_file = found_600x900[0]
        elif found_capsule:
            local_cache_file = found_capsule[0]
            
    if local_cache_file.exists():
        print(f"\n🖼️  Local cache hit! Copying artwork for: {game_name}...")
        try:
            shutil.copy(local_cache_file, destination_file)
            print(f"✅ Copied local asset to -> {destination_file}")
            return # Exit the function successfully
        except Exception as e:
            print(f"⚠️  Failed to copy local file: {e}. Falling back to web download.")
    else:
        print(f"Could not find: {local_cache_file}")
    # 3. Fallback to the web CDN if the local file is missing or failed
    cdn_url = f"https://steamcdn-a.akamaihd.net/steam/apps/{game_id}/library_600x900_2x.jpg"
    print(f"\n🌐 Local cache miss. Fetching official vertical box art from Steam CDN for: {game_name}...")
    
    try:
        req = urllib.request.Request(cdn_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            with open(destination_file, 'wb') as out_file:
                out_file.write(response.read())
        print(f"✅ Saved capsule artwork to -> {destination_file}")
    except Exception as e:
        print(f"⚠️  Could not grab custom artwork from Steam servers: {e}")

def save_toml_config(file_path: Path, cards_list: list):
    toml_output_buffer = []
    for card in cards_list:
        toml_output_buffer.append(
            f"[[cards]]\n"
            f'name = "{card["name"]}"\n'
            f'type = "{card.get("type", "Steam")}"\n'
            f'cmd = "{card["cmd"]}"\n'
            f'uid = "{card["uid"]}"\n'
        )
    file_path.write_text("\n".join(toml_output_buffer), encoding="utf-8")
    print(f"💾 File updated successfully at -> {file_path}")

class CardScanProvisioner(CardObserver):
    def __init__(self):
        super().__init__()
        self.captured_uid = None

    def update(self, observable, handlers):
        added_cards, _ = handlers
        for card in added_cards:
            if self.captured_uid: return
            try:
                connection = card.createConnection()
                connection.connect()
                data, sw1, sw2 = connection.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
                if sw1 == 0x90 and sw2 == 0x00:
                    self.captured_uid = "-".join(f"{b:02X}" for b in data)
            except Exception:
                pass

def wait_for_card_tap() -> str:
    print("\n💳 [Step 1] Please TAP your physical card onto the WCR330 reader surface now...")
    provisioner = CardScanProvisioner()
    monitor = CardMonitor()
    monitor.addObserver(provisioner)
    try:
        while provisioner.captured_uid is None:
            sleep(0.2)
    finally:
        monitor.deleteObserver(provisioner)
    print(f"🎯 Card Intercepted successfully! Unique ID Profile: {provisioner.captured_uid}")
    return provisioner.captured_uid

# ==========================================
# CLI APPLICATION LOOP
# ==========================================
def run_cli():
    print("==================================================")
    print(" 🎮 STEAM CARD UPDATE & ASSIGNMENT UTILITY (CLI) ")
    print("==================================================")

    target_uid = wait_for_card_tap()
    clean_uid = target_uid.strip().upper()
    existing_cards = load_existing_cards(CONFIG_FILE_PATH)
    card_index_to_overwrite = -1

    for index, card in enumerate(existing_cards):
        if card.get("uid", "").strip().upper() == clean_uid:
            card_index_to_overwrite = index
            print(f"\n⚠️  [CONFLICT DETECTED] This card is already assigned!")
            print(f"   Current Assignment: {card.get('name')} (AppID: {card.get('cmd')})")
            break

    if card_index_to_overwrite != -1:
        while True:
            confirm = input("👉 Do you want to OVERWRITE this card with a new game? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']: break
            elif confirm in ['n', 'no']: sys.exit(0)

    print("\n🔍 [Step 2] Querying internal local installation vectors for active games...")
    games_list = scan_installed_steam_games(filter_ignored=True)

    if not games_list:
        print("❌ No valid games cataloged inside the local directory.")
        sys.exit(1)

    print(f"\n📋 Detected {len(games_list)} games ready for physical card mapping:\n")
    print("  [0] CANCEL AND EXIT SCRIPT")
    for idx, game in enumerate(games_list):
        print(f"  [{idx + 1}] {game['name']} (AppID: {game['id']})")

    while True:
        choice = input(f"\n👉 Select target match index (1-{len(games_list)}): ").strip()
        if choice in ['0', 'q', 'quit', 'exit']: sys.exit(0)
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(games_list):
                selected_game = games_list[choice_idx]
                break
        except ValueError:
            pass

    download_cover_art(selected_game["id"], selected_game["name"], COVERS_DIR_PATH)

    new_card_data = {
        "name": selected_game["name"],
        "type": "Steam",
        "cmd": selected_game["id"],
        "uid": target_uid
    }

    if card_index_to_overwrite != -1:
        existing_cards[card_index_to_overwrite] = new_card_data
    else:
        existing_cards.append(new_card_data)

    save_toml_config(CONFIG_FILE_PATH, existing_cards)
    print("\n🎉 Provisioning sequence finalized. You can now tap this card during background listening phases!")

# ==========================================
# GUI APPLICATION LOOP
# ==========================================
def run_gui():
    import customtkinter as ctk 

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Provision NFC Card")
    
    # Calculate screen center for provisioner
    screen_width = app.winfo_screenwidth()
    screen_height = app.winfo_screenheight()
    window_width = round(screen_width * 0.75)
    window_height = round(screen_height * 0.75)
    x_coord = int((screen_width / 2) - (window_width / 2))
    y_coord = int((screen_height / 2) - (window_height / 2))
    
    app.geometry(f"{window_width}x{window_height}+{x_coord}+{y_coord}")
    app.minsize(650, 450)

    try:
        app_id = 'crosyns_card_launcher.provisioner.gui.1' # (Use .provisioner.1 for the other file)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        
        # Load the original image
        img = Image.open("assets/icon.png").convert("RGBA")
        
        # 1. Save the transparency mask for later
        alpha = img.getchannel('A')
        
        # 2. Convert the image to grayscale to preserve shading, then back to RGB to accept color
        grayscale_img = img.convert("L").convert("RGB")
        
        # 3. Create a solid block of your desired color
        icon_color = "#FFABFB" # Your color choice
        color_block = Image.new("RGB", img.size, icon_color)
        
        # 4. Multiply the grayscale image with the color block (tints it, keeps details)
        tinted_img = ImageChops.multiply(grayscale_img, color_block)
        
        # 5. Re-apply the original transparency mask
        tinted_img.putalpha(alpha)
        
        # Save and apply
        tinted_img.save("assets/icon.ico", format="ICO")
        app.iconbitmap("assets/icon.ico")
    except Exception as e:
        print(f"Icon error: {e}")

    # Core Variables
    captured_uid = ctk.StringVar(value="")
    # Pass filter_ignored=False so the UI has access to all games
    games_list = scan_installed_steam_games(filter_ignored=False)

    # --- UI Components ---
    header_frame = ctk.CTkFrame(app, fg_color="transparent")
    header_frame.pack(fill="x", padx=20, pady=(20, 0))

    title_label = ctk.CTkLabel(header_frame, text="🎮 Steam Card Assignment", font=ctk.CTkFont(size=24, weight="bold"))
    title_label.pack()

    status_label = ctk.CTkLabel(header_frame, text="💳 Please TAP your physical card on the reader...", font=ctk.CTkFont(size=16))
    status_label.pack(pady=5)

    uid_label = ctk.CTkLabel(header_frame, text="", font=ctk.CTkFont(size=18, weight="bold"), text_color="#00FF00")
    uid_label.pack(pady=5)

    # --- Upgraded Existing Assignment Indicator Container (Top Right) ---
    existing_assignment_frame = ctk.CTkFrame(app, fg_color="transparent")
    existing_assignment_frame.place(relx=0.96, rely=0.03, anchor="ne")

    existing_title_lbl = ctk.CTkLabel(
        existing_assignment_frame, 
        text="", 
        font=ctk.CTkFont(size=13, slant="italic"), 
        text_color="gray",
        justify="right"
    )
    existing_title_lbl.pack(anchor="e")
    
    # Label intended to hold the miniature preview image
    existing_img_lbl = ctk.CTkLabel(existing_assignment_frame, text="")
    existing_img_lbl.pack(anchor="e", pady=(5, 0))

    # --- Filters Frame (Search + Checkboxes) ---
    filters_frame = ctk.CTkFrame(app, fg_color="transparent")
    filters_frame.pack(pady=(10, 15))
    
    search_var = ctk.StringVar()
    search_entry = ctk.CTkEntry(filters_frame, textvariable=search_var, placeholder_text="🔍 Search installed games...", width=280, height=35)
    search_entry.pack(side="left", padx=(0, 10))

    hide_assigned_var = ctk.BooleanVar(value=True)
    hide_ignored_var = ctk.BooleanVar(value=True)

    # Note: We must define update_grid BEFORE we bind it to the checkbox commands
    
    grid_frame = ctk.CTkScrollableFrame(app, width=800, height=400)
    grid_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    app.current_cols = 4

# --- Grid Population Logic ---
    def update_grid(*args):
        search_query = search_var.get().lower()
        
        for widget in grid_frame.winfo_children():
            widget.destroy()

        ignored_games = load_ignored_games(IGNORE_FILE_PATH)
        existing_cards = load_existing_cards(CONFIG_FILE_PATH)
        assigned_game_ids = [c.get("cmd") for c in existing_cards]

        filtered_games = []
        for g in games_list:
            if search_query not in g['name'].lower():
                continue
                
            is_ignored = str(g['id']) in ignored_games
            is_assigned = g['id'] in assigned_game_ids

            if is_ignored and hide_ignored_var.get():
                continue
            if is_assigned and hide_assigned_var.get():
                continue
                
            filtered_games.append((g, is_ignored, is_assigned))

        if not filtered_games:
            no_results = ctk.CTkLabel(grid_frame, text="No games found.", font=ctk.CTkFont(size=14, slant="italic"))
            no_results.grid(row=0, column=0, padx=20, pady=20)
            return

        current_btn_state = "normal" if captured_uid.get() else "disabled"

        for index, (game, is_ignored, is_assigned) in enumerate(filtered_games):
            row = index // app.current_cols
            col = index % app.current_cols

            if is_ignored:
                # Red border for ignored games
                card = ctk.CTkFrame(grid_frame, width=170, height=260, corner_radius=10, 
                                    fg_color="#3b1a1a", border_width=2, border_color="#E74C3C")
            elif is_assigned:
                # Green border for assigned games
                card = ctk.CTkFrame(grid_frame, width=170, height=260, corner_radius=10, 
                                    fg_color="#1a3b2b", border_width=2, border_color="#2ECC71")
            else:
                card = ctk.CTkFrame(grid_frame, width=170, height=260, corner_radius=10)
                
            card.grid(row=row, column=col, padx=10, pady=10)
            card.grid_propagate(False) 
            card.grid_columnconfigure(0, weight=1)

            img_path = COVERS_DIR_PATH / f"{game['id']}.jpg"
            if not img_path.exists():
                download_cover_art(game['id'], game['name'], COVERS_DIR_PATH)
                img_path = COVERS_DIR_PATH / f"{game['id']}.jpg"
            
            if img_path.exists():
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((120, 180)) 
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(100, 150))
                    
                    img_lbl = ctk.CTkLabel(card, image=ctk_img, text="")
                    img_lbl.image = ctk_img 
                    img_lbl.grid(row=0, column=0, pady=(10, 0))
                except Exception:
                    img_lbl = ctk.CTkLabel(card, text="[Art Error]", width=100, height=150, fg_color="gray30")
                    img_lbl.grid(row=0, column=0, pady=(10, 0))
            else:
                img_lbl = ctk.CTkLabel(card, text="[No Cached Art]", width=100, height=150, fg_color="gray30")
                img_lbl.grid(row=0, column=0, pady=(10, 0))

            name_lbl = ctk.CTkLabel(card, text=game['name'], wraplength=150, font=ctk.CTkFont(size=12, weight="bold"))
            name_lbl.grid(row=1, column=0, pady=(5, 0), sticky="n")

            assign_btn = ctk.CTkButton(card, text="Assign", width=100, height=28, 
                                       command=lambda g=game: commit_assignment(g),
                                       state=current_btn_state) 
            assign_btn.grid(row=2, column=0, pady=(5, 10), sticky="s")
            
            card.assign_btn = assign_btn

            right_click_action = lambda event, g=game: show_context_menu(event, g)
            card.bind("<Button-3>", right_click_action)
            img_lbl.bind("<Button-3>", right_click_action)
            name_lbl.bind("<Button-3>", right_click_action)

    # Now that update_grid exists, pack the checkboxes and bind their commands
    chk_hide_assigned = ctk.CTkCheckBox(filters_frame, text="Hide Assigned", variable=hide_assigned_var, command=update_grid)
    chk_hide_assigned.pack(side="left", padx=10)

    chk_hide_ignored = ctk.CTkCheckBox(filters_frame, text="Hide Ignored", variable=hide_ignored_var, command=update_grid)
    chk_hide_ignored.pack(side="left", padx=10)

    search_var.trace_add("write", update_grid)

    def on_resize(event):
        # Calculate how many 190px wide cards can fit in the current frame width
        # (170px width + 10px padx on left + 10px padx on right = 190px)
        new_cols = max(1, event.width // 190)
        
        # Only re-layout if the number of columns actually changed
        if getattr(app, 'current_cols', 4) != new_cols:
            app.current_cols = new_cols
            
            # Reposition existing cards instantly without reloading images!
            for index, widget in enumerate(grid_frame.winfo_children()):
                # Skip the "No games found" label if it's the only thing on screen
                if isinstance(widget, ctk.CTkLabel) and widget.cget("text") == "No games found.":
                    continue
                    
                row = index // new_cols
                col = index % new_cols
                widget.grid(row=row, column=col, padx=10, pady=10)

    # Bind the resize event to the grid frame
    grid_frame.bind("<Configure>", on_resize, add="+")

    search_var.trace_add("write", update_grid)
    update_grid()

    # --- Hardware Listener Setup ---
    provisioner = CardScanProvisioner()
    monitor = CardMonitor()
    monitor.addObserver(provisioner)

    def check_for_tap():
        if provisioner.captured_uid:
            monitor.deleteObserver(provisioner)
            captured_uid.set(provisioner.captured_uid)
            
            # 1. Update UI to Assignment Phase
            status_label.configure(text="✅ Card Intercepted! Select a game from the grid:")
            uid_label.configure(text=f"UID: {provisioner.captured_uid}")
            
            # 2. Check config.toml for an existing assignment immediately after tap
            existing_cards = load_existing_cards(CONFIG_FILE_PATH)
            current_match = next((c for c in existing_cards if c.get("uid", "").upper() == provisioner.captured_uid), None)
            
            if current_match:
                existing_title_lbl.configure(text=f"📌 Currently Assigned:\n{current_match.get('name')}")
                
                game_id = current_match.get("cmd")
                img_path = COVERS_DIR_PATH / f"{game_id}.jpg"
                
                if not img_path.exists():
                    download_cover_art(game_id, current_match.get('name'), COVERS_DIR_PATH)
                    img_path = COVERS_DIR_PATH / f"{game_id}.jpg"
                
                if img_path.exists():
                    try:
                        pil_img = Image.open(img_path)
                        pil_img.thumbnail((80, 120)) 
                        # Size it slightly smaller than the standard grid cards
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(60, 90))
                        existing_img_lbl.configure(image=ctk_img, text="")
                        existing_img_lbl.image = ctk_img
                    except Exception:
                        existing_img_lbl.configure(image="", text="[Art Error]", width=60, height=90, fg_color="gray30")
                else:
                    existing_img_lbl.configure(image="", text="[No Art]", width=60, height=90, fg_color="gray30")
                    
            else:
                existing_title_lbl.configure(text="✨ Blank Tag")
                existing_img_lbl.configure(image="", text="")

            # 3. Just enable the buttons (grid is already drawn)
            enable_grid_buttons()
        else:
            app.after(500, check_for_tap)

    def enable_grid_buttons():
        for card_frame in grid_frame.winfo_children():
            if hasattr(card_frame, 'assign_btn'):
                card_frame.assign_btn.configure(state="normal")

    def commit_assignment(game):
        search_entry.pack_forget()
        grid_frame.pack_forget()
        existing_assignment_frame.place_forget() # Hide the corner frame during processing
        status_label.configure(text=f"⚙️ Provisioning {game['name']}...", text_color="orange")
        app.update()

        download_cover_art(game['id'], game['name'], COVERS_DIR_PATH)
        existing_cards = load_existing_cards(CONFIG_FILE_PATH)
        
        new_card_data = {
            "name": game['name'],
            "type": "Steam",
            "cmd": game['id'],
            "uid": captured_uid.get()
        }
        
        overwritten = False
        for idx, card in enumerate(existing_cards):
            if card.get("uid", "").upper() == captured_uid.get():
                existing_cards[idx] = new_card_data
                overwritten = True
                break
        
        if not overwritten:
            existing_cards.append(new_card_data)
            
        save_toml_config(CONFIG_FILE_PATH, existing_cards)
        
        status_label.configure(text="🎉 Card Provisioned Successfully!", text_color="#00FF00")
        app.after(2500, on_close)

    def ignore_game(game):
        append_to_ignore_list(game['id'], game['name'], IGNORE_FILE_PATH)
        update_grid() # Just refresh the grid, the filters will hide it
        if captured_uid.get(): enable_grid_buttons()

    def unignore_game(game):
        remove_from_ignore_list(game['id'], IGNORE_FILE_PATH)
        update_grid()
        if captured_uid.get(): enable_grid_buttons()

    def launch_art_editor(game):
        # Calculate where the cover art is located
        img_path = COVERS_DIR_PATH / f"{game['id']}.jpg"
        
        # Ensure the art is downloaded first if it somehow isn't
        if not img_path.exists():
            download_cover_art(game['id'], game['name'], COVERS_DIR_PATH)
            
        # Spin up the art_editor.py script in a separate process
        subprocess.Popen([
            sys.executable, "art_editor.py", 
            "--id", str(game['id']), 
            "--name", game['name'], 
            "--cover", str(img_path)
        ])

    def show_context_menu(event, game):
        popup = tk.Menu(app, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#C62828")
        
        ignored_games = load_ignored_games(IGNORE_FILE_PATH)
        if str(game['id']) in ignored_games:
            popup.add_command(label="✅ Un-Ignore Game", command=lambda: unignore_game(game))
        else:
            popup.add_command(label="🚫 Ignore Game", command=lambda: ignore_game(game))
            
        # Add a separator and the new Art Editor command
        popup.add_separator()
        popup.add_command(label="🎨 Create Card Art", command=lambda: launch_art_editor(game))
        
        try:
            popup.tk_popup(event.x_root, event.y_root)
        finally:
            popup.grab_release()

    def on_close():
        try: 
            monitor.deleteObserver(provisioner)
        except Exception: 
            pass
        app.quit()    # Stop the mainloop first
        app.destroy() # Then destroy the window

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.after(500, check_for_tap)
    app.mainloop()


if __name__ == "__main__":
    # Setup flag arguments
    parser = argparse.ArgumentParser(description="Provision NFC Cards for Steam Games.")
    parser.add_argument("--gui", action="store_true", help="Launch the graphical interface.")
    args = parser.parse_args()

    # Route based on the execution flag
    if args.gui:
        run_gui()
    else:
        run_cli()