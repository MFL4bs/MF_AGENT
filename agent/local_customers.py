"""
Base de datos de clientes local por perfil.
"""
import json
from pathlib import Path
from agent.profiles import get_profile_data_dir


def _customers_file(profile_id: str) -> Path:
    return get_profile_data_dir(profile_id) / "customers.json"


def _load(profile_id: str) -> list:
    f = _customers_file(profile_id)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def _save(profile_id: str, customers: list):
    _customers_file(profile_id).write_text(
        json.dumps(customers, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_customers(profile_id: str) -> list[dict]:
    return sorted(_load(profile_id), key=lambda x: x.get("name", "").lower())


def get_customer(profile_id: str, customer_id: str) -> dict | None:
    return next((c for c in _load(profile_id) if c.get("id") == customer_id), None)


def search_customers(profile_id: str, query: str) -> list[dict]:
    q = query.lower()
    return [
        c for c in _load(profile_id)
        if q in c.get("name", "").lower()
        or q in c.get("phone", "").lower()
        or q in c.get("email", "").lower()
    ]


def upsert_customer(profile_id: str, customer: dict) -> dict:
    customers = _load(profile_id)
    if not customer.get("id"):
        import uuid
        customer["id"] = str(uuid.uuid4())[:8]
    customers = [c for c in customers if c.get("id") != customer["id"]]
    customers.append(customer)
    _save(profile_id, customers)
    return customer


def delete_customer(profile_id: str, customer_id: str):
    customers = [c for c in _load(profile_id) if c.get("id") != customer_id]
    _save(profile_id, customers)


def import_from_sales(profile_id: str) -> int:
    """Importa clientes únicos desde el historial de ventas. Retorna cantidad agregada."""
    from agent.local_sales import list_invoices
    import uuid

    existing = _load(profile_id)
    existing_keys = {
        (c.get("name", "").strip().lower(), c.get("phone", "").strip())
        for c in existing
    }
    added = 0
    for inv in list_invoices(profile_id, limit=9999):
        name  = (inv.get("customer") or "").strip()
        phone = (inv.get("customer_phone") or "").strip()
        if not name:
            continue
        key = (name.lower(), phone)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        existing.append({
            "id":      str(uuid.uuid4())[:8],
            "name":    name,
            "phone":   phone,
            "address": (inv.get("customer_address") or "").strip(),
            "rfc":     (inv.get("customer_rfc") or "").strip(),
        })
        added += 1
    if added:
        _save(profile_id, existing)
    return added
