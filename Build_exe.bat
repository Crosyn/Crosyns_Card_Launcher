@echo off
pyinstaller --noconfirm --onedir --noconsole --distpath "../" --name "Crosyns_Card_Launcher_Portable" --icon "assets/icon.ico" gui_launcher.py
xcopy assets ..\Crosyns_Card_Launcher_Portable\assets\
pause
