with open('app.py', 'r', encoding='utf-8') as f:
    src = f.read()

# ── 1. Reemplazar _generate_pdf completa ─────────────────────────────────────
# buscar con cualquier line ending
for sep in ['\r\ndef _generate_pdf(', '\ndef _generate_pdf(']:
    start = src.find(sep)
    if start != -1:
        break
for sep2 in ['\r\n\r\n# \u2500\u2500 Modal Factura', '\n\n# \u2500\u2500 Modal Factura']:
    end = src.find(sep2, start)
    if end != -1:
        break
assert start != -1 and end != -1, f"bounds: {start} {end}"

NEW_PDF = r'''
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
'''

src2 = src[:start] + NEW_PDF + src[end:]

# ── 2. Renombrar Marca Agua -> Logo Empresa ───────────────────────────────────
src2 = src2.replace('\U0001f5bc\ufe0f  Marca Agua', '\U0001f5bc\ufe0f  Logo Empresa')
src2 = src2.replace('dlg.setWindowTitle("Configurar Marca de Agua")', 'dlg.setWindowTitle("Logo de Empresa")')
src2 = src2.replace('\U0001f5bc\ufe0f  Configurar Marca de Agua', '\U0001f5bc\ufe0f  Logo de Empresa')
src2 = src2.replace('"Imagen actual:"', '"Logo actual:"')
src2 = src2.replace('dlg, "Seleccionar Marca de Agua", "",', 'dlg, "Seleccionar Logo de Empresa", "",')

# Reemplazar el mensaje de exito del watermark
old_msg = ('QMessageBox.information(\n'
           '                self, "Exito",\n'
           '                f"\u2705 Marca de agua actualizada\\n\\nLa nueva configuraci\u00f3n se usar\u00e1 en todas las facturas PDF.\\n\\nImagen: {Path(new_path[0]).name}\\nOpacidad: {opacity_spin.value()}"\n'
           '            )')
new_msg = ('QMessageBox.information(\n'
           '                self, "Exito",\n'
           '                f"\u2705 Logo actualizado. Aparecera en la parte superior izquierda del PDF.\\n\\nArchivo: {Path(new_path[0]).name}"\n'
           '            )')
if old_msg in src2:
    src2 = src2.replace(old_msg, new_msg)
    print("msg replaced")
else:
    # buscar variante con acento
    idx = src2.find('Marca de agua actualizada')
    print("msg not found exactly, idx:", idx)

# ── 3. Agregar boton Firmas en sidebar ────────────────────────────────────────
old_sidebar = ('btn_bot_config.clicked.connect(self._manage_bot_config)\r\n'
               '            layout.addWidget(btn_bot_config)\r\n\r\n'
               '            # \u2500\u2500 Control del bot')
new_sidebar = ('btn_bot_config.clicked.connect(self._manage_bot_config)\r\n'
               '            layout.addWidget(btn_bot_config)\r\n\r\n'
               '            btn_firmas = QPushButton("\u270d\ufe0f  Firmas PDF")\r\n'
               '            btn_firmas.setObjectName("primary")\r\n'
               '            btn_firmas.clicked.connect(self._manage_firmas)\r\n'
               '            layout.addWidget(btn_firmas)\r\n\r\n'
               '            # \u2500\u2500 Control del bot')
if old_sidebar in src2:
    src2 = src2.replace(old_sidebar, new_sidebar)
    print("sidebar OK")
else:
    print("sidebar NOT FOUND")

# ── 4. Agregar metodo _manage_firmas ─────────────────────────────────────────
FIRMAS_METHOD = '''    def _manage_firmas(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Configurar Firmas del PDF")
        dlg.setMinimumSize(420, 260)
        dlg.setStyleSheet(QSS)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("\u270d\ufe0f  Etiquetas de Firmas en el PDF")
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
        btn_save = QPushButton("\U0001f4be  Guardar")
        btn_save.setObjectName("primary")

        def save():
            _write_env({
                "FIRMA1_LABEL": firma1_input.text().strip() or "Firma Empresa",
                "FIRMA2_LABEL": firma2_input.text().strip() or "Firma Cliente",
            })
            dlg.accept()
            QMessageBox.information(self, "Guardado", "\u2705 Firmas actualizadas.")

        btn_save.clicked.connect(save)
        btns.addWidget(btn_cancel)
        btns.addStretch()
        btns.addWidget(btn_save)
        layout.addLayout(btns)
        dlg.exec()

    def _manage_bot_config(self):'''

if '    def _manage_bot_config(self):' in src2:
    src2 = src2.replace('    def _manage_bot_config(self):', FIRMAS_METHOD, 1)
    print("firmas method OK")
else:
    print("_manage_bot_config NOT FOUND")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(src2)

print("DONE")
print("firma_tbl:", 'firma_tbl' in src2)
print("Logo Empresa:", 'Logo Empresa' in src2)
print("Firmas PDF:", 'Firmas PDF' in src2)
print("_manage_firmas:", '_manage_firmas' in src2)
