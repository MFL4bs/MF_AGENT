# 🎨 Marca de Agua en PDFs de Facturas

## Características

✅ **Marca de agua automática** en todos los PDFs de facturas
✅ **Opacidad ajustable** (0-100%) configurable en .env
✅ **Imagen personalizable** (PNG, JPG, SVG, WebP)
✅ **Centrada y proporcional** en cada página
✅ **No interfiere con el contenido** (semitransparente)
✅ **Configuración persistente** (guardada en .env)

## Uso

### 1. Configuración en .env

Agrega o modifica estas variables en tu archivo `.env`:

```bash
# Ruta de la imagen para marca de agua (PNG recomendado con fondo transparente)
WATERMARK_IMAGE=MF_LABS.png

# Opacidad de la marca de agua (0.0 = invisible, 1.0 = opaco)
WATERMARK_OPACITY=0.15
```

### 2. Valores recomendados

- **Opacidad**: 0.10 - 0.20 (10-20%) para facturas profesionales
- **Formato**: PNG con fondo transparente
- **Tamaño**: 500x500px o superior (se escala automáticamente a 300px en el PDF)
- **Colores**: Logos monocromáticos o con colores suaves

### 3. Cambiar la imagen

1. Coloca tu logo en la carpeta del proyecto
2. Actualiza `WATERMARK_IMAGE` en `.env` con la ruta:
   ```bash
   WATERMARK_IMAGE=mi_logo.png
   # o ruta absoluta:
   WATERMARK_IMAGE=C:\imagenes\mi_logo.png
   ```

### 4. Ajustar opacidad

Modifica el valor de `WATERMARK_OPACITY` en `.env`:

```bash
# Muy sutil (recomendado para facturas formales)
WATERMARK_OPACITY=0.10

# Moderado (balance entre visibilidad y discreción)
WATERMARK_OPACITY=0.15

# Visible (para documentos internos)
WATERMARK_OPACITY=0.25
```

## Dónde aparece

La marca de agua se aplica automáticamente a:
- ✅ **Facturas generadas** desde "Nueva Factura"
- ✅ **PDFs exportados** desde el historial de ventas
- ✅ **Todas las páginas** del documento

## Personalización avanzada

### Cambiar tamaño de la marca de agua

Edita `app.py`, busca la función `_generate_pdf` y modifica:

```python
img_size = 300  # Cambia este valor (en puntos)
```

### Cambiar posición

En la misma función, modifica las coordenadas:

```python
# Centrado (por defecto)
x = (page_width - img_size) / 2
y = (page_height - img_size) / 2

# Esquina superior derecha
x = page_width - img_size - 50
y = page_height - img_size - 50

# Esquina inferior izquierda
x = 50
y = 50
```

### Desactivar marca de agua

Elimina o comenta las variables en `.env`:

```bash
# WATERMARK_IMAGE=MF_LABS.png
# WATERMARK_OPACITY=0.15
```

O establece opacidad en 0:

```bash
WATERMARK_OPACITY=0.0
```
