import json
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from config import settings
from models.schemas import Sale, Invoice

# ── Almacenamiento local (fallback si DynamoDB no está disponible) ────────────
_LOCAL_FILE = Path(__file__).parent.parent / "data" / "sales.json"

def _local_load() -> list:
    if _LOCAL_FILE.exists():
        return json.loads(_LOCAL_FILE.read_text(encoding="utf-8"))
    return []

def _local_save(records: list):
    _LOCAL_FILE.parent.mkdir(exist_ok=True)
    _LOCAL_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

def _local_append(item: dict):
    records = _local_load()
    records.append(item)
    _local_save(records)

# ── DynamoDB ──────────────────────────────────────────────────────────────────
dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
table = dynamodb.Table("mf_sales")

def _dynamo_ok() -> bool:
    try:
        table.load()
        return True
    except Exception:
        return False

_USE_DYNAMO = None  # se evalúa la primera vez

def _use_dynamo() -> bool:
    global _USE_DYNAMO
    if _USE_DYNAMO is None:
        _USE_DYNAMO = _dynamo_ok()
    return _USE_DYNAMO


def _to_dec(obj):
    if isinstance(obj, dict):
        return {k: _to_dec(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dec(i) for i in obj]
    if isinstance(obj, float):
        return Decimal(str(obj))
    return obj

def _from_dec(obj):
    if isinstance(obj, dict):
        return {k: _from_dec(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_dec(i) for i in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


# ── API pública ───────────────────────────────────────────────────────────────
def record_sale(sale: Sale) -> dict:
    item = sale.dict()
    if _use_dynamo():
        table.put_item(Item=_to_dec(item))
    else:
        _local_append(item)
    return item


def record_invoice(invoice: Invoice) -> dict:
    item = invoice.dict()
    item["record_type"] = "invoice"
    item["sale_id"] = invoice.invoice_id
    if _use_dynamo():
        table.put_item(Item=_to_dec(item))
    else:
        _local_append(item)
    return item


def list_sales(limit: int = 200) -> list[dict]:
    try:
        if _use_dynamo():
            r = table.scan()
            items = [_from_dec(i) for i in r.get("Items", [])
                     if i.get("record_type") != "invoice"]
        else:
            items = [r for r in _local_load() if r.get("record_type") != "invoice"]
        return sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
    except Exception:
        return []


def list_invoices(limit: int = 200) -> list[dict]:
    try:
        if _use_dynamo():
            r = table.scan(FilterExpression=Attr("record_type").eq("invoice"))
            items = [_from_dec(i) for i in r.get("Items", [])]
        else:
            items = [r for r in _local_load() if r.get("record_type") == "invoice"]
        return sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
    except Exception:
        return []


def sales_today() -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    return [s for s in list_sales() if s.get("timestamp", "").startswith(today)]


def delete_record(sale_id: str):
    try:
        if _use_dynamo():
            table.delete_item(Key={"sale_id": sale_id})
        else:
            records = [r for r in _local_load() if r.get("sale_id") != sale_id]
            _local_save(records)
    except Exception:
        pass


def total_today() -> float:
    return sum(s.get("total", 0) for s in sales_today())
