"""
key_panel.py  —  Panel de gestión de licencias (uso exclusivo del admin)
Ejecutar: python key_panel.py
"""
import sys
import secrets
import string
from datetime import datetime, timezone, timedelta
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QMessageBox,
    QFrame, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont

CRED_FILE = "mf-agent-2b482-firebase-adminsdk-fbsvc-937c5dc694.json"


def _base_path() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


CRED_PATH = _base_path() / CRED_FILE

BG      = "#F5F0EB"
CARD    = "#FDFAF7"
TEXT    = "#1F2937"
SUBTEXT = "#6B7280"
ACCENT  = "#1B6CA8"
SUCCESS = "#16A34A"
DANGER  = "#DC2626"
WARNING = "#D97706"
BORDER  = "#D1CBC4"

QSS = f"""
QWidget {{ background:{BG}; color:{TEXT}; font-family:'Segoe UI'; font-size:13px; }}
QTableWidget {{ background:{CARD}; border:1px solid {BORDER}; border-radius:8px; gridline-color:{BORDER}; }}
QHeaderView::section {{ background:{BG}; color:{SUBTEXT}; font-weight:600; border:none; padding:8px; }}
QLineEdit, QComboBox, QSpinBox {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:6px; padding:6px 10px;
}}
QPushButton {{
    background:{ACCENT}; color:white; border:none; border-radius:6px;
    padding:8px 16px; font-weight:600;
}}
QPushButton:hover {{ background:#1558a0; }}
QPushButton#danger {{ background:{DANGER}; }}
QPushButton#danger:hover {{ background:#b91c1c; }}
QPushButton#success {{ background:{SUCCESS}; }}
QPushButton#success:hover {{ background:#15803d; }}
QPushButton#warn {{ background:{WARNING}; }}
QPushButton#warn:hover {{ background:#b45309; }}
QTabWidget::pane {{ border:1px solid {BORDER}; border-radius:8px; }}
QTabBar::tab {{ background:{BG}; padding:8px 20px; border:1px solid {BORDER}; border-bottom:none; border-radius:6px 6px 0 0; }}
QTabBar::tab:selected {{ background:{CARD}; color:{ACCENT}; font-weight:700; }}
"""

# ── Firebase ──────────────────────────────────────────────────────────────────

def get_db():
    if not firebase_admin._apps:
        cred = credentials.Certificate(str(CRED_PATH))
        firebase_admin.initialize_app(cred)
    return firestore.client()


def gen_key() -> str:
    chars = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(chars) for _ in range(4)) for _ in range(4)]
    return "MF-" + "-".join(parts)


# ── Worker para cargar datos en background ────────────────────────────────────

class LoadWorker(QThread):
    done = pyqtSignal(list, list)

    def run(self):
        try:
            db = get_db()
            licenses = [{"id": d.id, **d.to_dict()} for d in db.collection("licenses").stream()]
            devices  = [{"id": d.id, **d.to_dict()} for d in db.collection("devices").stream()]
            self.done.emit(licenses, devices)
        except Exception as e:
            self.done.emit([], [])


# ── Diálogo: Crear Key ────────────────────────────────────────────────────────

class CreateKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Licencia")
        self.setFixedWidth(420)
        self.setStyleSheet(QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Generar Nueva Key")
        title.setStyleSheet("font-size:17px;font-weight:700;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.key_display = QLineEdit()
        self.key_display.setReadOnly(True)
        self.key_display.setText(gen_key())
        btn_regen = QPushButton("↺")
        btn_regen.setFixedWidth(36)
        btn_regen.clicked.connect(lambda: self.key_display.setText(gen_key()))
        key_row = QHBoxLayout()
        key_row.addWidget(self.key_display)
        key_row.addWidget(btn_regen)

        self.type_cb = QComboBox()
        self.type_cb.addItems(["individual", "multi", "permanente"])
        self.type_cb.currentTextChanged.connect(self._on_type_change)

        self.platform_cb = QComboBox()
        self.platform_cb.addItems(["pc", "mobile", "both"])

        self.max_devices_spin = QSpinBox()
        self.max_devices_spin.setRange(1, 50)
        self.max_devices_spin.setValue(1)

        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 3650)
        self.days_spin.setValue(30)
        self.days_spin.setSuffix(" días")

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Ej: Cliente Juan Pérez")

        self.profile_input = QLineEdit()
        self.profile_input.setPlaceholderText("Ej: 30b9707f")

        form.addRow("Key:", key_row)
        form.addRow("Tipo:", self.type_cb)
        form.addRow("Plataforma:", self.platform_cb)
        form.addRow("Máx. dispositivos:", self.max_devices_spin)
        form.addRow("Duración:", self.days_spin)
        form.addRow("Profile ID:", self.profile_input)
        form.addRow("Notas:", self.notes_input)
        layout.addLayout(form)

        self._days_label = form.labelForField(self.days_spin)
        self._on_type_change("individual")

        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.setStyleSheet(f"background:#6B7280;")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Generar y Subir")
        ok.setObjectName("success")
        ok.clicked.connect(self._create)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    def _on_type_change(self, t):
        if t == "permanente":
            self.days_spin.setEnabled(False)
            self.max_devices_spin.setValue(2)
            self.max_devices_spin.setEnabled(True)  # permitir configurar
            self.platform_cb.setCurrentText("both")
            self.platform_cb.setEnabled(False)
        elif t == "individual":
            self.days_spin.setEnabled(True)
            self.max_devices_spin.setValue(1)
            self.max_devices_spin.setEnabled(False)
            self.platform_cb.setEnabled(True)
        else:  # multi
            self.days_spin.setEnabled(True)
            self.max_devices_spin.setEnabled(True)
            self.platform_cb.setCurrentText("both")
            self.platform_cb.setEnabled(True)

    def _create(self):
        key      = self.key_display.text()
        lic_type = self.type_cb.currentText()
        platform = self.platform_cb.currentText()
        max_dev  = self.max_devices_spin.value()
        days     = self.days_spin.value()
        notes    = self.notes_input.text().strip()
        profile_id = self.profile_input.text().strip()

        if not profile_id:
            QMessageBox.warning(self, "Error", "El Profile ID es obligatorio.")
            return

        if lic_type == "permanente":
            expires_at = "never"
            # max_dev viene del spin — ya no se fuerza a 2
        else:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

        try:
            db = get_db()
            db.collection("licenses").document(key).set({
                "type": lic_type,
                "platform": platform,
                "max_devices": max_dev,
                "expires_at": expires_at,
                "days": days if lic_type != "permanente" else 0,
                "active": True,
                "notes": notes,
                "profile_id": profile_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            QMessageBox.information(self, "Éxito", f"Key generada:\n\n{key}\n\nYa puedes enviarla al cliente.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# ── Diálogo: Ampliar días ─────────────────────────────────────────────────────

class ExtendDialog(QDialog):
    def __init__(self, key_id: str, current_expires: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ampliar Licencia")
        self.setFixedWidth(340)
        self.setStyleSheet(QSS)
        self._key_id = key_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        layout.addWidget(QLabel(f"Key: {key_id}"))

        if current_expires and current_expires != "never":
            exp = datetime.fromisoformat(current_expires).replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days_left = max(0, (exp - now).days)
            layout.addWidget(QLabel(f"Vence en: {days_left} días ({exp.strftime('%d/%m/%Y')})"))
        else:
            layout.addWidget(QLabel("Licencia permanente"))

        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 3650)
        self.days_spin.setValue(30)
        self.days_spin.setSuffix(" días adicionales")

        form = QFormLayout()
        form.addRow("Agregar:", self.days_spin)
        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.setStyleSheet(f"background:#6B7280;")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Ampliar")
        ok.setObjectName("warn")
        ok.clicked.connect(self._extend)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

        self._current_expires = current_expires

    def _extend(self):
        days = self.days_spin.value()
        try:
            db = get_db()
            if self._current_expires and self._current_expires != "never":
                base = datetime.fromisoformat(self._current_expires).replace(tzinfo=timezone.utc)
                now  = datetime.now(timezone.utc)
                base = max(base, now)  # si ya venció, extiende desde hoy
            else:
                base = datetime.now(timezone.utc)

            new_exp = (base + timedelta(days=days)).isoformat()
            db.collection("licenses").document(self._key_id).update({"expires_at": new_exp})
            QMessageBox.information(self, "Listo", f"Licencia extendida {days} días.\nNuevo vencimiento: {datetime.fromisoformat(new_exp).strftime('%d/%m/%Y')}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# ── Ventana principal ─────────────────────────────────────────────────────────

class KeyPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MF Agent — Panel de Licencias")
        self.setMinimumSize(1000, 620)
        self.setStyleSheet(QSS)
        self._licenses = []
        self._devices  = []
        self._build()
        self._load()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Panel de Licencias")
        title.setStyleSheet("font-size:20px;font-weight:700;")
        header.addWidget(title)
        header.addStretch()

        btn_new = QPushButton("＋ Nueva Key")
        btn_new.setObjectName("success")
        btn_new.clicked.connect(self._create_key)

        btn_refresh = QPushButton("↺ Actualizar")
        btn_refresh.setStyleSheet(f"background:#6B7280;")
        btn_refresh.clicked.connect(self._load)

        header.addWidget(btn_new)
        header.addWidget(btn_refresh)
        root.addLayout(header)

        # Tabs
        tabs = QTabWidget()
        root.addWidget(tabs)

        # Tab 1: Licencias
        lic_tab = QWidget()
        lic_layout = QVBoxLayout(lic_tab)
        lic_layout.setContentsMargins(0, 12, 0, 0)

        self._lic_table = QTableWidget()
        self._lic_table.setColumnCount(8)
        self._lic_table.setHorizontalHeaderLabels(["Key", "Tipo", "Plataforma", "Dispositivos", "Vence", "Días restantes", "Estado", "Acciones"])
        self._lic_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._lic_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self._lic_table.setColumnWidth(7, 260)
        self._lic_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._lic_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._lic_table.verticalHeader().setVisible(False)
        self._lic_table.setAlternatingRowColors(True)
        lic_layout.addWidget(self._lic_table)
        tabs.addTab(lic_tab, "🔑  Licencias")

        # Tab 2: Dispositivos
        dev_tab = QWidget()
        dev_layout = QVBoxLayout(dev_tab)
        dev_layout.setContentsMargins(0, 12, 0, 0)

        self._dev_table = QTableWidget()
        self._dev_table.setColumnCount(6)
        self._dev_table.setHorizontalHeaderLabels(["Equipo", "Key", "IP", "Plataforma", "Registrado", "Último acceso"])
        self._dev_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._dev_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._dev_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._dev_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._dev_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._dev_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._dev_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._dev_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._dev_table.verticalHeader().setVisible(False)
        self._dev_table.setAlternatingRowColors(True)

        btn_del_dev = QPushButton("🗑 Eliminar dispositivo seleccionado")
        btn_del_dev.setObjectName("danger")
        btn_del_dev.setFixedWidth(280)
        btn_del_dev.clicked.connect(self._delete_device)

        dev_layout.addWidget(self._dev_table)
        dev_layout.addWidget(btn_del_dev)
        tabs.addTab(dev_tab, "💻  Dispositivos")

        self._status = QLabel("Cargando...")
        self._status.setStyleSheet(f"color:{SUBTEXT};font-size:11px;")
        root.addWidget(self._status)

    def _load(self):
        self._status.setText("Conectando con Firebase...")
        self._worker = LoadWorker()
        self._worker.done.connect(self._on_loaded)
        self._worker.start()

    def _on_loaded(self, licenses, devices):
        self._licenses = licenses
        self._devices  = devices
        self._populate_licenses()
        self._populate_devices()
        self._status.setText(f"✓  {len(licenses)} licencias · {len(devices)} dispositivos registrados")

    def _populate_licenses(self):
        self._lic_table.setRowCount(len(self._licenses))
        now = datetime.now(timezone.utc)

        for row, lic in enumerate(self._licenses):
            key_id   = lic.get("id", "")
            lic_type = lic.get("type", "")
            platform = lic.get("platform", "")
            max_dev  = lic.get("max_devices", 1)
            active   = lic.get("active", False)
            expires  = lic.get("expires_at", "never")
            notes    = lic.get("notes", "")

            # Contar dispositivos de esta key
            dev_count = sum(1 for d in self._devices if d.get("key_id") == key_id)

            # Días restantes
            if expires == "never":
                exp_str  = "Permanente"
                days_str = "∞"
                days_left = 99999
            else:
                try:
                    exp_dt   = datetime.fromisoformat(expires).replace(tzinfo=timezone.utc)
                    days_left = (exp_dt - now).days
                    exp_str  = exp_dt.strftime("%d/%m/%Y")
                    days_str = str(max(0, days_left))
                except Exception:
                    exp_str  = expires
                    days_str = "?"
                    days_left = 0

            estado = "✅ Activa" if active else "🚫 Inactiva"
            if active and days_left <= 0 and expires != "never":
                estado = "⛔ Vencida"
            elif active and days_left <= 7 and expires != "never":
                estado = "⚠️ Por vencer"

            self._lic_table.setItem(row, 0, QTableWidgetItem(f"{key_id}  {('— '+notes) if notes else ''}"))
            self._lic_table.setItem(row, 1, QTableWidgetItem(lic_type))
            self._lic_table.setItem(row, 2, QTableWidgetItem(platform))
            self._lic_table.setItem(row, 3, QTableWidgetItem(f"{dev_count}/{max_dev}"))
            self._lic_table.setItem(row, 4, QTableWidgetItem(exp_str))

            days_item = QTableWidgetItem(days_str)
            if days_left <= 7 and expires != "never":
                days_item.setForeground(QColor(DANGER))
            self._lic_table.setItem(row, 5, days_item)
            self._lic_table.setItem(row, 6, QTableWidgetItem(estado))

            # Botones de acción
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            btn_extend = QPushButton("＋ Días")
            btn_extend.setObjectName("warn")
            btn_extend.setFixedHeight(28)
            btn_extend.clicked.connect(lambda _, k=key_id, e=expires: self._extend_key(k, e))

            btn_add_dev = QPushButton("💻 ＋")
            btn_add_dev.setObjectName("success")
            btn_add_dev.setFixedHeight(28)
            btn_add_dev.setFixedWidth(52)
            btn_add_dev.setToolTip("Aumentar máx. dispositivos")
            btn_add_dev.clicked.connect(lambda _, k=key_id, m=max_dev: self._add_device_slot(k, m))

            btn_toggle = QPushButton("🚫 Revocar" if active else "✅ Activar")
            btn_toggle.setObjectName("danger" if active else "success")
            btn_toggle.setFixedHeight(28)
            btn_toggle.clicked.connect(lambda _, k=key_id, a=active: self._toggle_key(k, a))

            btn_copy = QPushButton("📋")
            btn_copy.setFixedWidth(32)
            btn_copy.setFixedHeight(28)
            btn_copy.setStyleSheet(f"background:#6B7280;")
            btn_copy.clicked.connect(lambda _, k=key_id: QApplication.clipboard().setText(k))

            btn_delete = QPushButton("🗑")
            btn_delete.setObjectName("danger")
            btn_delete.setFixedWidth(32)
            btn_delete.setFixedHeight(28)
            btn_delete.clicked.connect(lambda _, k=key_id: self._delete_key(k))

            actions_layout.addWidget(btn_extend)
            actions_layout.addWidget(btn_add_dev)
            actions_layout.addWidget(btn_toggle)
            actions_layout.addWidget(btn_copy)
            actions_layout.addWidget(btn_delete)
            self._lic_table.setCellWidget(row, 7, actions)

    def _populate_devices(self):
        self._dev_table.setRowCount(len(self._devices))
        for row, dev in enumerate(self._devices):
            last = dev.get("last_seen", "")
            registered = dev.get("registered_at", "")
            try:
                last = datetime.fromisoformat(last).strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass
            try:
                registered = datetime.fromisoformat(registered).strftime("%d/%m/%Y")
            except Exception:
                pass

            key_id = dev.get("key_id", "")
            # Buscar notas de la key para mostrar a quien pertenece
            lic = next((l for l in self._licenses if l.get("id") == key_id), {})
            notes = lic.get("notes", "")
            key_display = f"{key_id}" + (f"  ({notes})" if notes else "")

            self._dev_table.setItem(row, 0, QTableWidgetItem(dev.get("hostname", "desconocido")))
            self._dev_table.setItem(row, 1, QTableWidgetItem(key_display))
            self._dev_table.setItem(row, 2, QTableWidgetItem(dev.get("ip", "—")))
            self._dev_table.setItem(row, 3, QTableWidgetItem(dev.get("platform", "")))
            self._dev_table.setItem(row, 4, QTableWidgetItem(registered))
            self._dev_table.setItem(row, 5, QTableWidgetItem(last))

    def _create_key(self):
        dlg = CreateKeyDialog(self)
        if dlg.exec():
            self._load()

    def _add_device_slot(self, key_id: str, current_max: int):
        new_max, ok = __import__('PyQt6.QtWidgets', fromlist=['QInputDialog']).QInputDialog.getInt(
            self, "Ampliar dispositivos",
            f"Máx. dispositivos actuales: {current_max}\nNuevo máximo:",
            value=current_max + 1, min=current_max + 1, max=100
        )
        if ok:
            try:
                get_db().collection("licenses").document(key_id).update({"max_devices": new_max})
                QMessageBox.information(self, "Listo", f"✅ Ahora permite {new_max} dispositivos.")
                self._load()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _extend_key(self, key_id: str, expires: str):
        dlg = ExtendDialog(key_id, expires, self)
        if dlg.exec():
            self._load()

    def _toggle_key(self, key_id: str, currently_active: bool):
        action = "revocar" if currently_active else "activar"
        box = QMessageBox(self)
        box.setWindowTitle("Confirmar")
        box.setText(f"¿{action.capitalize()} la key {key_id}?")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            try:
                get_db().collection("licenses").document(key_id).update({"active": not currently_active})
                self._load()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _delete_key(self, key_id: str):
        box = QMessageBox(self)
        box.setWindowTitle("Eliminar Key")
        box.setText(f"¿Eliminar permanentemente la key:\n{key_id}?\n\nTambién se eliminarán todos sus dispositivos registrados.")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            try:
                db = get_db()
                db.collection("licenses").document(key_id).delete()
                for dev in [d for d in self._devices if d.get("key_id") == key_id]:
                    db.collection("devices").document(dev["id"]).delete()
                self._load()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _delete_device(self):
        row = self._dev_table.currentRow()
        if row < 0:
            return
        dev = self._devices[row]
        box = QMessageBox(self)
        box.setWindowTitle("Confirmar")
        box.setText(f"¿Eliminar dispositivo de {dev.get('hostname', '')}?\nEl cliente podrá registrar otro dispositivo.")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            try:
                get_db().collection("devices").document(dev["id"]).delete()
                self._load()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = KeyPanel()
    window.show()
    sys.exit(app.exec())
