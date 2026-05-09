"""
Ventas/Facturas locales por perfil.
"""
import json
from pathlib import Path
from agent.profiles import get_profile_data_dir


def _sales_file(profile_id: str) -> Path:
    return get_profile_data_dir(profile_id) / "sales.json"


def _load(profile_id: str) -> list:
    f = _sales_file(profile_id)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def _save(profile_id: str, records: list):
    _sales_file(profile_id).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def record_invoice(profile_id: str, invoice: dict):
    records = _load(profile_id)
    records.append(invoice)
    _save(profile_id, records)


def list_invoices(profile_id: str, limit: int = 200) -> list[dict]:
    records = _load(profile_id)
    return sorted(records, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]


def delete_record(profile_id: str, sale_id: str):
    records = [r for r in _load(profile_id)
               if r.get("sale_id") != sale_id and r.get("invoice_id") != sale_id]
    _save(profile_id, records)
