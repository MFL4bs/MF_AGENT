"""
Test automatizado del menú de navegación.
Simula clicks simples, dobles y secuencias rápidas.
Imprime PASS/FAIL por cada caso.
"""
import sys
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # sin ventana visible

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
_pre_app = QApplication.instance() or QApplication(sys.argv)
_pre_app.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

from unittest.mock import patch, MagicMock

# ── Mocks de dependencias externas ───────────────────────────────────────────
mock_products = [
    {"sku": "P001", "name": "Prod A", "price": 10.0, "stock": 10, "category": "general", "image_url": ""},
    {"sku": "P002", "name": "Prod B", "price": 5.0,  "stock": 2,  "category": "general", "image_url": ""},
]

with patch.dict("sys.modules", {
    "main": MagicMock(app=MagicMock()),
    "uvicorn": MagicMock(),
}):
    with patch("agent.inventory.list_products", return_value=mock_products), \
         patch("agent.inventory.low_stock_products", return_value=[mock_products[1]]), \
         patch("agent.sales.list_sales", return_value=[]), \
         patch("agent.sales.total_today", return_value=0):

        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        app = _pre_app

        import threading
        with patch("threading.Thread"):
            from app import MainWindow

        results = []

        def check(name, condition):
            status = "PASS" if condition else "FAIL"
            results.append((name, status))
            print(f"  [{status}] {name}")

        win = MainWindow()

        # ── Helpers ───────────────────────────────────────────────────────────
        def current_page():
            return getattr(win, "_current_page", "Dashboard")

        def page_title():
            return win.page_title.text()

        def checked_btn():
            for name in ["Dashboard", "Inventario", "Ventas", "Stock Bajo"]:
                btn = getattr(win, f"nav_{name.lower().replace(' ', '_')}")
                if btn.isChecked():
                    return name
            return None

        def nav(page):
            win._nav(page)
            app.processEvents()

        # ── Tests ─────────────────────────────────────────────────────────────
        print("\n=== Test navegación básica ===")
        nav("Inventario")
        check("Inventario: título correcto",     page_title() == "Inventario")
        check("Inventario: botón marcado",        checked_btn() == "Inventario")
        check("Inventario: tabla visible",        win._table.isVisible())
        check("Inventario: dashboard oculto",     not win._dashboard_widget.isVisible())

        nav("Ventas")
        check("Ventas: título correcto",          page_title() == "Ventas")
        check("Ventas: botón marcado",            checked_btn() == "Ventas")
        check("Ventas: sales_widget visible",     win._sales_widget.isVisible())
        check("Ventas: tabla oculta",             not win._table.isVisible())

        nav("Stock Bajo")
        check("Stock Bajo: título correcto",      page_title() == "Stock Bajo")
        check("Stock Bajo: botón marcado",        checked_btn() == "Stock Bajo")
        check("Stock Bajo: tabla visible",        win._table.isVisible())

        nav("Dashboard")
        check("Dashboard: título correcto",       page_title() == "Dashboard")
        check("Dashboard: botón marcado",         checked_btn() == "Dashboard")
        check("Dashboard: dashboard visible",     win._dashboard_widget.isVisible())
        check("Dashboard: tabla oculta",          not win._table.isVisible())

        print("\n=== Test doble click (bug principal) ===")
        nav("Inventario")
        page_before = current_page()
        nav("Inventario")  # segundo click en la misma página
        check("Doble click Inventario: página no cambia", current_page() == page_before)
        check("Doble click Inventario: título no cambia", page_title() == "Inventario")
        check("Doble click Inventario: botón sigue marcado", checked_btn() == "Inventario")

        nav("Ventas")
        nav("Ventas")  # doble click en Ventas
        check("Doble click Ventas: página no cambia",  current_page() == "Ventas")
        check("Doble click Ventas: botón sigue marcado", checked_btn() == "Ventas")

        print("\n=== Test clicks rápidos en secuencia ===")
        for page in ["Dashboard", "Inventario", "Ventas", "Stock Bajo", "Dashboard", "Inventario"]:
            nav(page)
        check("Secuencia rápida: termina en Inventario", current_page() == "Inventario")
        check("Secuencia rápida: botón correcto",        checked_btn() == "Inventario")
        check("Secuencia rápida: solo 1 botón marcado",
              sum(1 for n in ["Dashboard","Inventario","Ventas","Stock Bajo"]
                  if getattr(win, f"nav_{n.lower().replace(' ','_')}").isChecked()) == 1)

        print("\n=== Test botón add_btn ===")
        nav("Inventario")
        check("Inventario: add_btn texto correcto", "Agregar" in win._add_btn.text())
        nav("Ventas")
        check("Ventas: add_btn texto correcto",     "Venta" in win._add_btn.text())
        nav("Dashboard")
        check("Dashboard: add_btn oculto",          not win._add_btn.isVisible())

        # ── Resumen ───────────────────────────────────────────────────────────
        passed = sum(1 for _, s in results if s == "PASS")
        failed = sum(1 for _, s in results if s == "FAIL")
        print(f"\n{'='*40}")
        print(f"  TOTAL: {len(results)} tests | PASS: {passed} | FAIL: {failed}")
        print(f"{'='*40}\n")

        sys.exit(0 if failed == 0 else 1)
