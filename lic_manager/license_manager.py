"""
license_manager.py
Valida la licencia contra Firebase al iniciar la app.
"""
import uuid
import hashlib
import hmac
import platform
import json
from datetime import datetime, timezone
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

# Clave secreta para firmar el .license — nunca la compartas
_SECRET = b"MF-4g9zK2#pL8mXqR5vN1wJ7cT0bY6hD"

CRED_FILE = "mf-agent-2b482-firebase-adminsdk-fbsvc-937c5dc694.json"
WARN_DAYS = 7


def _base_path() -> Path:
    """Ruta base compatible con PyInstaller y ejecución normal."""
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def _exe_dir() -> Path:
    """Directorio donde vive el .exe (o el script en desarrollo)."""
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


CRED_PATH    = _base_path() / CRED_FILE
LICENSE_FILE = _exe_dir() / ".license"

_db = None

def _get_db():
    global _db
    if _db is None:
        if not firebase_admin._apps:
            cred = credentials.Certificate(str(CRED_PATH))
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db


def _get_ip() -> str:
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "desconocida"


def get_hardware_id() -> str:
    raw = f"{platform.node()}-{platform.machine()}-{uuid.getnode()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _sign(data: dict) -> str:
    """Genera firma HMAC del contenido del .license."""
    payload = f"{data['key']}:{data['device_id']}".encode()
    return hmac.new(_SECRET, payload, hashlib.sha256).hexdigest()


def _save_local(key: str, device_id: str, profile_id: str):
    data = {"key": key, "device_id": device_id, "profile_id": profile_id}
    data["sig"] = _sign(data)
    LICENSE_FILE.write_text(json.dumps(data), encoding="utf-8")


def _load_local() -> dict:
    if LICENSE_FILE.exists():
        try:
            data = json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
            # Verificar firma — si fue alterado o copiado de otro PC, falla
            expected = _sign(data)
            if not hmac.compare_digest(data.get("sig", ""), expected):
                return {}
            return data
        except Exception:
            pass
    return {}


def activate(key: str) -> dict:
    """
    Activa la key en este dispositivo.
    Retorna {"ok": bool, "msg": str, "days_left": int|None}
    """
    db = _get_db()
    device_id = get_hardware_id()

    lic_ref = db.collection("licenses").document(key)
    lic = lic_ref.get()

    if not lic.exists:
        return {"ok": False, "msg": "Key inválida."}

    data = lic.to_dict()

    if not data.get("active", False):
        return {"ok": False, "msg": "Key desactivada."}

    # Verificar expiración
    days_left = None
    expires_at = data.get("expires_at")
    if expires_at and expires_at != "never":
        exp = datetime.fromisoformat(expires_at).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if now > exp:
            return {"ok": False, "msg": "Key vencida."}
        days_left = (exp - now).days

    # Verificar dispositivos registrados
    devices_ref = db.collection("devices")
    existing = list(devices_ref.where("key_id", "==", key).stream())
    device_ids = [d.to_dict().get("device_id") for d in existing]

    lic_type = data.get("type")  # individual | multi | permanente
    max_devices = data.get("max_devices", 1)
    platform_allowed = data.get("platform", "pc")  # pc | mobile | both

    # Verificar plataforma
    if platform_allowed == "mobile":
        return {"ok": False, "msg": "Esta key es solo para dispositivos móviles."}

    # Si ya está registrado este dispositivo, permitir
    if device_id in device_ids:
        _save_local(key, device_id, data.get("profile_id", ""))
        return {"ok": True, "msg": "Licencia válida.", "days_left": days_left, "type": lic_type, "profile_id": data.get("profile_id", "")}

    # Verificar límite de dispositivos
    if len(device_ids) >= max_devices:
        return {
            "ok": False,
            "msg": f"Límite de dispositivos alcanzado ({max_devices}). Contacta al administrador para reemplazar un dispositivo."
        }

    # Registrar nuevo dispositivo
    devices_ref.document(device_id).set({
        "device_id": device_id,
        "key_id": key,
        "platform": "pc",
        "hostname": platform.node(),
        "ip": _get_ip(),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
    })

    _save_local(key, device_id, data.get("profile_id", ""))
    return {"ok": True, "msg": "Licencia activada correctamente.", "days_left": days_left, "type": lic_type, "profile_id": data.get("profile_id", "")}


def validate() -> dict:
    """
    Valida la licencia guardada localmente contra Firebase.
    Retorna {"ok": bool, "msg": str, "days_left": int|None, "warn": bool}
    """
    local = _load_local()
    if not local:
        return {"ok": False, "msg": "No hay licencia activada."}

    key = local.get("key")
    device_id = local.get("device_id")

    if get_hardware_id() != device_id:
        return {"ok": False, "msg": "Licencia no válida para este equipo."}

    try:
        db = _get_db()
        lic = db.collection("licenses").document(key).get()
        if not lic.exists:
            return {"ok": False, "msg": "Key no encontrada."}

        data = lic.to_dict()
        if not data.get("active", False):
            return {"ok": False, "msg": "Licencia revocada."}

        days_left = None
        warn = False
        expires_at = data.get("expires_at")
        if expires_at and expires_at != "never":
            exp = datetime.fromisoformat(expires_at).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if now > exp:
                return {"ok": False, "msg": "Licencia vencida. Renueva tu plan."}
            days_left = (exp - now).days
            warn = days_left <= WARN_DAYS

        # Actualizar last_seen
        db.collection("devices").document(device_id).update({
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "ip": _get_ip(),
        })

        return {"ok": True, "msg": "Licencia válida.", "days_left": days_left, "warn": warn, "type": data.get("type"), "profile_id": local.get("profile_id", "")}

    except Exception as e:
        return {"ok": False, "msg": f"Error al validar licencia: {e}"}
