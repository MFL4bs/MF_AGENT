# -*- coding: utf-8 -*-
"""Patch app.py: Dashboard con stats+mapa, inventario separado."""

lines = open('app.py', encoding='utf-8').readlines()

# ── Encontrar rangos ──────────────────────────────────────────────────────────
def find_line(keyword, start=0):
    for i in range(start, len(lines)):
        if keyword in lines[i]:
            return i
    return -1

build_start = find_line('    def _build_content(self)')
# El método termina cuando empieza el siguiente método al mismo nivel
build_end = find_line('    def _toggle_bot(self)', build_start)

nav_start = find_line('    def _nav(self, page: str)')
nav_end   = find_line('    def _load_products(self)', nav_start)

print(f"_build_content: {build_start+1} -> {build_end}")
print(f"_nav:           {nav_start+1} -> {nav_end}")

NEW_BUILD_CONTENT = '''    def _build_content(self) -> QWidget:
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
        self.search.setPlaceholderText("\U0001f50d  Buscar producto...")
        self.search.setFixedWidth(260)
        self.search.textChanged.connect(self._filter_table)
        self.search.setVisible(False)

        self._add_btn = QPushButton("\uff0b  Agregar Producto")
        self._add_btn.setObjectName("primary")
        self._add_btn.clicked.connect(self._add_product)
        self._add_btn.setVisible(False)

        header.addWidget(self.page_title)
        header.addStretch()
        header.addWidget(self.search)
        header.addWidget(self._add_btn)

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
        logo_pix = QPixmap(str(Path(__file__).parent / "MF_LABS.png"))
        if not logo_pix.isNull():
            size = 40
            rounded = QPixmap(size, size)
            rounded.fill(Qt.GlobalColor.transparent)
            from PyQt6.QtGui import QPainter, QPainterPath
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, logo_pix.scaled(size, size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation))
            painter.end()
            logo_btn.setPixmap(rounded)
        else:
            logo_btn.setText("\U0001f517")
        logo_btn.mousePressEvent = lambda _: __import__("webbrowser").open("https://github.com/MFL4bs")
        header.addWidget(logo_btn)

        github_btn = QPushButton("\u2b21  MFL4bs")
        github_btn.setObjectName("github")
        github_btn.setToolTip("github.com/MFL4bs")
        github_btn.clicked.connect(lambda: __import__("webbrowser").open("https://github.com/MFL4bs"))
        header.addWidget(github_btn)
        self.content_layout.addLayout(header)

        # \u2500\u2500 DASHBOARD WIDGET \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        self._dashboard_widget = QWidget()
        dash_layout = QVBoxLayout(self._dashboard_widget)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_layout.setSpacing(20)

        card1, self.stat_total = make_stat_card("\U0001f4e6", "Total Productos", "0", ACCENT2)
        card2, self.stat_stock = make_stat_card("\u2705", "En Stock", "0", SUCCESS)
        card3, self.stat_low   = make_stat_card("\u26a0\ufe0f", "Stock Bajo", "0", WARNING)
        card4, self.stat_out   = make_stat_card("\u274c", "Sin Stock", "0", DANGER)
        card5, self.stat_bot   = make_stat_card("\U0001f916", "Estado Bot", "Activo", SUCCESS)
        card6, self.stat_msgs  = make_stat_card("\U0001f4ac", "Mensajes Hoy", "\u2014", ACCENT)
        self._slider = CardsSlider([card1, card2, card3, card4, card5, card6])
        dash_layout.addWidget(self._slider)

        # Mapa
        map_card = QWidget()
        map_card.setObjectName("card")
        map_shadow = QGraphicsDropShadowEffect()
        map_shadow.setBlurRadius(20)
        map_shadow.setColor(QColor(0, 0, 0, 40))
        map_shadow.setOffset(0, 4)
        map_card.setGraphicsEffect(map_shadow)
        map_layout = QVBoxLayout(map_card)
        map_layout.setContentsMargins(16, 16, 16, 16)
        map_layout.setSpacing(8)

        map_title = QLabel("\U0001f4cd  Ubicaci\u00f3n del Negocio")
        map_title.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 700;")
        map_layout.addWidget(map_title)

        if HAS_WEBENGINE:
            self._map_view = QWebEngineView()
            self._map_view.setMinimumHeight(380)
            map_html = """<!DOCTYPE html><html><head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>html,body,#map{width:100%;height:100%;margin:0;padding:0;}</style>
            </head><body><div id="map"></div>
            <script>
              var map = L.map('map').setView([19.4326, -99.1332], 13);
              L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
                attribution:'&copy; OpenStreetMap'
              }).addTo(map);
              var marker = L.marker([19.4326, -99.1332], {draggable:true}).addTo(map)
                .bindPopup('<b>Mi Negocio</b><br>Arrastra para cambiar ubicaci\u00f3n').openPopup();
            </script></body></html>"""
            self._map_view.setHtml(map_html)
            map_layout.addWidget(self._map_view)
        else:
            map_lbl = QLabel("\U0001f5fa\ufe0f  Haz clic para ver el mapa del negocio")
            map_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            map_lbl.setMinimumHeight(380)
            map_lbl.setStyleSheet(f"""
                color: {ACCENT2}; font-size: 16px; font-weight: 600;
                background: {SIDEBAR}; border-radius: 12px;
                border: 2px dashed {BORDER};
            """)
            map_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            map_lbl.mousePressEvent = lambda _: __import__("webbrowser").open(
                "https://www.openstreetmap.org/?mlat=19.4326&mlon=-99.1332#map=15/19.4326/-99.1332"
            )
            map_layout.addWidget(map_lbl)

        dash_layout.addWidget(map_card, 1)
        self.content_layout.addWidget(self._dashboard_widget)

        # \u2500\u2500 INVENTARIO WIDGET \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["Foto", "SKU", "Nombre", "Categor\u00eda", "Precio", "Stock", "Acciones"])
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
        self._table.setStyleSheet(self._table.styleSheet() +
            f"QTableWidget {{ alternate-background-color: {SIDEBAR}; }}")
        self._table.setVisible(False)
        self.content_layout.addWidget(self._table)

        # \u2500\u2500 VENTAS WIDGET \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        self._sales_widget = QWidget()
        self._sales_widget.setVisible(False)
        sv_layout = QVBoxLayout(self._sales_widget)
        sv_layout.setContentsMargins(0, 0, 0, 0)
        sv_layout.setSpacing(12)
        card_st, self.stat_sales_total = make_stat_card("\U0001f4b0", "Ventas Hoy", "$0", SUCCESS)
        card_sc, self.stat_sales_count = make_stat_card("\U0001f6d2", "Pedidos Hoy", "0", ACCENT2)
        card_sw, self.stat_sales_wa    = make_stat_card("\U0001f4f1", "V\u00eda WhatsApp", "0", WARNING)
        sv_stats = QHBoxLayout()
        sv_stats.addWidget(card_st)
        sv_stats.addWidget(card_sc)
        sv_stats.addWidget(card_sw)
        sv_stats.addStretch()
        sv_layout.addLayout(sv_stats)
        self._sales_table = QTableWidget()
        self._sales_table.setColumnCount(7)
        self._sales_table.setHorizontalHeaderLabels(
            ["Fecha", "SKU", "Producto", "Cliente", "Canal", "Cant.", "Total"])
        self._sales_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._sales_table.verticalHeader().setVisible(False)
        self._sales_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._sales_table.setAlternatingRowColors(True)
        self._sales_table.setStyleSheet(self._sales_table.styleSheet() +
            f"QTableWidget {{ alternate-background-color: {SIDEBAR}; }}")
        sv_layout.addWidget(self._sales_table)
        self.content_layout.addWidget(self._sales_widget)

        return self.content

'''

NEW_NAV = '''    def _nav(self, page: str):
        for name in ["Dashboard", "Inventario", "Ventas", "Stock Bajo"]:
            btn = getattr(self, f"nav_{name.lower().replace(' ', '_')}")
            btn.setChecked(name == page)

        self.page_title.setText(page)

        # Visibilidad de widgets
        self._dashboard_widget.setVisible(page == "Dashboard")
        self._table.setVisible(page in ("Inventario", "Stock Bajo"))
        self._sales_widget.setVisible(page == "Ventas")
        self.search.setVisible(page in ("Inventario", "Stock Bajo"))
        self._add_btn.setVisible(page in ("Inventario", "Ventas"))

        if page == "Ventas":
            self._add_btn.setText("\uff0b  Registrar Venta")
            self._add_btn.clicked.disconnect()
            self._add_btn.clicked.connect(self._add_sale)
            self._show_sales_view()
        elif page == "Inventario":
            self._add_btn.setText("\uff0b  Agregar Producto")
            self._add_btn.clicked.disconnect()
            self._add_btn.clicked.connect(self._add_product)
            self._populate_table(self.products)
        elif page == "Stock Bajo":
            self._add_btn.setText("\uff0b  Agregar Producto")
            self._add_btn.clicked.disconnect()
            self._add_btn.clicked.connect(self._add_product)
            self._populate_table(low_stock_products(5))

'''

# Reemplazar bloques
new_lines = lines[:build_start] + [NEW_BUILD_CONTENT] + lines[build_end:nav_start] + [NEW_NAV] + lines[nav_end:]
open('app.py', 'w', encoding='utf-8').writelines(new_lines)
print("Patch aplicado OK")

# Verificar sintaxis
import ast
try:
    ast.parse(open('app.py', encoding='utf-8').read())
    print("Sintaxis OK")
except SyntaxError as e:
    print(f"ERROR sintaxis: {e}")
    # Restaurar backup
    import shutil
    shutil.copy('app_backup.py', 'app.py')
    print("Backup restaurado")
