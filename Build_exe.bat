@echo off
pyinstaller --noconfirm --onedir --noconsole --distpath "../" --name "Crosyns_Card_Launcher_Portable" --icon "assets/icon.ico" --version-file "version.txt" gui_launcher.py
xcopy assets ..\Crosyns_Card_Launcher_Portable\assets\
rmdir /s /q "build"
pause
