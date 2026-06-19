"""
activation_screen.py  —  Pantalla de activación/validación de licencia
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from pathlib import Path

BG     = "#F5F0EB"
CARD   = "#FDFAF7"
TEXT   = "#1F2937"
SUB    = "#6B7280"
ACCENT = "#1B6CA8"
DANGER = "#DC2626"
WARN   = "#D97706"
OK     = "#16A34A"
BORDER = "#D1CBC4"

QSS = f"""
QWidget {{ background:{BG}; color:{TEXT}; font-family:'Segoe UI'; }}
QLineEdit {{
    background:{CARD}; border:1px solid {BORDER}; border-radius:8px;
    padding:10px 14px; font-size:14px; letter-spacing:2px;
}}
QLineEdit:focus {{ border:1px solid {ACCENT}; }}
QPushButton {{
    background:{ACCENT}; color:white; border:none;
    border-radius:8px; padding:11px 24px; font-size:13px; font-weight:600;
}}
QPushButton:hover {{ background:#1558a0; }}
"""


class ActivateWorker(QThread):
    done = pyqtSignal(dict)

    def __init__(self, key: str):
        super().__init__()
        self._key = key

    def run(self):
        from lic_manager.license_manager import activate
        result = activate(self._key)
        self.done.emit(result)


class ValidateWorker(QThread):
    done = pyqtSignal(dict)

    def run(self):
        from lic_manager.license_manager import validate
        result = validate()
        self.done.emit(result)


class ActivationScreen(QWidget):
    """
    Muestra pantalla de activación si no hay licencia.
    Emite `activated` cuando la licencia es válida.
    """
    activated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(QSS)
        self._build()
        self._auto_validate()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setFixedWidth(460)
        card.setStyleSheet(f"QFrame{{background:{CARD};border-radius:16px;border:1px solid {BORDER};}}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(18)

        # Logo
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = Path(__file__).parent.parent / "MF_LABS.png"
        pix = QPixmap(str(logo_path))
        if not pix.isNull():
            size = 64
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
            logo_lbl.setPixmap(rounded)
        card_layout.addWidget(logo_lbl)

        title = QLabel("Activar MF Agent")
        title.setStyleSheet("font-size:20px;font-weight:700;border:none;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        sub = QLabel("Ingresa tu clave de licencia para continuar")
        sub.setStyleSheet(f"color:{SUB};font-size:12px;border:none;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(sub)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("MF-XXXX-XXXX-XXXX-XXXX")
        self.key_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_input.returnPressed.connect(self._activate)
        card_layout.addWidget(self.key_input)

        self.msg_lbl = QLabel("")
        self.msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_lbl.setStyleSheet(f"font-size:12px;border:none;")
        self.msg_lbl.setWordWrap(True)
        card_layout.addWidget(self.msg_lbl)

        self.btn_activate = QPushButton("Activar Licencia")
        self.btn_activate.clicked.connect(self._activate)
        card_layout.addWidget(self.btn_activate)

        footer = QLabel("¿No tienes una key? Contacta a tu proveedor.")
        footer.setStyleSheet(f"color:{SUB};font-size:11px;border:none;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(footer)

        layout.addWidget(card)

    def _auto_validate(self):
        """Valida automáticamente si ya hay una licencia guardada."""
        self.btn_activate.setEnabled(False)
        self.msg_lbl.setStyleSheet(f"font-size:12px;border:none;color:{SUB};")
        self.msg_lbl.setText("Verificando licencia...")
        self._val_worker = ValidateWorker()
        self._val_worker.done.connect(self._on_validated)
        self._val_worker.start()

    def _on_validated(self, result):
        self.btn_activate.setEnabled(True)
        if result["ok"]:
            self._show_success(result)
        else:
            self.msg_lbl.setStyleSheet(f"font-size:12px;border:none;color:{SUB};")
            self.msg_lbl.setText("Ingresa tu clave de licencia.")

    def _activate(self):
        key = self.key_input.text().strip().upper()
        if not key:
            return
        self.btn_activate.setEnabled(False)
        self.msg_lbl.setStyleSheet(f"font-size:12px;border:none;color:{SUB};")
        self.msg_lbl.setText("Validando...")
        self._worker = ActivateWorker(key)
        self._worker.done.connect(self._on_activate_done)
        self._worker.start()

    def _on_activate_done(self, result):
        self.btn_activate.setEnabled(True)
        if result["ok"]:
            self._show_success(result)
        else:
            self.msg_lbl.setStyleSheet(f"font-size:12px;border:none;color:{DANGER};")
            self.msg_lbl.setText(f"❌  {result['msg']}")

    def _show_success(self, result):
        days_left = result.get("days_left")
        if days_left is None:
            msg = "✅  Licencia permanente activa."
            color = OK
        elif days_left <= 7:
            msg = f"⚠️  Licencia válida. Vence en {days_left} días. Renueva pronto."
            color = WARN
        else:
            msg = f"✅  Licencia activa. Vence en {days_left} días."
            color = OK

        self.msg_lbl.setStyleSheet(f"font-size:12px;border:none;color:{color};")
        self.msg_lbl.setText(msg)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1200, self.activated.emit)
