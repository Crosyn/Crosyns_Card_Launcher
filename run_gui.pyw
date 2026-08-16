import subprocess

# Runs your standard script completely hidden in the background
subprocess.Popen(["python", "gui_launcher.py"], creationflags=subprocess.CREATE_NO_WINDOW)