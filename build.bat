@echo off
python -m pip install -r requirements.txt
python -m PyInstaller main.spec
if %ERRORLEVEL% equ 0 (
  echo Build completed successfully.
  echo Output executable is in dist\Captions.exe
) else (
  echo Build failed.
)
