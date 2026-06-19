"""
build.py — Compila MF_AGENT (inventario) y MF_KeyManager por separado
Uso:
    python build.py          -> compila ambos
    python build.py app      -> solo inventario
    python build.py keys     -> solo key manager
"""
import subprocess
import sys

BASE_DATA = [
    "--add-data=MF_LABS.png;.",
    "--add-data=MF_LABS.ico;.",
    "--add-data=mf-agent-2b482-firebase-adminsdk-fbsvc-937c5dc694.json;.",
    "--add-data=lic_manager;lic_manager",
]

HIDDEN_FIREBASE = [
    "--hidden-import=firebase_admin",
    "--hidden-import=google.cloud.firestore",
    "--hidden-import=google.auth",
    "--hidden-import=google.oauth2.service_account",
]

HIDDEN_UVICORN = [
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
]

EXCLUDES = [
    "--exclude-module=matplotlib",
    "--exclude-module=numpy",
    "--exclude-module=pandas",
    "--exclude-module=scipy",
]


def build_app():
    print("\n" + "=" * 60)
    print("  Compilando MF_AGENT (Inventario)...")
    print("=" * 60)

    cmd = [
        "pyinstaller",
        "--name=MF_AGENT",
        "--onefile",
        "--windowed",
        "--icon=MF_LABS.ico",
        *BASE_DATA,
        "--add-data=.env.example;.",
        "--add-data=manuales;manuales",
        "--add-data=agent;agent",
        "--add-data=models;models",
        "--add-data=whatsapp_bridge;whatsapp_bridge",
        "--hidden-import=PyQt6.QtWebEngineWidgets",
        "--hidden-import=PyQt6.QtWebEngineCore",
        "--hidden-import=reportlab.pdfbase._fontdata",
        "--hidden-import=reportlab.graphics.barcode",
        *HIDDEN_UVICORN,
        *HIDDEN_FIREBASE,
        *EXCLUDES,
        "app.py",
    ]

    _run(cmd, "dist/MF_AGENT.exe")


def build_keys():
    print("\n" + "=" * 60)
    print("  Compilando MF_KeyManager (Panel de Licencias)...")
    print("=" * 60)

    cmd = [
        "pyinstaller",
        "--name=MF_KeyManager",
        "--onefile",
        "--windowed",
        "--icon=MF_LABS.ico",
        *BASE_DATA,
        *HIDDEN_FIREBASE,
        *EXCLUDES,
        "--exclude-module=uvicorn",
        "--exclude-module=fastapi",
        "--exclude-module=boto3",
        "--exclude-module=reportlab",
        "lic_manager/key_panel.py",
    ]

    _run(cmd, "dist/MF_KeyManager.exe")


def _run(cmd: list, output: str):
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        print(f"\n✅  Listo: {output}")
    except subprocess.CalledProcessError as e:
        print("\n❌  Error durante la compilación:")
        print(e.stderr[-3000:] if len(e.stderr) > 3000 else e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌  PyInstaller no está instalado.")
        print("Instálalo con: pip install pyinstaller")
        sys.exit(1)


if __name__ == "__main__":
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "both"

    if target == "app":
        build_app()
    elif target == "keys":
        build_keys()
    else:
        build_app()
        build_keys()
        print("\n" + "=" * 60)
        print("  Ambos ejecutables compilados en dist/")
        print("  MF_AGENT.exe      -> App de inventario")
        print("  MF_KeyManager.exe -> Panel de licencias")
        print("=" * 60)
