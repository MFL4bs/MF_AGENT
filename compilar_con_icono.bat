@echo off
echo ========================================
echo    COMPILADOR MF_AGENT CON ICONO
echo ========================================
echo.

REM Verificar si Pillow está instalado
python -c "import PIL" 2>nul
if errorlevel 1 (
    echo [INFO] Instalando Pillow para crear icono...
    pip install Pillow
)

REM Crear icono .ico desde PNG
echo [INFO] Creando icono MF_LABS.ico...
python create_icon.py
if errorlevel 1 (
    echo [WARNING] No se pudo crear el icono, continuando sin el...
)

echo.
echo [INFO] Verificando PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [INFO] Instalando PyInstaller...
    pip install pyinstaller
)

echo.
echo [INFO] Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MF_AGENT.spec del /q MF_AGENT.spec

echo.
echo [INFO] Compilando MF_AGENT con icono...
echo.

pyinstaller --name=MF_AGENT ^
    --onefile ^
    --windowed ^
    --icon=MF_LABS.ico ^
    --add-data="MF_LABS.png;." ^
    --add-data="MF_LABS.ico;." ^
    --add-data=".env.example;." ^
    --add-data="manuales;manuales" ^
    --add-data="agent;agent" ^
    --add-data="models;models" ^
    --add-data="whatsapp_bridge;whatsapp_bridge" ^
    --add-data="login.py;." ^
    --add-data="main.py;." ^
    --add-data="config.py;." ^
    --add-data="splash.py;." ^
    --hidden-import=PyQt6.QtWebEngineWidgets ^
    --hidden-import=PyQt6.QtWebEngineCore ^
    --hidden-import=uvicorn.logging ^
    --hidden-import=uvicorn.loops.auto ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=uvicorn.protocols.websockets.auto ^
    --hidden-import=uvicorn.lifespan.on ^
    --hidden-import=reportlab.pdfbase._fontdata ^
    --exclude-module=matplotlib ^
    --exclude-module=numpy ^
    --exclude-module=pandas ^
    app.py

if errorlevel 1 (
    echo.
    echo [ERROR] La compilacion fallo
    pause
    exit /b 1
)

echo.
echo ========================================
echo    COMPILACION EXITOSA!
echo ========================================
echo.
echo Ejecutable creado en: dist\MF_AGENT.exe
echo Con icono MF Labs en:
echo   - Ejecutable (.exe)
echo   - Ventana de la aplicacion
echo   - Barra de tareas
echo.
echo Presiona cualquier tecla para abrir la carpeta...
pause >nul
explorer dist

exit /b 0
