"""
Inventario local por perfil (sin DynamoDB).
"""
import json
import uuid
from pathlib import Path
from agent.profiles import get_profile_data_dir


def _inv_file(profile_id: str) -> Path:
    return get_profile_data_dir(profile_id) / "inventory.json"


def _load(profile_id: str) -> list:
    f = _inv_file(profile_id)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def _save(profile_id: str, items: list):
    _inv_file(profile_id).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def list_products(profile_id: str) -> list[dict]:
    return sorted(_load(profile_id), key=lambda x: x.get("name", ""))


def get_product(profile_id: str, sku: str) -> dict | None:
    return next((p for p in _load(profile_id) if p["sku"] == sku), None)


def upsert_product(profile_id: str, product: dict):
    items = _load(profile_id)
    items = [p for p in items if p["sku"] != product["sku"]]
    items.append(product)
    _save(profile_id, items)


def update_product(profile_id: str, sku: str, updates: dict) -> dict | None:
    items = _load(profile_id)
    for p in items:
        if p["sku"] == sku:
            p.update({k: v for k, v in updates.items() if v is not None})
            _save(profile_id, items)
            return p
    return None


def delete_product(profile_id: str, sku: str):
    items = [p for p in _load(profile_id) if p["sku"] != sku]
    _save(profile_id, items)


def low_stock_products(profile_id: str, threshold: int = 15) -> list[dict]:
    return [p for p in _load(profile_id) if 0 < int(p.get("stock", 0)) <= threshold]


def next_sku(profile_id: str) -> str:
    if not profile_id:
        return "PROD-0001"
    items = _load(profile_id)
    nums = [int(p["sku"][5:]) for p in items if p.get("sku", "").startswith("PROD-") and p["sku"][5:].isdigit()]
    return f"PROD-{(max(nums) + 1 if nums else 1):04d}"
