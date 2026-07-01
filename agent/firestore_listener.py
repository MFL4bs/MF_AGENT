"""
firestore_listener.py
Escucha cambios en Firestore (inventory) y los aplica al JSON local.
Permite que agregar/eliminar desde el móvil se refleje en el PC.
"""
from __future__ import annotations
import threading
from PyQt6.QtCore import QObject, pyqtSignal


class FirestoreListener(QObject):
    product_changed = pyqtSignal()  # emite cuando hay cambio → refresca UI

    def __init__(self, profile_id: str, parent=None):
        super().__init__(parent)
        self._profile_id = profile_id
        self._unsubscribe = None
        self._thread = None
        self._stopped = False

    def start(self):
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self):
        self._stopped = True
        if self._unsubscribe:
            try:
                self._unsubscribe()
            except Exception:
                pass
            self._unsubscribe = None

    def _listen(self):
        try:
            import firebase_admin
            from firebase_admin import firestore
            from agent.firestore_sync import _get_data_app

            data_app = _get_data_app()

            db = firestore.client(app=data_app)
            from agent.local_inventory import upsert_product, delete_product

            def on_snapshot(col_snapshot, changes, read_time):
                if self._stopped:
                    return
                from google.cloud.firestore_v1.watch import ChangeType
                changed = False
                for change in changes:
                    try:
                        doc = change.document
                        data = doc.to_dict()
                        if not data or data.get("profile_id") != self._profile_id:
                            continue
                        if change.type == ChangeType.REMOVED:
                            delete_product(self._profile_id, data.get("sku", ""))
                        else:  # ADDED or MODIFIED
                            upsert_product(self._profile_id, data)
                        changed = True
                    except Exception as e:
                        print(f"[FirestoreListener] Error en cambio: {e}")
                # Un solo emit por batch, no uno por producto
                if changed and not self._stopped:
                    self.product_changed.emit()

            query = db.collection("inventory").where(filter=firestore.FieldFilter("profile_id", "==", self._profile_id))
            self._unsubscribe = query.on_snapshot(on_snapshot)

            # Mantener el hilo vivo
            import time
            while self._unsubscribe:
                time.sleep(1)
        except Exception as e:
            print(f"[FirestoreListener] Error: {e}")
