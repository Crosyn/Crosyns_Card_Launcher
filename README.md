# Crosyns Card Launcher

Crosyns Card Launcher is a simple, lightweight system that allows you to program physical NFC cards to launch applications on your PC. Currently, it supports launching Steam games natively, but the architecture is designed to accommodate more program types in the future.

## Table of Contents
* [🚀 How it Works](#-how-it-works)
* [✨ Features](#-features)
* [🤖 AI Usage](#-ai-usage)
* [🏁 Getting Started](#-getting-started)
  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
  * [Initial Setup & Usage](#initial-setup--usage)
* [🎨 Creating Physical Card Art](#-creating-physical-card-art)
* [⚙️ Configuration Files (TOML Formats)](#️-configuration-files-toml-formats)
  * [`card_config.toml`](#card_configtoml)
  * [`box_art_config.toml`](#box_art_configtoml)
  * [`steam_ignore.toml`](#steam_ignoretoml)
* [❓ Frequently Asked Questions (FAQ)](#-frequently-asked-questions-faq)
* [🔮 Roadmap](#-roadmap)
* [🛠️ Troubleshooting](#️-troubleshooting)
* [🧲 Tested Hardware](#-tested-hardware)
* [📝 License](#-license)

## 🚀 How it Works

The barrier to entry for many NFC projects is the need to write specific data to the cards. Crosyns Card Launcher bypasses this completely. 

Under the hood, instead of parsing the full Answer To Reset (ATR) byte arrays to identify card parameters or writing complex NDEF payloads to the card's memory, the system simply transmits a standard PC/SC APDU command (`FF CA 00 00 00`) to retrieve the card's unique hardware UID. This raw data is then converted into a clean string representation of hexadecimal bytes separated by dashes (e.g., `04-83-D5-1E-46-02-89`). 

Because it only reads the UID, **any standard NFC reader (like the WCR330) and any unformatted NFC card or tag can be natively used**.

## ✨ Features
*   **UID-Based Launching:** No need to format or write data to your NFC cards.
*   **GUI and CLI Interfaces:** Manage your cards via a sleek CustomTkinter system tray app or a straightforward command-line interface.
*   **Card Provisioning:** Built-in tool to scan your installed Steam games and bind them to a card tap instantly.
*   **Splash Screens:** Displays customizable vertical cover art while your game boots.
*   **Integrated Art Editor:** Generate and crop personalized physical card art right from the app.

## 🤖 AI Usage

The development of this project was accelerated with the assistance of **Gemini 3.1 Pro**. Specifically, its advanced coding capabilities were utilized to generate much of the foundational UI code for the CustomTkinter interfaces, such as the Art Editor and the main Provisioning dashboard. 

While Gemini handled a significant portion of the boilerplate layout and UI structure, the core application logic, hardware monitoring implementation, and specific bug fixes were all hand-adjusted, reviewed, and manually tested to ensure seamless integration between the NFC reader and Steam.

Crosyn's Note: Yeah, I used A.I. to help with a large part of this project. if you follow the command line version of the code, I used A.I. to make it look prettier and give better messages. The idea on how to do all the stuff is mine (Crosyn's) though. I also hate doing UI programming because it is very labor intensive and I just don't have the knowledge to create the basic foundation, so A.I. has helped me a bit with that part, but I understand how it works and often adjust what is generated to suit my needs better. 80% Vibe coded, 20% Human Framework and Polish.

## 🏁 Getting Started

### Prerequisites
*   **Python:** Python 3.11 or higher is recommended to take advantage of native `tomllib` support[cite: 1, 3, 8].
*   **Hardware:** A PC/SC compliant USB NFC Reader (such as the WCR330)[cite: 8].
*   **Media:** Unformatted or formatted NFC cards, tags, or stickers.

### Installation
1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Crosyn/Crosyns_Card_Launcher.git](https://github.com/Crosyn/Crosyns_Card_Launcher.git)
    cd Crosyns_Card_Launcher
    ```
2.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Initial Setup & Usage
1.  **Connect your hardware:** Plug your NFC reader into an available USB port on your PC.
2.  **Start the Launcher:** Open the main graphical interface by running:
    ```bash
    python gui_launcher.py
    ```
    Or just double click run_gui.pyw
3.  **Provision your first card:** 
    *   Click the **Provision New Card** button in the launcher interface[cite: 6]. This will pause the background listener and open the provisioner[cite: 6].
    *   Tap a blank NFC card onto your reader[cite: 8].
    *   Select the Steam game you want to assign to the card from the visual grid and click **Assign**[cite: 8].
4.  **Tap to Play:** Once the provisioner closes, the system will automatically resume listening for cards[cite: 6]. With the app running (or minimized to your system tray), tap your newly provisioned card to the reader to launch your game!

## 🎨 Creating Physical Card Art

If you want your physical NFC cards to match your digital library, the launcher includes a built-in Art Editor to help you format images for printing[cite: 1]. 

1. **Open the Provisioner:** Launch the provisioning tool from the main menu or GUI[cite: 5, 6].
2. **Launch the Editor:** Right-click on any game in the visual grid and select **🎨 Create Card Art**[cite: 8].
3. **Design:** The editor allows you to overlay the official Steam capsule art onto custom backgrounds, adjust padding and border colors, and tweak the contrast or zoom to fit your style[cite: 1]. 
4. **Export:** Once you are happy with the layout, click **Export Final Image** to save a properly proportioned file (with optional 90-degree rotation) that you can print and apply to your physical cards[cite: 1].

## ⚙️ Configuration Files (TOML Formats)

The application relies on a few easily readable `.toml` files to manage mappings and settings.

### `card_config.toml`
This is the core mapping file that links your physical NFC cards to your games. It uses an array of tables format (`[[cards]]`). 

*   `name`: The display name of the application.
*   `type`: The platform or application type (currently `"Steam"`).
*   `cmd`: The launch command or ID. For Steam, this is the Steam AppID (e.g., `"1091500"` for Cyberpunk 2077).
*   `uid`: The exact hexadecimal UID string read from your NFC card.

**Example:**
```toml
[[cards]]
name = "Cyberpunk 2077"
type = "Steam"
cmd = "1091500"
uid = "04-83-D5-1E-46-02-89"
```

### `box_art_config.toml`
This file saves your layout preferences for the integrated Card Art Editor[cite: 1]. It stores everything from canvas dimensions to cropping parameters.

*   `background_image`: Path to the background asset[cite: 2].
*   `width` / `height`: The core canvas dimensions for your final output[cite: 1, 2].
*   `left_right_pad`, `top_pad`, `bottom_pad`: Inner padding values that push the game cover inward to create a border inset[cite: 1, 2].
*   `card_border_color` / `border_width`: Styling for the frame around the game cover[cite: 1, 2].
*   `crop_top`, `crop_bottom`, `crop_left`, `crop_right`: Art cropping coordinates[cite: 1, 2].
*   `bg_contrast` / `card_contrast`: Image contrast percentage (default 100)[cite: 1, 2].
*   `zoom`: Scale ratio for the game cover (default 100)[cite: 1, 2].
*   `rotate_90`: Boolean value to rotate the final image on export[cite: 1, 2].

**Example:**
```toml
background_image = "assets/default_background.png"
width = 200
height = 350
left_right_pad = 21
top_pad = 40
bottom_pad = 70
card_border_color = "#000000"
border_width = 2
crop_top = 0
crop_bottom = 0
crop_left = 0
crop_right = 0
bg_contrast = 125
card_contrast = 125
zoom = 100
rotate_90 = true
```

### `steam_ignore.toml`
This file is generated automatically when you hide specific apps (like test servers or software tools) from your Steam library in the provisioner[cite: 8].

*   `id`: The Steam AppID of the ignored game[cite: 8].
*   `name`: The name of the ignored game[cite: 8].

**Example:**
```toml
[[ignored]]
id = "1091500"
name = "Cyberpunk 2077"
```

## ❓ Frequently Asked Questions (FAQ)

**Do I need to format my NFC cards or write data to them?**
No, formatting or writing is completely unnecessary. The application bypasses the writable memory of the card entirely and sends a raw PC/SC command (`FF CA 00 00 00`) to read the card's unique, read-only hardware UID[cite: 3, 8]. Because of this, even locked, unformatted, or "read-only" tags will work perfectly.

**Why did my game fail to launch when I tapped a card?**
The launcher has a built-in safety check to prevent system lockups. Before executing a launch command, it checks the Windows Registry (`RunningAppId`) to see if a Steam game is already running[cite: 3]. If a game is active, the launch is blocked[cite: 3]. Close your current game and tap the card again.

**Why aren't my installed games showing up in the Provisioning menu?**
The provisioner locates games by finding your main Steam installation via the Windows Registry, and then reading your `libraryfolders.vdf` file to locate secondary installation drives[cite: 8]. It then scans those drives for `appmanifest_*.acf` files[cite: 8]. If your Steam installation is highly customized or registry keys are missing, it may fail to locate some secondary libraries.

**Can I hide games I don't want to see in the Provisioner?**
Yes. In the Provisioning GUI, right-click any game and select **🚫 Ignore Game**[cite: 8]. This will add the game to your `steam_ignore.toml` file so it won't clutter your grid in the future[cite: 8]. You can un-ignore games the same way if you change your mind[cite: 8].

**What happens if I accidentally assign a game to a card that is already in use?**
The system handles this gracefully. During provisioning, it checks the UID against your existing `card_config.toml`[cite: 8]. If it finds a match, it will simply update that specific entry with the new game's data rather than creating a duplicate or breaking the file[cite: 8].

## 🔮 Roadmap
Currently, Crosyns Card Launcher natively supports Steam integration. Future updates are planned to include:
*   Support for standalone `.exe` files and standard shortcuts.
*   Integrations for other launchers (Epic Games, GOG, etc.).
*   Support for emulation platforms.

## 🛠️ Troubleshooting
*   **My card isn't being detected:** Ensure your reader is PC/SC compliant and the drivers are installed. Try closing the app, replugging the reader, and restarting. In general it uses plug and play drivers though, but submit a bug and I'll see what I can do.
*   **Games aren't showing up in the Provisioner:** The system checks standard Steam library folders. If your Steam registry keys are missing or heavily modified, the scanner might miss your secondary drives.
*   **"A Steam game is currently running" error:** The launcher blocks overlapping launches to prevent system lockups. Close your active game before tapping a new card.

## 🧲 Tested Hardware
*   **NFC Reader:** WCR330 (Standard PC/SC compliant readers should all work natively).
*   **Cards/Tags:** Any unformatted 13.56MHz NFC tags (e.g., NTAG215, Mifare Classic 1K) will work since the system only reads the hardware UID.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.