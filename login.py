"""
Pantallas de Login y Gestión de Perfiles.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QDialog, QFormLayout, QMessageBox,
    QListWidget, QListWidgetItem, QStackedWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from agent.profiles import (
    list_profiles, create_profile, delete_profile,
    add_user, delete_user, authenticate, get_profile
)

BG      = "#F5F0EB"
CARD    = "#FDFAF7"
SIDEBAR = "#EDE8E3"
TEXT    = "#1F2937"
SUBTEXT = "#6B7280"
ACCENT  = "#6B7280"
ACCENT2 = "#1B6CA8"
SUCCESS = "#16A34A"
DANGER  = "#DC2626"
WARNING = "#D97706"
BORDER  = "#D1CBC4"

BASE_QSS = f"""
QWidget {{ background: {BG}; color: {TEXT}; font-family: 'Segoe UI'; }}
QLabel {{ color: {TEXT}; }}
QLineEdit, QComboBox {{
    background: {CARD}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 8px 12px; font-size: 13px;
}}
QLineEdit:focus {{ border: 1px solid {ACCENT2}; }}
QPushButton {{
    background: {ACCENT2}; color: white; border: none;
    border-radius: 8px; padding: 10px 20px; font-size: 13px; font-weight: 600;
}}
QPushButton:hover {{ background: #1558a0; }}
QPushButton#danger {{
    background: {DANGER};
}}
QPushButton#danger:hover {{ background: #b91c1c; }}
QPushButton#secondary {{
    background: {SIDEBAR}; color: {TEXT};
}}
QPushButton#secondary:hover {{ background: {BORDER}; }}
QListWidget {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px;
    font-size: 13px; color: {TEXT};
}}
QListWidget::item {{ padding: 10px; border-bottom: 1px solid {BORDER}; }}
QListWidget::item:selected {{ background: {ACCENT2}; color: white; }}
"""


# ── Dialog: Crear Perfil ──────────────────────────────────────────────────────
class CreateProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Perfil")
        self.setFixedWidth(400)
        self.setStyleSheet(BASE_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        QLabel_title = QLabel("Crear Nuevo Perfil")
        QLabel_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(QLabel_title)

        form = QFormLayout()
        form.setSpacing(10)
        self.biz_name = QLineEdit()
        self.biz_name.setPlaceholderText("Nombre del negocio")
        self.admin_user = QLineEdit()
        self.admin_user.setPlaceholderText("Usuario administrador")
        self.admin_pass = QLineEdit()
        self.admin_pass.setPlaceholderText("Contraseña")
        self.admin_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_pass2 = QLineEdit()
        self.admin_pass2.setPlaceholderText("Confirmar contraseña")
        self.admin_pass2.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Negocio *", self.biz_name)
        form.addRow("Admin *", self.admin_user)
        form.addRow("Contraseña *", self.admin_pass)
        form.addRow("Confirmar *", self.admin_pass2)
        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Crear")
        ok.clicked.connect(self._create)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    def _create(self):
        name = self.biz_name.text().strip()
        user = self.admin_user.text().strip()
        pw   = self.admin_pass.text()
        pw2  = self.admin_pass2.text()
        if not name or not user or not pw:
            self._err("Todos los campos son obligatorios.")
            return
        if pw != pw2:
            self._err("Las contraseñas no coinciden.")
            return
        # Verificar que la key activa no tenga ya un perfil creado
        try:
            from lic_manager.license_manager import _load_local
            local_lic = _load_local()
            key = local_lic.get('key', '')
            if key:
                from agent.profiles import list_profiles
                existing = list_profiles()
                if len(existing) >= 1:
                    self._err(
                        "Ya existe un perfil creado para esta licencia.\n"
                        "Solo se permite un perfil por key."
                    )
                    return
        except Exception:
            pass
        create_profile(name, user, pw)
        self.accept()

    def _err(self, msg):
        b = QMessageBox(self)
        b.setStyleSheet("QMessageBox{background:#fff;}QLabel{color:#1F2937;}")
        b.setWindowTitle("Error"); b.setText(msg); b.exec()


# ── Dialog: Agregar Usuario ───────────────────────────────────────────────────
class AddUserDialog(QDialog):
    def __init__(self, profile_id: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar Usuario")
        self.setFixedWidth(380)
        self.setStyleSheet(BASE_QSS)
        self._profile_id = profile_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        QLabel_t = QLabel("Nuevo Usuario")
        QLabel_t.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(QLabel_t)

        form = QFormLayout()
        form.setSpacing(10)
        self.username = QLineEdit()
        self.username.setPlaceholderText("Nombre de usuario")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Contraseña")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.role_cb = QComboBox()
        self.role_cb.addItems(["vendedor", "admin"])
        form.addRow("Usuario *", self.username)
        form.addRow("Contraseña *", self.password)
        form.addRow("Rol", self.role_cb)
        layout.addLayout(form)

        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Agregar")
        ok.clicked.connect(self._add)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    def _add(self):
        user = self.username.text().strip()
        pw   = self.password.text()
        role = self.role_cb.currentText()
        if not user or not pw:
            return
        if not add_user(self._profile_id, user, pw, role):
            b = QMessageBox(self)
            b.setStyleSheet("QMessageBox{background:#fff;}QLabel{color:#1F2937;}")
            b.setWindowTitle("Error"); b.setText("El usuario ya existe."); b.exec()
            return
        self.accept()


# ── Pantalla de Login ─────────────────────────────────────────────────────────
class LoginScreen(QWidget):
    login_success = pyqtSignal(dict)   # emite {"username", "role", "profile_id", "profile_name"}
    manage_profiles = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(BASE_QSS)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(0)

        card = QFrame()
        card.setFixedWidth(420)
        card.setStyleSheet(f"QFrame{{background:{CARD};border-radius:16px;border:1px solid {BORDER};}}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(16)

        title = QLabel("MF Agent")
        title.setStyleSheet("font-size: 26px; font-weight: 700; border:none;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
        from pathlib import Path
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = Path(__file__).parent / "MF_LABS.png"
        pix = QPixmap(str(logo_path))
        if not pix.isNull():
            size = 72
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
        else:
            logo_lbl.setText("MF")
        card_layout.addWidget(logo_lbl)

        sub = QLabel("Selecciona tu perfil e inicia sesión")
        sub.setStyleSheet(f"color:{SUBTEXT}; font-size:13px; border:none;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER};border:none;background:{BORDER};max-height:1px;")
        card_layout.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(12)

        self.profile_cb = QComboBox()
        self.profile_cb.setStyleSheet(f"background:{SIDEBAR};")
        self._refresh_profiles()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Usuario")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Contraseña")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self._login)

        form.addRow("Perfil:", self.profile_cb)
        form.addRow("Usuario:", self.username_input)
        form.addRow("Contraseña:", self.password_input)
        card_layout.addLayout(form)

        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet(f"color:{DANGER}; font-size:12px; border:none;")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.error_lbl)

        btn_login = QPushButton("Iniciar Sesión")
        btn_login.setFixedHeight(42)
        btn_login.clicked.connect(self._login)
        card_layout.addWidget(btn_login)

        btn_manage = QPushButton("Gestionar Perfiles")
        btn_manage.setObjectName("secondary")
        btn_manage.setFixedHeight(36)
        btn_manage.clicked.connect(self.manage_profiles.emit)
        card_layout.addWidget(btn_manage)

        layout.addWidget(card)

    def _refresh_profiles(self):
        self.profile_cb.clear()
        for p in list_profiles():
            self.profile_cb.addItem(p["name"], p["id"])
        if self.profile_cb.count() == 0:
            self.profile_cb.addItem("— Sin perfiles —", None)

    def _login(self):
        profile_id = self.profile_cb.currentData()
        if not profile_id:
            self.error_lbl.setText("Crea un perfil primero.")
            return
        user = self.username_input.text().strip()
        pw   = self.password_input.text()
        result = authenticate(profile_id, user, pw)
        if result:
            profile = get_profile(profile_id)
            result["profile_name"] = profile["name"]
            # Incluir key de licencia para sincronizar a Firestore
            try:
                from lic_manager.license_manager import _load_local
                result["key"] = _load_local().get("key", "")
            except Exception:
                result["key"] = ""
            self.login_success.emit(result)
        else:
            self.error_lbl.setText("Usuario o contraseña incorrectos.")
            self.password_input.clear()


# ── Pantalla de Gestión de Perfiles ──────────────────────────────────────────
class ProfileManagerScreen(QWidget):
    back = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(BASE_QSS)
        self._selected_profile_id = None
        self._authenticated = False  # se autentica al entrar
        self._build()

    def showEvent(self, event):
        """Pide credenciales de admin solo si ya hay perfiles creados."""
        super().showEvent(event)
        self._authenticated = False
        if list_profiles():
            self._ask_admin_credentials()
        else:
            self._authenticated = True  # primer uso, sin perfiles aun

    def _ask_admin_credentials(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Acceso de Administrador")
        dlg.setFixedWidth(360)
        dlg.setStyleSheet(BASE_QSS)
        dlg.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        lbl = QLabel("🔒  Ingresa tus credenciales de administrador para gestionar perfiles.")
        lbl.setStyleSheet(f"color:{TEXT}; font-size:13px;")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(10)
        profile_cb = QComboBox()
        for p in list_profiles():
            profile_cb.addItem(p["name"], p["id"])
        user_input = QLineEdit()
        user_input.setPlaceholderText("Usuario admin")
        pass_input = QLineEdit()
        pass_input.setPlaceholderText("Contraseña")
        pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Perfil:", profile_cb)
        form.addRow("Usuario:", user_input)
        form.addRow("Contraseña:", pass_input)
        lay.addLayout(form)

        err_lbl = QLabel("")
        err_lbl.setStyleSheet(f"color:{DANGER}; font-size:12px;")
        lay.addWidget(err_lbl)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("secondary")
        btn_confirm = QPushButton("Entrar")

        def confirm():
            pid = profile_cb.currentData()
            result = authenticate(pid, user_input.text().strip(), pass_input.text())
            if not result or result.get("role") != "admin":
                err_lbl.setText("Credenciales incorrectas o no eres admin.")
                pass_input.clear()
                return
            self._authenticated = True
            dlg.accept()

        def cancel():
            dlg.reject()
            self.back.emit()

        btn_cancel.clicked.connect(cancel)
        btn_confirm.clicked.connect(confirm)
        pass_input.returnPressed.connect(confirm)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_confirm)
        lay.addLayout(btns)

        dlg.exec()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Panel izquierdo: lista de perfiles
        left = QVBoxLayout()
        lbl = QLabel("Perfiles")
        lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        left.addWidget(lbl)

        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_selected)
        left.addWidget(self.profile_list)

        btns_left = QHBoxLayout()
        btn_new = QPushButton("＋ Nuevo")
        btn_new.clicked.connect(self._create_profile)
        btn_del_p = QPushButton("Eliminar")
        btn_del_p.setObjectName("danger")
        btn_del_p.clicked.connect(self._delete_profile)
        btns_left.addWidget(btn_new)
        btns_left.addWidget(btn_del_p)
        left.addLayout(btns_left)

        btn_back = QPushButton("← Volver al Login")
        btn_back.setObjectName("secondary")
        btn_back.clicked.connect(self.back.emit)
        left.addWidget(btn_back)

        layout.addLayout(left, 1)

        # Panel derecho: usuarios del perfil
        right = QVBoxLayout()
        self.users_title = QLabel("Usuarios")
        self.users_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        right.addWidget(self.users_title)

        self.users_list = QListWidget()
        right.addWidget(self.users_list)

        btns_right = QHBoxLayout()
        btn_add_u = QPushButton("＋ Agregar Usuario")
        btn_add_u.clicked.connect(self._add_user)
        btn_del_u = QPushButton("Eliminar Usuario")
        btn_del_u.setObjectName("danger")
        btn_del_u.clicked.connect(self._delete_user)
        btns_right.addWidget(btn_add_u)
        btns_right.addWidget(btn_del_u)
        right.addLayout(btns_right)

        layout.addLayout(right, 1)
        self._refresh_profiles()

    def _refresh_profiles(self):
        self.profile_list.clear()
        for p in list_profiles():
            item = QListWidgetItem(f"🏢  {p['name']}")
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.profile_list.addItem(item)

    def _on_profile_selected(self, item):
        if not item:
            return
        self._selected_profile_id = item.data(Qt.ItemDataRole.UserRole)
        profile = get_profile(self._selected_profile_id)
        if not profile:
            return
        self.users_title.setText(f"Usuarios — {profile['name']}")
        self.users_list.clear()
        for u in profile["users"]:
            role_icon = "👑" if u["role"] == "admin" else "🛒"
            self.users_list.addItem(f"{role_icon}  {u['username']}  [{u['role']}]")

    def _create_profile(self):
        dlg = CreateProfileDialog(self)
        if dlg.exec():
            self._refresh_profiles()

    def _delete_profile(self):
        if not self._authenticated or not self._selected_profile_id:
            return
        profile = get_profile(self._selected_profile_id)
        if not profile:
            return
        b = QMessageBox(self)
        b.setStyleSheet("QMessageBox{background:#fff;}QLabel{color:#1F2937;}")
        b.setWindowTitle("Confirmar")
        b.setText(f"¿Eliminar el perfil '{profile['name']}' y todos sus datos?")
        b.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        b.exec()
        if b.result() == QMessageBox.StandardButton.Yes:
            delete_profile(self._selected_profile_id)
            self._selected_profile_id = None
            self._refresh_profiles()
            self.users_list.clear()

    def _add_user(self):
        if not self._selected_profile_id:
            return
        dlg = AddUserDialog(self._selected_profile_id, self)
        if dlg.exec():
            self._on_profile_selected(self.profile_list.currentItem())

    def _delete_user(self):
        if not self._authenticated or not self._selected_profile_id:
            return
        item = self.users_list.currentItem()
        if not item:
            return
        username = item.text().split("  ")[1].strip()
        b = QMessageBox(self)
        b.setStyleSheet("QMessageBox{background:#fff;}QLabel{color:#1F2937;}")
        b.setWindowTitle("Confirmar")
        b.setText(f"¿Eliminar el usuario '{username}'?")
        b.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        b.exec()
        if b.result() == QMessageBox.StandardButton.Yes:
            delete_user(self._selected_profile_id, username)
            self._on_profile_selected(self.profile_list.currentItem())
