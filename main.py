import re
import json
import boto3
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from config import settings
from models.schemas import Product, ProductUpdate, Sale
from agent.local_inventory import (
    get_product, list_products, update_product,
    upsert_product, low_stock_products
)
from agent.bot import bot_reply, trigger_calificacion, load_advisors, save_advisors
from agent.local_sales import record_invoice, list_invoices
from agent.labor_prices import set_labor_price, list_labor_prices, delete_labor_price

app = FastAPI(title="MF Agent")

dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
sessions_table = dynamodb.Table(settings.dynamodb_table_sessions)


def _load_admin_phones():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ADMIN_PHONES=") or line.startswith("OWNER_PHONE="):
                _, value = line.split("=", 1)
                return [p.strip() for p in value.split(",") if p.strip()]
    return []

ADMIN_PHONES  = _load_admin_phones()
BRIDGE_URL    = "http://127.0.0.1:3000"
bridge_connected = False


class WhatsAppMessage(BaseModel):
    From: str
    Body: str

class BridgeStatus(BaseModel):
    status: str


def get_history(phone: str) -> str:
    r = sessions_table.get_item(Key={"phone": phone})
    return r.get("Item", {}).get("history", "")

def save_history(phone: str, history: str):
    sessions_table.put_item(Item={"phone": phone, "history": history[-3000:]})


async def send_whatsapp(phone: str, message: str, buttons: list = None):
    try:
        payload = {"phone": phone, "message": message}
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(f"{BRIDGE_URL}/send", json=payload)
    except Exception:
        pass

async def notify_owner(message: str):
    for p in ADMIN_PHONES:
        await send_whatsapp(p, message)


@app.post("/bridge/status")
async def bridge_status(data: BridgeStatus):
    global bridge_connected
    bridge_connected = data.status == "connected"
    return {"ok": True}

@app.get("/bridge/status")
def get_bridge_status():
    return {"connected": bridge_connected}


# ── Pendientes ────────────────────────────────────────────────────────────────

def _pending_file(profile_id: str, name: str) -> Path:
    from agent.profiles import get_profile_data_dir
    return get_profile_data_dir(profile_id) / name

def _load_pending(profile_id: str, name: str) -> list:
    f = _pending_file(profile_id, name)
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save_pending(profile_id: str, name: str, data: list):
    _pending_file(profile_id, name).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

def save_pending_quote(profile_id, phone, work_type, quantity, unit):
    pending = _load_pending(profile_id, "pending_quotes.json")
    pending.append({"phone": phone, "work_type": work_type,
                    "quantity": quantity, "unit": unit,
                    "timestamp": datetime.now().isoformat()})
    _save_pending(profile_id, "pending_quotes.json", pending)

def save_pending_payment(profile_id, phone, msg_text, sku=None, qty=1, total=0):
    pending = _load_pending(profile_id, "pending_payments.json")
    pending = [p for p in pending if p["phone"] != phone]
    pending.append({"phone": phone, "message": msg_text,
                    "sku": sku, "qty": qty, "total": total,
                    "timestamp": datetime.now().isoformat()})
    _save_pending(profile_id, "pending_payments.json", pending)

def save_pending_advisor_request(profile_id, client_phone):
    pending = _load_pending(profile_id, "pending_advisor.json")
    pending = [p for p in pending if p["phone"] != client_phone]
    pending.append({"phone": client_phone, "timestamp": datetime.now().isoformat()})
    _save_pending(profile_id, "pending_advisor.json", pending)

def pop_pending_payment(profile_id: str) -> dict | None:
    pending = _load_pending(profile_id, "pending_payments.json")
    if not pending:
        return None
    item = pending.pop()
    _save_pending(profile_id, "pending_payments.json", pending)
    return item

def pop_pending_advisor_request(profile_id: str) -> dict | None:
    pending = _load_pending(profile_id, "pending_advisor.json")
    if not pending:
        return None
    item = pending.pop(0)
    _save_pending(profile_id, "pending_advisor.json", pending)
    return item


# ── Webhook ───────────────────────────────────────────────────────────────────

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(msg: WhatsAppMessage):
    import app as desktop_app

    phone   = msg.From.replace("whatsapp:", "").strip()
    # Quitar cualquier sufijo @... que pueda venir
    phone = re.sub(r'@.*$', '', phone).strip()
    message = msg.Body.strip()

    if not desktop_app.bot_enabled:
        return {"reply": "Servicio pausado temporalmente."}

    from lic_manager.license_manager import validate
    _lic = validate()
    profile_id = _lic.get("profile_id") if _lic.get("ok") else None
    if not profile_id:
        from agent.profiles import list_profiles
        profiles = list_profiles()
        profile_id = profiles[0]["id"] if profiles else None
    history    = get_history(phone)

    # ── Admin: nunca recibe el menu del bot ───────────────────────────────────
    # Normalizar: comparar solo digitos
    phone_digits = re.sub(r'\D', '', phone)
    is_admin = any(re.sub(r'\D', '', ap) == phone_digits for ap in ADMIN_PHONES)
    if is_admin:
        msg_clean = message.strip().lower()

        if message.lower().startswith("/"):
            reply = handle_admin_command(message, profile_id)

        elif msg_clean in ("si", "yes", "confirmado", "llego"):
            reply = await handle_owner_payment_confirm(True, profile_id)

        elif msg_clean in ("no", "nop", "no llego"):
            reply = await handle_owner_payment_confirm(False, profile_id)

        elif re.fullmatch(r'[\$]?\s*(\d+(?:[.,]\d+)?)', message.strip()):
            price_val = re.fullmatch(r'[\$]?\s*(\d+(?:[.,]\d+)?)', message.strip()).group(1).replace(",", ".")
            reply = await handle_owner_price_reply(price_val, profile_id)

        else:
            # Admin escribe algo no reconocido — no responder nada
            return {"reply": ""}

        save_history(phone, f"{history}\nAdmin: {message}\nBot: {reply}")
        return {"reply": reply}

    # ── Cliente ───────────────────────────────────────────────────────────────
    PAYMENT_KW = ["pague", "ya pague", "hice el pago", "transferi", "envie el pago", "comprobante"]
    if any(w in message.lower() for w in PAYMENT_KW):
        save_pending_payment(profile_id, phone, message)
        await notify_owner(
            f"PAGO REPORTADO\n\nCliente: {phone}\nMensaje: {message[:150]}\n\n"
            f"Confirmas que llego el pago?\nResponde si o no"
        )
        reply = "Gracias, verificaremos tu pago y te confirmamos en breve."
    else:
        try:
            reply, _, event = bot_reply(phone, message, history, profile_id)
            await _handle_event(phone, event, profile_id)
        except Exception as e:
            reply = "Lo siento, ocurrio un error. Intentalo de nuevo."
            print(f"[ERROR webhook] {e}")

    save_history(phone, f"{history}\nCliente: {message}\nBot: {reply}")
    return {"reply": reply}


# ── Eventos del bot ───────────────────────────────────────────────────────────

async def _handle_event(phone: str, event, profile_id: str):
    if event is None:
        return

    if event == "transfer_generic":
        advisors = load_advisors(profile_id)
        clean_number = re.sub(r'\D', '', phone)
        msg_asesor = f"CLIENTE SOLICITA ASESOR\n\nNumero: +{clean_number}\nLink: https://wa.me/{clean_number}"
        if advisors:
            for advisor in advisors:
                ap = advisor.get("phone", "")
                if ap:
                    await send_whatsapp(ap, msg_asesor)
        else:
            await notify_owner(msg_asesor)

    elif isinstance(event, tuple) and event[0] == "cotizacion_con_datos":
        _, datos, work_type, qty, unit, descripcion = event
        advisors = load_advisors(profile_id)
        num_match = re.search(r'(\d[\d\s\-]{6,14}\d)', datos)
        client_num = re.sub(r'\D', '', num_match.group(1)) if num_match else re.sub(r'\D', '', phone)
        link = f"https://wa.me/{client_num}"
        unit_label = {"m": "metro lineal", "m2": "metro cuadrado", "m3": "metro cubico", "unidad": "unidad"}.get(unit, unit)
        msg_asesor = (
            f"SOLICITUD DE COTIZACION\n\n"
            f"Cliente: {datos}\n"
            f"Link WhatsApp: {link}\n\n"
            f"Trabajo: {work_type}\n"
            f"Cantidad: {qty} {unit_label}\n"
            + (f"Descripcion: {descripcion}\n" if descripcion else "") +
            f"\nResponde con el precio por {unit_label} para enviarle la cotizacion."
        )
        save_pending_quote(profile_id, phone, work_type, qty, unit)
        if advisors:
            for advisor in advisors:
                ap = advisor.get("phone", "")
                if ap:
                    await send_whatsapp(ap, msg_asesor)
        else:
            await notify_owner(msg_asesor)

    elif isinstance(event, tuple) and event[0] == "compra_con_datos":
        _, datos, carrito = event
        advisors = load_advisors(profile_id)
        # Extraer número del texto del cliente
        num_match = re.search(r'(\d[\d\s\-]{6,14}\d)', datos)
        client_num = re.sub(r'\D', '', num_match.group(1)) if num_match else re.sub(r'\D', '', phone)
        link = f"https://wa.me/{client_num}"
        resumen = "\n".join(f"  - {c['name']} x{c['qty']} = ${c['price']*c['qty']:,.0f} COP" for c in carrito)
        total = sum(c['price'] * c['qty'] for c in carrito)
        msg_asesor = (
            f"PEDIDO DE COMPRA\n\n"
            f"Cliente: {datos}\n"
            f"Link WhatsApp: {link}\n\n"
            f"Productos solicitados:\n{resumen}\n\n"
            f"TOTAL ESTIMADO: ${total:,.0f} COP"
        )
        if advisors:
            for advisor in advisors:
                ap = advisor.get("phone", "")
                if ap:
                    await send_whatsapp(ap, msg_asesor)
        else:
            await notify_owner(msg_asesor)

    elif isinstance(event, tuple) and event[0] == "transfer_con_nombre":
        _, datos = event
        advisors = load_advisors(profile_id)
        # Extraer número del texto que el cliente escribió
        num_match = re.search(r'(\d[\d\s\-]{6,14}\d)', datos)
        if num_match:
            client_num = re.sub(r'\D', '', num_match.group(1))
        else:
            client_num = re.sub(r'\D', '', phone)
        link = f"https://wa.me/{client_num}"
        msg_asesor = (
            f"CLIENTE SOLICITA ASESOR\n\n"
            f"Datos: {datos}\n"
            f"Link WhatsApp: {link}"
        )
        if advisors:
            for advisor in advisors:
                ap = advisor.get("phone", "")
                if ap:
                    await send_whatsapp(ap, msg_asesor)
        else:
            await notify_owner(msg_asesor)

    elif isinstance(event, tuple) and event[0] == "request_price":
        _, work_type, qty, unit = event
        unit_sym = {"m": "m", "m2": "m2", "m3": "m3", "unidad": "unidad"}.get(unit, unit)
        save_pending_quote(profile_id, phone, work_type, qty, unit)
        await notify_owner(
            f"PRECIO REQUERIDO\n\nCliente: {phone}\nTrabajo: {work_type}\n"
            f"Cantidad: {qty} {unit_sym}\n\nResponde solo con el numero del precio por {unit_sym}\nEjemplo: 150000"
        )

    elif isinstance(event, tuple) and event[0] == "purchase_confirmed":
        _, sku, name, qty, total = event
        save_pending_payment(profile_id, phone, f"{name} x{qty}", sku=sku, qty=qty, total=total)
        await notify_owner(
            f"NUEVO PEDIDO\n\nCliente: {phone}\nProducto: {name} x{qty}\n"
            f"Total: ${total:,.0f} COP\n\nEsperando confirmacion de pago."
        )

    elif isinstance(event, tuple) and event[0] == "rating":
        _, rating = event
        await notify_owner(f"Calificacion recibida\nCliente: {phone}\n{rating}")


# ── Confirmar pago ────────────────────────────────────────────────────────────

async def handle_owner_payment_confirm(confirmed: bool, profile_id: str) -> str:
    payment = pop_pending_payment(profile_id)
    if not payment:
        return "No hay pagos pendientes."

    client_phone = payment["phone"]
    sku   = payment.get("sku", "WHATSAPP")
    qty   = payment.get("qty", 1)
    total = payment.get("total", 0)
    name  = payment.get("message", "Venta WhatsApp")[:80]

    if confirmed:
        inv_dict = {
            "customer": client_phone,
            "items": [{"sku": sku, "product_name": name,
                       "quantity": qty, "unit_price": total / qty if qty else total,
                       "subtotal": total}],
            "total": total, "channel": "whatsapp",
            "timestamp": datetime.now().isoformat()
        }
        try:
            record_invoice(profile_id, inv_dict)
            if sku and sku != "WHATSAPP":
                p = get_product(profile_id, sku)
                if p:
                    update_product(profile_id, sku, {"stock": max(0, int(p.get("stock", 0)) - qty)})
        except Exception as e:
            print(f"[ERROR registro venta] {e}")

        await send_whatsapp(client_phone,
            "Pago confirmado!\n\nTu pago fue recibido. En breve nos ponemos en contacto.")
        import asyncio
        await asyncio.sleep(2)
        cal_text, _ = trigger_calificacion(profile_id, client_phone)
        await send_whatsapp(client_phone, cal_text)
        save_history(client_phone, get_history(client_phone) + "\nBot: Pago confirmado.")
        return f"Venta registrada. Cliente {client_phone} notificado."
    else:
        await send_whatsapp(client_phone,
            "Pago no recibido aun\n\nRevisamos pero no vemos tu pago. Por favor verifica e intenta de nuevo.")
        return f"Pago no confirmado. Cliente {client_phone} notificado."


# ── Precio del supervisor ─────────────────────────────────────────────────────

async def handle_owner_price_reply(price_str: str, profile_id: str) -> str:
    """El supervisor responde con el precio — notifica al cliente directamente."""
    pending = _load_pending(profile_id, "pending_quotes.json")
    if not pending:
        return "No hay cotizaciones pendientes."

    price = float(price_str)

    # Tomar el mas reciente y eliminarlo
    q = pending.pop()
    _save_pending(profile_id, "pending_quotes.json", pending)

    work_type  = q["work_type"]
    unit       = q["unit"]
    unit_sym   = {"m": "m", "m2": "m2", "m3": "m3", "unidad": "unidad"}.get(unit, unit)
    unit_label = {"m": "metro lineal", "m2": "metro cuadrado", "m3": "metro cubico", "unidad": "unidad"}.get(unit, unit)

    # Guardar precio para futuras consultas
    set_labor_price(profile_id, work_type, unit, price)

    # Calcular total
    try:
        qty = float(q["quantity"])
    except Exception:
        qty = 1.0
    total = price * qty

    # Enviar cotizacion al cliente
    msg = (
        f"COTIZACION\n\n"
        f"Trabajo: {work_type}\n"
        f"Cantidad: {qty:.0f} {unit_sym}\n"
        f"Precio por {unit_label}: ${price:,.0f} COP\n\n"
        f"TOTAL: ${total:,.0f} COP\n\n"
        f"Te gustaria proceder?\n"
        f"Cuando realices el pago escribeme: pague"
    )
    await send_whatsapp(q["phone"], msg)
    save_history(q["phone"], get_history(q["phone"]) + f"\nBot: {msg}")

    # Notificar otros clientes pendientes con el mismo trabajo
    remaining = _load_pending(profile_id, "pending_quotes.json")
    still_remaining = []
    for r in remaining:
        if work_type.lower() in r["work_type"].lower() or r["work_type"].lower() in work_type.lower():
            try:
                r_qty = float(r["quantity"])
            except Exception:
                r_qty = 1.0
            r_total = price * r_qty
            r_msg = (
                f"COTIZACION\n\n"
                f"Trabajo: {r['work_type']}\n"
                f"Cantidad: {r_qty:.0f} {unit_sym}\n"
                f"Precio por {unit_label}: ${price:,.0f} COP\n\n"
                f"TOTAL: ${r_total:,.0f} COP\n\n"
                f"Te gustaria proceder?\n"
                f"Cuando realices el pago escribeme: pague"
            )
            await send_whatsapp(r["phone"], r_msg)
            save_history(r["phone"], get_history(r["phone"]) + f"\nBot: {r_msg}")
        else:
            still_remaining.append(r)
    _save_pending(profile_id, "pending_quotes.json", still_remaining)

    return f"Cotizacion enviada al cliente {q['phone']}\n{work_type}: ${price:,.0f}/{unit_sym}"


# ── Comandos admin ────────────────────────────────────────────────────────────

def handle_admin_command(message: str, profile_id: str = None) -> str:
    parts = message.split()
    cmd   = parts[0].lower()

    if cmd == "/stock":
        products = list_products(profile_id)
        if not products:
            return "Inventario vacio."
        lines = [f"Inventario ({len(products)} productos)"]
        for p in products:
            lines.append(f"- {p['name']} | Stock: {p['stock']} | ${float(p['price']):,.0f} COP")
        return "\n".join(lines)

    if cmd == "/bajo":
        products = low_stock_products(profile_id, threshold=5)
        if not products:
            return "Stock suficiente."
        lines = ["Stock bajo (<=5):"]
        for p in products:
            lines.append(f"- {p['name']} | Stock: {p['stock']}")
        return "\n".join(lines)

    if cmd == "/update" and len(parts) >= 3:
        sku = parts[1]
        updates = {}
        for param in parts[2:]:
            if "=" in param:
                k, v = param.split("=", 1)
                if k == "stock":    updates["stock"] = int(v)
                elif k == "precio": updates["price"] = float(v)
        if updates:
            result = update_product(profile_id, sku, updates)
            return f"Actualizado: {result['name']}" if result else f"SKU {sku} no encontrado."

    if cmd == "/precio" and len(parts) >= 4:
        work_type, unit = parts[1], parts[2].lower()
        try:
            price = float(parts[3])
            desc  = " ".join(parts[4:]) if len(parts) > 4 else ""
            set_labor_price(profile_id, work_type, unit, price, desc)
            return f"Precio guardado: {work_type} ${price:,.0f}/{unit}"
        except ValueError:
            return "Uso: /precio [trabajo] [m|m2|m3] [precio]"

    if cmd == "/precios":
        prices = list_labor_prices(profile_id)
        if not prices:
            return "Sin precios.\nUsa: /precio [trabajo] [m|m2|m3] [precio]"
        lines = ["PRECIOS MANO DE OBRA"]
        for p in prices:
            lines.append(f"- {p['work_type']}: ${p['price']:,.0f}/{p['unit']}")
        return "\n".join(lines)

    if cmd == "/delprecio" and len(parts) >= 3:
        delete_labor_price(profile_id, parts[1], parts[2].lower())
        return f"Precio eliminado: {parts[1]}"

    if cmd == "/pendientes":
        pending = _load_pending(profile_id, "pending_quotes.json")
        if not pending:
            return "Sin cotizaciones pendientes."
        lines = ["COTIZACIONES PENDIENTES"]
        for i, p in enumerate(pending[-10:], 1):
            lines.append(f"{i}. {p['phone']} - {p['work_type']} ({p['quantity']} {p['unit']})")
        return "\n".join(lines)

    if cmd == "/pagos":
        pending = _load_pending(profile_id, "pending_payments.json")
        if not pending:
            return "Sin pagos pendientes."
        lines = ["PAGOS PENDIENTES"]
        for i, p in enumerate(pending[-10:], 1):
            lines.append(f"{i}. {p['phone']} - {p['message'][:50]}")
        return "\n".join(lines)

    if cmd == "/asesores":
        advisors = load_advisors(profile_id)
        if not advisors:
            return "Sin asesores.\nUsa: /addasesor [nombre] [telefono]"
        lines = ["ASESORES"]
        for i, a in enumerate(advisors, 1):
            lines.append(f"{i}. {a['name']} - {a['phone']}")
        return "\n".join(lines)

    if cmd == "/addasesor" and len(parts) >= 3:
        advisors = load_advisors(profile_id)
        advisors.append({"name": parts[1], "phone": parts[2]})
        save_advisors(profile_id, advisors)
        return f"Asesor agregado: {parts[1]} ({parts[2]})"

    if cmd == "/delasesor" and len(parts) >= 2:
        advisors = load_advisors(profile_id)
        save_advisors(profile_id, [a for a in advisors if a["name"].lower() != parts[1].lower()])
        return f"Asesor eliminado: {parts[1]}"

    return (
        "COMANDOS\n\n"
        "/stock | /bajo\n"
        "/update [SKU] stock=N precio=N\n"
        "/precio [trabajo] [m|m2|m3] [precio]\n"
        "/precios | /delprecio [trabajo] [unidad]\n"
        "/pendientes | /pagos\n"
        "/asesores | /addasesor [nombre] [tel] | /delasesor [nombre]"
    )


# ── API ───────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "bridge": bridge_connected}

@app.get("/inventory")
def get_inventory():
    return []

@app.get("/sales")
def get_sales():
    return []

@app.get("/sales/today")
def get_sales_today():
    return {"sales": [], "total": 0}
