@echo off
echo ========================================
echo    COMPILADOR MF_AGENT
echo ========================================
echo.

REM Verificar si PyInstaller está instalado
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [ERROR] PyInstaller no esta instalado
    echo Instalando PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] No se pudo instalar PyInstaller
        pause
        exit /b 1
    )
)

echo [INFO] Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MF_AGENT.spec del /q MF_AGENT.spec

echo.
echo [INFO] Compilando MF_AGENT...
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
echo.
echo Presiona cualquier tecla para abrir la carpeta...
pause >nul
explorer dist

exit /b 0
