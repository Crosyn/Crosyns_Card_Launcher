# splash.py
import sys
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
splash_time_ms = 5000

def show_splash(image_name):
    root = tk.Tk()
    root.overrideredirect(True) # Removes window borders and title bar
    root.attributes("-topmost", True) # Keeps the splash above other windows

    # Locate the image in the card_covers directory
    image_path = Path("card_covers") / f"{image_name}.jpg" #[cite: 4]
    
    if image_path.exists():
        img = Image.open(image_path)
        # Resize if necessary while maintaining the vertical aspect ratio
        img.thumbnail((300, 450)) 
        photo = ImageTk.PhotoImage(img)
        
        label = tk.Label(root, image=photo, bg="black")
        label.image = photo 
        label.pack()

        # Center the borderless window on the screen
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (img.width // 2)
        y = (root.winfo_screenheight() // 2) - (img.height // 2)
        root.geometry(f"+{x}+{y}")

    # Destroy the splash screen after 3.5 seconds
    root.after(splash_time_ms, root.destroy)
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        show_splash(sys.argv[1])