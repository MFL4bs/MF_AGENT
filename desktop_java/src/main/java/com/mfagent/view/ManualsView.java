package com.mfagent.view;

import com.mfagent.model.Session;
import com.mfagent.service.BotService;
import javafx.collections.FXCollections;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.layout.*;

/**
 * Vista de Manuales del bot — equivalente al panel de manuales en app.py.
 * Lista de archivos .txt por perfil con editor de texto integrado.
 */
public class ManualsView {

    private final Session session;
    private final BotService botService;
    private final BorderPane root;

    private ListView<String> listView;
    private TextArea editor;
    private String currentManual;

    public ManualsView(Session session, BotService botService) {
        this.session    = session;
        this.botService = botService;
        this.root       = new BorderPane();
        root.getStyleClass().add("content-area");
        build();
    }

    private void build() {
        Label title = new Label("📚  Manuales del Bot");
        title.getStyleClass().add("section-title");
        BorderPane.setMargin(title, new Insets(0, 0, 12, 0));
        root.setTop(title);

        // Lista de manuales
        listView = new ListView<>();
        listView.setPrefWidth(200);
        listView.getSelectionModel().selectedItemProperty().addListener((obs, old, name) -> {
            if (name != null) loadManual(name);
        });

        // Editor
        editor = new TextArea();
        editor.setWrapText(true);
        editor.setPromptText("Selecciona o crea un manual...");
        editor.setEditable(session.isAdmin());

        SplitPane split = new SplitPane(listView, editor);
        split.setDividerPositions(0.25);
        root.setCenter(split);

        if (session.isAdmin()) root.setBottom(buildToolbar());

        loadList();
    }

    private HBox buildToolbar() {
        TextField tfName = new TextField();
        tfName.setPromptText("Nombre del manual");
        tfName.setPrefWidth(180);

        Button btnNew = new Button("➕  Nuevo");
        btnNew.getStyleClass().add("btn-primary");
        btnNew.setOnAction(e -> {
            String name = tfName.getText().trim();
            if (name.isEmpty()) { new Alert(Alert.AlertType.WARNING, "Escribe un nombre.").show(); return; }
            botService.saveManual(name, "");
            tfName.clear();
            loadList();
            listView.getSelectionModel().select(name);
        });

        Button btnSave = new Button("💾  Guardar");
        btnSave.getStyleClass().add("btn-success");
        btnSave.setOnAction(e -> {
            if (currentManual == null) { new Alert(Alert.AlertType.WARNING, "Selecciona un manual.").show(); return; }
            botService.saveManual(currentManual, editor.getText());
            new Alert(Alert.AlertType.INFORMATION, "Manual guardado.").show();
        });

        Button btnDel = new Button("🗑  Eliminar");
        btnDel.getStyleClass().add("btn-danger");
        btnDel.setOnAction(e -> {
            if (currentManual == null) return;
            botService.saveManual(currentManual, null); // null = borrar
            currentManual = null;
            editor.clear();
            loadList();
        });

        HBox bar = new HBox(10, new Label("Nombre:"), tfName, btnNew, btnSave, btnDel);
        bar.setAlignment(Pos.CENTER_LEFT);
        bar.setPadding(new Insets(12, 0, 0, 0));
        return bar;
    }

    private void loadList() {
        listView.setItems(FXCollections.observableArrayList(botService.listManuals()));
    }

    private void loadManual(String name) {
        currentManual = name;
        editor.setText(botService.loadManual(name));
    }

    public BorderPane getRoot() { return root; }
}
