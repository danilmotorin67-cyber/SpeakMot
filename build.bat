@echo off
REM Локальная сборка SpeakMot.exe (запускать в активированном venv на Windows)
pip install -r requirements.txt
pip install pyinstaller==6.11.1
pyinstaller --noconfirm --onedir --windowed --name SpeakMot ^
  --collect-all faster_whisper ^
  --collect-all ctranslate2 ^
  --collect-all tokenizers ^
  --collect-all av ^
  main.py
echo.
echo Готово: dist\SpeakMot\SpeakMot.exe
pause
