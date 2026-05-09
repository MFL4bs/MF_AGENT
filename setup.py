"""
Setup script para compilar MF_AGENT a ejecutable
Uso: python setup.py build
"""
import sys
from cx_Freeze import setup, Executable

# Dependencias que deben incluirse
build_exe_options = {
    "packages": [
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui", 
        "PyQt6.QtWidgets",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineCore",
        "uvicorn",
        "fastapi",
        "pydantic",
        "boto3",
        "reportlab",
        "pathlib",
        "threading",
        "json",
        "os",
        "sys",
    ],
    "include_files": [
        ("MF_LABS.png", "MF_LABS.png"),
        (".env.example", ".env.example"),
        ("manuales/", "manuales/"),
        ("agent/", "agent/"),
        ("models/", "models/"),
        ("whatsapp_bridge/", "whatsapp_bridge/"),
        ("data/", "data/"),
    ],
    "excludes": [
        "tkinter",
        "unittest",
        "email",
        "http",
        "xml",
        "pydoc",
    ],
}

# Configuración base
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # Oculta la consola en Windows

setup(
    name="MF_AGENT",
    version="1.0.0",
    description="Sistema Inteligente de Chat para Leads",
    author="MF Labs",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "app.py",
            base=base,
            target_name="MF_AGENT.exe",
            icon=None,  # Puedes agregar un .ico aquí
        )
    ],
)
