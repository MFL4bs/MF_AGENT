import json
import re
from pathlib import Path
from agent.local_inventory import list_products
from agent.profiles import get_profile_data_dir

MENU_PRINCIPAL     = "menu_principal"
MENU_CATALOGO      = "menu_catalogo"
SELECCIONANDO      = "seleccionando"
ESPERANDO_CUPON    = "esperando_cupon"
ESPERANDO_NOMBRE   = "esperando_nombre"
CALIFICANDO        = "calificando"


def _states_file(profile_id: str) -> Path:
    return get_profile_data_dir(profile_id) / "chat_states.json"

def get_state(profile_id: str, phone: str) -> dict:
    f = _states_file(profile_id)
    if not f.exists():
        return {"step": MENU_PRINCIPAL}
    try:
        return json.loads(f.read_text(encoding="utf-8")).get(phone, {"step": MENU_PRINCIPAL})
    except Exception:
        return {"step": MENU_PRINCIPAL}

def set_state(profile_id: str, phone: str, step: str, data: dict = None):
    f = _states_file(profile_id)
    try:
        all_states = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except Exception:
        all_states = {}
    all_states[phone] = {"step": step, **(data or {})}
    f.write_text(json.dumps(all_states, ensure_ascii=False, indent=2), encoding="utf-8")


def load_advisors(profile_id: str) -> list:
    f = get_profile_data_dir(profile_id) / "advisors.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_advisors(profile_id: str, advisors: list):
    f = get_profile_data_dir(profile_id) / "advisors.json"
    f.write_text(json.dumps(advisors, ensure_ascii=False, indent=2), encoding="utf-8")


def _fmt(price: float) -> str:
    return "${:,.0f} COP".format(price).replace(",", ".")


# ── Menús ──────────────────────────────────────────────────────────────────────

def menu_principal(profile_id: str = None) -> str:
    from agent.profiles import get_profile
    profile_name = ""
    if profile_id:
        try:
            p = get_profile(profile_id)
            if p:
                profile_name = p.get("name", "")
        except Exception:
            pass
    default = (
        "Hola! Bienvenido{}.\n\n"
        "1. Ver catalogo de productos\n"
        "2. Hablar con un asesor\n\n"
        "Escribe el numero de tu opcion."
    ).format(f" a {profile_name}" if profile_name else "")
    return _cfg_msg(profile_id, "msg_bienvenida", default)


def menu_catalogo(profile_id: str, seleccionados: list = None) -> str:
    """Catálogo numerado con carrito actual."""
    products = [p for p in list_products(profile_id) if int(p.get("stock", 0)) > 0]
    if not products:
        return (
            "No hay productos disponibles en este momento.\n\n"
            "Para mas informacion contacta a un asesor.\n\n"
            "0. Volver al menu"
        )

    lines = ["--- CATALOGO DE PRODUCTOS ---\n"]
    for i, p in enumerate(products, start=1):
        desc = p.get("description", "")
        line = "{}. {}\n   Precio: {}  |  Stock: {} und".format(
            i, p["name"], _fmt(float(p["price"])), int(p.get("stock", 0)))
        if desc:
            line += "\n   {}".format(desc)
        lines.append(line)

    lines.append("")

    # Mostrar carrito si tiene items
    if seleccionados:
        lines.append("🛒 *Tu seleccion actual:*")
        total = 0.0
        for item in seleccionados:
            subtotal = item["price"] * item["qty"]
            total   += subtotal
            lines.append("  • {} x{} = {}".format(
                item["name"], item["qty"], _fmt(subtotal)))
        lines.append("  *Total estimado: {}*".format(_fmt(total)))
        lines.append("")
        lines.append("Escribe el *numero* para agregar otro producto.")
        lines.append("Escribe *listo* para continuar con tu pedido.")
    else:
        lines.append("Escribe el *numero* del producto que te interesa.")
        lines.append("Puedes elegir varios productos antes de continuar.")
        lines.append("Cuando termines escribe *listo*.")

    lines.append("0. Volver al menu")
    return "\n".join(lines)


def _resumen_pedido(seleccionados: list) -> str:
    """Genera el resumen del pedido con total."""
    lines = ["📋 *RESUMEN DEL PEDIDO*\n"]
    total = 0.0
    for item in seleccionados:
        subtotal = item["price"] * item["qty"]
        total   += subtotal
        lines.append("  • {} x{} — {}".format(
            item["name"], item["qty"], _fmt(subtotal)))
    lines.append("\n*Total estimado: {}*".format(_fmt(total)))
    return "\n".join(lines)


def menu_calificacion() -> str:
    return (
        "Como calificarias la atencion recibida?\n\n"
        "1. Excelente\n"
        "2. Bueno\n"
        "3. Regular\n"
        "4. Malo\n\n"
        "Escribe el numero."
    )


# ── Motor ──────────────────────────────────────────────────────────────────────

def bot_reply(phone: str, message: str, history: str, profile_id: str = None) -> tuple:
    """Retorna (reply_text, [], event)"""
    msg     = message.strip()
    msg_low = msg.lower()
    state   = get_state(profile_id, phone)
    step    = state.get("step", MENU_PRINCIPAL)

    # Volver al menú desde cualquier punto
    if msg_low in ("0", "menu", "inicio", "volver", "cancelar",
                   "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"):
        set_state(profile_id, phone, MENU_PRINCIPAL)
        return menu_principal(profile_id), [], None

    # ── CALIFICANDO ───────────────────────────────────────────────────────────
    if step == CALIFICANDO:
        ratings = {"1": "Excelente", "2": "Bueno", "3": "Regular", "4": "Malo"}
        rating  = ratings.get(msg_low)
        set_state(profile_id, phone, MENU_PRINCIPAL)
        if rating:
            return (
                "Gracias por tu calificacion: {}!\n"
                "Fue un placer atenderte. Hasta pronto!\n\n"
                "Escribe 0 si necesitas algo mas.".format(rating),
                [], ("rating", rating)
            )
        return menu_calificacion(), [], None

    # ── MENU PRINCIPAL ────────────────────────────────────────────────────────
    if step == MENU_PRINCIPAL:
        if msg_low == "1":
            set_state(profile_id, phone, SELECCIONANDO, {"carrito": []})
            return menu_catalogo(profile_id, []), [], None
        elif msg_low in ("2", "asesor", "humano", "persona"):
            set_state(profile_id, phone, ESPERANDO_NOMBRE)
            return (
                "Con gusto te conecto con un asesor.\n\n"
                "Por favor enviame tu nombre y numero de celular:\n"
                "Ejemplo: Juan Perez 3001234567",
                [], None
            )
        return menu_principal(profile_id), [], None

    # ── SELECCIONANDO PRODUCTOS ───────────────────────────────────────────────
    elif step == SELECCIONANDO:
        products   = [p for p in list_products(profile_id) if int(p.get("stock", 0)) > 0]
        carrito    = state.get("carrito", [])

        # Cliente escribe "listo" — preguntar si tiene cupón
        if msg_low in ("listo", "ya", "continuar", "siguiente", "ok", "confirmar"):
            if not carrito:
                return (
                    "Aun no has seleccionado ningun producto.\n\n"
                    + menu_catalogo(profile_id, carrito),
                    [], None
                )
            resumen = _resumen_pedido(carrito)
            set_state(profile_id, phone, ESPERANDO_CUPON, {"carrito": carrito})
            msg_cupon = _cfg_msg(profile_id, "msg_cupon",
                "Tienes un *cupon de descuento*?\nEscribe el codigo o escribe *no* para continuar.")
            return (resumen + "\n\n" + msg_cupon, [], None)

        # Cliente escribe un número de producto
        num_match = re.fullmatch(r'\d+', msg_low)
        if num_match:
            idx = int(msg_low)
            if 1 <= idx <= len(products):
                prod = products[idx - 1]
                # Si ya está en el carrito, sumar cantidad
                encontrado = False
                for item in carrito:
                    if item["sku"] == prod["sku"]:
                        item["qty"] += 1
                        encontrado   = True
                        break
                if not encontrado:
                    carrito.append({
                        "sku":   prod["sku"],
                        "name":  prod["name"],
                        "price": float(prod["price"]),
                        "qty":   1,
                    })
                set_state(profile_id, phone, SELECCIONANDO, {"carrito": carrito})
                return (
                    "✅ *{}* agregado a tu seleccion.\n\n"
                    "{}".format(prod["name"], menu_catalogo(profile_id, carrito)),
                    [], None
                )
            else:
                return (
                    "Numero no valido. Elige entre 1 y {}.\n\n"
                    "{}".format(len(products), menu_catalogo(profile_id, carrito)),
                    [], None
                )

        # Asesor desde el catálogo
        if "asesor" in msg_low or msg_low == "2":
            set_state(profile_id, phone, ESPERANDO_NOMBRE,
                      {"carrito": carrito} if carrito else {})
            return (
                "Con gusto te conecto con un asesor.\n\n"
                "Por favor enviame tu nombre y numero de celular:\n"
                "Ejemplo: Juan Perez 3001234567",
                [], None
            )

        return menu_catalogo(profile_id, carrito), [], None

    # ── ESPERANDO CUPÓN ─────────────────────────────────────────────────────
    elif step == ESPERANDO_CUPON:
        carrito = state.get("carrito", [])
        total   = sum(i["price"] * i["qty"] for i in carrito)

        if msg_low in ("no", "no tengo", "sin cupon", "ninguno", "n"):
            # Sin cupón — pasar a pedir nombre
            set_state(profile_id, phone, ESPERANDO_NOMBRE, {"carrito": carrito})
            return (
                "Perfecto! Para continuar necesito tus datos.\n"
                "Por favor enviame tu nombre y numero de celular:\n"
                "Ejemplo: Juan Perez 3001234567",
                [], None
            )

        # Intentar validar el código como cupón
        from agent.coupons import validate_coupon
        result = validate_coupon(profile_id, msg.strip(), total)

        if result["ok"]:
            # Aplicar descuento al carrito
            discount     = result["discount"]
            final_total  = result["final_total"]
            # Guardar descuento en el carrito como item especial
            carrito_con_desc = carrito + [{
                "sku":   "DESC",
                "name":  f"Descuento cupón {msg.strip().upper()}",
                "price": -discount,
                "qty":   1,
            }]
            set_state(profile_id, phone, ESPERANDO_NOMBRE, {"carrito": carrito_con_desc})
            return (
                f"{result['msg']}\n\n"
                f"Total original: {_fmt(total)}\n"
                f"Descuento: -{_fmt(discount)}\n"
                f"*Total final: {_fmt(final_total)}*\n\n"
                "Para continuar necesito tus datos.\n"
                "Por favor enviame tu nombre y numero de celular:\n"
                "Ejemplo: Juan Perez 3001234567",
                [], None
            )
        else:
            # Cupón inválido — dejar intentar de nuevo o saltar
            return (
                f"{result['msg']}\n\n"
                "Intenta con otro codigo o escribe *no* para continuar sin descuento.",
                [], None
            )

    # ── ESPERANDO NOMBRE ──────────────────────────────────────────────────────
    elif step == ESPERANDO_NOMBRE:
        datos   = msg.strip()
        carrito = state.get("carrito", [])
        set_state(profile_id, phone, MENU_PRINCIPAL)
        despedida = _cfg_msg(profile_id, "msg_despedida",
            "Gracias! Un asesor te contactara pronto.\n\nEscribe 0 si necesitas algo mas.")
        if carrito:
            resumen = _resumen_pedido(carrito)
            nombre  = datos.split()[0] if datos else ""
            return (
                f"Gracias {nombre}!\n\n{despedida}",
                [], ("transfer_con_pedido", datos, carrito, resumen)
            )
        return (despedida, [], ("transfer_con_nombre", datos))

    # Fallback
    set_state(profile_id, phone, MENU_PRINCIPAL)
    return menu_principal(profile_id), [], None


def trigger_calificacion(profile_id: str, phone: str) -> tuple:
    set_state(profile_id, phone, CALIFICANDO)
    return menu_calificacion(), []


def _bot_config_file(profile_id: str) -> Path:
    return get_profile_data_dir(profile_id) / "bot_config.json"

def get_bot_config(profile_id: str) -> dict:
    f = _bot_config_file(profile_id)
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _cfg_msg(profile_id: str, key: str, default: str) -> str:
    return get_bot_config(profile_id).get(key, "").strip() or default

def save_bot_config(profile_id: str, config: dict):
    f = _bot_config_file(profile_id)
    f.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
