@echo off
setlocal

set JAVA_HOME=C:\Program Files\Java\jdk-21.0.11
set MVN=D:\Aplicaciones\maven\apache-maven-3.9.6\bin\mvn.cmd
set JPACKAGE=%JAVA_HOME%\bin\jpackage.exe
set M2=%USERPROFILE%\.m2\repository\org\openjfx
set FX_VER=21.0.2
set FX_MODS=%M2%\javafx-controls\%FX_VER%\javafx-controls-%FX_VER%-win.jar;%M2%\javafx-fxml\%FX_VER%\javafx-fxml-%FX_VER%-win.jar;%M2%\javafx-base\%FX_VER%\javafx-base-%FX_VER%-win.jar;%M2%\javafx-graphics\%FX_VER%\javafx-graphics-%FX_VER%-win.jar
set JAR=target\mf-agent-desktop-1.0.0.jar
set DIST=..\dist\dastock_java

echo [1/3] Compilando...
call "%MVN%" clean package -q
if errorlevel 1 ( echo ERROR en compilacion & exit /b 1 )

echo [2/3] Generando EXE...
if exist "%DIST%\MF_AGENT" rmdir /s /q "%DIST%\MF_AGENT"

"%JPACKAGE%" ^
  --type app-image ^
  --name MF_AGENT ^
  --app-version 1.0.0 ^
  --input target ^
  --main-jar mf-agent-desktop-1.0.0.jar ^
  --main-class com.mfagent.App ^
  --java-options "--module-path app\javafx-mods --add-modules javafx.controls,javafx.fxml,javafx.base,javafx.graphics" ^
  --dest "%DIST%" ^
  --icon ..\MF_LABS.ico

if errorlevel 1 ( echo ERROR en jpackage & exit /b 1 )

echo Copiando modulos JavaFX al runtime...
mkdir "%DIST%\MF_AGENT\app\javafx-mods" 2>nul
for %%F in ("%M2%\javafx-controls\%FX_VER%\javafx-controls-%FX_VER%-win.jar" "%M2%\javafx-fxml\%FX_VER%\javafx-fxml-%FX_VER%-win.jar" "%M2%\javafx-base\%FX_VER%\javafx-base-%FX_VER%-win.jar" "%M2%\javafx-graphics\%FX_VER%\javafx-graphics-%FX_VER%-win.jar") do (
    copy "%%F" "%DIST%\MF_AGENT\app\javafx-mods\" >nul
)

echo Copiando archivos necesarios...
copy ".\..\mf-agent-2b482-firebase-adminsdk-fbsvc-3eff30e990.json" "%DIST%\MF_AGENT\" >nul
copy ".\..\mf-agent-2b482-firebase-adminsdk-fbsvc-937c5dc694.json" "%DIST%\MF_AGENT\" >nul
if exist "..\..env" copy "..\..env" "%DIST%\MF_AGENT\" >nul
if exist "..\.license" copy "..\.license" "%DIST%\MF_AGENT\" >nul
if exist "..\MF_LABS.ico" copy "..\MF_LABS.ico" "%DIST%\MF_AGENT\" >nul
if exist "..\MF_LABS.png" copy "..\MF_LABS.png" "%DIST%\MF_AGENT\" >nul
if exist "..\data" xcopy /e /i /q "..\data" "%DIST%\MF_AGENT\data\"
if exist "..\whatsapp_bridge" xcopy /e /i /q "..\whatsapp_bridge" "%DIST%\MF_AGENT\whatsapp_bridge\"

echo.
echo LISTO: %DIST%\MF_AGENT\MF_AGENT.exe
