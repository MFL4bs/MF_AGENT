package com.mfagent.view;

import com.mfagent.model.Product;
import com.mfagent.model.Session;
import com.mfagent.service.LocalInventory;
import com.mfagent.service.FirestoreSync;
import javafx.application.Platform;
import javafx.beans.property.SimpleStringProperty;
import javafx.collections.FXCollections;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.layout.*;

import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * Vista de Inventario con tabla, búsqueda y CRUD.
 * Equivalente a _populate_table() + ProductDialog en app.py
 */
public class InventoryView {

    private final Session session;
    private final LocalInventory inventory;
    private final VBox root;
    private FirestoreSync firestoreSync;

    private TableView<Product> table;
    private TextField searchField;
    private List<Product> allProducts;

    // Totales
    private Label lblTotalUnits;
    private Label lblTotalCost;
    private Label lblTotalProfit;

    public InventoryView(Session session, LocalInventory inventory) {
        this.session = session;
        this.inventory = inventory;
        this.root = new VBox(16);
        root.setPadding(new Insets(28));
        root.setStyle("-fx-background-color: #F5F0EB;");
        build();
    }

    private void build() {
        // Header
        HBox header = new HBox(12);
        header.setAlignment(Pos.CENTER_LEFT);

        Label title = new Label("Inventario");
        title.setStyle("-fx-font-size: 22px; -fx-font-weight: bold; -fx-text-fill: #1F2937;");

        searchField = new TextField();
        searchField.setPromptText("🔍  Buscar producto...");
        searchField.getStyleClass().add("search-field");
        searchField.textProperty().addListener((obs, old, val) -> filterTable(val));

        Region spacer = new Region();
        HBox.setHgrow(spacer, Priority.ALWAYS);

        header.getChildren().addAll(title, spacer, searchField);

        if (session.isAdmin()) {
            Button btnAdd = new Button("＋  Producto");
            btnAdd.getStyleClass().add("btn-primary");
            btnAdd.setOnAction(e -> openProductDialog(null));
            header.getChildren().add(btnAdd);
        }

        // Barra de totales
        HBox totalsBar = new HBox(32);
        totalsBar.getStyleClass().add("card");
        totalsBar.setPadding(new Insets(10, 16, 10, 16));
        lblTotalUnits  = new Label("Total unidades: —");
        lblTotalUnits.setStyle("-fx-text-fill: #1F2937; -fx-font-weight: bold;");
        lblTotalCost   = new Label("Costo total: —");
        lblTotalCost.setStyle("-fx-text-fill: #D97706; -fx-font-weight: bold;");
        lblTotalProfit = new Label("Ganancia potencial: —");
        lblTotalProfit.setStyle("-fx-text-fill: #16A34A; -fx-font-weight: bold;");
        if (!session.isAdmin()) {
            lblTotalCost.setVisible(false);
            lblTotalProfit.setVisible(false);
        }
        totalsBar.getChildren().addAll(lblTotalUnits, lblTotalCost, lblTotalProfit);

        // Tabla
        table = buildTable();
        VBox.setVgrow(table, Priority.ALWAYS);

        root.getChildren().addAll(header, totalsBar, table);
    }

    @SuppressWarnings("unchecked")
    private TableView<Product> buildTable() {
        TableView<Product> tv = new TableView<>();
        tv.setColumnResizePolicy(TableView.CONSTRAINED_RESIZE_POLICY);
        tv.getStyleClass().add("table-view");

        TableColumn<Product, String> colSku = new TableColumn<>("SKU");
        colSku.setCellValueFactory(c -> new SimpleStringProperty(c.getValue().getSku()));
        colSku.setPrefWidth(100);

        TableColumn<Product, String> colName = new TableColumn<>("Nombre");
        colName.setCellValueFactory(c -> new SimpleStringProperty(c.getValue().getName()));
        colName.setPrefWidth(200);

        TableColumn<Product, String> colCat = new TableColumn<>("Categoría");
        colCat.setCellValueFactory(c -> new SimpleStringProperty(c.getValue().getCategory()));
        colCat.setPrefWidth(110);

        TableColumn<Product, String> colCost = new TableColumn<>("Costo");
        colCost.setCellValueFactory(c -> new SimpleStringProperty(
                c.getValue().getCostPrice() > 0 ? String.format("$%,.0f", c.getValue().getCostPrice()) : "—"));
        colCost.setPrefWidth(90);
        colCost.setVisible(session.isAdmin());

        TableColumn<Product, String> colPrice = new TableColumn<>("Venta");
        colPrice.setCellValueFactory(c -> new SimpleStringProperty(
                String.format("$%,.0f", c.getValue().getPrice())));
        colPrice.setPrefWidth(90);

        TableColumn<Product, String> colMargin = new TableColumn<>("Rentab.");
        colMargin.setCellValueFactory(c -> {
            Product p = c.getValue();
            if (p.getCostPrice() > 0)
                return new SimpleStringProperty(String.format("+$%,.0f (%.0f%%)", p.getMargin(), p.getMarginPct()));
            return new SimpleStringProperty("—");
        });
        colMargin.setPrefWidth(120);
        colMargin.setVisible(session.isAdmin());

        TableColumn<Product, String> colStock = new TableColumn<>("Stock");
        colStock.setCellValueFactory(c -> new SimpleStringProperty(String.valueOf(c.getValue().getStock())));
        colStock.setPrefWidth(65);
        colStock.setCellFactory(col -> new TableCell<>() {
            @Override
            protected void updateItem(String item, boolean empty) {
                super.updateItem(item, empty);
                if (empty || item == null) { setText(null); setStyle(""); return; }
                setText(item);
                int stock = Integer.parseInt(item);
                if (stock == 0)       setStyle("-fx-text-fill: #DC2626; -fx-font-weight: bold;");
                else if (stock <= 15) setStyle("-fx-text-fill: #D97706; -fx-font-weight: bold;");
                else                  setStyle("-fx-text-fill: #16A34A;");
            }
        });

        // Columna acciones (solo admin)
        TableColumn<Product, Void> colActions = new TableColumn<>("Acciones");
        colActions.setPrefWidth(110);
        colActions.setVisible(session.isAdmin());
        colActions.setCellFactory(col -> new TableCell<>() {
            private final Button btnEdit = new Button("✏️");
            private final Button btnDel  = new Button("🗑️");
            private final HBox box = new HBox(6, btnEdit, btnDel);
            {
                btnEdit.getStyleClass().add("btn-edit");
                btnDel.getStyleClass().add("btn-danger");
                btnEdit.setPrefHeight(28);
                btnDel.setPrefHeight(28);
                btnEdit.setOnAction(e -> {
                    Product p = getTableView().getItems().get(getIndex());
                    openProductDialog(p);
                });
                btnDel.setOnAction(e -> {
                    Product p = getTableView().getItems().get(getIndex());
                    confirmDelete(p);
                });
            }
            @Override
            protected void updateItem(Void item, boolean empty) {
                super.updateItem(item, empty);
                setGraphic(empty ? null : box);
            }
        });

        tv.getColumns().addAll(colSku, colName, colCat, colCost, colPrice, colMargin, colStock, colActions);
        return tv;
    }

    public void setFirestoreSync(FirestoreSync sync) { this.firestoreSync = sync; }

    public void load() {
        CompletableFuture.supplyAsync(inventory::list).thenAccept(products ->
            Platform.runLater(() -> populate(products))
        );
    }

    public void loadLowStock() {
        CompletableFuture.supplyAsync(() -> inventory.lowStock(15)).thenAccept(products ->
            Platform.runLater(() -> populate(products))
        );
    }

    private void populate(List<Product> products) {
        allProducts = products;
        table.setItems(FXCollections.observableArrayList(products));

        int totalUnits = products.stream().mapToInt(Product::getStock).sum();
        double totalCost   = products.stream().mapToDouble(p -> p.getCostPrice() * p.getStock()).sum();
        double totalProfit = products.stream().mapToDouble(p -> p.getMargin() * p.getStock()).sum();

        lblTotalUnits.setText("Total unidades: " + String.format("%,d", totalUnits));
        lblTotalCost.setText("Costo total: $" + String.format("%,.0f", totalCost));
        lblTotalProfit.setText("Ganancia potencial: $" + String.format("%,.0f", totalProfit));
    }

    private void filterTable(String query) {
        if (allProducts == null) return;
        String q = query.toLowerCase();
        List<Product> filtered = allProducts.stream()
                .filter(p -> p.getName().toLowerCase().contains(q)
                        || p.getSku().toLowerCase().contains(q)
                        || (p.getCategory() != null && p.getCategory().toLowerCase().contains(q)))
                .toList();
        table.setItems(FXCollections.observableArrayList(filtered));
    }

    private void openProductDialog(Product existing) {
        new ProductDialog(root.getScene().getWindow(), existing, inventory, session.getProfileId(), firestoreSync)
                .showAndWait()
                .ifPresent(saved -> load());
    }

    private void confirmDelete(Product p) {
        Alert alert = new Alert(Alert.AlertType.CONFIRMATION,
                "¿Eliminar producto " + p.getSku() + "?",
                ButtonType.YES, ButtonType.NO);
        alert.setHeaderText(null);
        alert.showAndWait().ifPresent(btn -> {
            if (btn == ButtonType.YES) {
                inventory.delete(p.getSku());
                if (firestoreSync != null) firestoreSync.deleteProduct(p.getSku());
                load();
            }
        });
    }

    public VBox getRoot() { return root; }
}
