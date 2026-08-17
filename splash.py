# splash.py
import sys
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk

splash_time_ms = 5000

def show_splash(image_name, display_name):
    root = tk.Tk()
    root.overrideredirect(True) # Removes window borders and title bar
    root.attributes("-topmost", True) # Keeps the splash above other windows
    root.configure(bg="black") # Ensure the base window is black

    # Locate the image in the card_covers directory
    image_path = Path("card_covers") / f"{image_name}.jpg"

    # Default fallback dimensions
    box_width = 300
    box_height = 450
    
    if image_path.exists():
        img = Image.open(image_path)
        # Resize if necessary while maintaining the vertical aspect ratio
        img.thumbnail((300, 450)) 
        photo = ImageTk.PhotoImage(img)
        
        label = tk.Label(root, image=photo, bg="black")
        label.image = photo 
        label.pack()
        
        # Update dimensions to match the loaded image for exact centering
        box_width = img.width
        box_height = img.height
    else:
        # Fallback text if the image is missing
        label = tk.Label(
            root, 
            text=f"Launching:\n{display_name}", 
            fg="white", 
            bg="black", 
            font=("Arial", 16, "bold"),
            wraplength=280,
            justify="center"
        )
        # Expand to fill the default 300x450 size
        label.pack(expand=True, fill="both")
        root.geometry(f"{box_width}x{box_height}")

    # Center the borderless window on the screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (box_width // 2)
    y = (root.winfo_screenheight() // 2) - (box_height // 2)
    root.geometry(f"+{x}+{y}")

    # Destroy the splash screen after the timer finishes
    root.after(splash_time_ms, root.destroy)
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd_id = sys.argv[1]
        # Grab the game name if provided, otherwise fallback to the ID
        game_name = sys.argv[2] if len(sys.argv) > 2 else f"AppID: {cmd_id}"
        show_splash(cmd_id, game_name)