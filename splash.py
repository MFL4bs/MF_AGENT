from PyQt6.QtWidgets import QSplashScreen, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QPainterPath, QPen, QRadialGradient
from pathlib import Path

W, H = 480, 580


class SplashScreen(QSplashScreen):
    def __init__(self):
        pixmap = QPixmap(W, H)
        pixmap.fill(Qt.GlobalColor.transparent)
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)

        # ── Fondo oscuro con borde sutil ──────────────────────────────────────
        bg = QWidget(self)
        bg.setGeometry(0, 0, W, H)
        bg.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0   #0a0f1e,
                    stop:0.5 #0d1b2e,
                    stop:1   #0a0f1e
                );
                border-radius: 20px;
                border: 1px solid rgba(59, 130, 246, 0.15);
            }
        """)

        layout = QVBoxLayout(bg)
        layout.setContentsMargins(50, 50, 50, 40)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Círculo de brillo detrás del logo ─────────────────────────────────
        glow = QLabel()
        glow.setFixedSize(180, 180)
        glow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glow.setStyleSheet("""
            background: radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%);
            border-radius: 90px;
        """)

        # ── Logo ──────────────────────────────────────────────────────────────
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = Path(__file__).parent / "MF_LABS.png"
        if logo_path.exists():
            original = QPixmap(str(logo_path))
            scaled = original.scaled(
                160, 160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(scaled)
            logo_label.setFixedSize(scaled.width(), scaled.height())
        else:
            logo_label.setText("MF")
            logo_label.setStyleSheet("font-size: 72px; font-weight: 900; color: white;")

        # Stack logo sobre el glow
        logo_container = QWidget()
        logo_container.setFixedSize(180, 180)
        logo_container.setStyleSheet("background: transparent;")
        glow.setParent(logo_container)
        glow.setGeometry(0, 0, 180, 180)
        logo_label.setParent(logo_container)
        logo_label.setGeometry(
            (180 - logo_label.width()) // 2,
            (180 - logo_label.height()) // 2,
            logo_label.width(), logo_label.height()
        )
        layout.addWidget(logo_container, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(24)

        # ── Nombre app ────────────────────────────────────────────────────────
        title = QLabel("MF AGENT")
        title.setStyleSheet("""
            font-size: 34px;
            font-weight: 900;
            color: #f8fafc;
            letter-spacing: 8px;
            background: transparent;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(6)

        # ── Badge versión ─────────────────────────────────────────────────────
        badge = QLabel("v1.0.0")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedHeight(22)
        badge.setStyleSheet("""
            font-size: 10px;
            font-weight: 700;
            color: #3b82f6;
            background: rgba(59, 130, 246, 0.12);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 10px;
            padding: 0px 12px;
            letter-spacing: 2px;
        """)
        badge_row = QHBoxLayout()
        badge_row.addStretch()
        badge_row.addWidget(badge)
        badge_row.addStretch()
        layout.addLayout(badge_row)

        layout.addSpacing(10)

        # ── Línea decorativa ──────────────────────────────────────────────────
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0   transparent,
                stop:0.2 rgba(59,130,246,0.2),
                stop:0.5 rgba(96,165,250,0.5),
                stop:0.8 rgba(59,130,246,0.2),
                stop:1   transparent
            );
        """)
        layout.addWidget(line)

        layout.addSpacing(10)

        # ── Subtítulo ─────────────────────────────────────────────────────────
        subtitle = QLabel("Sistema Inteligente de Ventas")
        subtitle.setStyleSheet("""
            font-size: 12px;
            color: rgba(148, 163, 184, 0.9);
            letter-spacing: 3px;
            background: transparent;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(44)

        # ── Barra de progreso delgada ─────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.06);
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1d4ed8,
                    stop:0.5 #3b82f6,
                    stop:1 #60a5fa
                );
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress)

        layout.addSpacing(16)

        # ── Estado con puntos animados ────────────────────────────────────────
        self.status_label = QLabel("Iniciando")
        self.status_label.setStyleSheet("""
            font-size: 11px;
            color: rgba(100, 116, 139, 0.9);
            letter-spacing: 1px;
            background: transparent;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addSpacing(28)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QLabel("© 2026 Jimmy Mojica · MFLABS")
        footer.setStyleSheet("""
            font-size: 9px;
            color: rgba(71, 85, 105, 0.8);
            letter-spacing: 1px;
            background: transparent;
        """)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        # ── Fade in ───────────────────────────────────────────────────────────
        self.setWindowOpacity(0)
        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(700)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_in.start()

        # ── Progreso ──────────────────────────────────────────────────────────
        self.progress_value = 0
        self._dots = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(28)

        self._dot_timer = QTimer()
        self._dot_timer.timeout.connect(self._animate_dots)
        self._dot_timer.start(400)

    def _animate_dots(self):
        self._dots = (self._dots + 1) % 4
        base = self._get_status_text(self.progress_value)
        self.status_label.setText(base + "." * self._dots)

    def _get_status_text(self, v):
        if v < 20:   return "Cargando modulos"
        if v < 40:   return "Inicializando base de datos"
        if v < 60:   return "Configurando interfaz"
        if v < 80:   return "Conectando servicios"
        if v < 95:   return "Preparando sistema"
        return "Listo"

    def _update_progress(self):
        if self.progress_value < 100:
            self.progress_value += 1
            self.progress.setValue(self.progress_value)
        else:
            self.timer.stop()
            self._dot_timer.stop()
            self.status_label.setText("✓  Listo")
            self.status_label.setStyleSheet("""
                font-size: 11px;
                color: rgba(74, 222, 128, 0.9);
                letter-spacing: 2px;
                background: transparent;
            """)

    def finish_loading(self, main_window):
        self._dot_timer.stop()
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(400)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(lambda: self._show_main(main_window))
        anim.start()
        self.fade_in = anim

    def _show_main(self, main_window):
        self.finish(main_window)
        main_window.show()
