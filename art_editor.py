'''
This file is used to help desingn some art, it's not as fancy as some tools,
but it does the job so... meh.
'''
import sys
import os
import argparse
from pathlib import Path
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk, ImageChops, ImageDraw, ImageEnhance

try:
    import tomllib
except ImportError:
    import pip._vendor.tomli as tomllib

CONFIG_FILE = Path("box_art_config.toml")

class ArtEditor(ctk.CTk):
    def __init__(self, game_id, game_name, cover_path):
        super().__init__()

        self.game_id = game_id
        self.game_name = game_name
        self.cover_path = Path(cover_path)

        self.title(f"Card Art Editor - {self.game_name}")
        # Calculate screen center for provisioner
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = round(screen_width * 0.75)
        window_height = round(screen_height * 0.75)
        x_coord = int((screen_width / 2) - (window_width / 2))
        y_coord = int((screen_height / 2) - (window_height / 2))
        
        self.geometry(f"{window_width}x{window_height}+{x_coord}+{y_coord}")
        self.minsize(800, 550)
        ctk.set_appearance_mode("System")
        
        try:
            app_id = 'crosyns_card_launcher.cardedit.gui.1' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            
            # Load the original image
            img = Image.open("assets/icon.png").convert("RGBA")
            alpha = img.getchannel('A')
            grayscale_img = img.convert("L").convert("RGB")
            icon_color = "#77E000" 
            color_block = Image.new("RGB", img.size, icon_color)
            tinted_img = ImageChops.multiply(grayscale_img, color_block)
            tinted_img.putalpha(alpha)
            tinted_img.save("assets/icon.ico", format="ICO")
            self.iconbitmap("assets/icon.ico")
        except Exception as e:
            print(f"Icon error: {e}")
        
        # Default config fallback
        self.config = {
            "background_image": "assets/default_background.png",
            "width": 200,
            "height": 350,
            "left_right_pad": 21,
            "top_pad": 40,
            "bottom_pad": 70,
            "card_border_color": "#000000",
            "border_width": 2,
            "crop_top": 0,
            "crop_bottom": 0,
            "crop_left": 0,
            "crop_right": 0,
            "bg_contrast": 125,
            "card_contrast": 125,
            "zoom": 100,
            "rotate_90": True
        }
        self.load_config()

        # --- UI Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left Panel (Controls) - Scrollable Frame
        self.controls_frame = ctk.CTkScrollableFrame(self, width=320)
        self.controls_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(self.controls_frame, text="🎨 Editor Settings", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 20))

        # Background Picker
        self.bg_label = ctk.CTkLabel(self.controls_frame, text=f"BG: {Path(self.config['background_image']).name if self.config['background_image'] else 'None'}")
        self.bg_label.pack(pady=(5, 0))
        ctk.CTkButton(self.controls_frame, text="Choose Background", command=self.pick_background).pack(pady=(0, 15))

        # --- Canvas Settings ---
        ctk.CTkLabel(self.controls_frame, text="--- Dimensions ---", text_color="gray").pack(pady=(10, 0))
        self.width_var = ctk.IntVar(value=self.config["width"])
        self.add_control("Canvas Width", self.width_var, 100, 1000)

        self.height_var = ctk.IntVar(value=self.config["height"])
        self.add_control("Canvas Height", self.height_var, 100, 1000)

        self.lr_pad_var = ctk.IntVar(value=self.config["left_right_pad"])
        self.add_control("L/R Padding", self.lr_pad_var, 0, 200)

        self.top_pad_var = ctk.IntVar(value=self.config["top_pad"])
        self.add_control("Top Padding", self.top_pad_var, 0, 200)
        
        self.bot_pad_var = ctk.IntVar(value=self.config.get("bottom_pad", 15))
        self.add_control("Bottom Padding", self.bot_pad_var, 0, 200)
        
        self.rotate_var = ctk.BooleanVar(value=self.config.get("rotate_90", False))
        ctk.CTkCheckBox(self.controls_frame, text="Rotate Card 90° (Clockwise) on save", variable=self.rotate_var).pack(pady=(10, 5), padx=10, anchor="w")

        # --- Image Adjustments ---
        ctk.CTkLabel(self.controls_frame, text="--- Image Adjustments ---", text_color="gray").pack(pady=(15, 0))
        
        self.bg_contrast_var = ctk.IntVar(value=self.config.get("bg_contrast", 100))
        self.add_control("BG Contrast (%)", self.bg_contrast_var, 0, 300)

        self.card_contrast_var = ctk.IntVar(value=self.config.get("card_contrast", 100))
        self.add_control("Card Contrast (%)", self.card_contrast_var, 0, 300)

        self.zoom_var = ctk.IntVar(value=self.config.get("zoom", 100))
        self.add_control("Card Zoom (%)", self.zoom_var, 10, 400)

        # --- Art Cropping ---
        ctk.CTkLabel(self.controls_frame, text="--- Card Cropping ---", text_color="gray").pack(pady=(15, 0))
        self.crop_top_var = ctk.IntVar(value=self.config["crop_top"])
        self.add_control("Crop Top", self.crop_top_var, 0, 500)
        
        self.crop_bot_var = ctk.IntVar(value=self.config["crop_bottom"])
        self.add_control("Crop Bottom", self.crop_bot_var, 0, 500)
        
        self.crop_left_var = ctk.IntVar(value=self.config["crop_left"])
        self.add_control("Crop Left", self.crop_left_var, 0, 500)
        
        self.crop_right_var = ctk.IntVar(value=self.config["crop_right"])
        self.add_control("Crop Right", self.crop_right_var, 0, 500)

        # --- Border Settings ---
        ctk.CTkLabel(self.controls_frame, text="--- Border ---", text_color="gray").pack(pady=(15, 0))
        self.bw_var = ctk.IntVar(value=self.config["border_width"])
        self.add_control("Border Width", self.bw_var, 0, 30)

        ctk.CTkLabel(self.controls_frame, text="Border Color (Hex):").pack(pady=(5, 0))
        self.color_var = ctk.StringVar(value=self.config["card_border_color"])
        color_entry = ctk.CTkEntry(self.controls_frame, textvariable=self.color_var)
        color_entry.pack(pady=(0, 15))
        color_entry.bind("<KeyRelease>", lambda e: self.update_preview())

        # Action Buttons
        ctk.CTkButton(self.controls_frame, text="💾 Save Config", command=self.save_config, fg_color="#F39C12", hover_color="#D68910").pack(pady=(20, 5), fill="x", padx=10)
        ctk.CTkButton(self.controls_frame, text="🖼️ Export Final Image", command=self.export_image, fg_color="#27AE60", hover_color="#229954").pack(pady=5, fill="x", padx=10)

        # Right Panel (Preview)
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        self.preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(self.preview_frame, text="Loading preview...")
        self.preview_label.grid(row=0, column=0)

        # Bind the preview frame resize event so the image scales dynamically
        self.preview_frame.bind("<Configure>", self.render_preview)

        # Render initial preview
        self.current_composite = None
        self.update_preview()

    def add_control(self, label_text, variable, min_val, max_val):
        row_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        row_frame.pack(fill="x", padx=10, pady=(5, 0))
        
        lbl = ctk.CTkLabel(row_frame, text=label_text)
        lbl.pack(side="left")
        
        entry = ctk.CTkEntry(row_frame, textvariable=variable, width=60)
        entry.pack(side="right")
        
        def on_var_change(*args):
            try:
                val = variable.get()
                self.update_preview()
            except ValueError:
                pass

        variable.trace_add("write", on_var_change)

        slider = ctk.CTkSlider(self.controls_frame, from_=min_val, to=max_val, variable=variable)
        slider.pack(fill="x", padx=10, pady=(5, 10))

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "rb") as f:
                    data = tomllib.load(f)
                    self.config.update(data)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        toml_content = (
            f'background_image = "{self.config["background_image"].replace("\\", "\\\\")}"\n'
            f'width = {self.width_var.get()}\n'
            f'height = {self.height_var.get()}\n'
            f'left_right_pad = {self.lr_pad_var.get()}\n'
            f'top_pad = {self.top_pad_var.get()}\n'
            f'bottom_pad = {self.bot_pad_var.get()}\n'
            f'card_border_color = "{self.color_var.get()}"\n'
            f'border_width = {self.bw_var.get()}\n'
            f'crop_top = {self.crop_top_var.get()}\n'
            f'crop_bottom = {self.crop_bot_var.get()}\n'
            f'crop_left = {self.crop_left_var.get()}\n'
            f'crop_right = {self.crop_right_var.get()}\n'
            f'bg_contrast = {self.bg_contrast_var.get()}\n'
            f'card_contrast = {self.card_contrast_var.get()}\n'
            f'zoom = {self.zoom_var.get()}\n'
            f'rotate_90 = {str(self.rotate_var.get()).lower()}\n'
        )
        try:
            CONFIG_FILE.write_text(toml_content, encoding="utf-8")
            messagebox.showinfo("Success", "Configuration saved to box_art_config.toml")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")

    def pick_background(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if filepath:
            self.config["background_image"] = filepath
            self.bg_label.configure(text=f"BG: {Path(filepath).name}")
            self.update_preview()

    def update_preview(self):
        """Builds the full resolution composite image in memory."""
        try:
            # The core canvas dimensions (Total final output size)
            canvas_w = self.width_var.get()
            canvas_h = self.height_var.get()
            
            # The padding pushes the card INWARD, creating an inset
            lr_pad = self.lr_pad_var.get()
            t_pad = self.top_pad_var.get()
            b_pad = self.bot_pad_var.get()
            
            border_col = self.color_var.get()
            bw = self.bw_var.get()
            bg_contrast_val = self.bg_contrast_var.get() / 100.0
            card_contrast_val = self.card_contrast_var.get() / 100.0
            zoom_val = self.zoom_var.get() / 100.0

            # 1. Prepare Base Canvas (Background)
            if self.config["background_image"] and Path(self.config["background_image"]).exists():
                bg = Image.open(self.config["background_image"]).convert("RGBA")
                
                # --- Apply BG Contrast ---
                if bg_contrast_val != 1.0:
                    enhancer = ImageEnhance.Contrast(bg)
                    bg = enhancer.enhance(bg_contrast_val)
                    
                bg = bg.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
            else:
                bg = Image.new("RGBA", (canvas_w, canvas_h), (40, 40, 40, 255))

            # 2. Prepare Game Cover overlay
            if self.cover_path.exists():
                cover = Image.open(self.cover_path).convert("RGBA")
                
                # --- Apply Card Contrast ---
                if card_contrast_val != 1.0:
                    enhancer = ImageEnhance.Contrast(cover)
                    cover = enhancer.enhance(card_contrast_val)
                
                orig_w, orig_h = cover.size
                
                # --- A. Frame Boundaries (Inset by padding) ---
                # Use max(1) to prevent crashing if padding overlaps entirely
                target_cover_w = max(1, canvas_w - (lr_pad * 2))
                target_cover_h = max(1, canvas_h - t_pad - b_pad)
                
                # --- B. Calculate Scale Ratio including Zoom Factor ---
                base_ratio = min(target_cover_w / orig_w, target_cover_h / orig_h)
                ratio = base_ratio * zoom_val
                
                new_w = max(1, int(orig_w * ratio))
                new_h = max(1, int(orig_h * ratio))
                
                # --- C. Scale the Cover Image BEFORE Cropping ---
                scaled_cover = cover.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # --- D. Calculate the crops relative to the Original Image ---
                c_left = min(max(0, self.crop_left_var.get()), orig_w - 1)
                c_right = min(max(0, self.crop_right_var.get()), orig_w - c_left - 1)
                c_top = min(max(0, self.crop_top_var.get()), orig_h - 1)
                c_bottom = min(max(0, self.crop_bot_var.get()), orig_h - c_top - 1)
                
                # Convert original crop sizes to scaled crop sizes
                s_left = int(c_left * ratio)
                s_right = int(c_right * ratio)
                s_top = int(c_top * ratio)
                s_bot = int(c_bottom * ratio)
                
                # --- E. Crop the Scaled Cover ---
                if s_left > 0 or s_right > 0 or s_top > 0 or s_bot > 0:
                    # Constrain to prevent crashing from rounding errors
                    s_right = min(s_right, new_w - s_left - 1)
                    s_bot = min(s_bot, new_h - s_top - 1)
                    cropped_cover = scaled_cover.crop((s_left, s_top, new_w - s_right, new_h - s_bot))
                else:
                    cropped_cover = scaled_cover

                # --- F. Assemble the Fixed Frame Layer (Clipping Mask) ---
                frame_layer = Image.new("RGBA", (target_cover_w, target_cover_h), (0, 0, 0, 0))
                
                # Calculate center placement for the cover INSIDE the fixed frame layer
                paste_x = (target_cover_w - cropped_cover.width) // 2
                paste_y = (target_cover_h - cropped_cover.height) // 2
                
                frame_layer.paste(cropped_cover, (paste_x, paste_y))
                
                # Draw the fixed border perfectly along the edge of the frame layer
                if bw > 0:
                    draw = ImageDraw.Draw(frame_layer)
                    draw.rectangle([0, 0, target_cover_w - 1, target_cover_h - 1], outline=border_col, width=bw)
                
                # --- G. Paste Frame Layer onto Background ---
                bg.paste(frame_layer, (lr_pad, t_pad), frame_layer)

            self.current_composite = bg

            # 3. Request a dynamic UI render
            self.render_preview()

        except Exception as e:
            self.preview_label.configure(text=f"Error rendering preview:\n{e}", image="")

    def render_preview(self, event=None):
        """Scales the high-res composite to perfectly fit the available UI space."""
        if not self.current_composite:
            return
            
        # Dynamically check available space
        frame_w = self.preview_frame.winfo_width()
        frame_h = self.preview_frame.winfo_height()
        
        # Fallback dimensions if the window hasn't drawn itself yet
        if frame_w < 50 or frame_h < 50:
            frame_w, frame_h = 800, 800
            
        # Add a slight padding cushion to keep it off the literal edge
        target_w = max(10, frame_w - 40)
        target_h = max(10, frame_h - 40)

        # Scale down a copy of the high-res composite for display
        display_img = self.current_composite.copy()
        display_img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        
        ctk_img = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=display_img.size)
        self.preview_label.configure(image=ctk_img, text="")
        self.preview_label.image = ctk_img

    def export_image(self):
        if not self.current_composite:
            return
        # --- Apply Final Rotation ---
        if self.rotate_var.get():
            # Transpose is lossless and flips 90 degrees clockwise (ROTATE_270)
            self.current_composite = self.current_composite.transpose(Image.Transpose.ROTATE_270)
            
        suggested_name = f"{self.game_id}_art.png"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=suggested_name,
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")]
        )
        if filepath:
            try:
                if filepath.lower().endswith(".jpg") or filepath.lower().endswith(".jpeg"):
                    export_img = self.current_composite.convert("RGB")
                else:
                    export_img = self.current_composite
                    
                export_img.save(filepath)
                messagebox.showinfo("Success", f"Image saved successfully to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="Game App ID")
    parser.add_argument("--name", required=True, help="Game Name")
    parser.add_argument("--cover", required=True, help="Path to cached cover image")
    args = parser.parse_args()

    app = ArtEditor(args.id, args.name, args.cover)
    app.mainloop()