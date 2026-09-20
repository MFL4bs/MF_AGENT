package com.mfagent.view;

import com.mfagent.model.Invoice;
import com.mfagent.model.InvoiceItem;
import com.mfagent.model.Product;
import com.mfagent.model.Session;
import com.mfagent.service.FirestoreSync;
import com.mfagent.service.LocalInventory;
import com.mfagent.service.LocalSales;
import com.mfagent.service.PdfService;
import javafx.application.Platform;
import javafx.beans.property.SimpleStringProperty;
import javafx.collections.FXCollections;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.stage.FileChooser;

import java.time.LocalDate;
import java.time.YearMonth;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.concurrent.CompletableFuture;

public class SalesView {

    private final Session session;
    private final LocalInventory inventory;
    private final LocalSales sales;
    private final VBox root;
    private FirestoreSync firestoreSync;

    private TableView<Invoice> table;
    private List<Invoice> allVisible = List.of();

    // Stats
    private Label valHoy, valPedidosHoy, valWhatsApp, valTotal, valTotalCount;

    // Calendario
    private GridPane calGrid;
    private Label calMonthLabel;
    private TableView<Invoice> calTable;
    private Label calDayTotal, calDayCount, calDayProfit;
    private YearMonth calMonth = YearMonth.now();
    private LocalDate calSelected = null;

    public SalesView(Session session, LocalInventory inventory, LocalSales sales) {
        this.session = session;
        this.inventory = inventory;
        this.sales = sales;
        this.root = new VBox(16);
        root.setPadding(new Insets(28));
        root.setStyle("-fx-background-color: #F5F0EB;");
        build();
    }

    private void build() {
        // Header
        HBox header = new HBox(12);
        header.setAlignment(Pos.CENTER_LEFT);
        Label title = new Label("Ventas");
        title.setStyle("-fx-font-size: 22px; -fx-font-weight: bold; -fx-text-fill: #1F2937;");
        Region spacer = new Region();
        HBox.setHgrow(spacer, Priority.ALWAYS);

        Button btnVenta = new Button("＋  Venta");
        btnVenta.getStyleClass().add("btn-primary");
        btnVenta.setOnAction(e -> openSaleDialog());

        Button btnFactura = new Button("🧾  Factura");
        btnFactura.getStyleClass().add("btn-primary");
        btnFactura.setOnAction(e -> openInvoiceDialog());

        header.getChildren().addAll(title, spacer, btnVenta, btnFactura);

        // Stats
        HBox statsRow = new HBox(16);
        statsRow.setAlignment(Pos.CENTER_LEFT);
        VBox c1 = makeStatCard("💰", "Ventas Hoy",      "$0", "#16A34A"); valHoy        = (Label) c1.getChildren().get(1);
        VBox c2 = makeStatCard("🛒", "Pedidos Hoy",     "0",  "#1B6CA8"); valPedidosHoy = (Label) c2.getChildren().get(1);
        VBox c3 = makeStatCard("📱", "Vía WhatsApp",    "0",  "#D97706"); valWhatsApp   = (Label) c3.getChildren().get(1);
        VBox c4 = makeStatCard("💎", "Ventas Totales",  "$0", "#1B6CA8"); valTotal      = (Label) c4.getChildren().get(1);
        VBox c5 = makeStatCard("📊", "Pedidos Totales", "0",  "#6B7280"); valTotalCount = (Label) c5.getChildren().get(1);
        statsRow.getChildren().addAll(c1, c2, c3, c4, c5);

        // Tabs: Lista | Calendario (solo admin)
        TabPane tabs = new TabPane();
        tabs.setTabClosingPolicy(TabPane.TabClosingPolicy.UNAVAILABLE);
        tabs.setStyle("""
            -fx-background-color: transparent;
            -fx-tab-min-height: 34px;
        """);
        VBox.setVgrow(tabs, Priority.ALWAYS);

        // Tab Lista
        table = buildTable();
        VBox.setVgrow(table, Priority.ALWAYS);
        Tab tabLista = new Tab("📋  Lista", table);
        tabs.getTabs().add(tabLista);

        // Tab Calendario (solo admin)
        if (session.isAdmin()) {
            Tab tabCal = new Tab("📅  Calendario", buildCalendarPane());
            tabs.getTabs().add(tabCal);
        }

        root.getChildren().addAll(header, statsRow, tabs);
    }

    // ── Calendario ────────────────────────────────────────────────────────────

    private SplitPane buildCalendarPane() {
        // Panel izquierdo: navegación + grid
        VBox left = new VBox(10);
        left.setPadding(new Insets(12));
        left.setMinWidth(320);
        left.setMaxWidth(360);

        HBox nav = new HBox(8);
        nav.setAlignment(Pos.CENTER_LEFT);
        Button btnPrev = new Button("‹");
        btnPrev.getStyleClass().add("btn-primary");
        btnPrev.setOnAction(e -> { calMonth = calMonth.minusMonths(1); refreshCalGrid(); });
        Button btnNext = new Button("›");
        btnNext.getStyleClass().add("btn-primary");
        btnNext.setOnAction(e -> { calMonth = calMonth.plusMonths(1); refreshCalGrid(); });
        calMonthLabel = new Label();
        calMonthLabel.setStyle("-fx-font-size: 14px; -fx-font-weight: bold; -fx-text-fill: #1F2937;");
        Region navSpacerL = new Region(); HBox.setHgrow(navSpacerL, Priority.ALWAYS);
        Region navSpacerR = new Region(); HBox.setHgrow(navSpacerR, Priority.ALWAYS);
        nav.getChildren().addAll(btnPrev, navSpacerL, calMonthLabel, navSpacerR, btnNext);

        // Cabecera días
        String[] days = {"Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"};
        calGrid = new GridPane();
        calGrid.setHgap(4); calGrid.setVgap(4);
        for (int i = 0; i < 7; i++) {
            Label d = new Label(days[i]);
            d.setStyle("-fx-font-size: 11px; -fx-font-weight: bold; -fx-text-fill: #6B7280;");
            d.setMinWidth(38); d.setAlignment(Pos.CENTER);
            calGrid.add(d, i, 0);
        }

        left.getChildren().addAll(nav, calGrid);

        // Panel derecho: tabla del día + footer
        VBox right = new VBox(10);
        right.setPadding(new Insets(12));

        Label dayTitle = new Label("Selecciona un día");
        dayTitle.setStyle("-fx-font-size: 14px; -fx-font-weight: bold; -fx-text-fill: #1F2937;");

        calTable = buildCalTable();
        VBox.setVgrow(calTable, Priority.ALWAYS);

        // Footer totales
        HBox footer = new HBox(24);
        footer.setPadding(new Insets(10, 14, 10, 14));
        footer.setStyle("-fx-background-color: #FDFAF7; -fx-background-radius: 10;");
        calDayCount  = new Label("Ventas: —");
        calDayCount.setStyle("-fx-font-size: 13px; -fx-font-weight: bold; -fx-text-fill: #1F2937;");
        calDayTotal  = new Label("Total: —");
        calDayTotal.setStyle("-fx-font-size: 13px; -fx-font-weight: bold; -fx-text-fill: #16A34A;");
        calDayProfit = new Label("Ganancia: —");
        calDayProfit.setStyle("-fx-font-size: 13px; -fx-font-weight: bold; -fx-text-fill: #1B6CA8;");
        footer.getChildren().addAll(calDayCount, calDayTotal, calDayProfit);

        right.getChildren().addAll(dayTitle, calTable, footer);

        SplitPane split = new SplitPane(left, right);
        split.setDividerPositions(0.35);
        split.setStyle("-fx-background-color: transparent;");

        refreshCalGrid();
        return split;
    }

    private void refreshCalGrid() {
        // Limpiar filas de días (mantener fila 0 = cabecera)
        calGrid.getChildren().removeIf(n -> GridPane.getRowIndex(n) != null && GridPane.getRowIndex(n) > 0);

        calMonthLabel.setText(calMonth.getMonth().getDisplayName(
                java.time.format.TextStyle.FULL, new java.util.Locale("es")) + " " + calMonth.getYear());

        // Calcular totales por día del mes actual
        java.util.Map<LocalDate, Double> dayTotals = new java.util.HashMap<>();
        String prefix = calMonth.toString(); // "yyyy-MM"
        for (Invoice inv : allVisible) {
            if (inv.getTimestamp() != null && inv.getTimestamp().startsWith(prefix)) {
                try {
                    LocalDate d = LocalDate.parse(inv.getTimestamp().substring(0, 10));
                    dayTotals.merge(d, inv.getTotal(), Double::sum);
                } catch (Exception ignored) {}
            }
        }

        int firstDow = calMonth.atDay(1).getDayOfWeek().getValue(); // 1=Lu … 7=Do
        int daysInMonth = calMonth.lengthOfMonth();
        int col = firstDow - 1;
        int row = 1;

        for (int day = 1; day <= daysInMonth; day++) {
            LocalDate date = calMonth.atDay(day);
            double total = dayTotals.getOrDefault(date, 0.0);
            boolean isToday = date.equals(LocalDate.now());
            boolean isSelected = date.equals(calSelected);

            Button btn = new Button(String.valueOf(day));
            btn.setMinWidth(38); btn.setMinHeight(38);
            btn.setMaxWidth(38); btn.setMaxHeight(38);

            String bg = isSelected ? "#1B6CA8" : (isToday ? "#EDE8E3" : "#FDFAF7");
            String fg = isSelected ? "white" : (total > 0 ? "#16A34A" : "#1F2937");
            String border = total > 0 ? "2px solid #16A34A" : "1px solid #D1CBC4";
            btn.setStyle(String.format(
                "-fx-background-color: %s; -fx-text-fill: %s; -fx-border-color: %s; " +
                "-fx-border-radius: 8; -fx-background-radius: 8; -fx-font-size: 12px; " +
                "-fx-font-weight: %s; -fx-cursor: hand;",
                bg, fg, border, total > 0 ? "bold" : "normal"));

            final LocalDate fd = date;
            btn.setOnAction(e -> selectDay(fd));

            calGrid.add(btn, col, row);
            col++;
            if (col == 7) { col = 0; row++; }
        }
    }

    private void selectDay(LocalDate date) {
        calSelected = date;
        refreshCalGrid();

        String prefix = date.toString(); // "yyyy-MM-dd"
        List<Invoice> dayInvoices = allVisible.stream()
                .filter(inv -> inv.getTimestamp() != null && inv.getTimestamp().startsWith(prefix))
                .toList();

        calTable.setItems(FXCollections.observableArrayList(dayInvoices));

        double total = dayInvoices.stream().mapToDouble(Invoice::getTotal).sum();
        double cost  = dayInvoices.stream().flatMap(inv -> inv.getItems() == null ? java.util.stream.Stream.empty() : inv.getItems().stream())
                .filter(i -> i.getSku() != null && !i.getSku().startsWith("COT-"))
                .mapToDouble(i -> {
                    var p = inventory.get(i.getSku());
                    return p.map(prod -> prod.getCostPrice() * i.getQuantity()).orElse(0.0);
                }).sum();
        double profit = total - cost;

        calDayCount.setText("Ventas: " + dayInvoices.size());
        calDayTotal.setText(String.format("Total: $%,.0f", total));
        calDayProfit.setText(String.format("Ganancia: $%,.0f", profit));
    }

    @SuppressWarnings("unchecked")
    private TableView<Invoice> buildCalTable() {
        TableView<Invoice> tv = new TableView<>();
        tv.setColumnResizePolicy(TableView.CONSTRAINED_RESIZE_POLICY);
        tv.getStyleClass().add("table-view");

        TableColumn<Invoice, String> colId = new TableColumn<>("ID");
        colId.setCellValueFactory(c -> new SimpleStringProperty(c.getValue().getInvoiceId()));
        colId.setPrefWidth(110);

        TableColumn<Invoice, String> colClient = new TableColumn<>("Cliente");
        colClient.setCellValueFactory(c -> new SimpleStringProperty(c.getValue().getCustomer()));
        colClient.setPrefWidth(130);

        TableColumn<Invoice, String> colVendedor = new TableColumn<>("Vendedor");
        colVendedor.setCellValueFactory(c -> new SimpleStringProperty(
                c.getValue().getRegisteredBy() != null ? c.getValue().getRegisteredBy() : "—"));
        colVendedor.setPrefWidth(90);

        TableColumn<Invoice, String> colCanal = new TableColumn<>("Canal");
        colCanal.setCellValueFactory(c -> new SimpleStringProperty(
                "whatsapp".equals(c.getValue().getChannel()) ? "WhatsApp" : "Manual"));
        colCanal.setPrefWidth(80);

        TableColumn<Invoice, String> colItems = new TableColumn<>("Items");
        colItems.setCellValueFactory(c -> {
            List<InvoiceItem> items = c.getValue().getItems();
            if (items == null) return new SimpleStringProperty("");
            String txt = items.stream()
                    .map(i -> (i.getProductName() != null ? i.getProductName() : i.getSku()) + " x" + i.getQuantity())
                    .reduce((a, b) -> a + ", " + b).orElse("");
            return new SimpleStringProperty(txt);
        });

        TableColumn<Invoice, String> colTotal = new TableColumn<>("Total");
        colTotal.setCellValueFactory(c -> new SimpleStringProperty(
                String.format("$%,.0f", c.getValue().getTotal())));
        colTotal.setPrefWidth(90);
        colTotal.setCellFactory(col -> new TableCell<>() {
            @Override protected void updateItem(String item, boolean empty) {
                super.updateItem(item, empty);
                setText(empty ? null : item);
                setStyle(empty ? "" : "-fx-text-fill: #16A34A; -fx-font-weight: bold;");
            }
        });

        tv.getColumns().addAll(colId, colClient, colVendedor, colCanal, colItems, colTotal);
        return tv;
    }

    // ── Tabla principal ───────────────────────────────────────────────────────

    private VBox makeStatCard(String icon, String label, String value, String color) {
        VBox card = new VBox(4);
        card.getStyleClass().add("card");
        card.setPrefWidth(180); card.setPrefHeight(100);
        card.setPadding(new Insets(16));
        Label iconLbl = new Label(icon); iconLbl.setStyle("-fx-font-size: 20px;");
        Label valLbl  = new Label(value);
        valLbl.setStyle("-fx-font-size: 22px; -fx-font-weight: bold; -fx-text-fill: " + color + ";");
        Label lblLbl  = new Label(label);
        lblLbl.setStyle("-fx-font-size: 11px; -fx-text-fill: #6B7280;");
        card.getChildren().addAll(iconLbl, valLbl, lblLbl);
        return card;
    }

    @SuppressWarnings("unchecked")
    private TableView<Invoice> buildTable() {
        TableView<Invoice> tv = new TableView<>();
        tv.setColumnResizePolicy(TableView.CONSTRAINED_RESIZE_POLICY);
        tv.getStyleClass().add("table-view");

        TableColumn<Invoice, String> colDate = new TableColumn<>("Fecha");
        colDate.setCellValueFactory(c -> new SimpleStringProperty(c.getValue().getTimestamp()));
        colDate.setPrefWidth(130);

        TableColumn<Invoice, String> colId = new TableColumn<>("ID");
        colId.setCellValueFactory(c -> new SimpleStringProperty(c.getValue().getInvoiceId()));
        colId.setPrefWidth(110);

        TableColumn<Invoice, String> colClient = new TableColumn<>("Cliente");
        colClient.setCellValueFactory(c -> new SimpleStringProperty(c.getValue().getCustomer()));
        colClient.setPrefWidth(130);

        TableColumn<Invoice, String> colCanal = new TableColumn<>("Canal");
        colCanal.setCellValueFactory(c -> new SimpleStringProperty(
                "whatsapp".equals(c.getValue().getChannel()) ? "WhatsApp" : "Manual"));
        colCanal.setPrefWidth(80);

        TableColumn<Invoice, String> colItems = new TableColumn<>("Items");
        colItems.setCellValueFactory(c -> {
            List<InvoiceItem> items = c.getValue().getItems();
            if (items == null) return new SimpleStringProperty("");
            String txt = items.stream()
                    .map(i -> (i.getProductName() != null ? i.getProductName() : i.getSku()) + " x" + i.getQuantity())
                    .reduce((a, b) -> a + ", " + b).orElse("");
            return new SimpleStringProperty(txt);
        });

        TableColumn<Invoice, String> colTotal = new TableColumn<>("Total");
        colTotal.setCellValueFactory(c -> new SimpleStringProperty(
                String.format("$%,.0f", c.getValue().getTotal())));
        colTotal.setPrefWidth(90);
        colTotal.setCellFactory(col -> new TableCell<>() {
            @Override protected void updateItem(String item, boolean empty) {
                super.updateItem(item, empty);
                setText(empty ? null : item);
                setStyle(empty ? "" : "-fx-text-fill: #16A34A; -fx-font-weight: bold;");
            }
        });

        TableColumn<Invoice, Void> colActions = new TableColumn<>("");
        colActions.setPrefWidth(session.isAdmin() ? 130 : 60);
        colActions.setCellFactory(col -> new TableCell<>() {
            private final Button btnPdf  = new Button("PDF");
            private final Button btnEdit = new Button("✏️");
            private final Button btnDel  = new Button("🗑️");
            private final HBox box;
            {
                btnPdf.setStyle("-fx-background-color:#1B6CA8;-fx-text-fill:white;" +
                        "-fx-background-radius:4;-fx-font-size:12px;-fx-font-weight:bold;");
                btnPdf.setPrefHeight(30);
                btnEdit.getStyleClass().add("btn-edit");  btnEdit.setPrefHeight(30);
                btnDel.getStyleClass().add("btn-danger"); btnDel.setPrefHeight(30);

                btnPdf.setOnAction(e  -> exportPdf(getTableView().getItems().get(getIndex())));
                btnEdit.setOnAction(e -> editInvoice(getTableView().getItems().get(getIndex())));
                btnDel.setOnAction(e  -> deleteInvoice(getTableView().getItems().get(getIndex())));

                box = session.isAdmin()
                        ? new HBox(4, btnPdf, btnEdit, btnDel)
                        : new HBox(4, btnPdf);
            }
            @Override protected void updateItem(Void item, boolean empty) {
                super.updateItem(item, empty);
                setGraphic(empty ? null : box);
            }
        });

        if (session.isAdmin()) {
            TableColumn<Invoice, String> colVendedor = new TableColumn<>("Vendedor");
            colVendedor.setCellValueFactory(c -> new SimpleStringProperty(
                    c.getValue().getRegisteredBy() != null ? c.getValue().getRegisteredBy() : "—"));
            colVendedor.setPrefWidth(90);
            tv.getColumns().addAll(colDate, colId, colClient, colCanal, colVendedor, colItems, colTotal, colActions);
        } else {
            tv.getColumns().addAll(colDate, colId, colClient, colCanal, colItems, colTotal, colActions);
        }
        return tv;
    }

    // ── Carga y populate ─────────────────────────────────────────────────────

    public void setFirestoreSync(FirestoreSync sync) { this.firestoreSync = sync; }

    public void load() {
        CompletableFuture.supplyAsync(sales::list)
                .thenAccept(records -> Platform.runLater(() -> populate(records)));
    }

    private void populate(List<Invoice> records) {
        // Deduplicar por invoiceId (quita las filas sin ID o duplicadas)
        java.util.Map<String, Invoice> seen = new java.util.LinkedHashMap<>();
        for (Invoice inv : records) {
            String id = inv.getInvoiceId();
            if (id != null && !id.isBlank()) {
                seen.putIfAbsent(id, inv);
            }
            // facturas sin ID se descartan de la vista (son duplicados corruptos)
        }
        List<Invoice> deduped = new java.util.ArrayList<>(seen.values());

        // Vendedor solo ve sus propias ventas
        allVisible = session.isAdmin() ? deduped :
                deduped.stream().filter(r -> session.getUsername().equals(r.getRegisteredBy())
                        || r.getRegisteredBy() == null || r.getRegisteredBy().isEmpty()).toList();

        table.setItems(FXCollections.observableArrayList(allVisible));

        String today = LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE);
        List<Invoice> todayRecs = allVisible.stream()
                .filter(r -> r.getTimestamp() != null && r.getTimestamp().startsWith(today)).toList();

        double totalHoy = todayRecs.stream().mapToDouble(Invoice::getTotal).sum();
        long   waCount  = todayRecs.stream().filter(r -> "whatsapp".equals(r.getChannel())).count();
        double totalAll = allVisible.stream().mapToDouble(Invoice::getTotal).sum();

        valHoy.setText(String.format("$%,.0f", totalHoy));
        valPedidosHoy.setText(String.valueOf(todayRecs.size()));
        valWhatsApp.setText(String.valueOf(waCount));
        valTotal.setText(String.format("$%,.0f", totalAll));
        valTotalCount.setText(String.valueOf(allVisible.size()));

        // Refrescar calendario si está construido
        if (calGrid != null) {
            refreshCalGrid();
            if (calSelected != null) selectDay(calSelected);
        }
    }

    // ── Acciones ─────────────────────────────────────────────────────────────

    private void openSaleDialog() {
        List<Product> products = inventory.list();
        new SaleDialog(root.getScene().getWindow(), products, session, inventory, sales, firestoreSync)
                .showAndWait().ifPresent(inv -> load());
    }

    private void openInvoiceDialog() {
        List<Product> products = inventory.list();
        new InvoiceDialog(root.getScene().getWindow(), products, session, inventory, sales, firestoreSync, null)
                .showAndWait().ifPresent(inv -> load());
    }

    private void exportPdf(Invoice invoice) {
        String pdfDir = com.mfagent.util.EnvConfig.get("PDF_OUTPUT_DIR", "");
        String fileName = (invoice.getInvoiceId() != null ? invoice.getInvoiceId() : "factura") + ".pdf";
        java.io.File file;
        if (!pdfDir.isEmpty()) {
            java.io.File dir = new java.io.File(pdfDir);
            if (!dir.exists()) dir.mkdirs();
            file = new java.io.File(dir, fileName);
        } else {
            FileChooser fc = new FileChooser();
            fc.setTitle("Guardar PDF");
            fc.setInitialFileName(fileName);
            fc.getExtensionFilters().add(new FileChooser.ExtensionFilter("PDF", "*.pdf"));
            file = fc.showSaveDialog(root.getScene().getWindow());
            if (file == null) return;
        }
        try {
            new PdfService().generate(invoice, file.getAbsolutePath());
            new Alert(Alert.AlertType.INFORMATION, "PDF guardado:\n" + file.getAbsolutePath()).show();
        } catch (Exception e) {
            new Alert(Alert.AlertType.ERROR, "Error al generar PDF:\n" + e.getMessage()).show();
        }
    }

    private void editInvoice(Invoice invoice) {
        List<Product> products = inventory.list();
        new InvoiceDialog(root.getScene().getWindow(), products, session, inventory, sales, firestoreSync, invoice)
                .showAndWait().ifPresent(inv -> load());
    }

    private void deleteInvoice(Invoice invoice) {
        if (!session.isAdmin()) {
            new Alert(Alert.AlertType.WARNING, "Solo el administrador puede eliminar ventas.").show();
            return;
        }
        String displayId = invoice.getInvoiceId() != null ? invoice.getInvoiceId() : "(sin ID)";
        Alert alert = new Alert(Alert.AlertType.CONFIRMATION,
                "¿Eliminar registro " + displayId + "?", ButtonType.YES, ButtonType.NO);
        alert.setHeaderText(null);
        alert.showAndWait().ifPresent(btn -> {
            if (btn != ButtonType.YES) return;

            // Restaurar stock
            if (invoice.getItems() != null) {
                for (InvoiceItem item : invoice.getItems()) {
                    if (item.getSku() != null && !item.getSku().startsWith("COT-")) {
                        inventory.get(item.getSku()).ifPresent(p ->
                                inventory.updateStock(p.getSku(), p.getStock() + item.getQuantity()));
                    }
                }
            }

            // Borrar por ID o por referencia directa si no tiene ID
            if (invoice.getInvoiceId() != null && !invoice.getInvoiceId().isBlank()) {
                sales.delete(invoice.getInvoiceId());
                if (firestoreSync != null) firestoreSync.deleteInvoice(invoice.getInvoiceId());
            } else {
                sales.deleteByRef(invoice);
            }
            load();
        });
    }

    public VBox getRoot() { return root; }
}
