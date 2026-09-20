package com.mfagent.view;

import com.mfagent.model.Session;
import com.mfagent.service.*;
import com.mfagent.service.BridgeManager;
import com.mfagent.service.FirestoreSync;
import com.mfagent.util.EnvConfig;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.layout.*;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Ventana principal de la aplicación.
 * Equivalente a MainWindow en app.py
 *
 * Estructura: sidebar izquierdo + área de contenido derecha.
 * Páginas: Dashboard | Inventario | Ventas | Stock Bajo
 */
public class MainWindow {

    private final Session session;
    private final BorderPane root;

    private final LocalInventory inventory;
    private final LocalSales sales;

    private StackPane contentArea;
    private DashboardView dashboardView;
    private InventoryView inventoryView;
    private SalesView salesView;
    private AdvisorsView advisorsView;
    private ManualsView manualsView;
    private BotConfigView botConfigView;
    private UsersView usersView;

    private final BotService botService;
    private final BridgeManager bridgeManager;
    private Button activeNavBtn;
    private ScheduledExecutorService scheduler;
    private Runnable onLogout;
    private WhatsAppDialog waDialog;

    public MainWindow(Session session, BridgeManager bridgeManager) {
        this.session       = session;
        this.inventory     = new LocalInventory(session.getProfileId());
        this.sales         = new LocalSales(session.getProfileId());
        this.botService    = new BotService(session.getProfileId());
        this.bridgeManager = bridgeManager;
        this.root          = new BorderPane();
        root.setStyle("-fx-background-color: #F5F0EB;");
        build();
    }

    private HBox bizHeader;

    private void build() {
        root.setLeft(buildSidebar());
        bizHeader = buildBizHeader();
        contentArea = new StackPane();
        contentArea.setStyle("-fx-background-color: #F5F0EB;");

        dashboardView  = new DashboardView(session, inventory);
        inventoryView  = new InventoryView(session, inventory);
        salesView      = new SalesView(session, inventory, sales);
        advisorsView   = new AdvisorsView(session, botService);
        manualsView    = new ManualsView(session, botService);
        botConfigView  = new BotConfigView(session);
        usersView      = new UsersView(session, new com.mfagent.service.ProfileService());

        contentArea.getChildren().addAll(
                dashboardView.getRoot(), inventoryView.getRoot(), salesView.getRoot(),
                advisorsView.getRoot(), manualsView.getRoot(),
                botConfigView.getRoot(), usersView.getRoot());
        showPage("Dashboard");

        VBox centerBox = new VBox(bizHeader, contentArea);
        VBox.setVgrow(contentArea, Priority.ALWAYS);
        root.setCenter(centerBox);
    }

    private HBox buildBizHeader() {
        HBox bar = new HBox(16);
        bar.setAlignment(Pos.CENTER_LEFT);
        bar.setPadding(new Insets(8, 20, 8, 20));
        bar.setStyle("-fx-background-color: #1B6CA8;");

        String name    = EnvConfig.get("BUSINESS_NAME",    "");
        String phone   = EnvConfig.get("BUSINESS_PHONE",   "");
        String email   = EnvConfig.get("BUSINESS_EMAIL",   "");
        String address = EnvConfig.get("BUSINESS_ADDRESS", "");

        if (!name.isEmpty()) {
            Label lName = new Label("🏢  " + name);
            lName.setStyle("-fx-text-fill: white; -fx-font-size: 13px; -fx-font-weight: bold;");
            bar.getChildren().add(lName);
        }
        if (!phone.isEmpty()) {
            Label lPhone = new Label("📞 " + phone);
            lPhone.setStyle("-fx-text-fill: #D1E8FF; -fx-font-size: 12px;");
            bar.getChildren().add(lPhone);
        }
        if (!email.isEmpty()) {
            Label lEmail = new Label("✉️ " + email);
            lEmail.setStyle("-fx-text-fill: #D1E8FF; -fx-font-size: 12px;");
            bar.getChildren().add(lEmail);
        }
        if (!address.isEmpty()) {
            Label lAddr = new Label("📍 " + address);
            lAddr.setStyle("-fx-text-fill: #D1E8FF; -fx-font-size: 12px;");
            bar.getChildren().add(lAddr);
        }
        return bar;
    }

    /** Reconstruye el header con los datos actuales del .env */
    private void refreshBizHeader() {
        bizHeader.getChildren().clear();
        HBox updated = buildBizHeader();
        bizHeader.getChildren().addAll(updated.getChildren());
    }

    // ── Sidebar ───────────────────────────────────────────────────────────────

    private VBox buildSidebar() {
        VBox sidebar = new VBox(6);
        sidebar.getStyleClass().add("sidebar");
        sidebar.setPadding(new Insets(28, 16, 28, 16));

        // Logo + título
        HBox logoRow = new HBox(8);
        logoRow.setAlignment(Pos.CENTER_LEFT);
        Label logoTxt = new Label("MF Agent");
        logoTxt.getStyleClass().add("nav-title");
        logoRow.getChildren().add(logoTxt);

        // Usuario activo
        String roleIcon = session.isAdmin() ? "👑" : "🛒";
        Label userLbl = new Label(roleIcon + "  " + session.getUsername() + "  ·  " + session.getProfileName());
        userLbl.setStyle("-fx-text-fill: #6B7280; -fx-font-size: 11px; -fx-padding: 0 0 14 0;");
        userLbl.setWrapText(true);

        sidebar.getChildren().addAll(logoRow, userLbl);

        // Botones de navegación
        for (String[] item : new String[][]{
                {"🏠", "Dashboard"},
                {"📋", "Inventario"},
                {"🛒", "Ventas"},
                {"⚠️", "Stock Bajo"}
        }) {
            Button btn = navButton(item[0] + "  " + item[1], item[1]);
            sidebar.getChildren().add(btn);
            if ("Dashboard".equals(item[1])) setActiveNav(btn);
        }

        Region spacer = new Region();
        VBox.setVgrow(spacer, Priority.ALWAYS);
        sidebar.getChildren().add(spacer);

        // WhatsApp
        Label waSection = sectionLabel("WHATSAPP");
        Button btnWa = new Button("📱  WhatsApp");
        btnWa.getStyleClass().add("btn-whatsapp");
        btnWa.setMaxWidth(Double.MAX_VALUE);
        btnWa.setOnAction(e -> openWhatsApp());
        sidebar.getChildren().addAll(waSection, btnWa);

        // Configuración (solo admin)
        if (session.isAdmin()) {
            Label cfgSection = sectionLabel("CONFIGURACIÓN");
            sidebar.getChildren().add(cfgSection);
            for (String[] item : new String[][]{
                    {"🖼️", "Logo Empresa"},
                    {"🏢", "Datos Empresa"},
                    {"📚", "Manuales"},
                    {"👨\u200D💼", "Asesores"},
                    {"⚙️", "Config Bot"},
                    {"✍️", "Firmas PDF"},
                    {"👥", "Usuarios"}
            }) {
                Button btn = new Button(item[0] + "  " + item[1]);
                btn.getStyleClass().add("btn-primary");
                btn.setMaxWidth(Double.MAX_VALUE);
                final String action = item[1];
                btn.setOnAction(e -> handleConfigAction(action));
                sidebar.getChildren().add(btn);
            }
        }

        // Cerrar sesión
        Button btnLogout = new Button("🚪  Cerrar Sesión");
        btnLogout.getStyleClass().add("btn-danger");
        btnLogout.setMaxWidth(Double.MAX_VALUE);
        btnLogout.setOnAction(e -> { if (onLogout != null) onLogout.run(); });
        sidebar.getChildren().add(btnLogout);

        return sidebar;
    }

    private Button navButton(String text, String page) {
        Button btn = new Button(text);
        btn.getStyleClass().add("nav-btn");
        btn.setMaxWidth(Double.MAX_VALUE);
        btn.setOnAction(e -> {
            setActiveNav(btn);
            showPage(page);
        });
        return btn;
    }

    private void setActiveNav(Button btn) {
        if (activeNavBtn != null) activeNavBtn.getStyleClass().remove("active");
        activeNavBtn = btn;
        btn.getStyleClass().add("active");
    }

    private Label sectionLabel(String text) {
        Label lbl = new Label(text);
        lbl.setStyle("-fx-text-fill: #6B7280; -fx-font-size: 10px; -fx-font-weight: bold; " +
                "-fx-padding: 8 8 2 8; -fx-letter-spacing: 1px;");
        return lbl;
    }

    // ── Navegación ────────────────────────────────────────────────────────────

    private void showPage(String page) {
        dashboardView.getRoot().setVisible(false);
        inventoryView.getRoot().setVisible(false);
        salesView.getRoot().setVisible(false);
        advisorsView.getRoot().setVisible(false);
        manualsView.getRoot().setVisible(false);
        botConfigView.getRoot().setVisible(false);
        usersView.getRoot().setVisible(false);

        switch (page) {
            case "Dashboard"  -> { dashboardView.getRoot().setVisible(true); dashboardView.refresh(); }
            case "Inventario" -> { inventoryView.getRoot().setVisible(true); inventoryView.load(); }
            case "Ventas"     -> { salesView.getRoot().setVisible(true); salesView.load(); }
            case "Stock Bajo" -> { inventoryView.getRoot().setVisible(true); inventoryView.loadLowStock(); }
            case "Asesores"   -> { advisorsView.getRoot().setVisible(true); advisorsView.load(); }
            case "Manuales"   -> manualsView.getRoot().setVisible(true);
            case "Config Bot" -> { botConfigView.getRoot().setVisible(true); botConfigView.load(); }
            case "Usuarios"   -> { usersView.getRoot().setVisible(true); usersView.load(); }
        }
    }

    // ── Acciones de configuración ─────────────────────────────────────────────

    private void pickLogo() {
        javafx.stage.FileChooser fc = new javafx.stage.FileChooser();
        fc.setTitle("Seleccionar logo de empresa");
        fc.getExtensionFilters().add(
                new javafx.stage.FileChooser.ExtensionFilter("Imágenes", "*.png", "*.jpg", "*.jpeg", "*.gif"));
        java.io.File file = fc.showOpenDialog(root.getScene().getWindow());
        if (file != null) {
            com.mfagent.util.EnvConfig.set("WATERMARK_IMAGE", file.getAbsolutePath());
            new Alert(Alert.AlertType.INFORMATION, "Logo actualizado:\n" + file.getAbsolutePath()).show();
        }
    }

    private void openWhatsApp() {
        if (waDialog == null)
            waDialog = new WhatsAppDialog(root.getScene().getWindow(), session.isAdmin(), bridgeManager);
        waDialog.show();
    }

    private void handleConfigAction(String action) {
        switch (action) {
            case "Datos Empresa" -> { new BusinessDataDialog(root.getScene().getWindow()).showAndWait(); refreshBizHeader(); }
            case "Firmas PDF"    -> new FirmasDialog(root.getScene().getWindow()).show();
            case "Manuales"     -> showPage("Manuales");
            case "Asesores"     -> showPage("Asesores");
            case "Config Bot"   -> showPage("Config Bot");
            case "Logo Empresa" -> pickLogo();
            case "Usuarios"     -> showPage("Usuarios");
            default -> new Alert(Alert.AlertType.INFORMATION, action + " — próximamente").show();
        }
    }

    // ── Ciclo de vida ─────────────────────────────────────────────────────────

    public void start() {
        dashboardView.refresh();
        scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "auto-refresh");
            t.setDaemon(true);
            return t;
        });
        scheduler.scheduleAtFixedRate(
                () -> Platform.runLater(() -> dashboardView.refresh()),
                30, 30, TimeUnit.SECONDS
        );
    }

    public void stop() {
        if (scheduler != null) scheduler.shutdownNow();
    }

    public BorderPane getRoot() { return root; }

    public void setOnLogout(Runnable handler) { this.onLogout = handler; }

    public void setFirestoreSync(FirestoreSync sync) {
        salesView.setFirestoreSync(sync);
    }

    public void refreshInventory() {
        inventoryView.load();
        dashboardView.refresh();
    }

    public void refreshSales() {
        salesView.load();
        dashboardView.refresh();
    }

    public void refreshAll() {
        inventoryView.load();
        salesView.load();
        dashboardView.refresh();
    }
}
