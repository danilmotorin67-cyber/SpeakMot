@echo off
REM Сборка SpeakMot.exe (запускать в активированном venv)
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --name SpeakMot ^
  --collect-all faster_whisper ^
  --collect-all ctranslate2 ^
  --collect-all tokenizers ^
  --hidden-import pystray._win32 ^
  main.py
echo.
echo Готово: dist\SpeakMot\SpeakMot.exe
pause
