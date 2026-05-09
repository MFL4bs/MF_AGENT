from PyQt6.QtWidgets import QSplashScreen, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QPainterPath, QPen, QBrush
from pathlib import Path

W, H = 520, 620


class SplashScreen(QSplashScreen):
    def __init__(self):
        pixmap = QPixmap(W, H)
        pixmap.fill(Qt.GlobalColor.transparent)
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)

        # ── Fondo con gradiente pintado ───────────────────────────────────────
        bg = QWidget(self)
        bg.setGeometry(0, 0, W, H)
        bg.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0   #0f172a,
                    stop:0.5 #1e3a5f,
                    stop:1   #0f172a
                );
                border-radius: 24px;
            }
        """)

        layout = QVBoxLayout(bg)
        layout.setContentsMargins(48, 48, 48, 40)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Logo completo ─────────────────────────────────────────────────────
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = Path(__file__).parent / "MF_LABS.png"
        if logo_path.exists():
            # Cargar logo completo sin recortar
            original = QPixmap(str(logo_path))
            # Escalar manteniendo aspecto dentro de 200x200
            scaled = original.scaled(
                200, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(scaled)
            logo_label.setFixedSize(scaled.width(), scaled.height())
        else:
            logo_label.setText("MF")
            logo_label.setStyleSheet("font-size: 80px; font-weight: 900; color: white;")
        layout.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(28)

        # ── Nombre app ────────────────────────────────────────────────────────
        title = QLabel("MF AGENT")
        title.setStyleSheet("""
            font-size: 38px;
            font-weight: 900;
            color: #ffffff;
            letter-spacing: 6px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(8)

        # ── Línea decorativa ──────────────────────────────────────────────────
        line_widget = QWidget()
        line_widget.setFixedHeight(2)
        line_widget.setStyleSheet("""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0   transparent,
                stop:0.3 #3b82f6,
                stop:0.7 #60a5fa,
                stop:1   transparent
            );
        """)
        layout.addWidget(line_widget)

        layout.addSpacing(12)

        # ── Subtítulo ─────────────────────────────────────────────────────────
        subtitle = QLabel("Sistema Inteligente de Ventas")
        subtitle.setStyleSheet("""
            font-size: 13px;
            color: rgba(148, 163, 184, 1);
            letter-spacing: 2px;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(48)

        # ── Barra de progreso ─────────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.08);
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6,
                    stop:1 #60a5fa
                );
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress)

        layout.addSpacing(14)

        # ── Estado ────────────────────────────────────────────────────────────
        self.status_label = QLabel("Iniciando...")
        self.status_label.setStyleSheet("""
            font-size: 11px;
            color: rgba(148, 163, 184, 0.8);
            letter-spacing: 1px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addSpacing(24)

        # ── Version + crédito ─────────────────────────────────────────────────
        footer_row = QHBoxLayout()
        version = QLabel("v1.0.0")
        version.setStyleSheet("font-size: 10px; color: rgba(100,116,139,0.8);")
        credit = QLabel("by MF Labs")
        credit.setStyleSheet("font-size: 10px; color: rgba(100,116,139,0.8);")
        footer_row.addWidget(version)
        footer_row.addStretch()
        footer_row.addWidget(credit)
        layout.addLayout(footer_row)

        # ── Fade in ───────────────────────────────────────────────────────────
        self.setWindowOpacity(0)
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(600)
        self.fade_animation.setStartValue(0)
        self.fade_animation.setEndValue(1)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()

        # ── Progreso ──────────────────────────────────────────────────────────
        self.progress_value = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(30)

    def _update_progress(self):
        if self.progress_value < 100:
            self.progress_value += 1
            self.progress.setValue(self.progress_value)
            v = self.progress_value
            if v < 20:
                self.status_label.setText("Cargando modulos...")
            elif v < 40:
                self.status_label.setText("Inicializando base de datos...")
            elif v < 60:
                self.status_label.setText("Configurando interfaz...")
            elif v < 80:
                self.status_label.setText("Conectando servicios...")
            elif v < 95:
                self.status_label.setText("Preparando sistema...")
            else:
                self.status_label.setText("Listo!")
        else:
            self.timer.stop()

    def finish_loading(self, main_window):
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(400)
        self.fade_animation.setStartValue(1)
        self.fade_animation.setEndValue(0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.finished.connect(lambda: self._show_main(main_window))
        self.fade_animation.start()

    def _show_main(self, main_window):
        self.finish(main_window)
        main_window.show()
