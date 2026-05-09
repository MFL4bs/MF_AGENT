import boto3
import mimetypes
from boto3.dynamodb.conditions import Attr
from decimal import Decimal
from config import settings
from models.schemas import Product, ProductUpdate

dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
table = dynamodb.Table(settings.dynamodb_table_inventory)
s3 = boto3.client("s3", region_name=settings.aws_region)


def _to_decimal(obj: dict) -> dict:
    return {k: Decimal(str(v)) if isinstance(v, float) else v for k, v in obj.items()}


def _from_decimal(obj: dict) -> dict:
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in obj.items()}


def upload_product_image(sku: str, file_path: str) -> str:
    """Sube imagen a S3 y retorna la URL pública."""
    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or "image/jpeg"
    key = f"products/{sku}{file_path[file_path.rfind('.'):]}"
    s3.upload_file(file_path, settings.s3_bucket_products, key,
                   ExtraArgs={"ContentType": content_type, "ACL": "public-read"})
    return f"https://{settings.s3_bucket_products}.s3.amazonaws.com/{key}"


def get_product(sku: str) -> dict | None:
    r = table.get_item(Key={"sku": sku})
    item = r.get("Item")
    return _from_decimal(item) if item else None


def list_products(category: str = None) -> list[dict]:
    if category:
        r = table.scan(FilterExpression=Attr("category").eq(category))
    else:
        r = table.scan()
    return [_from_decimal(i) for i in r.get("Items", [])]


def search_products(query: str) -> list[dict]:
    """Busca productos cuyo nombre o descripción contenga el query (case-insensitive)."""
    q = query.lower()
    r = table.scan()
    results = []
    for item in r.get("Items", []):
        if q in item.get("name", "").lower() or q in item.get("description", "").lower():
            results.append(_from_decimal(item))
    return results


def low_stock_products(threshold: int = 15) -> list[dict]:
    r = table.scan(FilterExpression=Attr("stock").lte(threshold))
    return [_from_decimal(i) for i in r.get("Items", [])]


def next_sku() -> str:
    """Genera el siguiente SKU correlativo: PROD-0001, PROD-0002..."""
    items = table.scan(ProjectionExpression="sku").get("Items", [])
    nums = []
    for item in items:
        sku = item.get("sku", "")
        if sku.startswith("PROD-") and sku[5:].isdigit():
            nums.append(int(sku[5:]))
    return f"PROD-{(max(nums) + 1 if nums else 1):04d}"


def upsert_product(product: Product):
    table.put_item(Item=_to_decimal(product.dict()))


def update_product(sku: str, data: ProductUpdate) -> dict | None:
    updates = {k: v for k, v in data.dict().items() if v is not None}
    if not updates:
        return get_product(sku)

    expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
    names = {f"#{k}": k for k in updates}
    values = {f":{k}": Decimal(str(v)) if isinstance(v, float) else v for k, v in updates.items()}

    r = table.update_item(
        Key={"sku": sku},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW"
    )
    return _from_decimal(r.get("Attributes", {}))


def delete_product(sku: str):
    table.delete_item(Key={"sku": sku})
