"""
Script para compilar MF_AGENT a ejecutable usando PyInstaller
Uso: python build.py
"""
import os
import subprocess
import sys

def build_executable():
    print("🚀 Compilando MF_AGENT...")
    print("=" * 60)
    
    # Comando PyInstaller
    cmd = [
        "pyinstaller",
        "--name=MF_AGENT",
        "--onefile",  # Un solo archivo ejecutable
        "--windowed",  # Sin consola
        "--icon=MF_LABS.png",  # Icono (opcional)
        
        # Agregar archivos de datos
        "--add-data=MF_LABS.png;.",
        "--add-data=.env.example;.",
        "--add-data=manuales;manuales",
        "--add-data=agent;agent",
        "--add-data=models;models",
        "--add-data=whatsapp_bridge;whatsapp_bridge",
        
        # Módulos ocultos que PyInstaller no detecta automáticamente
        "--hidden-import=PyQt6.QtWebEngineWidgets",
        "--hidden-import=PyQt6.QtWebEngineCore",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=reportlab.pdfbase._fontdata",
        "--hidden-import=reportlab.graphics.barcode",
        
        # Excluir módulos innecesarios para reducir tamaño
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=scipy",
        "--exclude-module=PIL",
        
        # Archivo principal
        "app.py"
    ]
    
    try:
        # Ejecutar PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        print("\n" + "=" * 60)
        print("✅ Compilación exitosa!")
        print(f"📦 Ejecutable creado en: dist/MF_AGENT.exe")
        print("=" * 60)
        
    except subprocess.CalledProcessError as e:
        print("\n❌ Error durante la compilación:")
        print(e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌ PyInstaller no está instalado.")
        print("Instálalo con: pip install pyinstaller")
        sys.exit(1)

if __name__ == "__main__":
    build_executable()
