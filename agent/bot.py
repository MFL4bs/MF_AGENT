import json
import re
from pathlib import Path
from agent.local_inventory import list_products
from agent.profiles import get_profile_data_dir

MENU_PRINCIPAL     = "menu_principal"
MENU_MATERIALES    = "menu_materiales"
MENU_COTIZACION    = "menu_cotizacion"
MENU_UNIDAD        = "menu_unidad"
ESPERANDO_CANTIDAD = "esperando_cantidad"
CALIFICANDO        = "calificando"
ESPERANDO_NOMBRE   = "esperando_nombre"


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


# ── Menus ─────────────────────────────────────────────────────────────────────

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
    bienvenida = f"Hola! Bienvenido a {profile_name}." if profile_name else "Hola! Bienvenido."
    return (
        "{} En que puedo ayudarte?\n\n"
        "1. Consultar materiales y precios\n"
        "2. Solicitar cotizacion de trabajo\n"
        "3. Hablar con un asesor\n\n"
        "Escribe el numero de tu opcion."
    ).format(bienvenida)

def menu_materiales(profile_id: str) -> str:
    products = list_products(profile_id)
    if not products:
        return (
            "No hay materiales registrados en este momento.\n\n"
            "Para mas informacion contacta a un asesor.\n\n"
            "0. Volver al menu"
        )
    lines = ["--- CATALOGO DE MATERIALES ---\n"]
    for p in products:
        stock = int(p.get("stock", 0))
        if stock > 0:
            disponibilidad = "Disponible ({} unidades)".format(stock)
        else:
            disponibilidad = "Sin stock"
        desc = p.get("description", "")
        line = "* {}\n  Precio: {}\n  Disponibilidad: {}".format(
            p["name"], _fmt(float(p["price"])), disponibilidad)
        if desc:
            line += "\n  {}".format(desc)
        lines.append(line)
    lines.append("\nPara comprar o pedir mas informacion, contacta a un asesor.")
    lines.append("\n1. Ver materiales de nuevo")
    lines.append("2. Solicitar cotizacion")
    lines.append("3. Hablar con un asesor")
    lines.append("0. Volver al menu")
    return "\n".join(lines)

def menu_cotizacion() -> str:
    return (
        "--- COTIZACION DE TRABAJO ---\n\n"
        "Que tipo de trabajo necesitas cotizar?\n\n"
        "1. Construccion\n"
        "2. Soldadura\n"
        "3. Instalacion\n"
        "4. Pintura\n"
        "5. Otro tipo de trabajo\n"
        "0. Volver al menu\n\n"
        "Escribe el numero."
    )

def menu_unidad(work_type: str) -> str:
    return (
        "Trabajo: {}\n\n"
        "En que unidad se mide el trabajo?\n\n"
        "1. Metros lineales (m)\n"
        "2. Metros cuadrados (m2)\n"
        "3. Metros cubicos (m3)\n"
        "4. Por unidad / global\n"
        "0. Volver al menu\n\n"
        "Escribe el numero."
    ).format(work_type)

def menu_calificacion() -> str:
    return (
        "Como calificarias la atencion recibida?\n\n"
        "1. Excelente\n"
        "2. Bueno\n"
        "3. Regular\n"
        "4. Malo\n\n"
        "Escribe el numero."
    )


# ── Motor ─────────────────────────────────────────────────────────────────────

def bot_reply(phone: str, message: str, history: str, profile_id: str = None) -> tuple:
    """Retorna (reply_text, [], event)"""
    msg     = message.strip()
    msg_low = msg.lower()
    state   = get_state(profile_id, phone)
    step    = state.get("step", MENU_PRINCIPAL)

    # Volver al menu desde cualquier punto
    if msg_low in ("0", "menu", "inicio", "volver", "cancelar", "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"):
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
            set_state(profile_id, phone, MENU_MATERIALES)
            return menu_materiales(profile_id), [], None
        elif msg_low == "2":
            set_state(profile_id, phone, MENU_COTIZACION)
            return menu_cotizacion(), [], None
        elif msg_low in ("3", "asesor", "humano", "persona"):
            set_state(profile_id, phone, ESPERANDO_NOMBRE)
            return (
                "Con gusto te conecto con un asesor.\n\n"
                "Por favor enviame tu nombre y numero de celular:\n"
                "Ejemplo: Juan Perez 3001234567",
                [], None
            )
        # Si escribe algo que no es numero, mostrar menu
        return menu_principal(profile_id), [], None

    # ── MENU MATERIALES ───────────────────────────────────────────────────────
    elif step == MENU_MATERIALES:
        if msg_low == "1":
            return menu_materiales(profile_id), [], None
        elif msg_low == "2":
            set_state(profile_id, phone, MENU_COTIZACION)
            return menu_cotizacion(), [], None
        elif msg_low == "3":
            set_state(profile_id, phone, ESPERANDO_NOMBRE)
            return (
                "Con gusto te conecto con un asesor.\n\n"
                "Por favor enviame tu nombre y numero de celular:\n"
                "Ejemplo: Juan Perez 3001234567",
                [], None
            )
        set_state(profile_id, phone, MENU_PRINCIPAL)
        return menu_principal(profile_id), [], None

    # ── MENU COTIZACION ───────────────────────────────────────────────────────
    elif step == MENU_COTIZACION:
        work_map = {
            "1": "Construccion",  "construccion": "Construccion",
            "2": "Soldadura",     "soldadura": "Soldadura",
            "3": "Instalacion",   "instalacion": "Instalacion",
            "4": "Pintura",       "pintura": "Pintura",
            "5": "Otro trabajo",  "otro": "Otro trabajo",
        }
        work_type = work_map.get(msg_low)
        if work_type:
            set_state(profile_id, phone, MENU_UNIDAD, {"work_type": work_type})
            return menu_unidad(work_type), [], None
        return "Opcion no valida.\n\n" + menu_cotizacion(), [], None

    # ── MENU UNIDAD ───────────────────────────────────────────────────────────
    elif step == MENU_UNIDAD:
        unit_map = {
            "1": "m",       "m": "m",
            "2": "m2",      "m2": "m2",
            "3": "m3",      "m3": "m3",
            "4": "unidad",  "unidad": "unidad", "global": "unidad",
        }
        unit = unit_map.get(msg_low)
        if unit:
            work_type = state.get("work_type", "Trabajo")
            labels = {
                "m": "metros lineales", "m2": "metros cuadrados",
                "m3": "metros cubicos", "unidad": "unidades"
            }
            set_state(profile_id, phone, ESPERANDO_CANTIDAD,
                      {"work_type": work_type, "unit": unit})
            return (
                "Perfecto!\n\n"
                "Cuantos {} necesitas para el trabajo de {}?\n\n"
                "Escribe solo el numero (ejemplo: 25):".format(
                    labels.get(unit, unit), work_type),
                [], None
            )
        work_type = state.get("work_type", "Trabajo")
        return "Opcion no valida.\n\n" + menu_unidad(work_type), [], None

    # ── ESPERANDO CANTIDAD ────────────────────────────────────────────────────
    elif step == ESPERANDO_CANTIDAD:
        num_match = re.search(r'(\d+(?:[.,]\d+)?)', msg)
        if num_match:
            qty       = num_match.group(1).replace(",", ".")
            work_type = state.get("work_type", "Trabajo")
            unit      = state.get("unit", "m")
            set_state(profile_id, phone, MENU_PRINCIPAL)
            return (
                "Recibido!\n\n"
                "Trabajo: {}\n"
                "Cantidad: {} {}\n\n"
                "Estoy consultando el precio con nuestro equipo.\n"
                "Te respondo en unos minutos con la cotizacion completa.".format(
                    work_type, qty, unit),
                [], ("request_price", work_type, qty, unit)
            )
        return "Por favor escribe solo el numero. Ejemplo: 25", [], None

    # ── ESPERANDO NOMBRE ─────────────────────────────────────────────────────
    elif step == ESPERANDO_NOMBRE:
        datos = msg.strip()
        set_state(profile_id, phone, MENU_PRINCIPAL)
        return (
            f"Gracias! Un asesor te contactara pronto.\n\n"
            f"Escribe 0 si necesitas algo mas.",
            [], ("transfer_con_nombre", datos)
        )

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
        return {"cotizacion_opciones": ["Construccion", "Soldadura", "Instalacion", "Pintura", "Otro"]}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {"cotizacion_opciones": []}

def save_bot_config(profile_id: str, config: dict):
    f = _bot_config_file(profile_id)
    f.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
