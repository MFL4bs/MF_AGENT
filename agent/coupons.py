"""
coupons.py
Gestiona cupones de descuento por perfil.
Estructura coupons.json:
[
  {
    "code": "VERANO20",
    "type": "percent",      # percent | fixed
    "value": 20,            # 20% o $20.000 fijos
    "min_total": 0,         # monto mínimo para aplicar (0 = sin mínimo)
    "active": true,
    "uses": 0,              # veces usado
    "max_uses": 0,          # 0 = ilimitado
    "expires_at": ""        # fecha límite ISO YYYY-MM-DD, vacío = sin límite
  }
]
"""
import json
from pathlib import Path
from agent.profiles import get_profile_data_dir


def _coupons_file(profile_id: str) -> Path:
    return get_profile_data_dir(profile_id) / "coupons.json"


def _load(profile_id: str) -> list:
    f = _coupons_file(profile_id)
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(profile_id: str, coupons: list):
    _coupons_file(profile_id).write_text(
        json.dumps(coupons, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_coupons(profile_id: str) -> list:
    return _load(profile_id)


def add_coupon(profile_id: str, code: str, coupon_type: str,
               value: float, min_total: float = 0, max_uses: int = 0,
               expires_at: str = "") -> dict:
    coupons = _load(profile_id)
    code = code.strip().upper()
    if any(c["code"] == code for c in coupons):
        return {"ok": False, "msg": f"El cupón '{code}' ya existe."}
    coupon = {
        "code":       code,
        "type":       coupon_type,  # "percent" | "fixed"
        "value":      float(value),
        "min_total":  float(min_total),
        "active":     True,
        "uses":       0,
        "max_uses":   int(max_uses),
        "expires_at": expires_at.strip(),  # "YYYY-MM-DD" o vacío
    }
    coupons.append(coupon)
    _save(profile_id, coupons)
    return {"ok": True, "coupon": coupon}


def delete_coupon(profile_id: str, code: str):
    coupons = [c for c in _load(profile_id) if c["code"] != code.upper()]
    _save(profile_id, coupons)


def toggle_coupon(profile_id: str, code: str) -> bool:
    """Activa/desactiva un cupón. Retorna el nuevo estado."""
    coupons = _load(profile_id)
    for c in coupons:
        if c["code"] == code.upper():
            c["active"] = not c["active"]
            _save(profile_id, coupons)
            return c["active"]
    return False


def validate_coupon(profile_id: str, code: str, total: float) -> dict:
    """
    Valida un cupón contra un total.
    Retorna {"ok": bool, "msg": str, "discount": float, "final_total": float}
    """
    from datetime import date
    code = code.strip().upper()
    coupons = _load(profile_id)
    coupon  = next((c for c in coupons if c["code"] == code), None)

    if not coupon:
        return {"ok": False, "msg": f"El cupón *{code}* no existe.", "discount": 0, "final_total": total}

    if not coupon.get("active", True):
        return {"ok": False, "msg": f"El cupón *{code}* está desactivado.", "discount": 0, "final_total": total}

    # Verificar fecha límite
    expires_at = coupon.get("expires_at", "").strip()
    if expires_at:
        try:
            exp_date = date.fromisoformat(expires_at)
            if date.today() > exp_date:
                return {"ok": False, "msg": f"El cupón *{code}* venció el {expires_at}.", "discount": 0, "final_total": total}
        except ValueError:
            pass

    max_uses = coupon.get("max_uses", 0)
    if max_uses > 0 and coupon.get("uses", 0) >= max_uses:
        return {"ok": False, "msg": f"El cupón *{code}* ya alcanzó su límite de usos.", "discount": 0, "final_total": total}

    min_total = coupon.get("min_total", 0)
    if total < min_total:
        return {
            "ok": False,
            "msg": f"El cupón *{code}* requiere un monto mínimo de ${min_total:,.0f} COP.",
            "discount": 0, "final_total": total
        }

    # Calcular descuento
    if coupon["type"] == "percent":
        discount = total * (coupon["value"] / 100)
    else:
        discount = min(coupon["value"], total)

    final_total = max(0, total - discount)

    # Registrar uso
    for c in coupons:
        if c["code"] == code:
            c["uses"] = c.get("uses", 0) + 1
    _save(profile_id, coupons)

    label = f"{coupon['value']:.0f}%" if coupon["type"] == "percent" else f"${coupon['value']:,.0f} COP"
    return {
        "ok":          True,
        "msg":         f"✅ Cupón *{code}* aplicado — {label} de descuento.",
        "discount":    discount,
        "final_total": final_total,
    }
