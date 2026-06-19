"""
firestore_sync.py
Sincroniza inventario y ventas locales → Firestore al iniciar sesión.
"""
from __future__ import annotations
from PyQt6.QtCore import QThread, pyqtSignal

STORAGE_BUCKET = "mf-agent-2b482.appspot.com"
CRED_FILE      = "mf-agent-2b482-firebase-adminsdk-fbsvc-3eff30e990.json"
APP_NAME       = "data_sync"


def _get_data_app():
    """Inicializa (o reutiliza) el Firebase app con Storage habilitado."""
    import firebase_admin
    from firebase_admin import credentials
    from pathlib import Path
    import sys

    cred_path = (Path(sys._MEIPASS) if getattr(sys, "frozen", False)
                 else Path(__file__).parent.parent) / CRED_FILE

    if APP_NAME not in [a.name for a in firebase_admin._apps.values()]:
        return firebase_admin.initialize_app(
            credentials.Certificate(str(cred_path)),
            name=APP_NAME,
            options={"storageBucket": STORAGE_BUCKET},
        )
    return firebase_admin.get_app(APP_NAME)


def upload_invoice_pdf(profile_id: str, invoice_id: str, pdf_path: str):
    """Sube el PDF a Storage y guarda la URL en la coleccion 'pdf'."""
    try:
        from firebase_admin import storage, firestore
        from pathlib import Path
        app = _get_data_app()

        # Nombre del archivo = invoice_id (ej: INV-A1B2C3.pdf)
        filename = f"{invoice_id}.pdf"
        bucket = storage.bucket(app=app)
        blob = bucket.blob(f"pdf/{filename}")
        blob.upload_from_filename(pdf_path, content_type="application/pdf")
        blob.make_public()
        url = blob.public_url

        # Guardar en coleccion 'pdf' con doc ID = invoice_id
        db = firestore.client(app=app)
        db.collection("pdf").document(invoice_id).set({
            "invoice_id": invoice_id,
            "profile_id": profile_id,
            "pdf_url": url,
            "filename": filename,
        })
        print(f"[Storage] PDF subido: {url}")
    except Exception as e:
        print(f"[Storage] Error subiendo PDF {invoice_id}: {e}")


def delete_product_firestore(profile_id: str, sku: str):
    """Borra un producto de Firestore."""
    try:
        from firebase_admin import firestore
        db = firestore.client(app=_get_data_app())
        db.collection("inventory").document(f"{profile_id}_{sku}").delete()
    except Exception as e:
        print(f"[Firestore] Error al borrar {sku}: {e}")


class PullWorker(QThread):
    """Jala productos y ventas desde Firestore → JSON local."""
    done = pyqtSignal(bool, str, list)

    def __init__(self, profile_id: str):
        super().__init__()
        self._profile_id = profile_id

    def run(self):
        try:
            from firebase_admin import firestore
            db = firestore.client(app=_get_data_app())

            from agent.local_inventory import list_products, upsert_product, delete_product
            from agent.local_sales import list_invoices, record_invoice, delete_record

            changes = []

            # ── Inventario ────────────────────────────────────────────────
            snap = db.collection("inventory") \
                .where(filter=firestore.FieldFilter("profile_id", "==", self._profile_id)) \
                .get()
            remote = {d.to_dict()["sku"]: d.to_dict() for d in snap if "sku" in d.to_dict()}
            local  = {p["sku"]: p for p in list_products(self._profile_id)}

            for sku, rp in remote.items():
                lp = local.get(sku)
                if lp is None:
                    upsert_product(self._profile_id, rp)
                    changes.append(f"➕ {rp.get('name', sku)} (nuevo)")
                elif (lp.get("stock") != rp.get("stock") or
                      lp.get("price") != rp.get("price") or
                      lp.get("name")  != rp.get("name")):
                    upsert_product(self._profile_id, rp)
                    changes.append(f"✏️ {rp.get('name', sku)} (modificado)")

            for sku in list(local.keys()):
                if sku not in remote:
                    delete_product(self._profile_id, sku)
                    changes.append(f"🗑️ {local[sku].get('name', sku)} (eliminado)")

            # ── Ventas ────────────────────────────────────────────────────
            snap_inv = db.collection("invoices") \
                .where(filter=firestore.FieldFilter("profile_id", "==", self._profile_id)) \
                .get()
            remote_inv = {d.to_dict().get("invoice_id"): d.to_dict()
                          for d in snap_inv if d.to_dict().get("invoice_id")}
            local_inv  = {r.get("invoice_id"): r
                          for r in list_invoices(self._profile_id, limit=9999)}

            for inv_id, inv in remote_inv.items():
                if inv_id not in local_inv:
                    record_invoice(self._profile_id, inv)
                    changes.append(f"🧾 Venta {inv_id} (nueva desde móvil)")

            for inv_id in list(local_inv.keys()):
                if inv_id not in remote_inv:
                    delete_record(self._profile_id, inv_id)
                    changes.append(f"🗑️ Venta {inv_id} (eliminada desde móvil)")

            msg = f"{len(changes)} cambio(s) aplicado(s)" if changes else "Todo al día ✅"
            self.done.emit(True, msg, changes)
        except Exception as e:
            self.done.emit(False, str(e), [])


class SyncWorker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, profile_id: str):
        super().__init__()
        self._profile_id = profile_id

    def run(self):
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
            from pathlib import Path
            import sys

            db = firestore.client(app=_get_data_app())

            from agent.local_inventory import list_products
            from agent.local_sales import list_invoices
            from agent.profiles import get_profile

            products = list_products(self._profile_id)
            invoices = list_invoices(self._profile_id, limit=500)
            profile  = get_profile(self._profile_id)

            # Sync perfil
            if profile:
                from lic_manager.license_manager import _load_local
                local_lic = _load_local()
                key = local_lic.get('key', '')
                db.collection('profiles').document(self._profile_id).set({
                    'id': self._profile_id,
                    'name': profile.get('name', self._profile_id),
                    'key': key,
                }, merge=True)
                if key:
                    lic_cred_file = "mf-agent-2b482-firebase-adminsdk-fbsvc-937c5dc694.json"
                    cred_path = (Path(sys._MEIPASS) if getattr(sys, "frozen", False)
                                 else Path(__file__).parent.parent) / lic_cred_file
                    lic_app_name = "lic_sync"
                    if lic_app_name not in [a.name for a in firebase_admin._apps.values()]:
                        lic_app = firebase_admin.initialize_app(
                            credentials.Certificate(str(cred_path)), name=lic_app_name)
                    else:
                        lic_app = firebase_admin.get_app(lic_app_name)
                    lic_db = firestore.client(app=lic_app)
                    lic_db.collection('licenses').document(key).update({
                        'profile_id': self._profile_id,
                    })

            # Sync inventario
            if products:
                batch = db.batch()
                for p in products:
                    p = dict(p)
                    p["profile_id"] = self._profile_id
                    ref = db.collection("inventory").document(f"{self._profile_id}_{p['sku']}")
                    batch.set(ref, p, merge=True)
                batch.commit()

            # Sync ventas
            if invoices:
                batch = db.batch()
                for inv in invoices:
                    inv = dict(inv)
                    inv["profile_id"] = self._profile_id
                    inv_id = inv.get("invoice_id") or inv.get("sale_id")
                    if inv_id:
                        ref = db.collection("invoices").document(inv_id)
                        batch.set(ref, inv, merge=True)
                batch.commit()

            self.done.emit(True, f"Sync OK: {len(products)} productos, {len(invoices)} ventas")
        except Exception as e:
            self.done.emit(False, str(e))
