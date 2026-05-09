"""
Gestión de precios de mano de obra por perfil
Almacena precios por tipo de trabajo y unidad de medida
"""
from pathlib import Path
import json
from agent.profiles import get_profile_data_dir


def get_labor_prices_file(profile_id: str) -> Path:
    """Retorna la ruta del archivo JSON de precios de mano de obra."""
    data_dir = get_profile_data_dir(profile_id)
    return data_dir / "labor_prices.json"


def load_labor_prices(profile_id: str) -> dict:
    """Carga todos los precios de mano de obra del perfil."""
    file = get_labor_prices_file(profile_id)
    if not file.exists():
        return {}
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_labor_prices(profile_id: str, prices: dict):
    """Guarda los precios de mano de obra."""
    file = get_labor_prices_file(profile_id)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(prices, indent=2, ensure_ascii=False), encoding="utf-8")


def get_labor_price(profile_id: str, work_type: str, unit: str = "m") -> float | None:
    """
    Obtiene el precio de mano de obra para un tipo de trabajo.
    
    Args:
        profile_id: ID del perfil
        work_type: Tipo de trabajo (ej: "soldadura", "pintura", "instalacion")
        unit: Unidad de medida ("m", "m2", "m3")
    
    Returns:
        Precio por unidad o None si no existe
    """
    prices = load_labor_prices(profile_id)
    key = f"{work_type.lower().strip()}_{unit.lower()}"
    return prices.get(key)


def set_labor_price(profile_id: str, work_type: str, unit: str, price: float, description: str = ""):
    """
    Establece o actualiza el precio de mano de obra.
    
    Args:
        profile_id: ID del perfil
        work_type: Tipo de trabajo
        unit: Unidad de medida ("m", "m2", "m3")
        price: Precio por unidad
        description: Descripción opcional del trabajo
    """
    prices = load_labor_prices(profile_id)
    key = f"{work_type.lower().strip()}_{unit.lower()}"
    prices[key] = {
        "price": price,
        "work_type": work_type,
        "unit": unit,
        "description": description
    }
    save_labor_prices(profile_id, prices)


def list_labor_prices(profile_id: str) -> list:
    """Lista todos los precios de mano de obra registrados."""
    prices = load_labor_prices(profile_id)
    return [
        {
            "work_type": v["work_type"],
            "unit": v["unit"],
            "price": v["price"],
            "description": v.get("description", ""),
            "key": k
        }
        for k, v in prices.items()
    ]


def delete_labor_price(profile_id: str, work_type: str, unit: str):
    """Elimina un precio de mano de obra."""
    prices = load_labor_prices(profile_id)
    key = f"{work_type.lower().strip()}_{unit.lower()}"
    if key in prices:
        del prices[key]
        save_labor_prices(profile_id, prices)


def search_labor_price(profile_id: str, query: str) -> list:
    """
    Busca precios de mano de obra por palabra clave.
    
    Args:
        profile_id: ID del perfil
        query: Texto a buscar en tipo de trabajo o descripción
    
    Returns:
        Lista de precios que coinciden con la búsqueda
    """
    all_prices = list_labor_prices(profile_id)
    query_lower = query.lower()
    return [
        p for p in all_prices
        if query_lower in p["work_type"].lower() or query_lower in p.get("description", "").lower()
    ]


def format_labor_prices_for_bot(profile_id: str) -> str:
    """Formatea los precios de mano de obra para el contexto del bot."""
    prices = list_labor_prices(profile_id)
    if not prices:
        return "No hay precios de mano de obra registrados aún."
    
    lines = ["💼 PRECIOS DE MANO DE OBRA REGISTRADOS:"]
    for p in prices:
        unit_label = {"m": "metro lineal", "m2": "metro cuadrado", "m3": "metro cúbico"}.get(p["unit"], p["unit"])
        desc = f" - {p['description']}" if p.get("description") else ""
        lines.append(f"• {p['work_type']}: ${p['price']:.2f} por {unit_label}{desc}")
    
    return "\n".join(lines)
