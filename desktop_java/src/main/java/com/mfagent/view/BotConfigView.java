package com.mfagent.view;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import com.mfagent.model.Session;
import com.mfagent.service.CouponService;
import com.mfagent.service.ProfilePaths;
import javafx.beans.property.ReadOnlyObjectWrapper;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.layout.*;

import java.nio.file.*;
import java.time.LocalDate;
import java.util.*;

/**
 * Vista de configuración del bot.
 * Tab 1 — Mensajes del bot (bienvenida, menú, despedida, asesor)
 * Tab 2 — Cupones de descuento para ventas por WhatsApp
 */
public class BotConfigView {

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    private final Session session;
    private final CouponService couponService;
    private final BorderPane root;

    // Tab cupones
    private TableView<Map<String, Object>> couponTable;
    private ObservableList<Map<String, Object>> couponItems;

    // Tab mensajes
    private TextArea taBienvenida, taMenu, taDespedida, taAsesor, taCupon;

    public BotConfigView(Session session) {
        this.session       = session;
        this.couponService = new CouponService(session.getProfileId());
        this.root          = new BorderPane();
        root.getStyleClass().add("content-area");
        build();
    }

    private void build() {
        Label title = new Label("⚙️  Configuración del Bot");
        title.getStyleClass().add("section-title");
        BorderPane.setMargin(title, new Insets(0, 0, 12, 0));
        root.setTop(title);

        TabPane tabs = new TabPane();
        tabs.setTabClosingPolicy(TabPane.TabClosingPolicy.UNAVAILABLE);
        tabs.getTabs().addAll(buildMensajesTab(), buildCuponesTab());
        root.setCenter(tabs);
    }

    // ── Tab 1: Mensajes ───────────────────────────────────────────────────────

    private Tab buildMensajesTab() {
        Tab tab = new Tab("💬  Mensajes del Bot");

        VBox content = new VBox(14);
        content.setPadding(new Insets(16));

        taBienvenida = msgArea("Hola! Bienvenido. En que puedo ayudarte?\n\n1. Ver catalogo\n2. Hablar con un asesor\n\nEscribe el numero de tu opcion.");
        taBienvenida.setPrefRowCount(4);

        taMenu = msgArea("--- CATALOGO DE PRODUCTOS ---\n\nEscribe el numero del producto que te interesa.\nCuando termines escribe *listo*.\n0. Volver al menu");
        taMenu.setPrefRowCount(4);

        taCupon = msgArea("Tienes un *cupon de descuento*?\nEscribe el codigo o escribe *no* para continuar.");
        taCupon.setPrefRowCount(2);

        taAsesor = msgArea("Con gusto te conecto con un asesor.\n\nPor favor enviame tu nombre y numero de celular:\nEjemplo: Juan Perez 3001234567");
        taAsesor.setPrefRowCount(3);

        taDespedida = msgArea("Gracias! Un asesor te contactara pronto.\n\nEscribe 0 si necesitas algo mas.");
        taDespedida.setPrefRowCount(2);

        boolean editable = session.isAdmin();
        taBienvenida.setEditable(editable);
        taMenu.setEditable(editable);
        taCupon.setEditable(editable);
        taAsesor.setEditable(editable);
        taDespedida.setEditable(editable);

        content.getChildren().addAll(
            fieldRow("Bienvenida / Menú principal:", taBienvenida),
            fieldRow("Encabezado catálogo:", taMenu),
            fieldRow("Pregunta cupón:", taCupon),
            fieldRow("Transferencia a asesor:", taAsesor),
            fieldRow("Despedida:", taDespedida)
        );

        if (editable) {
            Button btnSave = new Button("💾  Guardar mensajes");
            btnSave.getStyleClass().add("btn-success");
            btnSave.setOnAction(e -> saveMensajes());
            HBox bar = new HBox(btnSave);
            bar.setAlignment(Pos.CENTER_RIGHT);
            content.getChildren().add(bar);
        }

        ScrollPane scroll = new ScrollPane(content);
        scroll.setFitToWidth(true);
        scroll.setStyle("-fx-background-color: transparent;");
        tab.setContent(scroll);
        return tab;
    }

    private TextArea msgArea(String defaultText) {
        TextArea ta = new TextArea(defaultText);
        ta.setWrapText(true);
        ta.setStyle("-fx-font-family: 'Consolas', monospace; -fx-font-size: 12px;");
        return ta;
    }

    private VBox fieldRow(String label, TextArea ta) {
        Label lbl = new Label(label);
        lbl.setStyle("-fx-font-weight: bold; -fx-text-fill: #1F2937;");
        VBox box = new VBox(4, lbl, ta);
        return box;
    }

    private void saveMensajes() {
        Map<String, Object> cfg = loadConfig();
        cfg.put("msg_bienvenida", taBienvenida.getText().trim());
        cfg.put("msg_menu",       taMenu.getText().trim());
        cfg.put("msg_cupon",      taCupon.getText().trim());
        cfg.put("msg_asesor",     taAsesor.getText().trim());
        cfg.put("msg_despedida",  taDespedida.getText().trim());
        saveConfig(cfg);
        new Alert(Alert.AlertType.INFORMATION, "✅ Mensajes guardados.").show();
    }

    // ── Tab 2: Cupones ────────────────────────────────────────────────────────

    private Tab buildCuponesTab() {
        Tab tab = new Tab("🎟  Cupones WhatsApp");

        BorderPane pane = new BorderPane();
        pane.setPadding(new Insets(16));

        couponTable = new TableView<>();
        couponTable.setColumnResizePolicy(TableView.CONSTRAINED_RESIZE_POLICY);
        addCouponCol("Código",     "code");
        addCouponCol("Tipo",       "type");
        addCouponCol("Valor",      "value");
        addCouponCol("Mín. total", "min_total");
        addCouponCol("Usos máx.",  "max_uses");
        addCouponCol("Usos act.",  "uses");
        addCouponCol("Vence",      "expires_at");
        addCouponCol("Activo",     "active");

        couponItems = FXCollections.observableArrayList();
        couponTable.setItems(couponItems);
        pane.setCenter(couponTable);

        if (session.isAdmin()) pane.setBottom(buildCouponForm());

        tab.setContent(pane);
        return tab;
    }

    private void addCouponCol(String header, String key) {
        TableColumn<Map<String, Object>, Object> col = new TableColumn<>(header);
        col.setCellValueFactory(cd -> new ReadOnlyObjectWrapper<>(cd.getValue().get(key)));
        couponTable.getColumns().add(col);
    }

    private VBox buildCouponForm() {
        TextField tfCode    = new TextField(); tfCode.setPromptText("Código (ej: PROMO10)"); tfCode.setPrefWidth(140);
        ComboBox<String> cbType = new ComboBox<>(FXCollections.observableArrayList("percent", "fixed"));
        cbType.setValue("percent");
        TextField tfValue   = new TextField(); tfValue.setPromptText("Valor"); tfValue.setPrefWidth(80);
        TextField tfMin     = new TextField("0"); tfMin.setPromptText("Mín. total"); tfMin.setPrefWidth(90);
        TextField tfMax     = new TextField("100"); tfMax.setPromptText("Usos máx."); tfMax.setPrefWidth(80);
        DatePicker dpExp    = new DatePicker(LocalDate.now().plusMonths(1));

        Button btnAdd = new Button("➕  Crear");
        btnAdd.getStyleClass().add("btn-success");
        btnAdd.setOnAction(e -> {
            String code = tfCode.getText().trim().toUpperCase();
            String valStr = tfValue.getText().trim();
            if (code.isEmpty() || valStr.isEmpty()) {
                new Alert(Alert.AlertType.WARNING, "Código y valor son requeridos.").show(); return;
            }
            double value, minTotal;
            int maxUses;
            try {
                value    = Double.parseDouble(valStr);
                minTotal = Double.parseDouble(tfMin.getText().trim());
                maxUses  = Integer.parseInt(tfMax.getText().trim());
            } catch (NumberFormatException ex) {
                new Alert(Alert.AlertType.WARNING, "Valor, mínimo y usos deben ser numéricos.").show(); return;
            }
            Map<String, Object> r = couponService.add(code, cbType.getValue(), value, minTotal, maxUses,
                    dpExp.getValue() != null ? dpExp.getValue().toString() : "");
            if (Boolean.TRUE.equals(r.get("ok"))) {
                tfCode.clear(); tfValue.clear();
                loadCoupons();
            } else {
                new Alert(Alert.AlertType.WARNING, r.get("msg").toString()).show();
            }
        });

        Button btnToggle = new Button("✅/❌  Activar");
        btnToggle.getStyleClass().add("btn-edit");
        btnToggle.setOnAction(e -> {
            Map<String, Object> sel = couponTable.getSelectionModel().getSelectedItem();
            if (sel == null) { new Alert(Alert.AlertType.WARNING, "Selecciona un cupón.").show(); return; }
            couponService.toggle(sel.get("code").toString());
            loadCoupons();
        });

        Button btnDel = new Button("🗑  Eliminar");
        btnDel.getStyleClass().add("btn-danger");
        btnDel.setOnAction(e -> {
            Map<String, Object> sel = couponTable.getSelectionModel().getSelectedItem();
            if (sel == null) { new Alert(Alert.AlertType.WARNING, "Selecciona un cupón.").show(); return; }
            couponService.delete(sel.get("code").toString());
            loadCoupons();
        });

        HBox row1 = new HBox(10, new Label("Código:"), tfCode,
                new Label("Tipo:"), cbType, new Label("Valor:"), tfValue,
                new Label("Mín. $:"), tfMin);
        row1.setAlignment(Pos.CENTER_LEFT);

        HBox row2 = new HBox(10, new Label("Usos máx:"), tfMax,
                new Label("Vence:"), dpExp, btnAdd, btnToggle, btnDel);
        row2.setAlignment(Pos.CENTER_LEFT);

        VBox form = new VBox(8, row1, row2);
        form.setPadding(new Insets(12, 0, 0, 0));
        return form;
    }

    // ── Config JSON ───────────────────────────────────────────────────────────

    private Path configFile() {
        return ProfilePaths.dataDir(session.getProfileId()).resolve("bot_config.json");
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> loadConfig() {
        Path f = configFile();
        if (!Files.exists(f)) return new LinkedHashMap<>();
        try {
            return GSON.fromJson(Files.readString(f),
                    new TypeToken<Map<String, Object>>(){}.getType());
        } catch (Exception e) { return new LinkedHashMap<>(); }
    }

    private void saveConfig(Map<String, Object> cfg) {
        try {
            Files.createDirectories(configFile().getParent());
            Files.writeString(configFile(), GSON.toJson(cfg));
        } catch (Exception e) { System.err.println("[BotConfig] " + e.getMessage()); }
    }

    private void loadMensajes() {
        Map<String, Object> cfg = loadConfig();
        setIfNotEmpty(taBienvenida, cfg, "msg_bienvenida");
        setIfNotEmpty(taMenu,       cfg, "msg_menu");
        setIfNotEmpty(taCupon,      cfg, "msg_cupon");
        setIfNotEmpty(taAsesor,     cfg, "msg_asesor");
        setIfNotEmpty(taDespedida,  cfg, "msg_despedida");
    }

    private void setIfNotEmpty(TextArea ta, Map<String, Object> cfg, String key) {
        Object v = cfg.get(key);
        if (v != null && !v.toString().isEmpty()) ta.setText(v.toString());
    }

    private void loadCoupons() {
        couponItems.setAll(couponService.loadAll());
    }

    public void load() {
        loadMensajes();
        loadCoupons();
    }

    public BorderPane getRoot() { return root; }
}
