package com.mfagent.view;

import com.mfagent.model.Invoice;
import com.mfagent.model.InvoiceItem;
import com.mfagent.model.Product;
import com.mfagent.model.Session;
import com.mfagent.service.FirestoreSync;
import com.mfagent.service.LocalCustomers;
import com.mfagent.service.LocalInventory;
import com.mfagent.service.LocalSales;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.stage.Window;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public class SaleDialog extends Dialog<Invoice> {

    private final List<Product> products;
    private final Session session;
    private final LocalInventory inventory;
    private final LocalSales sales;
    private final LocalCustomers customers;
    private final FirestoreSync firestoreSync;

    private final ObservableList<InvoiceItem> rows = FXCollections.observableArrayList();
    private final ObservableList<Product> filteredProducts = FXCollections.observableArrayList();
    private TextField searchField;
    private ListView<Product> productList;
    private Spinner<Integer> qtySpinner;
    private Label totalLabel;

    // Campos cliente
    private TextField customerField;
    private TextField phoneField;
    private TextField addressField;
    private TextField rfcField;

    public SaleDialog(Window owner, List<Product> products, Session session,
                      LocalInventory inventory, LocalSales sales, FirestoreSync firestoreSync) {
        this.products      = products;
        this.session       = session;
        this.inventory     = inventory;
        this.sales         = sales;
        this.customers     = new LocalCustomers(session.getProfileId());
        this.firestoreSync = firestoreSync;

        setTitle("Registrar Venta");
        initOwner(owner);
        getDialogPane().getStylesheets().add(
                getClass().getResource("/css/theme.css").toExternalForm());
        getDialogPane().setStyle("-fx-background-color: #FDFAF7;");
        getDialogPane().setPrefWidth(660);

        buildContent();
        addButtons();
        setResultConverter(this::convert);
    }

    private void buildContent() {
        VBox layout = new VBox(12);
        layout.setPadding(new Insets(20));

        Label title = new Label("🛒  Nueva Venta");
        title.setStyle("-fx-font-size: 18px; -fx-font-weight: bold; -fx-text-fill: #1F2937;");

        // ── Datos del cliente ─────────────────────────────────────────────────
        VBox clientCard = new VBox(8);
        clientCard.getStyleClass().add("card");
        clientCard.setPadding(new Insets(12));

        Label clientTitle = new Label("Datos del Cliente");
        clientTitle.setStyle("-fx-font-size: 13px; -fx-font-weight: bold; -fx-text-fill: #1F2937;");

        // Búsqueda de cliente guardado
        HBox searchRow = new HBox(8);
        searchRow.setAlignment(Pos.CENTER_LEFT);
        TextField clientSearchField = new TextField();
        clientSearchField.setPromptText("Buscar cliente guardado...");
        HBox.setHgrow(clientSearchField, Priority.ALWAYS);
        ComboBox<String> clientCombo = new ComboBox<>();
        clientCombo.setPromptText("Seleccionar");
        clientCombo.setPrefWidth(200);
        Button btnSearch = new Button("🔍");
        btnSearch.getStyleClass().add("btn-primary");
        searchRow.getChildren().addAll(new Label("Cliente guardado:"), clientSearchField, btnSearch, clientCombo);

        List<Map<String, Object>> allCustomers = customers.list();
        Map<String, Map<String, Object>> customerMap = new LinkedHashMap<>();
        for (Map<String, Object> c : allCustomers)
            customerMap.put(c.getOrDefault("name", "").toString(), c);
        clientCombo.getItems().addAll(customerMap.keySet());

        btnSearch.setOnAction(e -> {
            String q = clientSearchField.getText().strip();
            clientCombo.getItems().setAll(
                    customers.search(q.isEmpty() ? " " : q).stream()
                            .map(c -> c.getOrDefault("name", "").toString()).toList());
            clientCombo.show();
        });
        clientCombo.setOnAction(e -> {
            String sel = clientCombo.getValue();
            if (sel == null) return;
            Map<String, Object> c = customerMap.get(sel);
            if (c == null) c = customers.search(sel).stream().findFirst().orElse(null);
            if (c == null) return;
            customerField.setText(c.getOrDefault("name",    "").toString());
            phoneField.setText(   c.getOrDefault("phone",   "").toString());
            addressField.setText( c.getOrDefault("address", "").toString());
            rfcField.setText(     c.getOrDefault("rfc",     "").toString());
        });

        HBox row1 = new HBox(8);
        customerField = new TextField(); customerField.setPromptText("Nombre del cliente (opcional)");
        HBox.setHgrow(customerField, Priority.ALWAYS);
        phoneField = new TextField(); phoneField.setPromptText("Teléfono"); phoneField.setPrefWidth(150);
        row1.getChildren().addAll(new Label("Nombre:"), customerField, new Label("Tel:"), phoneField);

        HBox row2 = new HBox(8);
        addressField = new TextField(); addressField.setPromptText("Dirección");
        HBox.setHgrow(addressField, Priority.ALWAYS);
        rfcField = new TextField(); rfcField.setPromptText("RFC / ID fiscal"); rfcField.setPrefWidth(150);
        row2.getChildren().addAll(new Label("Dirección:"), addressField, new Label("RFC:"), rfcField);

        clientCard.getChildren().addAll(clientTitle, searchRow, row1, row2);

        // ── Productos ─────────────────────────────────────────────────────────
        searchField = new TextField();
        searchField.setPromptText("🔍  Buscar producto por nombre o SKU...");
        searchField.textProperty().addListener((obs, old, val) -> filterProducts(val));

        filteredProducts.setAll(products);
        productList = new ListView<>(filteredProducts);
        productList.setPrefHeight(140);
        productList.setCellFactory(lv -> new ListCell<>() {
            @Override protected void updateItem(Product p, boolean empty) {
                super.updateItem(p, empty);
                if (empty || p == null) { setText(null); }
                else setText(p.getName() + "  [" + p.getSku() + "]  $" +
                        String.format("%,.0f", p.getPrice()) + "  (stock: " + p.getStock() + ")");
            }
        });
        productList.setOnMouseClicked(e -> { if (e.getClickCount() == 2) addItem(); });

        HBox addRow = new HBox(8);
        addRow.setAlignment(Pos.CENTER_LEFT);
        qtySpinner = new Spinner<>(1, 9999, 1);
        qtySpinner.setEditable(true);
        qtySpinner.setPrefWidth(80);
        Button btnAdd = new Button("＋ Agregar");
        btnAdd.getStyleClass().add("btn-primary");
        btnAdd.setOnAction(e -> addItem());
        addRow.getChildren().addAll(new Label("Cantidad:"), qtySpinner, btnAdd);

        TableView<InvoiceItem> table = buildItemTable();
        table.setItems(rows);
        table.setPrefHeight(160);

        totalLabel = new Label("Total: $0");
        totalLabel.setStyle("-fx-font-size: 15px; -fx-font-weight: bold; -fx-text-fill: #1B6CA8;");

        layout.getChildren().addAll(title, clientCard, searchField, productList, addRow, table, totalLabel);
        getDialogPane().setContent(layout);
    }

    @SuppressWarnings("unchecked")
    private TableView<InvoiceItem> buildItemTable() {
        TableView<InvoiceItem> tv = new TableView<>();
        tv.getStyleClass().add("table-view");

        TableColumn<InvoiceItem, String> colSku = new TableColumn<>("SKU");
        colSku.setCellValueFactory(c -> new javafx.beans.property.SimpleStringProperty(c.getValue().getSku()));
        colSku.setPrefWidth(90);

        TableColumn<InvoiceItem, String> colName = new TableColumn<>("Producto");
        colName.setCellValueFactory(c -> new javafx.beans.property.SimpleStringProperty(c.getValue().getProductName()));
        colName.setPrefWidth(200);

        TableColumn<InvoiceItem, String> colQty = new TableColumn<>("Cant.");
        colQty.setCellValueFactory(c -> new javafx.beans.property.SimpleStringProperty(
                String.valueOf(c.getValue().getQuantity())));
        colQty.setPrefWidth(60);

        TableColumn<InvoiceItem, String> colSub = new TableColumn<>("Subtotal");
        colSub.setCellValueFactory(c -> new javafx.beans.property.SimpleStringProperty(
                String.format("$%,.0f", c.getValue().getSubtotal())));
        colSub.setPrefWidth(90);

        TableColumn<InvoiceItem, Void> colDel = new TableColumn<>("");
        colDel.setPrefWidth(40);
        colDel.setCellFactory(col -> new TableCell<>() {
            private final Button btn = new Button("✕");
            { btn.getStyleClass().add("btn-danger");
              btn.setPrefHeight(26);
              btn.setOnAction(e -> { rows.remove(getTableView().getItems().get(getIndex())); refreshTotal(); }); }
            @Override protected void updateItem(Void item, boolean empty) {
                super.updateItem(item, empty);
                setGraphic(empty ? null : btn);
            }
        });

        tv.getColumns().addAll(colSku, colName, colQty, colSub, colDel);
        return tv;
    }

    private void filterProducts(String query) {
        String q = query == null ? "" : query.toLowerCase().trim();
        if (q.isEmpty()) { filteredProducts.setAll(products); return; }
        filteredProducts.setAll(products.stream().filter(p ->
                p.getName().toLowerCase().contains(q) ||
                p.getSku().toLowerCase().contains(q) ||
                (p.getCategory() != null && p.getCategory().toLowerCase().contains(q))
        ).toList());
    }

    private void addItem() {
        Product p = productList.getSelectionModel().getSelectedItem();
        if (p == null && !filteredProducts.isEmpty()) p = filteredProducts.get(0);
        if (p == null) return;
        int qty = qtySpinner.getValue();
        final Product fp = p;
        rows.stream().filter(r -> r.getSku().equals(fp.getSku())).findFirst().ifPresentOrElse(
                r -> {
                    r.setQuantity(r.getQuantity() + qty);
                    rows.set(rows.indexOf(r), r); // forzar refresco de la tabla
                },
                () -> rows.add(new InvoiceItem(fp.getSku(), fp.getName(), qty, fp.getPrice()))
        );
        refreshTotal();
    }

    private void refreshTotal() {
        double total = rows.stream().mapToDouble(InvoiceItem::getSubtotal).sum();
        totalLabel.setText(String.format("Total: $%,.0f", total));
    }

    private void addButtons() {
        ButtonType saveBtn   = new ButtonType("💾  Registrar", ButtonBar.ButtonData.OK_DONE);
        ButtonType cancelBtn = new ButtonType("Cancelar", ButtonBar.ButtonData.CANCEL_CLOSE);
        getDialogPane().getButtonTypes().addAll(saveBtn, cancelBtn);

        Button save = (Button) getDialogPane().lookupButton(saveBtn);
        save.addEventFilter(javafx.event.ActionEvent.ACTION, e -> {
            if (rows.isEmpty()) {
                new Alert(Alert.AlertType.WARNING, "Agrega al menos un producto.").show();
                e.consume();
            }
        });
    }

    private Invoice convert(ButtonType btn) {
        if (btn.getButtonData() != ButtonBar.ButtonData.OK_DONE) return null;

        Invoice inv = new Invoice();
        inv.setInvoiceId("INV-" + UUID.randomUUID().toString().substring(0, 6).toUpperCase());
        inv.setTimestamp(LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
        inv.setCustomer(customerField.getText().strip());
        inv.setCustomerPhone(phoneField.getText().strip());
        inv.setCustomerAddress(addressField.getText().strip());
        inv.setCustomerRfc(rfcField.getText().strip());
        inv.setChannel("manual");
        inv.setRegisteredBy(session.getUsername());
        inv.setItems(new ArrayList<>(rows));
        inv.recalcTotal();

        // Descontar stock
        for (InvoiceItem item : inv.getItems()) {
            inventory.get(item.getSku()).ifPresent(p -> {
                int newStock = Math.max(0, p.getStock() - item.getQuantity());
                inventory.updateStock(p.getSku(), newStock);
                if (newStock <= 15)
                    com.mfagent.util.WhatsAppNotifier.notifyAll(
                        "\u26a0\ufe0f *Stock bajo*\nProducto: " + p.getName() +
                        " [" + p.getSku() + "]\nStock actual: " + newStock + " unidades");
            });
        }
        sales.record(inv);

        com.mfagent.util.WhatsAppNotifier.notifySale(inv, "PC - " + session.getUsername());

        if (firestoreSync != null) firestoreSync.syncInvoice(inv);

        // Guardar cliente completo
        String name = inv.getCustomer();
        if (name != null && !name.isEmpty()) {
            Map<String, Object> c = new LinkedHashMap<>();
            c.put("name",    name);
            c.put("phone",   inv.getCustomerPhone() != null ? inv.getCustomerPhone() : "");
            c.put("address", inv.getCustomerAddress() != null ? inv.getCustomerAddress() : "");
            c.put("rfc",     inv.getCustomerRfc() != null ? inv.getCustomerRfc() : "");
            customers.search(name).stream()
                    .filter(x -> x.getOrDefault("phone", "").equals(c.get("phone")))
                    .findFirst().ifPresent(x -> c.put("id", x.get("id")));
            Map<String, Object> saved = customers.upsert(c);
            if (firestoreSync != null) firestoreSync.syncCustomer(saved);
        }

        if (firestoreSync != null) firestoreSync.syncAll(null);
        return inv;
    }
}
