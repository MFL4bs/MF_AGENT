"""
Gestión de perfiles y usuarios locales.
Estructura de profiles.json:
{
  "profiles": [
    {
      "id": "uuid",
      "name": "Mi Negocio",
      "users": [
        {"username": "admin", "password_hash": "sha256...", "role": "admin"},
        {"username": "vendedor1", "password_hash": "sha256...", "role": "vendedor"}
      ]
    }
  ]
}
"""
import json
import hashlib
import uuid
import sys
from pathlib import Path


def _data_root() -> Path:
    """Directorio persistente junto al .exe o al script en desarrollo."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "data"
    return Path(__file__).parent.parent / "data"


def _profiles_file() -> Path:
    return _data_root() / "profiles.json"


def _load() -> dict:
    f = _profiles_file()
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"profiles": []}


def _save(data: dict):
    f = _profiles_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── API pública ───────────────────────────────────────────────────────────────

def list_profiles() -> list[dict]:
    return _load()["profiles"]


def get_profile(profile_id: str) -> dict | None:
    return next((p for p in list_profiles() if p["id"] == profile_id), None)


def create_profile(name: str, admin_username: str, admin_password: str, profile_id: str = None) -> dict:
    print(f"[create_profile] INICIO name={name!r} admin={admin_username!r} profile_id_arg={profile_id!r}")
    data = _load()
    print(f"[create_profile] profiles.json actual: {[p['id'] for p in data['profiles']]}")
    # Usar el profile_id de la licencia si está disponible, sino generar uno
    if not profile_id:
        try:
            from lic_manager.license_manager import _load_local, _save_local
            local_lic = _load_local()
            print(f"[create_profile] local_lic={local_lic}")
            profile_id = local_lic.get("profile_id", "")
            print(f"[create_profile] profile_id desde licencia: {profile_id!r}")
            if not profile_id:
                # Key nueva sin profile_id — generar uno y guardarlo
                profile_id = str(uuid.uuid4())[:8]
                print(f"[create_profile] Generando nuevo profile_id: {profile_id!r}")
                _save_local(local_lic["key"], local_lic["device_id"], profile_id)
                # Actualizar en Firestore también
                try:
                    print(f"[create_profile] Actualizando profile_id en Firestore...")
                    from agent.firestore_sync import _get_data_app
                    from firebase_admin import firestore as _fs
                    _db = _fs.client(app=_get_data_app())
                    _db.collection("licenses").document(local_lic["key"]).update({"profile_id": profile_id})
                    print(f"[create_profile] Firestore actualizado OK")
                except Exception as e:
                    print(f"[create_profile] Error Firestore (ignorado): {e}")
        except Exception as e:
            print(f"[create_profile] Exception en bloque licencia: {e}")
            profile_id = str(uuid.uuid4())[:8]
            print(f"[create_profile] Fallback profile_id: {profile_id!r}")
    profile = {
        "id": profile_id,
        "name": name,
        "users": [
            {"username": admin_username, "password_hash": _hash(admin_password), "role": "admin"}
        ]
    }
    print(f"[create_profile] Guardando perfil id={profile_id!r}")
    data["profiles"].append(profile)
    _save(data)
    print(f"[create_profile] DONE — perfil guardado en {_profiles_file()}")
    return profile


def delete_profile(profile_id: str):
    data = _load()
    data["profiles"] = [p for p in data["profiles"] if p["id"] != profile_id]
    _save(data)
    import shutil
    profile_dir = _data_root() / profile_id
    if profile_dir.exists():
        shutil.rmtree(profile_dir)


def add_user(profile_id: str, username: str, password: str, role: str) -> bool:
    data = _load()
    for p in data["profiles"]:
        if p["id"] == profile_id:
            if any(u["username"] == username for u in p["users"]):
                return False
            p["users"].append({"username": username, "password_hash": _hash(password), "role": role})
            _save(data)
            return True
    return False


def delete_user(profile_id: str, username: str):
    data = _load()
    for p in data["profiles"]:
        if p["id"] == profile_id:
            p["users"] = [u for u in p["users"] if u["username"] != username]
    _save(data)


def authenticate(profile_id: str, username: str, password: str) -> dict | None:
    profile = get_profile(profile_id)
    if not profile:
        return None
    for u in profile["users"]:
        if u["username"] == username and u["password_hash"] == _hash(password):
            return {"username": username, "role": u["role"], "profile_id": profile_id}
    return None


def get_profile_data_dir(profile_id: str) -> Path:
    d = _data_root() / profile_id
    d.mkdir(parents=True, exist_ok=True)
    return d
