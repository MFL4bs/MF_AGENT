from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

class Product(BaseModel):
    sku: str
    name: str
    description: str = ""
    price: float
    stock: int
    category: str = "general"
    image_url: Optional[str] = None

    class Config:
        json_encoders = {Decimal: float}

class ProductUpdate(BaseModel):
    stock: Optional[int] = None
    price: Optional[float] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

class ChatSession(BaseModel):
    phone: str
    history: str = ""

class Sale(BaseModel):
    sale_id: str
    sku: str
    product_name: str
    quantity: int
    unit_price: float
    total: float
    channel: str = "manual"   # "manual" | "whatsapp"
    customer: str = ""        # phone o nombre
    timestamp: str = ""

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        if not data.get("sale_id"):
            import uuid
            data["sale_id"] = str(uuid.uuid4())[:8]
        super().__init__(**data)


class InvoiceItem(BaseModel):
    sku: str
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float


class Invoice(BaseModel):
    invoice_id: str = ""
    # Datos del cliente
    customer: str = ""
    customer_phone: str = ""
    customer_email: str = ""
    customer_address: str = ""
    customer_nit: str = ""
    # Datos del negocio (se llenan al guardar)
    business_name: str = ""
    business_phone: str = ""
    business_address: str = ""
    # Notas
    notes: str = ""
    items: list[InvoiceItem] = []
    total: float = 0.0
    channel: str = "manual"
    timestamp: str = ""

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        if not data.get("invoice_id"):
            import uuid
            data["invoice_id"] = "INV-" + str(uuid.uuid4())[:6].upper()
        super().__init__(**data)
