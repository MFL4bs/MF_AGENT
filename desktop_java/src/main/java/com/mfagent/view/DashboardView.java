package com.mfagent.view;

import com.mfagent.model.Product;
import com.mfagent.model.Session;
import com.mfagent.service.LocalInventory;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.Label;
import javafx.scene.layout.*;

import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * Vista Dashboard.
 * Equivalente a _dashboard_widget en app.py
 */
public class DashboardView {

    private final Session session;
    private final LocalInventory inventory;
    private final VBox root;

    private Label valProducts;
    private Label valWhatsApp;
    private Label alertLabel;

    public DashboardView(Session session, LocalInventory inventory) {
        this.session = session;
        this.inventory = inventory;
        this.root = new VBox(20);
        root.setPadding(new Insets(28));
        root.setStyle("-fx-background-color: #F5F0EB;");
        build();
    }

    private void build() {
        Label title = new Label("Dashboard");
        title.setStyle("-fx-font-size: 22px; -fx-font-weight: bold; -fx-text-fill: #1F2937;");

        HBox cardsRow = new HBox(20);
        cardsRow.setAlignment(Pos.CENTER_LEFT);

        VBox cardProd = makeStatCard("📦", "Productos en catálogo", "0", "#1B6CA8");
        valProducts = (Label) cardProd.getChildren().get(1);

        VBox cardBot = makeStatCard("🤖", "Estado del bot", "Activo", "#16A34A");

        VBox cardWa = makeStatCard("📱", "WhatsApp", "—", "#6B7280");
        valWhatsApp = (Label) cardWa.getChildren().get(1);

        cardsRow.getChildren().addAll(cardProd, cardBot, cardWa);

        alertLabel = new Label();
        alertLabel.getStyleClass().add("alert-warning");
        alertLabel.setWrapText(true);
        alertLabel.setVisible(false);
        alertLabel.setManaged(false);

        root.getChildren().addAll(title, cardsRow, alertLabel);
    }

    private VBox makeStatCard(String icon, String label, String value, String color) {
        VBox card = new VBox(4);
        card.getStyleClass().add("card");
        card.setPrefWidth(200);
        card.setPrefHeight(110);
        card.setPadding(new Insets(20));

        Label iconLbl = new Label(icon);
        iconLbl.setStyle("-fx-font-size: 22px;");

        Label valLbl = new Label(value);
        valLbl.setStyle("-fx-font-size: 26px; -fx-font-weight: bold; -fx-text-fill: " + color + ";");

        Label lblLbl = new Label(label);
        lblLbl.setStyle("-fx-font-size: 12px; -fx-text-fill: #6B7280;");

        card.getChildren().addAll(iconLbl, valLbl, lblLbl);
        return card;
    }

    public void refresh() {
        CompletableFuture.supplyAsync(inventory::list).thenAccept(products ->
            Platform.runLater(() -> updateStats(products))
        );
    }

    private void updateStats(List<Product> products) {
        int total = products.size();
        long low  = products.stream().filter(Product::isLowStock).count();
        long out  = products.stream().filter(Product::isOutOfStock).count();

        valProducts.setText(String.valueOf(total));

        if (low > 0 || out > 0) {
            StringBuilder sb = new StringBuilder("⚠️  Atención: ");
            if (out > 0) sb.append(out).append(" sin stock");
            if (low > 0) { if (out > 0) sb.append(", "); sb.append(low).append(" con stock bajo"); }
            sb.append(". Revisa el inventario.");
            alertLabel.setText(sb.toString());
            alertLabel.setVisible(true);
            alertLabel.setManaged(true);
        } else {
            alertLabel.setVisible(false);
            alertLabel.setManaged(false);
        }

        CompletableFuture.supplyAsync(this::checkWhatsApp).thenAccept(connected ->
            Platform.runLater(() -> {
                if (connected) {
                    valWhatsApp.setText("Conectado");
                    valWhatsApp.setStyle("-fx-font-size: 20px; -fx-font-weight: bold; -fx-text-fill: #16A34A;");
                } else {
                    valWhatsApp.setText("Desconectado");
                    valWhatsApp.setStyle("-fx-font-size: 20px; -fx-font-weight: bold; -fx-text-fill: #DC2626;");
                }
            })
        );
    }

    private boolean checkWhatsApp() {
        try {
            java.net.HttpURLConnection conn = (java.net.HttpURLConnection)
                    new java.net.URL("http://127.0.0.1:8000/bridge/status").openConnection();
            conn.setConnectTimeout(1000);
            conn.setReadTimeout(1000);
            String body = new String(conn.getInputStream().readAllBytes());
            return body.contains("\"connected\":true");
        } catch (Exception e) {
            return false;
        }
    }

    public VBox getRoot() { return root; }
}
