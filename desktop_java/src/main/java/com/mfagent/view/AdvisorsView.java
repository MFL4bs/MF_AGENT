package com.mfagent.view;

import com.mfagent.model.Session;
import com.mfagent.service.BotService;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.beans.property.ReadOnlyObjectWrapper;
import javafx.scene.control.*;
import javafx.scene.layout.*;

import java.util.*;

/**
 * Vista de Asesores — equivalente al panel de asesores en app.py.
 * Permite agregar/eliminar asesores (nombre + teléfono).
 */
public class AdvisorsView {

    private final Session session;
    private final BotService botService;
    private final BorderPane root;

    private TableView<Map<String, Object>> table;
    private ObservableList<Map<String, Object>> items;

    public AdvisorsView(Session session, BotService botService) {
        this.session    = session;
        this.botService = botService;
        this.root       = new BorderPane();
        root.getStyleClass().add("content-area");
        build();
    }

    private void build() {
        // Título
        Label title = new Label("👨‍💼  Asesores");
        title.getStyleClass().add("section-title");
        BorderPane.setMargin(title, new Insets(0, 0, 12, 0));
        root.setTop(title);

        // Tabla
        table = new TableView<>();
        table.setColumnResizePolicy(TableView.CONSTRAINED_RESIZE_POLICY);

        TableColumn<Map<String, Object>, Object> colName = new TableColumn<>("Nombre");
        colName.setCellValueFactory(cd -> new ReadOnlyObjectWrapper<>(cd.getValue().get("name")));

        TableColumn<Map<String, Object>, Object> colPhone = new TableColumn<>("Teléfono");
        colPhone.setCellValueFactory(cd -> new ReadOnlyObjectWrapper<>(cd.getValue().get("phone")));

        table.getColumns().addAll(colName, colPhone);
        items = FXCollections.observableArrayList();
        table.setItems(items);

        root.setCenter(table);

        // Barra inferior: formulario + botones
        if (session.isAdmin()) {
            root.setBottom(buildForm());
        }

        load();
    }

    private HBox buildForm() {
        TextField tfName  = new TextField();
        tfName.setPromptText("Nombre del asesor");
        tfName.setPrefWidth(200);

        TextField tfPhone = new TextField();
        tfPhone.setPromptText("+52 55 1234 5678");
        tfPhone.setPrefWidth(180);

        Button btnAdd = new Button("➕  Agregar");
        btnAdd.getStyleClass().add("btn-success");
        btnAdd.setOnAction(e -> {
            String name  = tfName.getText().trim();
            String phone = tfPhone.getText().trim();
            if (name.isEmpty() || phone.isEmpty()) {
                new Alert(Alert.AlertType.WARNING, "Nombre y teléfono son requeridos.").show();
                return;
            }
            Map<String, Object> advisor = new LinkedHashMap<>();
            advisor.put("name", name);
            advisor.put("phone", phone);
            List<Map<String, Object>> all = botService.loadAdvisors();
            all.add(advisor);
            botService.saveAdvisors(all);
            tfName.clear(); tfPhone.clear();
            load();
        });

        Button btnDel = new Button("🗑  Eliminar");
        btnDel.getStyleClass().add("btn-danger");
        btnDel.setOnAction(e -> {
            Map<String, Object> sel = table.getSelectionModel().getSelectedItem();
            if (sel == null) { new Alert(Alert.AlertType.WARNING, "Selecciona un asesor.").show(); return; }
            List<Map<String, Object>> all = botService.loadAdvisors();
            all.removeIf(a -> Objects.equals(a.get("name"), sel.get("name"))
                           && Objects.equals(a.get("phone"), sel.get("phone")));
            botService.saveAdvisors(all);
            load();
        });

        HBox bar = new HBox(10, new Label("Nombre:"), tfName, new Label("Teléfono:"), tfPhone, btnAdd, btnDel);
        bar.setAlignment(Pos.CENTER_LEFT);
        bar.setPadding(new Insets(12, 0, 0, 0));
        return bar;
    }

    public void load() {
        items.setAll(botService.loadAdvisors());
    }

    public BorderPane getRoot() { return root; }
}
