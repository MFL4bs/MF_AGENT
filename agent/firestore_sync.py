"""
firestore_sync.py
Sincroniza inventario y ventas locales → Firestore al iniciar sesión.
"""
from __future__ import annotations
from PyQt6.QtCore import QThread, pyqtSignal

STORAGE_BUCKET = "mf-agent-2b482.appspot.com"
CRED_FILE      = "mf-agent-2b482-firebase-adminsdk-fbsvc-3eff30e990.json"
APP_NAME       = "data_sync"

import threading as _threading
_init_lock = _threading.Lock()


def _get_data_app():
    """Inicializa (o reutiliza) el Firebase app con Storage habilitado."""
    import firebase_admin
    from firebase_admin import credentials
    from pathlib import Path
    import sys

    cred_path = (Path(sys._MEIPASS) if getattr(sys, "frozen", False)
                 else Path(__file__).parent.parent) / CRED_FILE

    with _init_lock:
        try:
            return firebase_admin.get_app(APP_NAME)
        except ValueError:
            pass
        try:
            return firebase_admin.initialize_app(
                credentials.Certificate(str(cred_path)),
                name=APP_NAME,
                options={"storageBucket": STORAGE_BUCKET},
            )
        except ValueError:
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


def _notify_sale_whatsapp(invoice: dict):
    """Envía notificación al admin por WhatsApp cuando llega una venta nueva del móvil."""
    try:
        import urllib.request, json
        from pathlib import Path
        import sys

        env_path = (Path(sys.executable).parent if getattr(sys, "frozen", False)
                    else Path(__file__).parent.parent) / ".env"
        env = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()

        admin_phone = env.get("ADMIN_PHONES", env.get("OWNER_PHONE", ""))
        if not admin_phone:
            return

        items = invoice.get("items", [])
        items_txt = "\n".join(
            f"  \u2022 {i.get('product_name', '')} x{i.get('quantity', 1)} = ${i.get('subtotal', 0):.2f}"
            for i in items
        )
        customer = invoice.get("customer") or "Consumidor final"
        total    = invoice.get("total", 0)
        inv_id   = invoice.get("invoice_id", "")
        channel  = invoice.get("channel", "movil")

        msg = (
            f"\U0001f4f1 *Nueva venta desde {channel}*\n"
            f"ID: {inv_id}\n"
            f"Cliente: {customer}\n"
            f"{items_txt}\n"
            f"*Total: ${total:.2f}*"
        )
        payload = json.dumps({"phone": admin_phone, "message": msg}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:3000/send",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
        print(f"[Notify] Venta {inv_id} notificada al admin")
    except Exception as e:
        print(f"[Notify] No se pudo notificar venta movil: {e}")


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


class FirestoreListener(QThread):
    """Escucha en tiempo real la colección 'invoices' en Firestore.
    Cuando detecta una venta nueva del móvil, notifica al admin por WhatsApp."""
    # Usamos str para cruzar el hilo gRPC → hilo Qt de forma segura (dict causa crash)
    new_sale = pyqtSignal(str)

    def __init__(self, profile_id: str):
        super().__init__()
        self._profile_id = profile_id
        self._stop_flag  = False
        self._unsubscribe = None

    def run(self):
        try:
            import json
            from firebase_admin import firestore
            from agent.local_sales import list_invoices
            import threading

            db = firestore.client(app=_get_data_app())

            # IDs que ya existen localmente al arrancar — no notificar estos
            known_ids = set(
                r.get("invoice_id", r.get("sale_id", ""))
                for r in list_invoices(self._profile_id, limit=9999)
            )
            print(f"[Listener] Arrancando, conocidos: {len(known_ids)} ventas")

            self._stop_event = threading.Event()

            def on_snapshot(col_snap, changes, read_time):
                for change in changes:
                    try:
                        if change.type.name == "REMOVED":
                            # Al eliminar, to_dict() viene vacio — usar document.id
                            inv_id = change.document.id
                            print(f"[Listener] Venta eliminada desde movil: {inv_id}")
                            known_ids.discard(inv_id)
                            try:
                                from agent.local_sales import delete_record
                                delete_record(self._profile_id, inv_id)
                            except Exception as e:
                                print(f"[Listener] Error borrando venta local: {e}")
                            self.new_sale.emit(json.dumps({"__deleted__": inv_id}, default=str))

                        elif change.type.name == "ADDED":
                            inv = change.document.to_dict()
                            inv_id = inv.get("invoice_id", "")
                            if inv_id and inv_id not in known_ids:
                                known_ids.add(inv_id)
                                print(f"[Listener] Nueva venta detectada: {inv_id}")
                                try:
                                    from agent.local_sales import record_invoice
                                    record_invoice(self._profile_id, inv)
                                except Exception as e:
                                    print(f"[Listener] Error guardando venta local: {e}")
                                # Solo notificar si la venta NO viene del PC
                                if inv.get("source") != "pc":
                                    _notify_sale_whatsapp(inv)
                                self.new_sale.emit(json.dumps(inv, default=str))

                    except Exception as e:
                        print(f"[Listener] Error procesando cambio: {e}")

            col_ref = (db.collection("invoices")
                         .where(filter=firestore.FieldFilter("profile_id", "==", self._profile_id)))
            self._unsubscribe = col_ref.on_snapshot(on_snapshot)
            print("[Listener] Escuchando Firestore en tiempo real...")

            # Bloquear el hilo hasta que stop() libere el evento
            self._stop_event.wait()

        except Exception as e:
            print(f"[Listener] Error: {e}")

    def stop(self):
        self._stop_flag = True
        if hasattr(self, '_stop_event'):
            self._stop_event.set()
        if self._unsubscribe:
            try:
                self._unsubscribe()
            except Exception:
                pass


class RestoreWorker(QThread):
    """
    Restaura todos los datos desde Firestore al local cuando se activa
    la key en un PC nuevo (carpeta data/ vacía).
    Descarga: perfil + usuarios → profiles.json
              inventario        → data/{profile_id}/inventory.json
              ventas            → data/{profile_id}/sales.json
    """
    done = pyqtSignal(bool, str)  # ok, mensaje

    def __init__(self, key: str, profile_id: str):
        super().__init__()
        self._key        = key
        self._profile_id = profile_id

    def run(self):
        try:
            from firebase_admin import firestore
            from pathlib import Path
            import json, sys

            db = firestore.client(app=_get_data_app())

            # ── 1. Perfil + usuarios ──────────────────────────────────────────
            prof_doc = db.collection("profiles").document(self._profile_id).get()
            if not prof_doc.exists:
                self.done.emit(False, "No se encontró el perfil en Firestore.")
                return

            prof_data = prof_doc.to_dict()
            profile_name = prof_data.get("name", "Mi Negocio")

            # Usuarios desde profile_users
            users_snap = (
                db.collection("profile_users")
                .where("profile_id", "==", self._profile_id)
                .get()
            )
            users = [
                {
                    "username":      d.to_dict().get("username", ""),
                    "password_hash": d.to_dict().get("password_hash", ""),
                    "role":          d.to_dict().get("role", "vendedor"),
                }
                for d in users_snap
            ]

            # Si no hay usuarios en profile_users, intentar desde profiles.users
            if not users:
                users = prof_data.get("users", [])

            # Escribir profiles.json local
            from agent.profiles import _data_root
            data_root = _data_root()
            data_root.mkdir(parents=True, exist_ok=True)
            profiles_file = data_root / "profiles.json"

            existing = json.loads(profiles_file.read_text(encoding="utf-8")) if profiles_file.exists() else {"profiles": []}
            # Reemplazar o agregar el perfil
            existing["profiles"] = [p for p in existing["profiles"] if p["id"] != self._profile_id]
            existing["profiles"].append({
                "id":    self._profile_id,
                "name":  profile_name,
                "users": users,
            })
            profiles_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

            # ── 2. Inventario ─────────────────────────────────────────────────
            inv_snap = (
                db.collection("inventory")
                .where("profile_id", "==", self._profile_id)
                .get()
            )
            products = [d.to_dict() for d in inv_snap if "sku" in d.to_dict()]

            profile_dir = data_root / self._profile_id
            profile_dir.mkdir(parents=True, exist_ok=True)
            inv_file = profile_dir / "inventory.json"
            inv_file.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")

            # ── 3. Ventas ─────────────────────────────────────────────────────
            sales_snap = (
                db.collection("invoices")
                .where("profile_id", "==", self._profile_id)
                .get()
            )
            invoices = [d.to_dict() for d in sales_snap if d.to_dict().get("invoice_id")]

            sales_file = profile_dir / "sales.json"
            sales_file.write_text(json.dumps(invoices, ensure_ascii=False, indent=2), encoding="utf-8")

            self.done.emit(
                True,
                f"✅ Restaurado: {len(products)} productos, "
                f"{len(invoices)} ventas, {len(users)} usuarios"
            )
        except Exception as e:
            self.done.emit(False, str(e))


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
                        try:
                            lic_app = firebase_admin.initialize_app(
                                credentials.Certificate(str(cred_path)), name=lic_app_name)
                        except ValueError:
                            lic_app = firebase_admin.get_app(lic_app_name)
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

            # Sync usuarios del perfil → profile_users
            from agent.profiles import get_profile
            profile_data = get_profile(self._profile_id)
            users = profile_data.get("users", []) if profile_data else []
            if users:
                batch = db.batch()
                for u in users:
                    doc_id = f"{self._profile_id}_{u['username']}"
                    ref = db.collection("profile_users").document(doc_id)
                    batch.set(ref, {
                        "profile_id": self._profile_id,
                        "username": u["username"],
                        "password_hash": u["password_hash"],
                        "role": u.get("role", "vendedor"),
                    }, merge=True)
                batch.commit()

            self.done.emit(True, f"Sync OK: {len(products)} productos, {len(invoices)} ventas, {len(users)} usuarios")
        except Exception as e:
            self.done.emit(False, str(e))
