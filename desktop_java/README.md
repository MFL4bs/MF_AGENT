# MF Agent — Desktop Java (JavaFX)

Reescritura de la app de escritorio Python/PyQt6 en Java + JavaFX.
Misma funcionalidad, sin el crash nativo `0xC0000409` de gRPC/Firebase en Python.

---

## Stack

| Capa | Tecnología |
|---|---|
| UI | JavaFX 21 |
| JSON local | Gson |
| PDF | iText 8 |
| Firebase | Firebase Admin SDK 9 |
| HTTP (bridge WA) | OkHttp 4 |
| Build | Maven |

---

## Estructura

```
desktop_java/
├── pom.xml
└── src/main/java/com/mfagent/
    ├── App.java                        # Punto de entrada JavaFX
    ├── model/
    │   ├── Product.java                # Equivalente al dict producto Python
    │   ├── Invoice.java                # Equivalente al dict factura Python
    │   ├── InvoiceItem.java
    │   └── Session.java                # session dict de Python
    ├── service/
    │   ├── JsonStore.java              # _load() / _save() genérico
    │   ├── LocalInventory.java         # agent/local_inventory.py
    │   ├── LocalSales.java             # agent/local_sales.py
    │   └── ProfilePaths.java           # agent/profiles.py → get_profile_data_dir()
    ├── controller/
    │   └── AppController.java          # AppController de app.py
    ├── view/
    │   ├── ActivationView.java         # lic_manager/activation_screen.py
    │   ├── MainWindow.java             # MainWindow de app.py
    │   ├── DashboardView.java          # _dashboard_widget
    │   ├── InventoryView.java          # _populate_table() + ProductDialog
    │   ├── SalesView.java              # _show_sales_view()
    │   ├── ProductDialog.java          # ProductDialog
    │   ├── SaleDialog.java             # SaleDialog
    │   ├── InvoiceDialog.java          # InvoiceDialog
    │   ├── WhatsAppDialog.java         # WhatsAppConfigDialog / WhatsAppViewDialog
    │   ├── BusinessDataDialog.java     # _manage_business_data()
    │   └── FirmasDialog.java           # _manage_firmas()
    └── util/
        ├── EnvConfig.java              # _read_env() / _write_env()
        └── WhatsAppNotifier.java       # _notify_all_admins()
```

---

## Compilar y ejecutar

```bash
cd desktop_java

# Ejecutar en desarrollo
mvn javafx:run

# Generar JAR ejecutable
mvn package
java -jar target/mf-agent-desktop-1.0.0.jar
```

> Requiere Java 21+ y Maven 3.8+

---

## Pendiente de integrar

- `LicenseService` — validación de licencia contra Firebase (equivalente a `license_manager.py`)
- `ProfileService` — autenticación usuario/contraseña con hash (equivalente a `profiles.py`)
- `FirestoreSync` — sincronización PC ↔ Firestore (equivalente a `firestore_sync.py`)
- `PdfService` — generación de PDF con iText (equivalente a `_generate_pdf()`)
- `FirestoreListener` — listener en tiempo real de inventario/ventas
- Módulos: Cupones, Asesores, Manuales, Config Bot, Logo empresa

---

## Datos locales

Comparte la misma carpeta `data/` que la versión Python.
Los archivos JSON son compatibles — mismo formato.
