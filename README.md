# MF Agent

Sistema de gestión comercial con bot de WhatsApp, inventario, ventas y app móvil. Desarrollado por [MFL4bs](https://github.com/MFL4bs).

---

## ¿Qué hace?

MF Agent es una aplicación de escritorio (Windows) que permite a negocios gestionar su inventario, registrar ventas, generar facturas en PDF y atender clientes automáticamente por WhatsApp. Todo sincronizado en tiempo real con Firebase para que también puedas operar desde el celular.

---

## Componentes

### App de escritorio — `MF_AGENT.exe`
Construida con Python + PyQt6. Requiere licencia activa para funcionar.

**Módulos principales:**

- **Inventario** — CRUD de productos con SKU, precio de compra/venta, stock, categoría y foto. Muestra rentabilidad por producto y alerta stock bajo (≤15 unidades). Sincroniza automáticamente con Firestore.
- **Ventas** — Registro de ventas manuales y desde WhatsApp. Estadísticas del día y totales. Exportación de facturas en PDF con logo, datos del cliente, firma y marca de agua personalizable.
- **Facturas PDF** — Generadas con ReportLab. Incluyen encabezado con logo de empresa, tabla de productos, cotizaciones de trabajo (por metro lineal/cuadrado/cúbico), datos del cliente (nombre, teléfono, dirección, RFC) y líneas de firma.
- **Bot de WhatsApp** — Menú interactivo: catálogo de productos, carrito de compras, cupones de descuento, transferencia a asesor. El cliente escribe por WhatsApp y el bot responde automáticamente.
- **Bridge WhatsApp** — Proceso Node.js (`whatsapp-web.js`) que conecta WhatsApp Web. Se vincula escaneando un código QR desde la app.
- **Notificaciones al admin** — Cuando se registra una venta, hay stock bajo o un cliente solicita asesor, se envía un mensaje de WhatsApp a los números admin configurados.
- **Cupones** — El admin crea cupones de descuento (porcentaje o monto fijo) con fecha de vencimiento y límite de usos. El cliente los aplica escribiendo el código en el chat.
- **Asesores** — Lista de asesores con nombre y teléfono. Cuando un cliente pide hablar con alguien, el bot notifica a todos los asesores con el link de WhatsApp del cliente y el resumen del pedido.
- **Manuales del bot** — Archivos `.txt` por perfil que el bot usa como referencia. Se gestionan desde la app.
- **Clientes** — Base de datos local de clientes con nombre, teléfono, dirección y RFC. Se importan automáticamente desde el historial de ventas y se pueden guardar desde el formulario de factura.
- **Configuración** — Logo de empresa, datos para el PDF (nombre, teléfono, email, dirección), etiquetas de firmas, imagen del dashboard (soporta GIF animado).

**Roles de usuario:**
- `admin` — acceso completo: agregar/editar/eliminar productos, registrar ventas, configurar todo.
- `vendedor` — solo puede ver inventario, registrar ventas y ver el estado de WhatsApp.

**Licencias:**
- Validadas contra Firebase al iniciar. Vinculadas a un dispositivo por hardware ID.
- Soporte para múltiples dispositivos por licencia (`max_devices`).
- Aviso cuando quedan ≤7 días para vencer.
- Al activar en un PC nuevo, restaura automáticamente inventario, ventas y usuarios desde Firestore.

---

### App móvil — `mobile/`
Construida con Flutter. APK disponible para Android.

**Pantallas:**
- **Activación** — Ingresa la key de licencia para vincular la app al perfil del negocio.
- **Login** — Selección de perfil (si hay más de uno) y autenticación con usuario/contraseña.
- **Dashboard** — Resumen en tiempo real: total de productos, stock bajo, sin stock, ventas del día y ventas totales.
- **Inventario** — Lista de productos con búsqueda. Admin puede agregar y editar productos. Vendedor puede ver detalle.
- **Ventas** — Lista de facturas con estadísticas. Permite registrar nuevas ventas y eliminar existentes.

**Sesión persistente** — Al cerrar y abrir la app, no pide login de nuevo si la licencia sigue activa.

**Sincronización en tiempo real** — Usa Firestore Streams. Los cambios del PC se reflejan en el móvil al instante y viceversa.

---

### Sincronización PC ↔ Móvil (Firestore)

| Colección | Contenido |
|---|---|
| `inventory` | Productos por perfil (`profile_id_SKU`) |
| `invoices` | Facturas/ventas |
| `profiles` | Datos del perfil, usuarios y key de licencia |
| `licenses` | Licencias activas |
| `devices` | Dispositivos registrados por licencia |
| `pdf` | URLs de PDFs subidos a Firebase Storage |

El PC escucha cambios en tiempo real (`FirestoreListener`) y actualiza el inventario y ventas locales cuando el móvil hace modificaciones.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Desktop | Python 3.11, PyQt6, FastAPI, Uvicorn |
| Bot WhatsApp | Node.js, whatsapp-web.js |
| PDF | ReportLab |
| Móvil | Flutter (Dart) |
| Base de datos | Firebase Firestore |
| Almacenamiento | Firebase Storage (PDFs) |
| Licencias | Firebase Firestore + HMAC SHA-256 |
| Historial de chat | AWS DynamoDB |
| Empaquetado | PyInstaller |

---

## Estructura del proyecto

```
MF_AGENT/
├── app.py                  # UI principal (PyQt6) + AppController
├── main.py                 # API FastAPI + webhook WhatsApp
├── login.py                # Pantalla de login y gestión de perfiles
├── config.py               # Configuración (settings)
├── agent/
│   ├── bot.py              # Motor del bot de WhatsApp
│   ├── coupons.py          # Gestión de cupones
│   ├── firestore_sync.py   # Sync PC → Firestore (SyncWorker, FirestoreListener)
│   ├── firestore_listener.py # Listener de inventario en tiempo real
│   ├── local_inventory.py  # CRUD inventario local (JSON)
│   ├── local_sales.py      # CRUD ventas local (JSON)
│   ├── local_customers.py  # CRUD clientes local (JSON)
│   ├── profiles.py         # Gestión de perfiles
│   └── labor_prices.py     # Precios de mano de obra
├── lic_manager/
│   ├── license_manager.py  # Validación y activación de licencias
│   ├── activation_screen.py
│   └── key_panel.py
├── whatsapp_bridge/
│   └── index.js            # Bridge Node.js (whatsapp-web.js)
├── models/
│   └── schemas.py          # Modelos Pydantic
├── mobile/                 # App Flutter
│   └── lib/
│       ├── main.dart
│       ├── screens/
│       ├── services/
│       ├── models/
│       └── widgets/
└── data/                   # Datos locales por perfil (no se sube a git)
```

---

## Configuración

Copia `.env.example` a `.env` y completa:

```env
ADMIN_PHONES=+521234567890,+529876543210
BUSINESS_NAME=Mi Empresa
BUSINESS_PHONE=+52 55 1234 5678
BUSINESS_EMAIL=contacto@miempresa.com
BUSINESS_ADDRESS=Calle 123, Ciudad
AWS_REGION=us-east-1
DYNAMODB_TABLE_SESSIONS=mf_sessions
```

---

## Compilar el ejecutable

```bash
py -m PyInstaller MF_AGENT.spec --noconfirm
# Resultado: dist/MF_AGENT.exe
```

---

## Compilar APK Android

```bash
cd mobile
flutter build apk --release
# Resultado: build/app/outputs/flutter-apk/app-release.apk
```

---

## Notas de seguridad

- Los archivos `*firebase-adminsdk*.json` y `google-services*.json` **no se incluyen en el repositorio**.
- Las licencias se firman con HMAC-SHA256 y están vinculadas al hardware del dispositivo.
- Las contraseñas de usuarios se almacenan como hash.

---

## Licencia

Propietario — © MFL4bs. Ver [LICENSE](LICENSE).
