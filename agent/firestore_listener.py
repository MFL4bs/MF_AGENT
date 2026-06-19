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

    def start(self):
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self):
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

    def _listen(self):
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
            from pathlib import Path
            import sys

            cred_file = "mf-agent-2b482-firebase-adminsdk-fbsvc-3eff30e990.json"
            cred_path = (Path(sys._MEIPASS) if getattr(sys, "frozen", False)
                         else Path(__file__).parent.parent) / cred_file

            app_name = "data_sync"
            if app_name not in [a.name for a in firebase_admin._apps.values()]:
                data_app = firebase_admin.initialize_app(
                    credentials.Certificate(str(cred_path)), name=app_name)
            else:
                data_app = firebase_admin.get_app(app_name)

            db = firestore.client(app=data_app)
            from agent.local_inventory import upsert_product, delete_product

            def on_snapshot(col_snapshot, changes, read_time):
                from google.cloud.firestore_v1.watch import ChangeType
                for change in changes:
                    doc = change.document
                    data = doc.to_dict()
                    if data.get("profile_id") != self._profile_id:
                        continue
                    if change.type == ChangeType.REMOVED:
                        delete_product(self._profile_id, data.get("sku", ""))
                    else:  # ADDED or MODIFIED
                        upsert_product(self._profile_id, data)
                    self.product_changed.emit()

            query = db.collection("inventory").where(filter=firestore.FieldFilter("profile_id", "==", self._profile_id))
            self._unsubscribe = query.on_snapshot(on_snapshot)

            # Mantener el hilo vivo
            import time
            while self._unsubscribe:
                time.sleep(1)
        except Exception as e:
            print(f"[FirestoreListener] Error: {e}")
