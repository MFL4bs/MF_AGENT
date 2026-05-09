# 🔨 Guía de Compilación - MF_AGENT

## Requisitos Previos

1. **Python 3.10+** instalado
2. **Todas las dependencias** instaladas:
   ```bash
   pip install -r requirements.txt
   ```

3. **PyInstaller** instalado:
   ```bash
   pip install pyinstaller
   ```

## Métodos de Compilación

### Método 1: Script Automático (Recomendado) ⭐

```bash
python build.py
```

Este script:
- ✅ Compila automáticamente con PyInstaller
- ✅ Incluye todos los archivos necesarios
- ✅ Optimiza el tamaño del ejecutable
- ✅ Crea un solo archivo .exe

**Resultado:** `dist/MF_AGENT.exe`

---

### Método 2: Usando el archivo .spec

```bash
pyinstaller MF_AGENT.spec
```

Este método usa la configuración detallada del archivo `.spec`

**Resultado:** `dist/MF_AGENT.exe`

---

### Método 3: Comando Manual

```bash
pyinstaller --name=MF_AGENT ^
    --onefile ^
    --windowed ^
    --add-data="MF_LABS.png;." ^
    --add-data=".env.example;." ^
    --add-data="manuales;manuales" ^
    --add-data="agent;agent" ^
    --add-data="models;models" ^
    --add-data="whatsapp_bridge;whatsapp_bridge" ^
    --hidden-import=PyQt6.QtWebEngineWidgets ^
    --hidden-import=PyQt6.QtWebEngineCore ^
    --hidden-import=uvicorn.logging ^
    app.py
```

---

### Método 4: cx_Freeze (Alternativo)

```bash
pip install cx_Freeze
python setup.py build
```

**Resultado:** `build/exe.win-amd64-3.x/MF_AGENT.exe`

---

## Estructura del Ejecutable

El ejecutable incluye:
- ✅ Aplicación principal (app.py)
- ✅ Módulos de agente (agent/)
- ✅ Modelos de datos (models/)
- ✅ Bridge de WhatsApp (whatsapp_bridge/)
- ✅ Manuales de empresa (manuales/)
- ✅ Logo (MF_LABS.png)
- ✅ Configuración ejemplo (.env.example)

---

## Tamaño del Ejecutable

- **Con PyInstaller (onefile):** ~150-200 MB
- **Con PyInstaller (onedir):** ~300-400 MB (más rápido)
- **Con cx_Freeze:** ~250-350 MB

---

## Optimización del Tamaño

Para reducir el tamaño del ejecutable:

1. **Usar --onefile** (un solo archivo)
2. **Excluir módulos innecesarios:**
   ```bash
   --exclude-module=matplotlib
   --exclude-module=numpy
   --exclude-module=pandas
   ```

3. **Usar UPX** (compresor):
   ```bash
   --upx-dir=C:\path\to\upx
   ```

---

## Solución de Problemas

### Error: "PyInstaller no encontrado"
```bash
pip install pyinstaller
```

### Error: "Módulo no encontrado"
Agregar al comando:
```bash
--hidden-import=nombre_del_modulo
```

### Error: "Archivo no encontrado"
Verificar que todos los archivos existan:
```bash
dir MF_LABS.png
dir manuales
dir agent
```

### El ejecutable no inicia
1. Ejecutar desde CMD para ver errores:
   ```bash
   cd dist
   MF_AGENT.exe
   ```

2. Compilar con consola visible:
   ```bash
   pyinstaller --console app.py
   ```

---

## Distribución

### Archivos a incluir en la distribución:

```
MF_AGENT/
├── MF_AGENT.exe          # Ejecutable principal
├── .env.example          # Configuración ejemplo
├── README.md             # Instrucciones de uso
└── data/                 # Carpeta de datos (se crea automáticamente)
```

### Crear instalador (opcional)

Usar **Inno Setup** para crear un instalador profesional:

1. Descargar: https://jrsoftware.org/isdl.php
2. Crear script .iss
3. Compilar instalador

---

## Notas Importantes

⚠️ **Primera ejecución:**
- El ejecutable creará automáticamente la carpeta `data/`
- Copiará `.env.example` a `.env` si no existe
- Puede tardar unos segundos en iniciar

⚠️ **Antivirus:**
- Algunos antivirus pueden marcar el .exe como sospechoso
- Es un falso positivo común con PyInstaller
- Agregar excepción en el antivirus

⚠️ **Node.js:**
- Para WhatsApp, Node.js debe estar instalado
- El bridge se ejecuta automáticamente

---

## Comandos Rápidos

```bash
# Instalar dependencias
pip install -r requirements.txt pyinstaller

# Compilar
python build.py

# Ejecutar
dist\MF_AGENT.exe
```

---

## Soporte

Para problemas de compilación:
- Revisar logs en `build/` y `dist/`
- Verificar versiones de Python y dependencias
- Consultar documentación de PyInstaller

---

**¡Listo para distribuir! 🚀**
