with open('app.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix mensaje exito watermark (buscar y reemplazar la linea exacta)
idx = src.find('Marca de agua actualizada')
if idx != -1:
    # encontrar inicio y fin del QMessageBox.information completo
    s = src.rfind('QMessageBox.information(', 0, idx)
    e = src.find(')', idx) + 1
    old_block = src[s:e]
    new_block = ('QMessageBox.information(\n'
                 '                self, "Exito",\n'
                 '                f"\u2705 Logo actualizado. Aparecera en la parte superior izquierda del PDF.\\n\\nArchivo: {Path(new_path[0]).name}"\n'
                 '            )')
    src = src[:s] + new_block + src[e:]
    print("msg fixed")
else:
    print("msg already fixed or not found")

# Fix boton Firmas en sidebar
old_s = ('btn_bot_config.clicked.connect(self._manage_bot_config)\n'
         '            layout.addWidget(btn_bot_config)\n\n'
         '            # \u2500\u2500 Control del bot')
new_s = ('btn_bot_config.clicked.connect(self._manage_bot_config)\n'
         '            layout.addWidget(btn_bot_config)\n\n'
         '            btn_firmas = QPushButton("\u270d\ufe0f  Firmas PDF")\n'
         '            btn_firmas.setObjectName("primary")\n'
         '            btn_firmas.clicked.connect(self._manage_firmas)\n'
         '            layout.addWidget(btn_firmas)\n\n'
         '            # \u2500\u2500 Control del bot')
if old_s in src:
    src = src.replace(old_s, new_s)
    print("sidebar OK")
else:
    # intentar con \r\n
    old_s2 = old_s.replace('\n', '\r\n')
    new_s2 = new_s.replace('\n', '\r\n')
    if old_s2 in src:
        src = src.replace(old_s2, new_s2)
        print("sidebar OK (crlf)")
    else:
        idx2 = src.find('btn_bot_config.clicked.connect')
        print("sidebar NOT FOUND, btn_bot_config at:", idx2)
        if idx2 != -1:
            print(repr(src[idx2:idx2+200]))

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(src)

print("Firmas PDF:", 'Firmas PDF' in src)
print("DONE")
