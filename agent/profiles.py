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
from pathlib import Path

PROFILES_FILE = Path(__file__).parent.parent / "data" / "profiles.json"


def _load() -> dict:
    if PROFILES_FILE.exists():
        return json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    return {"profiles": []}


def _save(data: dict):
    PROFILES_FILE.parent.mkdir(exist_ok=True)
    PROFILES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── API pública ───────────────────────────────────────────────────────────────

def list_profiles() -> list[dict]:
    return _load()["profiles"]


def get_profile(profile_id: str) -> dict | None:
    return next((p for p in list_profiles() if p["id"] == profile_id), None)


def create_profile(name: str, admin_username: str, admin_password: str) -> dict:
    data = _load()
    profile = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "users": [
            {"username": admin_username, "password_hash": _hash(admin_password), "role": "admin"}
        ]
    }
    data["profiles"].append(profile)
    _save(data)
    return profile


def delete_profile(profile_id: str):
    data = _load()
    data["profiles"] = [p for p in data["profiles"] if p["id"] != profile_id]
    _save(data)
    # Borrar datos del perfil
    import shutil
    profile_dir = Path(__file__).parent.parent / "data" / profile_id
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
    d = Path(__file__).parent.parent / "data" / profile_id
    d.mkdir(parents=True, exist_ok=True)
    return d
