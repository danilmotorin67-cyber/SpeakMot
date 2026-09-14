@echo off
REM Локальная сборка SpeakMotor.exe (запускать в активированном venv на Windows)
pip install -r requirements.txt
pip install pyinstaller==6.11.1 --upgrade pyinstaller-hooks-contrib
pyinstaller --noconfirm --onedir --windowed --name SpeakMotor ^
  --collect-all faster_whisper ^
  --collect-all ctranslate2 ^
  --collect-all tokenizers ^
  --collect-all av ^
  --collect-submodules av ^
  --hidden-import av._core ^
  --collect-all huggingface_hub ^
  main.py
echo.
echo Готово: dist\SpeakMotor\SpeakMotor.exe
pause
