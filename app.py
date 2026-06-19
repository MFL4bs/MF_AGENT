import sys
import os
import threading
import uvicorn
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QLineEdit,
    QDialog, QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox,
    QHeaderView, QFrame, QMessageBox, QGraphicsDropShadowEffect, QFileDialog,
    QScrollArea, QTextEdit, QStackedWidget, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QUrl
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap
from pathlib import Path

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

from agent.local_inventory import (
    list_products, get_product, upsert_product,
    update_product, delete_product, low_stock_products, next_sku
)
from agent.local_sales import record_invoice, list_invoices, delete_record, update_record
from models.schemas import Product, ProductUpdate, Sale, Invoice, InvoiceItem
from login import LoginScreen, ProfileManagerScreen
import main as api_main

# ── Colores ───────────────────────────────────────────────────────────────────
BG        = "#F5F0EB"
SIDEBAR   = "#EDE8E3"
CARD      = "#FDFAF7"
ACCENT    = "#6B7280"
ACCENT2   = "#1B6CA8"
TEXT      = "#1F2937"
SUBTEXT   = "#6B7280"
SUCCESS   = "#16A34A"
WARNING   = "#D97706"
DANGER    = "#DC2626"
BORDER    = "#D1CBC4"

# ── Logo helper ──────────────────────────────────────────────────────────────
LOGO_PATH = Path(__file__).parent / "MF_LABS.png"

def _make_logo_pixmap(size: int) -> QPixmap | None:
    from PyQt6.QtGui import QPainter, QPainterPath
    pix = QPixmap(str(LOGO_PATH))
    if pix.isNull():
        return None
    rounded = QPixmap(size, size)
    rounded.fill(Qt.GlobalColor.transparent)
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pix.scaled(size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation))
    painter.end()
    return rounded

# ── Estado del bot ───────────────────────────────────────────────────────────
bot_enabled = True

ENV_PATH = Path(__file__).parent / ".env"

def _read_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env

def _write_env(updates: dict):
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    written = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                written.add(k)
                continue
        new_lines.append(line)
    for k, v in updates.items():
        if k not in written:
            new_lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

def _whatsapp_configured() -> bool:
    """Verifica si el bridge Node.js existe y tiene sus dependencias."""
    bridge_dir = Path(__file__).parent / "whatsapp_bridge"
    return (bridge_dir / "index.js").exists() and (bridge_dir / "node_modules").exists()


def _msg(parent, title: str, text: str, kind: str = "warning"):
    """QMessageBox con estilo nativo (evita texto blanco sobre blanco)."""
    box = QMessageBox(parent)
    box.setStyleSheet("""
        QMessageBox { background: #FFFFFF; }
        QMessageBox QLabel { color: #1F2937; font-size: 13px; }
        QMessageBox QPushButton {
            background: #6B7280; color: white; border: none;
            border-radius: 6px; padding: 6px 18px; font-size: 13px;
        }
        QMessageBox QPushButton:hover { background: #1B6CA8; }
    """)
    box.setWindowTitle(title)
    box.setText(text)
    if kind == "question":
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.exec()
    return box.result()


QSS = f"""
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget#sidebar {{ background: {SIDEBAR}; border-right: 1px solid {BORDER}; }}
QWidget#card {{ background: {CARD}; border-radius: 16px; }}
QLabel#title {{ color: {TEXT}; font-size: 22px; font-weight: 700; }}
QLabel#subtitle {{ color: {SUBTEXT}; font-size: 13px; }}
QLabel#stat_value {{ color: {TEXT}; font-size: 28px; font-weight: 700; }}
QLabel#stat_label {{ color: {SUBTEXT}; font-size: 12px; }}
QLabel#nav_title {{ color: {TEXT}; font-size: 16px; font-weight: 700; letter-spacing: 1px; }}
QPushButton#nav_btn {{
    background: transparent; color: {SUBTEXT};
    border: none; border-radius: 10px;
    padding: 10px 16px; text-align: left; font-size: 14px;
}}
QPushButton#nav_btn:hover {{ background: {CARD}; color: {TEXT}; }}
QPushButton#nav_btn:checked {{ background: #1B6CA8; color: white; font-weight: 600; }}
QPushButton#primary {{
    background: {ACCENT}; color: white; border: none;
    border-radius: 10px; padding: 10px 22px; font-size: 14px; font-weight: 600;
}}
QPushButton#primary:hover {{ background: #1B6CA8; }}
QPushButton#danger {{
    background: {DANGER}; color: white; border: none;
    border-radius: 8px; padding: 6px 14px; font-size: 13px;
}}
QPushButton#danger:hover {{ background: #1B6CA8; }}
QPushButton#edit {{
    background: {ACCENT}; color: white; border: none;
    border-radius: 8px; padding: 6px 14px; font-size: 13px;
}}
QPushButton#edit:hover {{ background: #1B6CA8; }}
QPushButton#bot_on {{
    background: {SUCCESS}; color: white; border: none;
    border-radius: 10px; padding: 9px 16px; font-size: 13px; font-weight: 600;
}}
QPushButton#bot_on:hover {{ background: #15803d; }}
QPushButton#bot_off {{
    background: {DANGER}; color: white; border: none;
    border-radius: 10px; padding: 9px 16px; font-size: 13px; font-weight: 600;
}}
QPushButton#bot_off:hover {{ background: #b91c1c; }}
QPushButton#bot_restart {{
    background: {WARNING}; color: white; border: none;
    border-radius: 10px; padding: 9px 16px; font-size: 13px; font-weight: 600;
}}
QPushButton#bot_restart:hover {{ background: #b45309; }}
QPushButton#whatsapp {{
    background: #25D366; color: white; border: none;
    border-radius: 10px; padding: 9px 16px; font-size: 13px; font-weight: 600;
}}
QPushButton#github {{
    background: #24292e; color: white; border: none;
    border-radius: 10px; padding: 8px 16px; font-size: 13px; font-weight: 600;
}}
QPushButton#github:hover {{ background: #1B6CA8; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:horizontal {{ background: {BG}; height: 6px; border-radius: 3px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 3px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QLineEdit#search {{
    background: {CARD}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 8px 14px; font-size: 14px;
}}
QLineEdit#search:focus {{ border: 1px solid {ACCENT}; }}
QTableWidget {{
    background: {CARD}; color: {TEXT}; border: none;
    border-radius: 12px; gridline-color: {BORDER};
    font-size: 13px;
}}
QTableWidget::item {{ padding: 8px; border-bottom: 1px solid {BORDER}; }}
QTableWidget::item:selected {{ background: {ACCENT}; color: white; }}
QHeaderView::section {{
    background: {SIDEBAR}; color: {SUBTEXT};
    border: none; padding: 10px 8px; font-size: 12px; font-weight: 600;
}}
QScrollBar:vertical {{ background: {BG}; width: 6px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px; }}
QDialog {{ background: {CARD}; }}
QDialog QLabel {{ color: {TEXT}; font-size: 13px; }}
QDialog QWidget {{ background: {CARD}; }}
QFormLayout QLabel {{ color: {TEXT}; font-size: 13px; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {SIDEBAR}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 7px 12px; font-size: 13px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{ background: {SIDEBAR}; color: {TEXT}; selection-background-color: {ACCENT}; }}
"""


# ── Worker que lee stdout del bridge Node.js ─────────────────────────────────
class BridgeWorker(QThread):
    output = pyqtSignal(str)
    connected = pyqtSignal()

    def __init__(self, bridge_dir: str):
        super().__init__()
        self._dir = bridge_dir
        self._proc = None

    def run(self):
        import subprocess
        # Liberar puerto 3000 si está ocupado
        try:
            result = subprocess.run(
                ["netstat", "-aon"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if ":3000 " in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid.isdigit() and pid != "0":
                        subprocess.run(["taskkill", "/F", "/PID", pid],
                                       capture_output=True, timeout=5)
        except Exception:
            pass
        self._proc = subprocess.Popen(
            ["node", "index.js"],
            cwd=self._dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in self._proc.stdout:
            self.output.emit(line.rstrip())
            if "listo" in line.lower() or "ready" in line.lower() or "conectado" in line.lower():
                self.connected.emit()

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


# ── Modal Conectar WhatsApp ───────────────────────────────────────────────────
class WhatsAppConfigDialog(QDialog):
    bridge_connected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Conectar WhatsApp")
        self.setMinimumSize(700, 600)
        self.resize(1000, 820)
        self.setStyleSheet(QSS)
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("📱  Conectar WhatsApp")
        title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        info = QLabel(
            "Haz clic en <b>Iniciar Bridge</b>. Aparecerá un código QR abajo.\n"
            "Ábrelo en WhatsApp → Dispositivos vinculados → Vincular dispositivo."
        )
        info.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Campo número admin
        env = _read_env()
        num_row = QHBoxLayout()
        num_lbl = QLabel("📞  Tu número admin:")
        num_lbl.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 600;")
        self.admin_number = QLineEdit(env.get("ADMIN_PHONES", env.get("OWNER_PHONE", "")))
        self.admin_number.setPlaceholderText("+521234567890")
        self.admin_number.setFixedWidth(200)
        btn_save_num = QPushButton("💾")
        btn_save_num.setObjectName("primary")
        btn_save_num.setFixedHeight(34)
        btn_save_num.setFixedWidth(50)
        btn_save_num.clicked.connect(self._save_number)
        num_row.addWidget(num_lbl)
        num_row.addWidget(self.admin_number)
        num_row.addWidget(btn_save_num)
        num_row.addStretch()
        layout.addLayout(num_row)

        self.status_lbl = QLabel("⚪  Bridge detenido")
        self.status_lbl.setStyleSheet(f"color: {SUBTEXT}; font-size: 13px; font-weight: 600;")
        layout.addWidget(self.status_lbl)

        # Consola de output
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(
            f"background: #1a1a2e; color: #ffffff; font-family: Consolas, monospace;"
            f"font-size: 8px; border-radius: 8px; padding: 8px;"
        )
        layout.addWidget(self.console, 1)

        btns = QHBoxLayout()
        self.btn_start = QPushButton("▶  Iniciar")
        self.btn_start.setObjectName("whatsapp")
        self.btn_start.clicked.connect(self._start)

        self.btn_stop = QPushButton("⏹  Detener")
        self.btn_stop.setObjectName("danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)

        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("primary")
        btn_close.clicked.connect(self.accept)

        btns.addWidget(self.btn_start)
        btns.addWidget(self.btn_stop)
        btns.addStretch()
        btns.addWidget(btn_close)
        layout.addLayout(btns)

    def _save_number(self):
        num = self.admin_number.text().strip()
        if not num:
            return
        _write_env({"ADMIN_PHONES": num, "OWNER_PHONE": num})
        # Actualizar en memoria sin reiniciar
        try:
            import main as api_main
            api_main.ADMIN_PHONES = [num]
            api_main.settings.admin_phones = num
            api_main.settings.owner_phone = num
        except Exception:
            pass
        QMessageBox.information(self, "Guardado",
            f"✅ Número guardado: {num}\nEl bot ya responderá a este número.")

    def _start(self):
        bridge_dir = str(Path(__file__).parent / "whatsapp_bridge")
        self._worker = BridgeWorker(bridge_dir)
        self._worker.output.connect(self._on_output)
        self._worker.connected.connect(self._on_connected)
        self._worker.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_lbl.setText("🟡  Iniciando bridge...")
        self.status_lbl.setStyleSheet(f"color: {WARNING}; font-size: 13px; font-weight: 600;")

    def _stop(self):
        if self._worker:
            self._worker.stop()
            self._worker = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_lbl.setText("⚪  Bridge detenido")
        self.status_lbl.setStyleSheet(f"color: {SUBTEXT}; font-size: 13px; font-weight: 600;")

    def _on_output(self, line: str):
        self.console.append(line)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def _on_connected(self):
        self.status_lbl.setText("🟢  WhatsApp conectado")
        self.status_lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 13px; font-weight: 600;")
        self.bridge_connected.emit()

    def closeEvent(self, event):
        # No matar el proceso al cerrar el modal — sigue corriendo en background
        super().closeEvent(event)


# ── Worker geocoding Nominatim (OpenStreetMap) ──────────────────────────────
class _GeoWorker(QThread):
    done = pyqtSignal(str, str, str)  # lat, lng, display_name

    def __init__(self, query: str):
        super().__init__()
        self._query = query

    def run(self):
        try:
            import urllib.request, urllib.parse, json
            params = urllib.parse.urlencode({"q": self._query, "format": "json", "limit": 1})
            url = f"https://nominatim.openstreetmap.org/search?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "MFAgent/1.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=6).read())
            if data:
                self.done.emit(data[0]["lat"], data[0]["lon"], data[0]["display_name"])
            else:
                self.done.emit("", "", "")
        except Exception:
            self.done.emit("", "", "")


# ── Worker mapa OpenStreetMap ────────────────────────────────────────────────
class _MapWorker(QThread):
    done = pyqtSignal(bytes)

    def __init__(self, lat: str, lng: str):
        super().__init__()
        self._lat = lat
        self._lng = lng

    def run(self):
        try:
            import urllib.request, math
            from PyQt6.QtGui import QPainter, QPainterPath, QPen, QBrush
            lat, lng = float(self._lat), float(self._lng)
            zoom = 16
            n = 2 ** zoom
            xt = int((lng + 180) / 360 * n)
            yt = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
            tile_size = 256
            canvas = QPixmap(tile_size * 3, tile_size * 3)
            canvas.fill(QColor("#e8e0d8"))
            painter = QPainter(canvas)
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    url = f"https://tile.openstreetmap.org/{zoom}/{xt+dx}/{yt+dy}.png"
                    req = urllib.request.Request(url, headers={"User-Agent": "MFAgent/1.0"})
                    data = urllib.request.urlopen(req, timeout=5).read()
                    tile = QPixmap()
                    tile.loadFromData(data)
                    painter.drawPixmap((dx + 1) * tile_size, (dy + 1) * tile_size, tile)
            cx = tile_size + tile_size // 2
            cy = tile_size + tile_size // 2
            painter.setPen(QPen(QColor("#DC2626"), 3))
            painter.setBrush(QBrush(QColor("#DC2626")))
            painter.drawEllipse(cx - 10, cy - 10, 20, 20)
            painter.setPen(QPen(QColor("white"), 2))
            painter.setBrush(QBrush(QColor("white")))
            painter.drawEllipse(cx - 5, cy - 5, 10, 10)
            painter.end()
            import tempfile, os
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            canvas.save(tmp.name, "PNG")
            with open(tmp.name, "rb") as f:
                result = f.read()
            os.unlink(tmp.name)
            self.done.emit(result)
        except Exception:
            self.done.emit(b"")


# ── Worker para cargar datos sin bloquear UI ──────────────────────────────────
class LoadWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, profile_id: str):
        super().__init__()
        self._profile_id = profile_id

    def run(self):
        try:
            self.done.emit(list_products(self._profile_id))
        except Exception:
            self.done.emit([])


class SalesWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, profile_id: str):
        super().__init__()
        self._profile_id = profile_id

    def run(self):
        try:
            self.done.emit(list_invoices(self._profile_id))
        except Exception:
            self.done.emit([])


# ── Modal Agregar / Editar Producto ───────────────────────────────────────────
class ProductDialog(QDialog):
    def __init__(self, parent=None, product: dict = None, profile_id: str = None):
        super().__init__(parent)
        self.setWindowTitle("Producto" if not product else "Editar Producto")
        self.setMinimumSize(420, 400)
        self.resize(460, 520)
        self.setStyleSheet(QSS)
        self._image_path = None
        self._image_url = product.get("image_url") if product else None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Nuevo Producto" if not product else "Editar Producto")
        title.setObjectName("title")
        title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.sku = QLineEdit(product["sku"] if product else next_sku(profile_id))
        self.sku.setPlaceholderText("ej: PROD-001")
        self.sku.setReadOnly(True)
        self.sku.setStyleSheet(f"background: {BG}; color: {SUBTEXT};")

        self.name = QLineEdit(product["name"] if product else "")
        self.name.setPlaceholderText("Nombre del producto")

        self.desc = QLineEdit(product.get("description", "") if product else "")
        self.desc.setPlaceholderText("Descripción breve")

        self.price = QDoubleSpinBox()
        self.price.setRange(0, 99999999)
        self.price.setDecimals(2)
        self.price.setPrefix("$ ")
        self.price.setValue(product["price"] if product else 0)

        self.stock = QSpinBox()
        self.stock.setRange(0, 99999)
        self.stock.setValue(int(product["stock"]) if product else 0)

        from agent.profiles import get_profile_data_dir
        import json as _json_cats
        _cats_file = get_profile_data_dir(profile_id) / "categories.json" if profile_id else None
        _default_cats = ["general", "computadoras", "accesorios", "electronica", "ropa", "hogar", "alimentos", "otro"]
        if _cats_file and _cats_file.exists():
            try:
                cats = _json_cats.loads(_cats_file.read_text(encoding="utf-8"))
            except Exception:
                cats = _default_cats[:]
        else:
            cats = _default_cats[:]
        self._cats_file = _cats_file
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.category.addItems(cats)
        current_cat = product.get("category", "") if product else ""
        if current_cat and current_cat not in cats:
            self.category.addItem(current_cat)
        if current_cat:
            self.category.setCurrentText(current_cat)

        def _on_cat_enter():
            text = self.category.currentText().strip()
            if text and self.category.findText(text) == -1:
                self.category.addItem(text)
                self.category.setCurrentText(text)
        self.category.lineEdit().returnPressed.connect(_on_cat_enter)

        form.addRow("SKU *", self.sku)
        form.addRow("Nombre *", self.name)
        form.addRow("Descripción", self.desc)
        form.addRow("Precio *", self.price)
        form.addRow("Stock *", self.stock)
        form.addRow("Categoría", self.category)
        layout.addLayout(form)

        # Foto
        photo_row = QHBoxLayout()
        self.img_preview = QLabel()
        self.img_preview.setFixedSize(72, 72)
        self.img_preview.setStyleSheet(f"border: 1px solid {BORDER}; border-radius: 8px; background: {SIDEBAR};")
        self.img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self._image_url and os.path.exists(self._image_url):
            pix = QPixmap(self._image_url).scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
            self.img_preview.setPixmap(pix)
        elif self._image_url:
            self.img_preview.setText("🖼️")
        else:
            self.img_preview.setText("Sin foto")
        self.img_preview.setStyleSheet(self.img_preview.styleSheet() + f" color: {SUBTEXT}; font-size: 11px;")

        photo_btn = QPushButton("📷  Foto")
        photo_btn.setObjectName("primary")
        photo_btn.clicked.connect(self._pick_image)
        photo_row.addWidget(self.img_preview)
        photo_row.addWidget(photo_btn)
        photo_row.addStretch()
        layout.addLayout(photo_row)

        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("danger")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Guardar")
        save.setObjectName("primary")
        save.clicked.connect(self._save)

        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen", "",
            "Imágenes (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._image_path = path
            pix = QPixmap(path).scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
            self.img_preview.setPixmap(pix)
            self.img_preview.setText("")

    def _save(self):
        if not self.sku.text().strip() or not self.name.text().strip():
            QMessageBox.warning(self, "Error", "SKU y Nombre son obligatorios.")
            return
        cat = self.category.currentText().strip()
        if cat and self._cats_file:
            import json as _jc
            try:
                existing = _jc.loads(self._cats_file.read_text(encoding="utf-8")) if self._cats_file.exists() else []
            except Exception:
                existing = []
            if cat not in existing:
                existing.append(cat)
                self._cats_file.write_text(_jc.dumps(existing, ensure_ascii=False), encoding="utf-8")
        self.accept()

    def get_product(self) -> Product:
        return Product(
            sku=self.sku.text().strip(),
            name=self.name.text().strip(),
            description=self.desc.text().strip(),
            price=self.price.value(),
            stock=self.stock.value(),
            category=self.category.currentText(),
            image_url=self._image_url
        )

    def get_image_path(self) -> str | None:
        return self._image_path


# ── Helpers de imagen ────────────────────────────────────────────────────────
def _load_pixmap(image_url: str, size: int) -> QPixmap | None:
    """Carga pixmap desde ruta local o URL http(s)."""
    if not image_url:
        return None
    # Ruta local
    if os.path.exists(image_url):
        pix = QPixmap(image_url)
        if not pix.isNull():
            return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
    # URL remota: descarga en memoria
    if image_url.startswith("http"):
        try:
            import urllib.request
            data = urllib.request.urlopen(image_url, timeout=3).read()
            pix = QPixmap()
            pix.loadFromData(data)
            if not pix.isNull():
                return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
        except Exception:
            pass
    return None


# ── Modal Registrar Venta Manual (multi-producto) ─────────────────────────────
class SaleDialog(QDialog):
    def __init__(self, parent=None, products: list = None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Venta")
        self.setMinimumSize(620, 480)
        self.resize(680, 560)
        self.setStyleSheet(QSS)
        self._products = {p["sku"]: p for p in (products or [])}
        self._rows: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("🛒  Nueva Venta")
        title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        row_c = QHBoxLayout()
        row_c.addWidget(QLabel("Cliente:"))
        self.customer = QLineEdit()
        self.customer.setPlaceholderText("Nombre o teléfono (opcional)")
        row_c.addWidget(self.customer)
        layout.addLayout(row_c)

        self._item_table = QTableWidget(0, 5)
        self._item_table.setHorizontalHeaderLabels(["SKU", "Producto", "Cant.", "Subtotal", ""])
        self._item_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._item_table.setColumnWidth(0, 90)
        self._item_table.setColumnWidth(2, 60)
        self._item_table.setColumnWidth(3, 90)
        self._item_table.setColumnWidth(4, 36)
        self._item_table.verticalHeader().setVisible(False)
        self._item_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._item_table.setFixedHeight(180)
        layout.addWidget(self._item_table)

        add_row = QHBoxLayout()
        self._prod_cb = QComboBox()
        self._prod_cb.addItems([f"{p['name']} ({p['sku']})" for p in (products or [])])
        self._qty_spin = QSpinBox()
        self._qty_spin.setRange(1, 9999)
        self._qty_spin.setFixedWidth(70)
        btn_add = QPushButton("＋ Agregar")
        btn_add.setObjectName("primary")
        btn_add.setFixedHeight(32)
        btn_add.clicked.connect(self._add_item)
        add_row.addWidget(self._prod_cb, 1)
        add_row.addWidget(QLabel("Cant:"))
        add_row.addWidget(self._qty_spin)
        add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        self._total_lbl = QLabel("Total: $0.00")
        self._total_lbl.setStyleSheet(f"color: {ACCENT2}; font-size: 15px; font-weight: 700;")
        layout.addWidget(self._total_lbl)

        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("danger")
        cancel.clicked.connect(self.reject)
        save = QPushButton("💾  Registrar")
        save.setObjectName("primary")
        save.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addStretch()
        btns.addWidget(save)
        layout.addLayout(btns)

    def _get_sku(self) -> str:
        text = self._prod_cb.currentText()
        return text.split("(")[-1].rstrip(")") if "(" in text else ""

    def _add_item(self):
        sku = self._get_sku()
        if not sku or sku not in self._products:
            return
        p = self._products[sku]
        qty = self._qty_spin.value()
        for row in self._rows:
            if row["sku"] == sku:
                row["qty"] += qty
                self._refresh_table()
                return
        self._rows.append({"sku": sku, "name": p["name"], "qty": qty, "price": p["price"]})
        self._refresh_table()

    def _remove_item(self, sku: str):
        self._rows = [r for r in self._rows if r["sku"] != sku]
        self._refresh_table()

    def _refresh_table(self):
        self._item_table.setRowCount(len(self._rows))
        total = 0.0
        for i, row in enumerate(self._rows):
            sub = row["qty"] * row["price"]
            total += sub
            self._item_table.setItem(i, 0, QTableWidgetItem(row["sku"]))
            self._item_table.setItem(i, 1, QTableWidgetItem(row["name"]))
            self._item_table.setItem(i, 2, QTableWidgetItem(str(row["qty"])))
            self._item_table.setItem(i, 3, QTableWidgetItem(f"${sub:.2f}"))
            del_btn = QPushButton("x")
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet(f"background:{DANGER};color:white;border:none;border-radius:4px;font-weight:700;")
            del_btn.clicked.connect(lambda _, s=row["sku"]: self._remove_item(s))
            self._item_table.setCellWidget(i, 4, del_btn)
        self._total_lbl.setText(f"Total: ${total:.2f}")

    def _save(self):
        if not self._rows:
            QMessageBox.warning(self, "Error", "Agrega al menos un producto.")
            return
        self.accept()

    def get_invoice(self) -> Invoice:
        items = [InvoiceItem(
            sku=r["sku"], product_name=r["name"],
            quantity=r["qty"], unit_price=r["price"],
            subtotal=r["qty"] * r["price"]
        ) for r in self._rows]
        return Invoice(
            customer=self.customer.text().strip(),
            items=items,
            total=sum(i.subtotal for i in items),
        )


# ── Stat Card ────────────────────────────────────────────────────────────────
def make_stat_card(icon: str, label: str, value: str, color: str) -> tuple:
    card = QWidget()
    card.setObjectName("card")
    card.setFixedWidth(200)
    card.setFixedHeight(110)

    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(20)
    shadow.setColor(QColor(0, 0, 0, 60))
    shadow.setOffset(0, 4)
    card.setGraphicsEffect(shadow)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(2)

    icon_lbl = QLabel(icon)
    icon_lbl.setStyleSheet(f"font-size: 22px;")

    val = QLabel(value)
    val.setObjectName("stat_value")
    val.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: 700;")

    lbl = QLabel(label)
    lbl.setObjectName("stat_label")

    layout.addWidget(icon_lbl)
    layout.addWidget(val)
    layout.addWidget(lbl)
    return card, val


# ── Cards Slider ──────────────────────────────────────────────────────────────
class CardsSlider(QWidget):
    """Contenedor horizontal deslizable con flechas de navegación."""
    def __init__(self, cards: list, parent=None):
        super().__init__(parent)
        self.setFixedHeight(140)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        self._prev_btn = QPushButton("‹")
        self._next_btn = QPushButton("›")
        for btn in (self._prev_btn, self._next_btn):
            btn.setFixedSize(32, 80)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {CARD}; color: {TEXT}; border: 1px solid {BORDER};
                    border-radius: 8px; font-size: 20px; font-weight: 700;
                }}
                QPushButton:hover {{ background: {SIDEBAR}; }}
            """)

        self._scroll = QScrollArea()
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidgetResizable(False)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        row = QHBoxLayout(inner)
        row.setContentsMargins(4, 8, 4, 8)
        row.setSpacing(16)
        for card in cards:
            row.addWidget(card)
        row.addStretch()
        inner.setFixedHeight(130)

        self._scroll.setWidget(inner)

        outer.addWidget(self._prev_btn)
        outer.addWidget(self._scroll, 1)
        outer.addWidget(self._next_btn)

        self._prev_btn.clicked.connect(self._slide_left)
        self._next_btn.clicked.connect(self._slide_right)

    def _animate_scroll(self, target: int):
        bar = self._scroll.horizontalScrollBar()
        anim = QPropertyAnimation(bar, b"value", self)
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(bar.value())
        anim.setEndValue(max(0, min(target, bar.maximum())))
        anim.start()
        self._anim = anim  # keep reference

    def _slide_left(self):
        self._animate_scroll(self._scroll.horizontalScrollBar().value() - 220)

    def _slide_right(self):
        self._animate_scroll(self._scroll.horizontalScrollBar().value() + 220)


# ── Generar PDF de factura con marca de agua ────────────────────────────────
def _generate_pdf(invoice: dict, path: str, business_name: str = None):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, Image)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    env = _read_env()
    logo_image   = env.get("WATERMARK_IMAGE", str(Path(__file__).parent / "MF_LABS.png"))
    biz          = business_name or env.get("BUSINESS_NAME", "Mi Empresa")
    biz_phone    = env.get("BUSINESS_PHONE", "")
    biz_email    = env.get("BUSINESS_EMAIL", "")
    biz_address  = env.get("BUSINESS_ADDRESS", "")
    firma1_label = env.get("FIRMA1_LABEL", "Firma Empresa")
    firma2_label = env.get("FIRMA2_LABEL", "Firma Cliente")

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    bold11   = ParagraphStyle("bold11",  parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11)
    normal10 = ParagraphStyle("n10",     parent=styles["Normal"], fontSize=10)
    right10  = ParagraphStyle("r10",     parent=styles["Normal"], fontSize=10, alignment=TA_RIGHT)
    center12 = ParagraphStyle("c12",     parent=styles["Normal"], fontSize=12,
                               alignment=TA_CENTER, fontName="Helvetica-Bold")
    center9  = ParagraphStyle("c9",      parent=styles["Normal"], fontSize=9,  alignment=TA_CENTER)
    story = []

    # Logo izq | Nombre centrado | Datos factura der
    logo_cell = ""
    if Path(logo_image).exists():
        try:
            logo_cell = Image(logo_image, width=2.5*cm, height=2.5*cm)
        except Exception:
            logo_cell = Paragraph("", normal10)
    else:
        logo_cell = Paragraph("", normal10)

    sub_lines = []
    if biz_address: sub_lines.append(biz_address)
    if biz_phone:   sub_lines.append(f"Tel: {biz_phone}")
    if biz_email:   sub_lines.append(biz_email)
    biz_txt = f"<b>{biz}</b>"
    if sub_lines:
        biz_txt += "<br/>" + "<br/>".join(sub_lines)
    biz_center = Paragraph(biz_txt, ParagraphStyle("biz_c", parent=styles["Normal"],
                           fontSize=11, alignment=TA_CENTER, fontName="Helvetica-Bold"))

    inv_lines = (f"<b>FACTURA</b><br/>"
                 f"No: {invoice.get('invoice_id', '')}<br/>"
                 f"Fecha: {invoice.get('timestamp', '')[:10]}")
    inv_cell = Paragraph(inv_lines, ParagraphStyle("inv", parent=styles["Normal"],
                         fontSize=10, alignment=TA_RIGHT))

    header_tbl = Table([[logo_cell, biz_center, inv_cell]],
                       colWidths=[3*cm, 11*cm, 3*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("LINEBELOW",     (0,0), (-1,0),  1.5, colors.HexColor("#1B6CA8")),
        ("BOTTOMPADDING", (0,0), (-1,0),  8),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.8*cm))

    # Datos del cliente
    cliente  = invoice.get("customer") or "Consumidor final"
    telefono = invoice.get("customer_phone", "")
    direccion= invoice.get("customer_address", "")
    rfc      = invoice.get("customer_rfc", "")
    notas    = invoice.get("notes", "")

    client_rows = [[Paragraph("<b>DATOS DEL CLIENTE</b>", bold11), ""]]
    client_rows.append([Paragraph("Nombre:",    normal10), Paragraph(cliente,   normal10)])
    if telefono:  client_rows.append([Paragraph("Telefono:",  normal10), Paragraph(telefono,  normal10)])
    if direccion: client_rows.append([Paragraph("Direccion:", normal10), Paragraph(direccion, normal10)])
    if rfc:       client_rows.append([Paragraph("RFC:",       normal10), Paragraph(rfc,       normal10)])

    ct = Table(client_rows, colWidths=[3.5*cm, 13.5*cm])
    ct.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0),  colors.HexColor("#EDE8E3")),
        ("SPAN",         (0,0), (-1,0)),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("BOX",          (0,0), (-1,-1), 0.5, colors.HexColor("#D1CBC4")),
        ("INNERGRID",    (0,1), (-1,-1), 0.3, colors.HexColor("#D1CBC4")),
    ]))
    story.append(ct)
    story.append(Spacer(1, 0.6*cm))

    # Tabla de items
    headers = [Paragraph(h, ParagraphStyle("th", parent=styles["Normal"],
               fontName="Helvetica-Bold", fontSize=10, textColor=colors.white))
               for h in ["SKU", "Descripcion", "Cant.", "Precio Unit.", "Subtotal"]]
    rows = [headers]
    for item in invoice.get("items", []):
        rows.append([
            Paragraph(item.get("sku", ""),          normal10),
            Paragraph(item.get("product_name", ""), normal10),
            Paragraph(str(item.get("quantity", 1)), normal10),
            Paragraph(f"${item.get('unit_price', 0):.2f}", right10),
            Paragraph(f"${item.get('subtotal',   0):.2f}", right10),
        ])
    rows.append(["", "", "",
                 Paragraph("<b>TOTAL</b>", ParagraphStyle("tot", parent=styles["Normal"],
                           fontName="Helvetica-Bold", fontSize=11, alignment=TA_RIGHT)),
                 Paragraph(f"<b>${invoice.get('total', 0):.2f}</b>",
                           ParagraphStyle("totv", parent=styles["Normal"],
                           fontName="Helvetica-Bold", fontSize=11, alignment=TA_RIGHT))])

    t = Table(rows, colWidths=[2.5*cm, 7.5*cm, 1.5*cm, 3*cm, 2.5*cm],
              repeatRows=1, splitByRow=True)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),  (-1,0),  colors.HexColor("#1B6CA8")),
        ("ROWBACKGROUNDS", (0,1),  (-1,-2), [colors.HexColor("#FDFAF7"), colors.HexColor("#EDE8E3")]),
        ("BACKGROUND",     (0,-1), (-1,-1), colors.HexColor("#F5F0EB")),
        ("GRID",           (0,0),  (-1,-1), 0.5, colors.HexColor("#D1CBC4")),
        ("ALIGN",          (2,1),  (-1,-1), "RIGHT"),
        ("VALIGN",         (0,0),  (-1,-1), "MIDDLE"),
        ("TOPPADDING",     (0,0),  (-1,-1), 6),
        ("BOTTOMPADDING",  (0,0),  (-1,-1), 6),
        ("LEFTPADDING",    (0,0),  (-1,-1), 6),
        ("LINEABOVE",      (0,-1), (-1,-1), 1.5, colors.HexColor("#1B6CA8")),
    ]))
    story.append(t)

    if notas:
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(f"<b>Notas:</b> {notas}", normal10))

    # Firmas al final
    story.append(Spacer(1, 1.5*cm))
    line = "_" * 38
    firma_tbl = Table(
        [[Paragraph(line, center9), Paragraph("", normal10), Paragraph(line, center9)],
         [Paragraph(firma1_label, center9), Paragraph("", normal10), Paragraph(firma2_label, center9)]],
        colWidths=[7*cm, 3*cm, 7*cm]
    )
    firma_tbl.setStyle(TableStyle([
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "BOTTOM"),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    story.append(firma_tbl)
    doc.build(story)


# ── Modal Factura Multi-Producto ──────────────────────────────────────────────
class InvoiceDialog(QDialog):
    def __init__(self, parent=None, products: list = None, business_name: str = None, existing: dict = None):
        super().__init__(parent)
        self._business_name = business_name or "Mi Empresa"
        self._existing = existing
        self.setWindowTitle(f"{'Editar' if existing else 'Nueva'} Factura — {self._business_name}")
        self.setMinimumSize(820, 600)
        self.resize(900, 750)
        self.setStyleSheet(QSS)
        self._products = {p["sku"]: p for p in (products or [])}
        self._rows: list[dict] = []

        # Layout principal del diálogo
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Widget contenedor del contenido
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        title = QLabel(f"\U0001f9fe  {'Editar' if self._existing else 'Nueva'} Factura  ·  {self._business_name}")
        title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        # ── Datos del cliente ─────────────────────────────────────────────────
        client_card = QWidget(); client_card.setObjectName("card")
        cl = QVBoxLayout(client_card); cl.setContentsMargins(12,10,12,10); cl.setSpacing(6)
        cl_title = QLabel("Datos del Cliente")
        cl_title.setStyleSheet(f"color:{TEXT};font-size:13px;font-weight:700;")
        cl.addWidget(cl_title)

        row1 = QHBoxLayout()
        self.customer = QLineEdit(existing.get("customer", "") if existing else ""); self.customer.setPlaceholderText("Nombre del cliente *")
        self.customer_phone = QLineEdit(existing.get("customer_phone", "") if existing else ""); self.customer_phone.setPlaceholderText("Teléfono")
        self.customer_phone.setFixedWidth(160)
        row1.addWidget(QLabel("Nombre:"))
        row1.addWidget(self.customer, 2)
        row1.addWidget(QLabel("Tel:"))
        row1.addWidget(self.customer_phone)
        cl.addLayout(row1)

        row2 = QHBoxLayout()
        self.customer_address = QLineEdit(existing.get("customer_address", "") if existing else ""); self.customer_address.setPlaceholderText("Dirección")
        self.customer_rfc = QLineEdit(existing.get("customer_rfc", "") if existing else ""); self.customer_rfc.setPlaceholderText("RFC / ID fiscal")
        self.customer_rfc.setFixedWidth(160)
        row2.addWidget(QLabel("Dirección:"))
        row2.addWidget(self.customer_address, 2)
        row2.addWidget(QLabel("RFC:"))
        row2.addWidget(self.customer_rfc)
        cl.addLayout(row2)

        row3 = QHBoxLayout()
        self.notes = QLineEdit(existing.get("notes", "") if existing else ""); self.notes.setPlaceholderText("Notas adicionales (opcional)")
        row3.addWidget(QLabel("Notas:"))
        row3.addWidget(self.notes)
        cl.addLayout(row3)

        layout.addWidget(client_card)

        # ── Productos ─────────────────────────────────────────────────────────
        lbl_prod = QLabel("Productos")
        lbl_prod.setStyleSheet(f"color:{TEXT};font-size:13px;font-weight:700;")
        layout.addWidget(lbl_prod)

        self._item_table = QTableWidget(0, 5)
        self._item_table.setHorizontalHeaderLabels(["SKU", "Producto", "Cant.", "Precio", ""])
        self._item_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._item_table.setColumnWidth(0, 100); self._item_table.setColumnWidth(2, 60)
        self._item_table.setColumnWidth(3, 90);  self._item_table.setColumnWidth(4, 40)
        self._item_table.verticalHeader().setVisible(False)
        self._item_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._item_table.setFixedHeight(140)
        layout.addWidget(self._item_table)

        add_row = QHBoxLayout()
        self._prod_cb = QComboBox()
        self._prod_cb.addItems([f"{p['name']} ({p['sku']})" for p in (products or [])])
        self._qty_spin = QSpinBox(); self._qty_spin.setRange(1, 9999); self._qty_spin.setFixedWidth(70)
        btn_add = QPushButton("+ Agregar"); btn_add.setObjectName("primary"); btn_add.setFixedHeight(30)
        btn_add.clicked.connect(self._add_item)
        lbl_cant = QLabel("Cant:"); lbl_cant.setStyleSheet(f"color:{TEXT};")
        add_row.addWidget(self._prod_cb, 1); add_row.addWidget(lbl_cant)
        add_row.addWidget(self._qty_spin); add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        # ── Cotización de trabajo (opcional) ──────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{BORDER};max-height:1px;border:none;")
        layout.addWidget(sep)

        self._cot_check = QPushButton("🔧  Cotización")
        self._cot_check.setObjectName("primary"); self._cot_check.setCheckable(True)
        self._cot_check.clicked.connect(self._toggle_cotizacion)
        layout.addWidget(self._cot_check)

        self._cot_widget = QWidget(); self._cot_widget.setVisible(False)
        cot_layout = QVBoxLayout(self._cot_widget); cot_layout.setContentsMargins(0,4,0,4); cot_layout.setSpacing(8)

        # Descripcion del trabajo
        row_desc = QHBoxLayout()
        lbl_desc = QLabel("Descripción:"); lbl_desc.setStyleSheet(f"color:{TEXT};font-size:13px;")
        self._cot_desc = QLineEdit(); self._cot_desc.setPlaceholderText("Ej: Instalación de piso, pintura, soldadura...")
        row_desc.addWidget(lbl_desc); row_desc.addWidget(self._cot_desc)
        cot_layout.addLayout(row_desc)

        # Mano de obra
        row_mo = QHBoxLayout()
        lbl_mo = QLabel("Precio mano de obra:"); lbl_mo.setStyleSheet(f"color:{TEXT};font-size:13px;")
        self._cot_mano = QDoubleSpinBox(); self._cot_mano.setRange(0,99999999); self._cot_mano.setDecimals(2); self._cot_mano.setPrefix("$ ")
        self._cot_mano.valueChanged.connect(self._recalc_total)
        row_mo.addWidget(lbl_mo); row_mo.addWidget(self._cot_mano)
        cot_layout.addLayout(row_mo)

        # Cantidad y unidad
        row_cant = QHBoxLayout()
        lbl_cant = QLabel("Cantidad:"); lbl_cant.setStyleSheet(f"color:{TEXT};font-size:13px;")
        self._cot_cantidad = QDoubleSpinBox(); self._cot_cantidad.setRange(0,99999); self._cot_cantidad.setDecimals(2)
        self._cot_cantidad.valueChanged.connect(self._recalc_total)
        lbl_unidad = QLabel("Unidad:"); lbl_unidad.setStyleSheet(f"color:{TEXT};font-size:13px;")
        self._cot_unidad = QComboBox()
        self._cot_unidad.addItems(["m (metro lineal)", "m² (metro cuadrado)", "m³ (metro cúbico)"])
        self._cot_unidad.currentIndexChanged.connect(self._recalc_total)
        row_cant.addWidget(lbl_cant); row_cant.addWidget(self._cot_cantidad)
        row_cant.addSpacing(16); row_cant.addWidget(lbl_unidad); row_cant.addWidget(self._cot_unidad)
        row_cant.addStretch()
        cot_layout.addLayout(row_cant)

        self._cot_subtotal_lbl = QLabel("Subtotal trabajo: $0.00")
        self._cot_subtotal_lbl.setStyleSheet(f"color:{ACCENT2};font-size:13px;font-weight:700;")
        cot_layout.addWidget(self._cot_subtotal_lbl)

        # Botón para agregar cotización
        btn_add_cot = QPushButton("📋  Agregar al PDF")
        btn_add_cot.setObjectName("primary")
        btn_add_cot.setFixedHeight(36)
        btn_add_cot.clicked.connect(self._add_cotizacion_to_pdf)
        cot_layout.addWidget(btn_add_cot)

        layout.addWidget(self._cot_widget)

        # Total general
        self._total_lbl = QLabel("Total: $0.00")
        self._total_lbl.setStyleSheet(f"color:{ACCENT2};font-size:16px;font-weight:700;")
        layout.addWidget(self._total_lbl)

        # Botones
        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar"); cancel.setObjectName("danger"); cancel.clicked.connect(self.reject)
        save = QPushButton("💾  Guardar"); save.setObjectName("primary"); save.clicked.connect(self._save)
        btns.addWidget(cancel); btns.addStretch(); btns.addWidget(save)
        layout.addLayout(btns)

        # Precargar items si es edición
        if existing:
            for item in existing.get("items", []):
                self._rows.append({
                    "sku": item.get("sku", ""),
                    "name": item.get("product_name", ""),
                    "qty": item.get("quantity", 1),
                    "price": item.get("unit_price", 0),
                })
            self._refresh_prod_table()

        # Agregar contenido al scroll
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _toggle_cotizacion(self, checked: bool):
        self._cot_widget.setVisible(checked)
        self._cot_check.setText(
            "🔧  Cotización ✓" if checked else "🔧  Cotización"
        )
        self._recalc_total()

    def _get_sku_from_cb(self, cb: QComboBox) -> str:
        text = cb.currentText()
        return text.split("(")[-1].rstrip(")") if "(" in text else ""

    # ── Productos ─────────────────────────────────────────────────────────────
    def _add_item(self):
        sku = self._get_sku_from_cb(self._prod_cb)
        if not sku or sku not in self._products:
            return
        p = self._products[sku]; qty = self._qty_spin.value()
        for row in self._rows:
            if row["sku"] == sku:
                row["qty"] += qty; self._refresh_prod_table(); return
        self._rows.append({"sku": sku, "name": p["name"], "qty": qty, "price": p["price"]})
        self._refresh_prod_table()

    def _remove_item(self, sku: str):
        self._rows = [r for r in self._rows if r["sku"] != sku]
        self._refresh_prod_table()

    def _refresh_prod_table(self):
        self._item_table.setRowCount(len(self._rows))
        for i, row in enumerate(self._rows):
            sub = row["qty"] * row["price"]
            self._item_table.setItem(i, 0, QTableWidgetItem(row["sku"]))
            self._item_table.setItem(i, 1, QTableWidgetItem(row["name"]))
            self._item_table.setItem(i, 2, QTableWidgetItem(str(row["qty"])))
            self._item_table.setItem(i, 3, QTableWidgetItem(f"${sub:.2f}"))
            btn = QPushButton("\u2715"); btn.setFixedSize(28,28)
            btn.setStyleSheet(f"background:{DANGER};color:white;border:none;border-radius:4px;")
            btn.clicked.connect(lambda _, s=row["sku"]: self._remove_item(s))
            self._item_table.setCellWidget(i, 4, btn)
        self._recalc_total()

    # ── Materiales (no usado) ────────────────────────────────────────────────
    def _add_material(self):
        pass

    def _remove_material(self, sku: str):
        pass

    def _refresh_mat_table(self):
        pass

    def _add_cotizacion_to_pdf(self):
        """Agrega la cotización actual como un item en la tabla de productos."""
        if not self._cot_desc.text().strip():
            QMessageBox.warning(self, "Error", "Ingresa una descripción para la cotización.")
            return
        
        desc = self._cot_desc.text().strip()
        precio_unitario = self._cot_mano.value()
        cantidad = self._cot_cantidad.value()
        unidad_idx = self._cot_unidad.currentIndex()
        unidades = ["m", "m²", "m³"]
        unidad = unidades[unidad_idx]
        
        total_cot = precio_unitario * cantidad
        
        if total_cot <= 0:
            QMessageBox.warning(self, "Error", "La cotización debe tener un valor mayor a $0.")
            return
        
        # Crear descripción detallada
        nombre_completo = f"{desc} | ${precio_unitario:.2f}/{unidad} x {cantidad:.2f}{unidad}"
        
        # Agregar como producto con SKU único
        import time
        sku_cot = f"COT-{int(time.time() * 1000) % 1000000}"
        self._rows.append({
            "sku": sku_cot,
            "name": nombre_completo,
            "qty": 1,
            "price": total_cot
        })
        
        # Limpiar cotización
        self._cot_desc.clear()
        self._cot_mano.setValue(0)
        self._cot_cantidad.setValue(0)
        self._cot_widget.setVisible(False)
        self._cot_check.setChecked(False)
        self._cot_check.setText("🔧  Cotización")
        
        # Actualizar tabla de productos
        self._refresh_prod_table()
        QMessageBox.information(self, "Éxito", f"Cotización '{desc}' agregada al PDF por ${total_cot:.2f}")

    def _recalc_total(self):
        prod_total = sum(r["qty"] * r["price"] for r in self._rows)
        trabajo_total = 0.0
        if self._cot_widget.isVisible():
            trabajo_total = self._cot_mano.value() * self._cot_cantidad.value()
            unidad_idx = self._cot_unidad.currentIndex()
            unidades = ["m", "m²", "m³"]
            self._cot_subtotal_lbl.setText(
                f"Subtotal trabajo: ${trabajo_total:.2f}  "
                f"(${self._cot_mano.value():.2f}/{unidades[unidad_idx]} x {self._cot_cantidad.value():.2f}{unidades[unidad_idx]})"
            )
        self._total_lbl.setText(f"Total: ${prod_total + trabajo_total:.2f}")

    def _save(self):
        if not self._rows:
            QMessageBox.warning(self, "Error", "Agrega al menos un producto o cotización al PDF.")
            return
        self.accept()

    def get_invoice(self) -> Invoice:
        items = [InvoiceItem(
            sku=r["sku"], product_name=r["name"],
            quantity=r["qty"], unit_price=r["price"],
            subtotal=r["qty"] * r["price"]
        ) for r in self._rows]

        inv = Invoice(
            customer=self.customer.text().strip(),
            items=items,
            total=sum(i.subtotal for i in items),
        )
        # Campos extra del cliente
        try:
            inv_dict = inv.model_dump()
        except AttributeError:
            inv_dict = inv.dict()
        inv_dict["customer_phone"]   = self.customer_phone.text().strip()
        inv_dict["customer_address"] = self.customer_address.text().strip()
        inv_dict["customer_rfc"]     = self.customer_rfc.text().strip()
        inv_dict["notes"]            = self.notes.text().strip()
        inv_dict["business_name"]    = self._business_name
        if self._existing:
            inv_dict["invoice_id"] = self._existing.get("invoice_id", inv_dict.get("invoice_id", ""))
            inv_dict["timestamp"]  = self._existing.get("timestamp",  inv_dict.get("timestamp", ""))
            inv_dict["channel"]    = self._existing.get("channel",    "manual")
        self._extra = inv_dict  # guardado para acceso externo
        return inv

    def get_invoice_dict(self) -> dict:
        """Retorna el dict completo con campos extra del cliente."""
        inv = self.get_invoice()
        return self._extra


# ── Ventana Principal ─────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    logout = pyqtSignal()

    def __init__(self, session: dict):
        super().__init__()
        self._session = session
        self._profile_id = session["profile_id"]
        self._role = session["role"]          # "admin" | "vendedor"
        self._is_admin = self._role == "admin"
        self.setWindowTitle(f"MF Agent — {session['profile_name']}  [{session['username']}]")
        
        # Establecer icono
        icon_path = Path(__file__).parent / "MF_LABS.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            png_path = Path(__file__).parent / "MF_LABS.png"
            if png_path.exists():
                self.setWindowIcon(QIcon(str(png_path)))
        
        self.setMinimumSize(1280, 780)
        self.resize(1400, 860)
        self.products = []
        self._bot_running = True

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self._build_sidebar())
        main_layout.addWidget(self._build_content(), 1)

        self.setStyleSheet(QSS)
        self._load_products()

        # Auto-refresh cada 30s
        timer = QTimer(self)
        timer.timeout.connect(self._load_products)
        timer.start(30000)

        # Avisar si WhatsApp no está conectado
        if not _whatsapp_configured():
            QTimer.singleShot(500, self._prompt_whatsapp_setup)

    def _prompt_whatsapp_setup(self):
        reply = QMessageBox.question(
            self, "WhatsApp no conectado",
            "El bridge de WhatsApp no está iniciado.\n"
            "¿Deseas conectarlo ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._open_whatsapp_config()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 28, 16, 28)
        layout.setSpacing(6)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)
        logo_img = QLabel()
        logo_img.setFixedSize(32, 32)
        pix32 = _make_logo_pixmap(32)
        if pix32:
            logo_img.setPixmap(pix32)
        else:
            logo_img.setText("MF")
        logo_txt = QLabel("MF Agent")
        logo_txt.setObjectName("nav_title")
        logo_txt.setStyleSheet(f"color: {TEXT}; font-size: 17px; font-weight: 700; margin-bottom: 4px;")
        logo_row.addWidget(logo_img)
        logo_row.addWidget(logo_txt)
        logo_row.addStretch()
        layout.addLayout(logo_row)

        # Usuario activo
        role_icon = "👑" if self._is_admin else "🛒"
        user_lbl = QLabel(f"{role_icon}  {self._session['username']}  ·  {self._session['profile_name']}")
        user_lbl.setStyleSheet(f"color: {SUBTEXT}; font-size: 11px; margin-bottom: 14px;")
        user_lbl.setWordWrap(True)
        layout.addWidget(user_lbl)

        for icon, text in [("🏠", "Dashboard"), ("📋", "Inventario"), ("🛒", "Ventas"), ("⚠️", "Stock Bajo")]:
            btn = QPushButton(f"  {icon}  {text}")
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, t=text: self._nav(t))
            layout.addWidget(btn)
            if text == "Dashboard":
                btn.setChecked(True)
            setattr(self, f"nav_{text.lower().replace(' ', '_')}", btn)

        layout.addStretch()

        if self._is_admin:
            # ── WhatsApp ──────────────────────────────────────────────────────
            wa_section = QLabel("WHATSAPP")
            wa_section.setStyleSheet(f"color: {SUBTEXT}; font-size: 10px; font-weight: 700; letter-spacing: 1px; padding: 4px 8px 2px 8px;")
            layout.addWidget(wa_section)

            btn_wa = QPushButton("📱  WhatsApp")
            btn_wa.setObjectName("whatsapp")
            btn_wa.clicked.connect(self._open_whatsapp_config)
            layout.addWidget(btn_wa)

            self.wa_status = QLabel()
            self._refresh_wa_status()
            layout.addWidget(self.wa_status)

            # ── Configuración ─────────────────────────────────────────────────
            config_section = QLabel("CONFIGURACIÓN")
            config_section.setStyleSheet(f"color: {SUBTEXT}; font-size: 10px; font-weight: 700; letter-spacing: 1px; padding: 4px 8px 2px 8px; margin-top: 8px;")
            layout.addWidget(config_section)

            btn_watermark = QPushButton("🖼️  Logo Empresa")
            btn_watermark.setObjectName("primary")
            btn_watermark.clicked.connect(self._change_watermark)
            layout.addWidget(btn_watermark)

            btn_biz = QPushButton("🏢  Datos Empresa")
            btn_biz.setObjectName("primary")
            btn_biz.clicked.connect(self._manage_business_data)
            layout.addWidget(btn_biz)

            btn_manuals = QPushButton("📚  Manuales")
            btn_manuals.setObjectName("primary")
            btn_manuals.clicked.connect(self._manage_manuals)
            layout.addWidget(btn_manuals)

            btn_advisors = QPushButton("👨💼  Asesores")
            btn_advisors.setObjectName("primary")
            btn_advisors.clicked.connect(self._manage_advisors)
            layout.addWidget(btn_advisors)

            btn_bot_config = QPushButton("⚙️  Config Bot")
            btn_bot_config.setObjectName("primary")
            btn_bot_config.clicked.connect(self._manage_bot_config)
            layout.addWidget(btn_bot_config)

            btn_pull = QPushButton("📥  Sync desde Móvil")
            btn_pull.setObjectName("primary")
            btn_pull.clicked.connect(self._pull_from_firestore)
            layout.addWidget(btn_pull)
            self._btn_pull = btn_pull

            btn_firmas = QPushButton("✍️  Firmas PDF")
            btn_firmas.setObjectName("primary")
            btn_firmas.clicked.connect(self._manage_firmas)
            layout.addWidget(btn_firmas)

        # ── Cerrar sesión (siempre al fondo) ──────────────────────────────────
        btn_logout = QPushButton("🚪  Cerrar Sesión")
        btn_logout.setObjectName("bot_off")
        btn_logout.clicked.connect(self.logout.emit)
        layout.addWidget(btn_logout)

        return sidebar

    def _refresh_wa_status(self):
        import urllib.request
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/bridge/status", timeout=1) as r:
                import json
                data = json.loads(r.read())
                if data.get("connected"):
                    self.wa_status.setText("🟢  WhatsApp conectado")
                    self.wa_status.setStyleSheet(f"color: {SUCCESS}; font-size: 11px; padding: 2px 8px 6px 8px;")
                    return
        except Exception:
            pass
        self.wa_status.setText("🔴  Bridge no conectado")
        self.wa_status.setStyleSheet(f"color: {DANGER}; font-size: 11px; padding: 2px 8px 6px 8px;")

    def _open_whatsapp_config(self):
        if not hasattr(self, '_wa_dialog') or self._wa_dialog is None:
            self._wa_dialog = WhatsAppConfigDialog(self)
            self._wa_dialog.bridge_connected.connect(self._refresh_wa_status)
        self._wa_dialog.show()
        self._wa_dialog.raise_()
        self._wa_dialog.activateWindow()
        self._refresh_wa_status()

    def _change_watermark(self):
        """Permite seleccionar una imagen personalizada para la marca de agua."""
        # Crear diálogo personalizado
        dlg = QDialog(self)
        dlg.setWindowTitle("Logo de Empresa")
        dlg.setMinimumSize(500, 300)
        dlg.setStyleSheet(QSS)
        
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title = QLabel("🖼️  Logo de Empresa")
        title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)
        
        # Imagen actual
        env = _read_env()
        current_img = env.get("WATERMARK_IMAGE", str(Path(__file__).parent / "MF_LABS.png"))
        current_opacity = float(env.get("WATERMARK_OPACITY", "0.15"))
        
        img_row = QHBoxLayout()
        img_lbl = QLabel("Logo actual:")
        img_lbl.setStyleSheet(f"color: {TEXT}; font-size: 13px;")
        img_path_lbl = QLabel(Path(current_img).name)
        img_path_lbl.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        img_path_lbl.setWordWrap(True)
        btn_select = QPushButton("📂  Seleccionar")
        btn_select.setObjectName("primary")
        btn_select.setFixedHeight(32)
        
        img_row.addWidget(img_lbl)
        img_row.addWidget(img_path_lbl, 1)
        img_row.addWidget(btn_select)
        layout.addLayout(img_row)
        
        # Preview de la imagen
        preview = QLabel()
        preview.setFixedSize(200, 200)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setStyleSheet(f"border: 2px solid {BORDER}; border-radius: 8px; background: {SIDEBAR};")
        if Path(current_img).exists():
            pix = QPixmap(current_img).scaled(190, 190, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
            preview.setPixmap(pix)
        else:
            preview.setText("❌ Sin imagen")
            preview.setStyleSheet(preview.styleSheet() + f" color: {SUBTEXT};")
        layout.addWidget(preview, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Opacidad
        opacity_row = QHBoxLayout()
        opacity_lbl = QLabel("Opacidad:")
        opacity_lbl.setStyleSheet(f"color: {TEXT}; font-size: 13px;")
        opacity_spin = QDoubleSpinBox()
        opacity_spin.setRange(0.05, 1.0)
        opacity_spin.setSingleStep(0.05)
        opacity_spin.setDecimals(2)
        opacity_spin.setValue(current_opacity)
        opacity_spin.setFixedWidth(100)
        opacity_info = QLabel("(0.05 = muy transparente, 1.0 = opaco)")
        opacity_info.setStyleSheet(f"color: {SUBTEXT}; font-size: 11px;")
        opacity_row.addWidget(opacity_lbl)
        opacity_row.addWidget(opacity_spin)
        opacity_row.addWidget(opacity_info)
        opacity_row.addStretch()
        layout.addLayout(opacity_row)
        
        # Variable para guardar la nueva ruta
        new_path = [current_img]
        
        def select_image():
            path, _ = QFileDialog.getOpenFileName(
                dlg, "Seleccionar Logo de Empresa", "",
                "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)"
            )
            if path:
                new_path[0] = path
                img_path_lbl.setText(Path(path).name)
                if Path(path).exists():
                    pix = QPixmap(path).scaled(190, 190, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                    preview.setPixmap(pix)
        
        btn_select.clicked.connect(select_image)
        
        # Botones
        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("danger")
        cancel.clicked.connect(dlg.reject)
        save = QPushButton("💾  Guardar")
        save.setObjectName("primary")
        
        def save_config():
            _write_env({
                "WATERMARK_IMAGE": new_path[0],
                "WATERMARK_OPACITY": str(opacity_spin.value())
            })
            dlg.accept()
        
        save.clicked.connect(save_config)
        btns.addWidget(cancel)
        btns.addStretch()
        btns.addWidget(save)
        layout.addLayout(btns)
        
        if dlg.exec():
            QMessageBox.information(
                self, "Exito",
                f"✅ Logo actualizado. Aparecera en la parte superior izquierda del PDF.\n\nArchivo: {Path(new_path[0]).name}"
            )

    def _manage_business_data(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Datos de la Empresa")
        dlg.setMinimumSize(440, 300)
        dlg.setStyleSheet(QSS)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("🏢  Datos de la Empresa (aparecen en el PDF)")
        title.setStyleSheet(f"color: {TEXT}; font-size: 17px; font-weight: 700;")
        layout.addWidget(title)

        env = _read_env()
        form = QFormLayout()
        form.setSpacing(10)

        name_input    = QLineEdit(env.get("BUSINESS_NAME", ""))
        phone_input   = QLineEdit(env.get("BUSINESS_PHONE", ""))
        email_input   = QLineEdit(env.get("BUSINESS_EMAIL", ""))
        address_input = QLineEdit(env.get("BUSINESS_ADDRESS", ""))

        name_input.setPlaceholderText("Ej: Mi Empresa S.A.")
        phone_input.setPlaceholderText("Ej: +52 55 1234 5678")
        email_input.setPlaceholderText("Ej: contacto@miempresa.com")
        address_input.setPlaceholderText("Ej: Calle 123, Ciudad, País")

        form.addRow("Nombre:",    name_input)
        form.addRow("Teléfono:",  phone_input)
        form.addRow("Email:",     email_input)
        form.addRow("Dirección:", address_input)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("danger")
        btn_cancel.clicked.connect(dlg.reject)
        btn_save = QPushButton("💾  Guardar")
        btn_save.setObjectName("primary")

        def save():
            _write_env({
                "BUSINESS_NAME":    name_input.text().strip() or "Mi Empresa",
                "BUSINESS_PHONE":   phone_input.text().strip(),
                "BUSINESS_EMAIL":   email_input.text().strip(),
                "BUSINESS_ADDRESS": address_input.text().strip(),
            })
            dlg.accept()
            QMessageBox.information(self, "Guardado", "✅ Datos de empresa actualizados.\nAparecen en el encabezado del PDF.")

        btn_save.clicked.connect(save)
        btns.addWidget(btn_cancel)
        btns.addStretch()
        btns.addWidget(btn_save)
        layout.addLayout(btns)
        dlg.exec()

    def _manage_advisors(self):
        from agent.bot import load_advisors, save_advisors
        dlg = QDialog(self)
        dlg.setWindowTitle("Gestionar Asesores")
        dlg.setMinimumSize(500, 400)
        dlg.setStyleSheet(QSS)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("👨💼  Asesores de WhatsApp")
        title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        info = QLabel("Los clientes podrán elegir con qué asesor hablar cuando soliciten atención.")
        info.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Nombre", "Teléfono", ""])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(2, 50)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(50)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setMinimumHeight(160)
        layout.addWidget(table, 1)

        def refresh():
            advisors = load_advisors(self._profile_id)
            table.setRowCount(len(advisors))
            for i, a in enumerate(advisors):
                table.setItem(i, 0, QTableWidgetItem(a["name"]))
                table.setItem(i, 1, QTableWidgetItem(a["phone"]))
                btn_del = QPushButton("X")
                btn_del.setFixedSize(26, 14)
                btn_del.setStyleSheet(f"background:{DANGER};color:white;border:none;border-radius:3px;font-size:11px;font-weight:700;")
                btn_del.clicked.connect(lambda _, n=a["name"]: delete_advisor(n))
                cell = QWidget()
                cell_layout = QHBoxLayout(cell)
                cell_layout.setContentsMargins(1, 1, 1, 1)
                cell_layout.addWidget(btn_del)
                table.setCellWidget(i, 2, cell)

        def delete_advisor(name):
            advisors = load_advisors(self._profile_id)
            save_advisors(self._profile_id, [a for a in advisors if a["name"] != name])
            refresh()

        # Formulario agregar
        form_row = QHBoxLayout()
        name_input  = QLineEdit(); name_input.setPlaceholderText("Nombre del asesor")
        phone_input = QLineEdit(); phone_input.setPlaceholderText("+573001234567")
        btn_add = QPushButton("➕ Agregar")
        btn_add.setObjectName("primary")
        btn_add.setFixedHeight(34)

        def add_advisor():
            name  = name_input.text().strip()
            phone = phone_input.text().strip()
            if not name or not phone:
                QMessageBox.warning(dlg, "Error", "Nombre y teléfono son obligatorios.")
                return
            advisors = load_advisors(self._profile_id)
            advisors.append({"name": name, "phone": phone})
            save_advisors(self._profile_id, advisors)
            name_input.clear(); phone_input.clear()
            refresh()

        btn_add.clicked.connect(add_advisor)
        form_row.addWidget(name_input, 2)
        form_row.addWidget(phone_input, 2)
        form_row.addWidget(btn_add)
        layout.addLayout(form_row)

        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("primary")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)

        refresh()
        dlg.exec()

    def _manage_firmas(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Configurar Firmas del PDF")
        dlg.setMinimumSize(420, 260)
        dlg.setStyleSheet(QSS)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("✍️  Etiquetas de Firmas en el PDF")
        title.setStyleSheet(f"color: {TEXT}; font-size: 17px; font-weight: 700;")
        layout.addWidget(title)

        info = QLabel("Estas etiquetas aparecen debajo de las lineas de firma al final del PDF.")
        info.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        env = _read_env()
        form = QFormLayout()
        form.setSpacing(10)
        firma1_input = QLineEdit(env.get("FIRMA1_LABEL", "Firma Empresa"))
        firma2_input = QLineEdit(env.get("FIRMA2_LABEL", "Firma Cliente"))
        form.addRow("Firma izquierda:", firma1_input)
        form.addRow("Firma derecha:",   firma2_input)
        layout.addLayout(form)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("danger")
        btn_cancel.clicked.connect(dlg.reject)
        btn_save = QPushButton("💾  Guardar")
        btn_save.setObjectName("primary")

        def save():
            _write_env({
                "FIRMA1_LABEL": firma1_input.text().strip() or "Firma Empresa",
                "FIRMA2_LABEL": firma2_input.text().strip() or "Firma Cliente",
            })
            dlg.accept()
            QMessageBox.information(self, "Guardado", "✅ Firmas actualizadas.")

        btn_save.clicked.connect(save)
        btns.addWidget(btn_cancel)
        btns.addStretch()
        btns.addWidget(btn_save)
        layout.addLayout(btns)
        dlg.exec()

    def _manage_bot_config(self):
        from agent.bot import get_bot_config, save_bot_config
        dlg = QDialog(self)
        dlg.setWindowTitle("Config Bot - Menu Cotizaciones")
        dlg.setMinimumSize(480, 420)
        dlg.setStyleSheet(QSS)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("⚙️  Opciones del Menu de Cotizaciones")
        title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        info = QLabel(
            "Estas son las opciones que el cliente vera cuando solicite una cotizacion.\n"
            "Puedes agregar, editar o eliminar segun el tipo de negocio."
        )
        info.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        config = get_bot_config(self._profile_id)
        opciones = list(config.get("cotizacion_opciones", []))

        list_widget = QTableWidget(0, 2)
        list_widget.setHorizontalHeaderLabels(["Opcion", ""])
        list_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        list_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        list_widget.setColumnWidth(1, 50)
        list_widget.verticalHeader().setVisible(False)
        list_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        list_widget.verticalHeader().setDefaultSectionSize(50)
        list_widget.setMinimumHeight(160)
        layout.addWidget(list_widget, 1)

        def refresh():
            list_widget.setRowCount(len(opciones))
            for i, op in enumerate(opciones):
                list_widget.setItem(i, 0, QTableWidgetItem(op))
                btn_del = QPushButton("X")
                btn_del.setFixedSize(32, 26)
                btn_del.setStyleSheet(f"background:{DANGER};color:white;border:none;border-radius:3px;font-size:11px;font-weight:700;")
                btn_del.clicked.connect(lambda _, idx=i: remove_opcion(idx))
                cell = QWidget()
                cl = QHBoxLayout(cell)
                cl.setContentsMargins(4, 4, 4, 4)
                cl.addWidget(btn_del)
                list_widget.setCellWidget(i, 1, cell)

        def remove_opcion(idx):
            opciones.pop(idx)
            refresh()

        add_row = QHBoxLayout()
        new_input = QLineEdit()
        new_input.setPlaceholderText("Ej: Plomeria, Electricidad, Carpinteria...")
        btn_add = QPushButton("+ Agregar")
        btn_add.setObjectName("primary")
        btn_add.setFixedHeight(34)

        def add_opcion():
            text = new_input.text().strip()
            if not text:
                return
            opciones.append(text)
            new_input.clear()
            refresh()

        btn_add.clicked.connect(add_opcion)
        new_input.returnPressed.connect(add_opcion)
        add_row.addWidget(new_input, 1)
        add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("danger")
        btn_cancel.clicked.connect(dlg.reject)
        btn_save = QPushButton("💾  Guardar")
        btn_save.setObjectName("primary")

        def save():
            if not opciones:
                QMessageBox.warning(dlg, "Error", "Debe haber al menos una opcion.")
                return
            config["cotizacion_opciones"] = opciones
            save_bot_config(self._profile_id, config)
            dlg.accept()
            QMessageBox.information(self, "Guardado", "✅ Menu de cotizaciones actualizado.")

        btn_save.clicked.connect(save)
        btns.addWidget(btn_cancel)
        btns.addStretch()
        btns.addWidget(btn_save)
        layout.addLayout(btns)

        refresh()
        dlg.exec()

    def _manage_manuals(self):
        """Permite gestionar los manuales del perfil actual."""
        from agent.profiles import get_profile_data_dir
        manuals_dir = get_profile_data_dir(self._profile_id) / "manuales"
        manuals_dir.mkdir(exist_ok=True)
        
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Gestionar Manuales - {self._session['profile_name']}")
        dlg.setMinimumSize(700, 500)
        dlg.resize(900, 650)
        dlg.setStyleSheet(QSS)
        
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title = QLabel(f"📚  Manuales del Bot - {self._session['profile_name']}")
        title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)
        
        info = QLabel(
            "Los manuales son archivos .txt que el bot usará como referencia para responder preguntas.\n"
            "Agrega información sobre tu empresa, productos, servicios, políticas, etc."
        )
        info.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Lista de manuales
        manuals_list = QTableWidget(0, 3)
        manuals_list.setHorizontalHeaderLabels(["Archivo", "Tamaño", "Acciones"])
        manuals_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        manuals_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        manuals_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        manuals_list.setColumnWidth(2, 100)
        manuals_list.verticalHeader().setVisible(False)
        manuals_list.verticalHeader().setDefaultSectionSize(50)
        manuals_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        manuals_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        manuals_list.setMinimumHeight(300)
        layout.addWidget(manuals_list, 1)
        
        def refresh_list():
            files = sorted(manuals_dir.glob("*.txt"))
            manuals_list.setRowCount(len(files))
            for row, file in enumerate(files):
                size_kb = file.stat().st_size / 1024
                manuals_list.setItem(row, 0, QTableWidgetItem(file.name))
                manuals_list.setItem(row, 1, QTableWidgetItem(f"{size_kb:.1f} KB"))
                
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 4, 4, 4)
                btn_layout.setSpacing(6)
                
                btn_edit = QPushButton("✏️")
                btn_edit.setObjectName("edit")
                btn_edit.setFixedSize(36, 28)
                btn_edit.clicked.connect(lambda _, f=file: edit_manual(f))

                btn_del = QPushButton("🗑️")
                btn_del.setObjectName("danger")
                btn_del.setFixedSize(36, 28)
                btn_del.clicked.connect(lambda _, f=file: delete_manual(f))

                btn_layout.addWidget(btn_edit)
                btn_layout.addWidget(btn_del)
                btn_layout.addStretch()
                manuals_list.setCellWidget(row, 2, btn_widget)
        
        def add_manual():
            path, _ = QFileDialog.getOpenFileName(
                dlg, "Seleccionar Manual (TXT)", "",
                "Archivos de texto (*.txt)"
            )
            if path:
                import shutil
                dest = manuals_dir / Path(path).name
                shutil.copy2(path, dest)
                refresh_list()
                QMessageBox.information(dlg, "Éxito", f"✅ Manual agregado: {Path(path).name}")
        
        def create_manual():
            name, ok = QInputDialog.getText(dlg, "Nuevo Manual", "Nombre del archivo (sin extensión):")
            if ok and name:
                if not name.endswith(".txt"):
                    name += ".txt"
                file_path = manuals_dir / name
                if file_path.exists():
                    QMessageBox.warning(dlg, "Error", "Ya existe un manual con ese nombre.")
                    return
                file_path.write_text("", encoding="utf-8")
                edit_manual(file_path)
                refresh_list()
        
        def edit_manual(file_path: Path):
            editor = QDialog(dlg)
            editor.setWindowTitle(f"Editar - {file_path.name}")
            editor.setMinimumSize(700, 500)
            editor.setStyleSheet(QSS)
            
            ed_layout = QVBoxLayout(editor)
            ed_layout.setContentsMargins(16, 16, 16, 16)
            ed_layout.setSpacing(12)
            
            ed_title = QLabel(f"✏️  {file_path.name}")
            ed_title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 700;")
            ed_layout.addWidget(ed_title)
            
            text_edit = QTextEdit()
            text_edit.setPlainText(file_path.read_text(encoding="utf-8"))
            text_edit.setStyleSheet(f"""
                QTextEdit {{
                    background: {CARD}; color: {TEXT};
                    border: 1px solid {BORDER}; border-radius: 8px;
                    padding: 12px; font-family: 'Consolas', monospace; font-size: 12px;
                }}
            """)
            ed_layout.addWidget(text_edit, 1)
            
            btn_row = QHBoxLayout()
            btn_cancel = QPushButton("Cancelar")
            btn_cancel.setObjectName("danger")
            btn_cancel.clicked.connect(editor.reject)
            
            btn_save = QPushButton("💾")
            btn_save.setObjectName("primary")
            btn_save.setFixedWidth(50)
            
            def save_content():
                file_path.write_text(text_edit.toPlainText(), encoding="utf-8")
                editor.accept()
                QMessageBox.information(editor, "Éxito", f"✅ Manual guardado: {file_path.name}")
            
            btn_save.clicked.connect(save_content)
            btn_row.addWidget(btn_cancel)
            btn_row.addStretch()
            btn_row.addWidget(btn_save)
            ed_layout.addLayout(btn_row)
            
            editor.exec()
        
        def delete_manual(file_path: Path):
            reply = QMessageBox.question(
                dlg, "Confirmar",
                f"¿Eliminar el manual '{file_path.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                file_path.unlink()
                refresh_list()
                QMessageBox.information(dlg, "Éxito", f"✅ Manual eliminado: {file_path.name}")
        
        # Botones principales
        btns = QHBoxLayout()
        btn_add = QPushButton("📄  Agregar")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(add_manual)
        
        btn_create = QPushButton("➕  Crear")
        btn_create.setObjectName("primary")
        btn_create.clicked.connect(create_manual)
        
        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("primary")
        btn_close.clicked.connect(dlg.accept)
        
        btns.addWidget(btn_add)
        btns.addWidget(btn_create)
        btns.addStretch()
        btns.addWidget(btn_close)
        layout.addLayout(btns)
        
        refresh_list()
        dlg.exec()

    # ── Contenido ─────────────────────────────────────────────────────────────
    def _build_content(self) -> QWidget:
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(28, 28, 28, 28)
        self.content_layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("title")

        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("🔍  Buscar producto...")
        self.search.setFixedWidth(260)
        self.search.textChanged.connect(self._filter_table)

        add_btn = QPushButton("＋  Producto")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_product)
        add_btn.setVisible(self._is_admin)
        self._add_btn = add_btn

        header.addWidget(self.page_title)
        header.addStretch()
        header.addWidget(self.search)
        header.addWidget(add_btn)

        # Logo header
        logo_btn = QLabel()
        logo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logo_btn.setToolTip("github.com/MFL4bs")
        logo_btn.setFixedSize(48, 48)
        logo_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_btn.setStyleSheet("""
            QLabel {
                background: white; border-radius: 24px;
                padding: 3px; border: 2px solid #D1CBC4;
            }
            QLabel:hover { border: 2px solid #1B6CA8; }
        """)
        pix48 = _make_logo_pixmap(40)
        if pix48:
            logo_btn.setPixmap(pix48)
        else:
            logo_btn.setText("MF")
        logo_btn.mousePressEvent = lambda _: __import__('webbrowser').open("https://github.com/MFL4bs")
        header.addWidget(logo_btn)

        github_btn = QPushButton("⬡  MFL4bs")
        github_btn.setObjectName("github")
        github_btn.setToolTip("github.com/MFL4bs")
        github_btn.clicked.connect(lambda: __import__('webbrowser').open("https://github.com/MFL4bs"))
        header.addWidget(github_btn)
        self.content_layout.addLayout(header)

        # ── Vista Dashboard ───────────────────────────────────────────────────
        self._dashboard_widget = QWidget()
        self._dashboard_widget.setVisible(True)
        dash_layout = QVBoxLayout(self._dashboard_widget)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_layout.setSpacing(20)

        dash_cards_row = QHBoxLayout()
        dash_cards_row.setSpacing(20)

        # Card productos
        card_prod = QWidget()
        card_prod.setObjectName("card")
        card_prod.setFixedSize(260, 140)
        _sh1 = QGraphicsDropShadowEffect()
        _sh1.setBlurRadius(20); _sh1.setColor(QColor(0,0,0,60)); _sh1.setOffset(0,4)
        card_prod.setGraphicsEffect(_sh1)
        cp_layout = QVBoxLayout(card_prod)
        cp_layout.setContentsMargins(24, 20, 24, 20)
        cp_layout.setSpacing(4)
        cp_icon = QLabel("📦"); cp_icon.setStyleSheet("font-size: 26px;")
        self.dash_prod_val = QLabel("0")
        self.dash_prod_val.setStyleSheet(f"color: {ACCENT2}; font-size: 32px; font-weight: 700;")
        self.dash_prod_lbl = QLabel("Productos en catálogo")
        self.dash_prod_lbl.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        cp_layout.addWidget(cp_icon)
        cp_layout.addWidget(self.dash_prod_val)
        cp_layout.addWidget(self.dash_prod_lbl)

        # Card bot
        card_bot_d = QWidget()
        card_bot_d.setObjectName("card")
        card_bot_d.setFixedSize(260, 140)
        _sh2 = QGraphicsDropShadowEffect()
        _sh2.setBlurRadius(20); _sh2.setColor(QColor(0,0,0,60)); _sh2.setOffset(0,4)
        card_bot_d.setGraphicsEffect(_sh2)
        cb_layout = QVBoxLayout(card_bot_d)
        cb_layout.setContentsMargins(24, 20, 24, 20)
        cb_layout.setSpacing(4)
        cb_icon = QLabel("🤖"); cb_icon.setStyleSheet("font-size: 26px;")
        self.dash_bot_val = QLabel("Activo")
        self.dash_bot_val.setStyleSheet(f"color: {SUCCESS}; font-size: 32px; font-weight: 700;")
        self.dash_bot_lbl = QLabel("Estado del bot")
        self.dash_bot_lbl.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        cb_layout.addWidget(cb_icon)
        cb_layout.addWidget(self.dash_bot_val)
        cb_layout.addWidget(self.dash_bot_lbl)

        # Card WhatsApp
        card_wa_d = QWidget()
        card_wa_d.setObjectName("card")
        card_wa_d.setFixedSize(260, 140)
        _sh3 = QGraphicsDropShadowEffect()
        _sh3.setBlurRadius(20); _sh3.setColor(QColor(0,0,0,60)); _sh3.setOffset(0,4)
        card_wa_d.setGraphicsEffect(_sh3)
        cw_layout = QVBoxLayout(card_wa_d)
        cw_layout.setContentsMargins(24, 20, 24, 20)
        cw_layout.setSpacing(4)
        cw_icon = QLabel("📱"); cw_icon.setStyleSheet("font-size: 26px;")
        self.dash_wa_val = QLabel("—")
        self.dash_wa_val.setStyleSheet(f"color: {SUBTEXT}; font-size: 32px; font-weight: 700;")
        self.dash_wa_lbl = QLabel("WhatsApp")
        self.dash_wa_lbl.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        cw_layout.addWidget(cw_icon)
        cw_layout.addWidget(self.dash_wa_val)
        cw_layout.addWidget(self.dash_wa_lbl)

        dash_cards_row.addWidget(card_prod)
        dash_cards_row.addWidget(card_bot_d)
        dash_cards_row.addWidget(card_wa_d)
        dash_cards_row.addStretch()
        dash_layout.addLayout(dash_cards_row)

        # Alerta stock bajo
        self.dash_alert = QLabel()
        self.dash_alert.setVisible(False)
        self.dash_alert.setWordWrap(True)
        self.dash_alert.setStyleSheet(
            f"background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D;"
            f"border-radius: 10px; padding: 12px 18px; font-size: 13px; font-weight: 600;"
        )
        dash_layout.addWidget(self.dash_alert)

        # Imagen/GIF personalizado del negocio
        map_card = QWidget()
        map_card.setObjectName("card")
        _sh_map = QGraphicsDropShadowEffect()
        _sh_map.setBlurRadius(20); _sh_map.setColor(QColor(0,0,0,60)); _sh_map.setOffset(0,4)
        map_card.setGraphicsEffect(_sh_map)
        map_card_layout = QVBoxLayout(map_card)
        map_card_layout.setContentsMargins(16, 16, 16, 16)
        map_card_layout.setSpacing(10)

        map_header = QHBoxLayout()
        map_title = QLabel("🎬  Imagen del Negocio")
        map_title.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 700;")
        map_header.addWidget(map_title)
        map_header.addStretch()

        # Botón para cambiar imagen
        btn_change_image = QPushButton("📷  Cambiar")
        btn_change_image.setObjectName("primary")
        btn_change_image.setFixedHeight(30)
        btn_change_image.clicked.connect(self._change_dashboard_image)
        map_header.addWidget(btn_change_image)
        
        map_card_layout.addLayout(map_header)

        # Label para imagen/GIF personalizado
        from PyQt6.QtGui import QMovie
        self._custom_image_label = QLabel()
        self._custom_image_label.setMinimumHeight(300)
        self._custom_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._custom_image_label.setStyleSheet(f"background: {SIDEBAR}; border-radius: 8px;")
        self._custom_image_label.setScaledContents(True)  # Escalar contenido para llenar el espacio
        
        env_now = _read_env()
        self._custom_image = env_now.get("DASHBOARD_IMAGE", "")
        
        # Cargar imagen por defecto si existe
        if self._custom_image and Path(self._custom_image).exists():
            self._load_dashboard_image(self._custom_image)
        else:
            # Mostrar placeholder
            self._custom_image_label.setScaledContents(False)
            self._custom_image_label.setText("🖼️\n\nHaz clic en 'Cambiar Imagen/GIF'\npara agregar tu imagen o GIF animado")
            self._custom_image_label.setStyleSheet(
                self._custom_image_label.styleSheet() + f" color: {SUBTEXT}; font-size: 14px;"
            )
        
        map_card_layout.addWidget(self._custom_image_label, 1)  # El 1 hace que se expanda

        dash_layout.addWidget(map_card)
        dash_layout.addStretch()
        
        self.content_layout.addWidget(self._dashboard_widget)

        # Stats cards con slider (Inventario)
        card1, self.stat_total = make_stat_card("📦", "Total Productos", "0", ACCENT2)
        card2, self.stat_stock = make_stat_card("✅", "En Stock", "0", SUCCESS)
        card3, self.stat_low  = make_stat_card("⚠️", "Stock Bajo", "0", WARNING)
        card4, self.stat_out  = make_stat_card("❌", "Sin Stock", "0", DANGER)
        card5, self.stat_bot  = make_stat_card("🤖", "Estado Bot", "Activo", SUCCESS)
        card6, self.stat_msgs = make_stat_card("💬", "Mensajes Hoy", "—", ACCENT)

        self._slider = CardsSlider([card1, card2, card3, card4, card5, card6])
        self._slider.setVisible(False)
        self.content_layout.addWidget(self._slider)

        # Tabla de inventario
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["Foto", "SKU", "Nombre", "Categoría", "Precio", "Stock", "Acciones"])
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 64)
        self._table.setColumnWidth(1, 110)
        self._table.setColumnWidth(3, 110)
        self._table.setColumnWidth(4, 90)
        self._table.setColumnWidth(5, 80)
        self._table.setColumnWidth(6, 140)
        self._table.verticalHeader().setDefaultSectionSize(56)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(self._table.styleSheet() + f"""
            QTableWidget {{ alternate-background-color: {SIDEBAR}; }}
        """)
        self.content_layout.addWidget(self._table)

        # Vista de ventas (oculta por defecto)
        self._sales_widget = QWidget()
        self._sales_widget.setVisible(False)
        sv_layout = QVBoxLayout(self._sales_widget)
        sv_layout.setContentsMargins(0, 0, 0, 0)
        sv_layout.setSpacing(12)

        # Stats ventas
        sv_stats = QHBoxLayout()
        card_st, self.stat_sales_total = make_stat_card("💰", "Ventas Hoy", "$0", SUCCESS)
        card_sc, self.stat_sales_count = make_stat_card("🛒", "Pedidos Hoy", "0", ACCENT2)
        card_sw, self.stat_sales_wa   = make_stat_card("📱", "Vía WhatsApp", "0", WARNING)
        card_all, self.stat_sales_all_total = make_stat_card("💎", "Ventas Totales", "$0", ACCENT2)
        card_all_count, self.stat_sales_all_count = make_stat_card("📊", "Pedidos Totales", "0", ACCENT)
        sv_stats.addWidget(card_st)
        sv_stats.addWidget(card_sc)
        sv_stats.addWidget(card_sw)
        sv_stats.addWidget(card_all)
        sv_stats.addWidget(card_all_count)
        sv_stats.addStretch()
        sv_layout.addLayout(sv_stats)

        self._sales_table = QTableWidget()
        self._sales_table.setColumnCount(9)
        self._sales_table.setHorizontalHeaderLabels(
            ["Fecha", "ID", "Cliente", "Canal", "Items", "Total", "PDF", "✏️", "🗑️"]
        )
        self._sales_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._sales_table.setColumnWidth(0, 130)
        self._sales_table.setColumnWidth(1, 110)
        self._sales_table.setColumnWidth(2, 120)
        self._sales_table.setColumnWidth(3, 90)
        self._sales_table.setColumnWidth(5, 90)
        self._sales_table.setColumnWidth(6, 70)
        self._sales_table.setColumnWidth(7, 50)
        self._sales_table.setColumnWidth(8, 50)
        self._sales_table.verticalHeader().setDefaultSectionSize(40)
        self._sales_table.verticalHeader().setVisible(False)
        self._sales_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._sales_table.setAlternatingRowColors(True)
        self._sales_table.setStyleSheet(self._sales_table.styleSheet() +
            f"QTableWidget {{ alternate-background-color: {SIDEBAR}; }}")
        sv_layout.addWidget(self._sales_table)
        self.content_layout.addWidget(self._sales_widget)

        return self.content

    def resizeEvent(self, event):
        """Ajusta la marca de agua al redimensionar la ventana."""
        super().resizeEvent(event)
        if hasattr(self, '_watermark') and hasattr(self, '_dashboard_widget'):
            if self._dashboard_widget.isVisible():
                size = self._dashboard_widget.size()
                self._watermark.setGeometry(0, 0, size.width(), size.height())

    def _change_dashboard_image(self):
        """Permite seleccionar una imagen o GIF para el dashboard."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen/GIF para Dashboard", "",
            "Imágenes (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"
        )
        if path:
            self._custom_image = path
            _write_env({"DASHBOARD_IMAGE": path})
            self._load_dashboard_image(path)
            QMessageBox.information(
                self, "Éxito",
                f"✅ Imagen actualizada\n\nLa nueva imagen se mostrará en el dashboard.\n\nArchivo: {Path(path).name}"
            )
    
    def _load_dashboard_image(self, path: str):
        """Carga una imagen o GIF en el dashboard."""
        if not path or not Path(path).exists():
            return
        
        self._custom_image_label.setScaledContents(True)
        
        # Cargar imagen o GIF
        if path.lower().endswith('.gif'):
            from PyQt6.QtGui import QMovie
            movie = QMovie(path)
            self._custom_image_label.setMovie(movie)
            movie.start()
            # Para GIFs, ajustar el tamaño del movie al label
            movie.setScaledSize(self._custom_image_label.size())
        else:
            # Para imágenes estáticas, cargar directamente
            pix = QPixmap(path)
            self._custom_image_label.setPixmap(pix)

    # ── Navegación ────────────────────────────────────────────────────────────
    def _nav(self, page: str):
        if getattr(self, "_current_page", None) == page:
            return
        self._current_page = page

        for name in ["Dashboard", "Inventario", "Ventas", "Stock Bajo"]:
            btn = getattr(self, f"nav_{name.lower().replace(' ', '_')}")
            btn.blockSignals(True)
            btn.setChecked(name == page)
            btn.blockSignals(False)

        self.page_title.setText(page)
        self.search.setVisible(page not in ("Ventas", "Dashboard"))
        self._dashboard_widget.setVisible(page == "Dashboard")
        self._slider.setVisible(page == "Inventario")
        if page == "Ventas":
            self._add_btn.setText("＋  Venta")
            self._add_btn.clicked.disconnect()
            self._add_btn.clicked.connect(self._add_sale)
            if not hasattr(self, "_invoice_btn"):
                self._invoice_btn = QPushButton("🧾  Factura")
                self._invoice_btn.setObjectName("primary")
                self._invoice_btn.clicked.connect(self._add_invoice)
                self.content_layout.itemAt(0).layout().insertWidget(
                    self.content_layout.itemAt(0).layout().count() - 2,
                    self._invoice_btn
                )
            self._invoice_btn.setVisible(True)
            self._show_sales_view()
        else:
            if hasattr(self, "_invoice_btn"):
                self._invoice_btn.setVisible(False)
            self._add_btn.setText("＋  Producto")
            self._add_btn.clicked.disconnect()
            self._add_btn.clicked.connect(self._add_product)
            self._add_btn.setVisible(page != "Dashboard")
            self._table.setVisible(page in ("Inventario", "Stock Bajo"))
            self._sales_widget.setVisible(False)
            if page == "Stock Bajo":
                self._populate_table(low_stock_products(self._profile_id, 15))
            elif page == "Inventario":
                self._populate_table(self.products)

    # ── Cargar datos ──────────────────────────────────────────────────────────
    def _load_products(self):
        self.worker = LoadWorker(self._profile_id)
        try:
            self.worker.done.disconnect()
        except Exception:
            pass
        self.worker.done.connect(self._on_products_loaded)
        self.worker.start()

    def _on_products_loaded(self, products: list):
        self.products = products
        self._update_stats(products)
        page = getattr(self, "_current_page", "Dashboard")
        if page == "Inventario":
            self._populate_table(products)
        elif page == "Stock Bajo":
            self._populate_table(low_stock_products(self._profile_id, 15))

    def _update_stats(self, products: list):
        total = len(products)
        in_stock = sum(1 for p in products if p["stock"] > 15)
        low = sum(1 for p in products if 0 < p["stock"] <= 15)
        out = sum(1 for p in products if p["stock"] == 0)
        self.stat_total.setText(str(total))
        self.stat_stock.setText(str(in_stock))
        self.stat_low.setText(str(low))
        self.stat_out.setText(str(out))

        # Dashboard: productos
        self.dash_prod_val.setText(str(total))
        if total == 0:
            self.dash_prod_val.setStyleSheet(f"color: {DANGER}; font-size: 32px; font-weight: 700;")
            self.dash_prod_lbl.setText("⚠️ Sin productos cargados")
        elif total <= 5:
            self.dash_prod_val.setStyleSheet(f"color: {WARNING}; font-size: 32px; font-weight: 700;")
            self.dash_prod_lbl.setText("Pocos productos en catálogo")
        else:
            self.dash_prod_val.setStyleSheet(f"color: {ACCENT2}; font-size: 32px; font-weight: 700;")
            self.dash_prod_lbl.setText("Productos en catálogo")

        # Dashboard: alerta stock
        parts = []
        if out: parts.append(f"{out} sin stock")
        if low: parts.append(f"{low} con stock bajo")
        if parts:
            self.dash_alert.setText(f"⚠️  Atención: {', '.join(parts)}. Revisa el inventario.")
            self.dash_alert.setVisible(True)
        else:
            self.dash_alert.setVisible(False)

        # Dashboard: WhatsApp
        import urllib.request as _ur, json as _json
        try:
            with _ur.urlopen("http://127.0.0.1:8000/bridge/status", timeout=1) as r:
                data = _json.loads(r.read())
                if data.get("connected"):
                    self.dash_wa_val.setText("Conectado")
                    self.dash_wa_val.setStyleSheet(f"color: {SUCCESS}; font-size: 26px; font-weight: 700;")
                    return
        except Exception:
            pass
        self.dash_wa_val.setText("Desconectado")
        self.dash_wa_val.setStyleSheet(f"color: {DANGER}; font-size: 26px; font-weight: 700;")

    def _show_sales_view(self):
        self._table.setVisible(False)
        self._sales_widget.setVisible(True)
        self._sales_worker = SalesWorker(self._profile_id)
        try:
            self._sales_worker.done.disconnect()
        except Exception:
            pass
        self._sales_worker.done.connect(self._on_sales_loaded)
        self._sales_worker.start()

    def _on_sales_loaded(self, invoices: list):
        from datetime import datetime
        all_records = sorted(invoices, key=lambda x: x.get("timestamp", ""), reverse=True)
        today = datetime.now().strftime("%Y-%m-%d")
        today_recs = [r for r in all_records if r.get("timestamp", "").startswith(today)]
        
        # Estadísticas de hoy
        total_hoy = sum(r.get("total", 0) for r in today_recs)
        wa_count = sum(1 for r in today_recs if r.get("channel") == "whatsapp")
        
        # Estadísticas totales (todos los tiempos)
        total_all = sum(r.get("total", 0) for r in all_records)
        
        self.stat_sales_total.setText(f"${total_hoy:.0f}")
        self.stat_sales_count.setText(str(len(today_recs)))
        self.stat_sales_wa.setText(str(wa_count))
        self.stat_sales_all_total.setText(f"${total_all:.0f}")
        self.stat_sales_all_count.setText(str(len(all_records)))

        self._sales_table.setRowCount(len(all_records))
        for row, rec in enumerate(all_records):
            canal = rec.get("channel", "manual")
            canal_icon = "WhatsApp" if canal == "whatsapp" else "Manual"
            items = rec.get("items", [])
            items_txt = ", ".join(f"{i.get('product_name','')} x{i.get('quantity',1)}" for i in items)
            total_val = rec.get("total", 0)
            total_item = QTableWidgetItem(f"${total_val:.2f}")
            total_item.setForeground(QColor(SUCCESS))
            self._sales_table.setItem(row, 0, QTableWidgetItem(rec.get("timestamp", "")))
            self._sales_table.setItem(row, 1, QTableWidgetItem(rec.get("invoice_id", "")))
            self._sales_table.setItem(row, 2, QTableWidgetItem(rec.get("customer", "")))
            self._sales_table.setItem(row, 3, QTableWidgetItem(canal_icon))
            self._sales_table.setItem(row, 4, QTableWidgetItem(items_txt))
            self._sales_table.setItem(row, 5, total_item)
            pdf_btn = QPushButton("PDF")
            pdf_btn.setFixedHeight(30)
            pdf_btn.setFixedWidth(60)
            pdf_btn.setStyleSheet(f"background:{ACCENT2};color:white;border:none;border-radius:4px;font-size:12px;font-weight:600;")
            pdf_btn.clicked.connect(lambda _, r=rec: self._export_pdf(r))
            self._sales_table.setCellWidget(row, 6, pdf_btn)
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedHeight(30)
            edit_btn.setFixedWidth(40)
            edit_btn.setStyleSheet(f"background:{ACCENT};color:white;border:none;border-radius:4px;font-size:12px;")
            edit_btn.setVisible(self._is_admin)
            edit_btn.clicked.connect(lambda _, r=rec: self._edit_invoice(r))
            self._sales_table.setCellWidget(row, 7, edit_btn)
            del_btn = QPushButton("🗑️")
            del_btn.setFixedHeight(30)
            del_btn.setFixedWidth(40)
            del_btn.setStyleSheet(f"background:{DANGER};color:white;border:none;border-radius:4px;font-size:12px;")
            del_btn.setVisible(self._is_admin)
            del_btn.clicked.connect(lambda _, r=rec: self._delete_record(r))
            self._sales_table.setCellWidget(row, 8, del_btn)

    def _edit_invoice(self, record: dict):
        if not self._is_admin:
            return
        from agent.profiles import get_profile
        profile = get_profile(self._profile_id)
        biz_name = record.get("business_name") or (profile["name"] if profile else "Mi Empresa")
        dlg = InvoiceDialog(self, self.products, business_name=biz_name, existing=record)
        if dlg.exec():
            inv_dict = dlg.get_invoice_dict()
            invoice = dlg.get_invoice()
            try:
                # Restaurar stock de la factura vieja
                for item in record.get("items", []):
                    sku = item.get("sku", "")
                    if sku.startswith("COT-"):
                        continue
                    p = get_product(self._profile_id, sku)
                    if p:
                        update_product(self._profile_id, sku, {"stock": int(p["stock"]) + item.get("quantity", 0)})
                # Descontar stock de la factura nueva
                for item in invoice.items:
                    if item.sku.startswith("COT-"):
                        continue
                    p = get_product(self._profile_id, item.sku)
                    if p:
                        update_product(self._profile_id, item.sku, {"stock": max(0, int(p["stock"]) - item.quantity)})
                update_record(self._profile_id, record.get("invoice_id", ""), inv_dict)
                self._show_sales_view()
                self._load_products()
            except Exception as e:
                _msg(self, "Error", str(e))

    def _add_invoice(self):
        from agent.profiles import get_profile
        profile = get_profile(self._profile_id)
        biz_name = profile["name"] if profile else "Mi Empresa"
        dlg = InvoiceDialog(self, self.products, business_name=biz_name)
        if dlg.exec():
            invoice = dlg.get_invoice()
            inv_dict = dlg.get_invoice_dict()
            try:
                record_invoice(self._profile_id, inv_dict)
                # Descontar stock de productos normales (no cotizaciones)
                for item in invoice.items:
                    if item.sku.startswith("COT-"):
                        continue
                    p = get_product(self._profile_id, item.sku)
                    if p and int(p["stock"]) >= item.quantity:
                        update_product(self._profile_id, item.sku, {"stock": int(p["stock"]) - item.quantity})
                path, _ = QFileDialog.getSaveFileName(
                    self, "Guardar Factura PDF", f"{inv_dict.get('invoice_id', 'factura')}.pdf", "PDF (*.pdf)"
                )
                if path:
                    _generate_pdf(inv_dict, path, business_name=biz_name)
                    import subprocess
                    subprocess.Popen(["start", "", path], shell=True)
                    # Subir PDF a Firestore para el móvil
                    from agent.firestore_sync import upload_invoice_pdf
                    import threading
                    threading.Thread(
                        target=upload_invoice_pdf,
                        args=(self._profile_id, inv_dict.get('invoice_id', ''), path),
                        daemon=True
                    ).start()
                self._show_sales_view()
                self._load_products()
                self._sync_firestore()
            except Exception as e:
                _msg(self, "Error", str(e))

    def _export_pdf(self, record: dict):
        inv_id = record.get("invoice_id", "factura")
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF", f"{inv_id}.pdf", "PDF (*.pdf)"
        )
        if path:
            try:
                from agent.profiles import get_profile
                profile = get_profile(self._profile_id)
                biz_name = record.get("business_name") or (profile["name"] if profile else "Mi Empresa")
                _generate_pdf(record, path, business_name=biz_name)
                import subprocess
                subprocess.Popen(["start", "", path], shell=True)
                # Subir PDF a Firestore para el móvil
                from agent.firestore_sync import upload_invoice_pdf
                import threading
                threading.Thread(
                    target=upload_invoice_pdf,
                    args=(self._profile_id, record.get('invoice_id', ''), path),
                    daemon=True
                ).start()
            except Exception as e:
                QMessageBox.warning(self, "Error al generar PDF", str(e))

    def _delete_record(self, record: dict):
        box = QMessageBox(self)
        box.setStyleSheet("QMessageBox{background:#fff;}QMessageBox QLabel{color:#1F2937;}QMessageBox QPushButton{background:#6B7280;color:white;border:none;border-radius:6px;padding:6px 18px;}")
        box.setWindowTitle("Confirmar")
        box.setText(f"Eliminar registro {record.get('invoice_id', '')}?")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.exec()
        if box.result() == QMessageBox.StandardButton.Yes:
            for item in record.get("items", []):
                sku = item.get("sku", "")
                if sku.startswith("COT-"):
                    continue
                qty = item.get("quantity", 0)
                p = get_product(self._profile_id, sku)
                if p:
                    new_stock = int(p["stock"]) + qty
                    update_product(self._profile_id, sku, {"stock": new_stock})
                    # Restaurar stock en Firestore
                    try:
                        from agent.firestore_sync import delete_product_firestore
                        import firebase_admin
                        from firebase_admin import firestore as _fs
                        _app = firebase_admin.get_app("data_sync")
                        _db = _fs.client(app=_app)
                        _db.collection("inventory").document(
                            f"{self._profile_id}_{sku}"
                        ).update({"stock": new_stock})
                    except Exception as _e:
                        print(f"[Firestore] Error restaurando stock {sku}: {_e}")
            sid = record.get("invoice_id", "")
            delete_record(self._profile_id, sid)
            # Borrar factura en Firestore
            try:
                import firebase_admin
                from firebase_admin import firestore as _fs
                _app = firebase_admin.get_app("data_sync")
                _db2 = _fs.client(app=_app)
                _db2.collection("invoices").document(sid).delete()
            except Exception as _e:
                print(f"[Firestore] Error al borrar factura {sid}: {_e}")
            self._show_sales_view()
            self._load_products()

    def _add_sale(self):
        dlg = SaleDialog(self, self.products)
        if dlg.exec():
            invoice = dlg.get_invoice()
            try:
                record_invoice(self._profile_id, invoice.dict())
                for item in invoice.items:
                    p = get_product(self._profile_id, item.sku)
                    if p and int(p["stock"]) >= item.quantity:
                        update_product(self._profile_id, item.sku, {"stock": int(p["stock"]) - item.quantity})
                self._show_sales_view()
                self._load_products()
            except Exception as e:
                import traceback; traceback.print_exc()
                _msg(self, "Error", str(e))

    # ── Tabla inventario ─────────────────────────────────────────────────────────────
    def _populate_table(self, products: list):
        self._table.setRowCount(len(products))
        for row, p in enumerate(products):
            # Foto
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pix = _load_pixmap(p.get("image_url", ""), 48)
            if pix:
                img_lbl.setPixmap(pix)
            else:
                pix_ph = _make_logo_pixmap(40)
                if pix_ph:
                    img_lbl.setPixmap(pix_ph)
                else:
                    img_lbl.setText("MF")
                    img_lbl.setStyleSheet(f"font-size: 11px; color: {SUBTEXT};")
            self._table.setCellWidget(row, 0, img_lbl)

            self._table.setItem(row, 1, QTableWidgetItem(p["sku"]))
            self._table.setItem(row, 2, QTableWidgetItem(p["name"]))
            self._table.setItem(row, 3, QTableWidgetItem(p.get("category", "")))
            self._table.setItem(row, 4, QTableWidgetItem(f"${p['price']:.2f}"))

            stock = int(p["stock"])
            stock_item = QTableWidgetItem(str(stock))
            if stock == 0:
                stock_item.setForeground(QColor(DANGER))
            elif stock <= 15:
                stock_item.setForeground(QColor(WARNING))
            else:
                stock_item.setForeground(QColor(SUCCESS))
            self._table.setItem(row, 5, stock_item)

            # Botones acciones
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 4, 4, 4)
            btn_layout.setSpacing(6)
            edit_btn = QPushButton("✏️")
            edit_btn.setObjectName("edit")
            edit_btn.setFixedHeight(28)
            edit_btn.setFixedWidth(50)
            edit_btn.setVisible(self._is_admin)
            edit_btn.clicked.connect(lambda _, s=p["sku"]: self._edit_product(s))
            del_btn = QPushButton("🗑️")
            del_btn.setObjectName("danger")
            del_btn.setFixedHeight(28)
            del_btn.setFixedWidth(50)
            del_btn.setVisible(self._is_admin)
            del_btn.clicked.connect(lambda _, s=p["sku"]: self._delete_product(s))
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(del_btn)
            self._table.setCellWidget(row, 6, btn_widget)

    def _filter_table(self, text: str):
        q = text.lower()
        filtered = [p for p in self.products
                    if q in p["name"].lower() or q in p["sku"].lower() or q in p.get("category", "").lower()]
        self._populate_table(filtered)

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def _pull_from_firestore(self):
        self._btn_pull.setEnabled(False)
        self._btn_pull.setText("⏳  Sincronizando...")
        from agent.firestore_sync import PullWorker
        self._pull_worker = PullWorker(self._profile_id)
        self._pull_worker.done.connect(self._on_pull_done)
        self._pull_worker.start()

    def _on_pull_done(self, ok: bool, msg: str, changes: list):
        self._btn_pull.setEnabled(True)
        self._btn_pull.setText("📥  Sync desde Móvil")
        self._load_products()
        # Si hay ventas nuevas y estamos en la vista de ventas, refrescar
        page = getattr(self, "_current_page", "Dashboard")
        if page == "Ventas":
            self._show_sales_view()
        if changes:
            detail = "\n".join(changes)
            QMessageBox.information(self, "Sync completado", f"{msg}\n\n{detail}")
        else:
            QMessageBox.information(self, "Sync completado", msg)

    def _sync_firestore(self):
        from agent.firestore_sync import SyncWorker
        self._fw = SyncWorker(self._profile_id)
        self._fw.done.connect(lambda ok, msg: print(f"[Sync] {msg}"))
        self._fw.start()

    def _add_product(self):
        if not self._is_admin:
            return
        dlg = ProductDialog(self, profile_id=self._profile_id)
        if dlg.exec():
            p = dlg.get_product()
            img_path = dlg.get_image_path()
            if img_path:
                import shutil
                from agent.profiles import get_profile_data_dir
                dest_dir = get_profile_data_dir(self._profile_id) / "images"
                dest_dir.mkdir(exist_ok=True)
                ext = Path(img_path).suffix
                dest = dest_dir / f"{p.sku}{ext}"
                shutil.copy2(img_path, dest)
                p.image_url = str(dest)
            upsert_product(self._profile_id, p.dict())
            self._load_products()
            self._sync_firestore()

    def _edit_product(self, sku: str):
        if not self._is_admin:
            return
        product = get_product(self._profile_id, sku)
        if not product:
            return
        dlg = ProductDialog(self, product, profile_id=self._profile_id)
        if dlg.exec():
            p = dlg.get_product()
            img_path = dlg.get_image_path()
            if img_path:
                import shutil
                from agent.profiles import get_profile_data_dir
                dest_dir = get_profile_data_dir(self._profile_id) / "images"
                dest_dir.mkdir(exist_ok=True)
                ext = Path(img_path).suffix
                dest = dest_dir / f"{p.sku}{ext}"
                shutil.copy2(img_path, dest)
                p.image_url = str(dest)
            update_product(self._profile_id, sku, {
                "stock": p.stock, "price": p.price,
                "description": p.description, "name": p.name,
                "category": p.category, "image_url": p.image_url
            })
            self._load_products()
            self._sync_firestore()

    def _delete_product(self, sku: str):
        if not self._is_admin:
            return
        box = QMessageBox(self)
        box.setStyleSheet("QMessageBox{background:#fff;}QMessageBox QLabel{color:#1F2937;}QMessageBox QPushButton{background:#6B7280;color:white;border:none;border-radius:6px;padding:6px 18px;}")
        box.setWindowTitle("Confirmar")
        box.setText(f"Eliminar producto {sku}?")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.exec()
        if box.result() == QMessageBox.StandardButton.Yes:
            delete_product(self._profile_id, sku)
            from agent.firestore_sync import delete_product_firestore
            delete_product_firestore(self._profile_id, sku)
            self._load_products()


# ── Servidor FastAPI en background ───────────────────────────────────────────
def run_server():
    uvicorn.run(api_main.app, host="127.0.0.1", port=8000, log_level="error")


# ── App con flujo Login → Main ────────────────────────────────────────────────
class AppController(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MF Agent")
        
        # Establecer icono de la ventana
        icon_path = Path(__file__).parent / "MF_LABS.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            png_path = Path(__file__).parent / "MF_LABS.png"
            if png_path.exists():
                self.setWindowIcon(QIcon(str(png_path)))
        
        self.showMaximized()

        self._login = LoginScreen()
        self._manager = ProfileManagerScreen()
        self.addWidget(self._login)    # index 0
        self.addWidget(self._manager) # index 1

        self._login.login_success.connect(self._on_login)
        self._login.manage_profiles.connect(lambda: self.setCurrentIndex(1))
        self._manager.back.connect(lambda: (
            self._login._refresh_profiles(),
            self.setCurrentIndex(0)
        ))
        self.setCurrentIndex(0)

    def _on_login(self, session: dict):
        self._main = MainWindow(session)
        self._main.logout.connect(self._on_logout)
        self.addWidget(self._main)
        self.setCurrentWidget(self._main)
        # Sync inmediato al login
        self._do_sync(session["profile_id"])
        # Sync automático cada 5 minutos
        self._sync_timer = QTimer()
        self._sync_timer.timeout.connect(lambda: self._do_sync(session["profile_id"]))
        self._sync_timer.start(5 * 60 * 1000)

    def _do_sync(self, profile_id: str):
        from agent.firestore_sync import SyncWorker
        self._sync = SyncWorker(profile_id)
        self._sync.done.connect(lambda ok, msg: print(f"[Sync] {msg}"))
        self._sync.start()

    def _on_logout(self):
        if hasattr(self, '_sync_timer') and self._sync_timer:
            self._sync_timer.stop()
        old = self._main
        self._login._refresh_profiles()
        self._login.username_input.clear()
        self._login.password_input.clear()
        self._login.error_lbl.setText("")
        self.setCurrentIndex(0)
        self.removeWidget(old)
        old.deleteLater()
        self._main = None


if __name__ == "__main__":
    # Iniciar servidor FastAPI en background
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    icon_path = Path(__file__).parent / "MF_LABS.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        png_path = Path(__file__).parent / "MF_LABS.png"
        if png_path.exists():
            app.setWindowIcon(QIcon(str(png_path)))

    # ── Validar licencia antes de arrancar ────────────────────────────────────
    from lic_manager.activation_screen import ActivationScreen

    activation = ActivationScreen()
    activation.setWindowTitle("MF Agent — Activación")
    activation.setMinimumSize(520, 400)

    def _launch_app():
        activation.hide()
        from splash import SplashScreen
        splash = SplashScreen()
        splash.show()
        app.processEvents()
        controller = AppController()
        controller.setStyleSheet(QSS)
        controller.hide()
        QTimer.singleShot(3300, lambda: splash.finish_loading(controller))

    activation.activated.connect(_launch_app)
    activation.show()

    sys.exit(app.exec())
