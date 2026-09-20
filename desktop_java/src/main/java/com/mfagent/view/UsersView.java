package com.mfagent.view;

import com.mfagent.model.Session;
import com.mfagent.service.FirebaseService;
import com.mfagent.service.ProfileService;
import javafx.beans.property.ReadOnlyObjectWrapper;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.layout.*;

import java.util.*;

/**
 * Vista de gestión de usuarios/vendedores — solo admin.
 * Permite crear, ver y eliminar usuarios del perfil activo.
 */
public class UsersView {

    private final Session session;
    private final ProfileService profileService;
    private final BorderPane root;

    private TableView<Map<String, Object>> table;
    private ObservableList<Map<String, Object>> items;

    public UsersView(Session session, ProfileService profileService) {
        this.session        = session;
        this.profileService = profileService;
        this.root           = new BorderPane();
        root.getStyleClass().add("content-area");
        build();
    }

    private void build() {
        Label title = new Label("👥  Usuarios / Vendedores");
        title.getStyleClass().add("section-title");
        BorderPane.setMargin(title, new Insets(0, 0, 12, 0));
        root.setTop(title);

        table = new TableView<>();
        table.setColumnResizePolicy(TableView.CONSTRAINED_RESIZE_POLICY);

        TableColumn<Map<String, Object>, Object> colUser = new TableColumn<>("Usuario");
        colUser.setCellValueFactory(cd -> new ReadOnlyObjectWrapper<>(cd.getValue().get("username")));

        TableColumn<Map<String, Object>, Object> colRole = new TableColumn<>("Rol");
        colRole.setCellValueFactory(cd -> new ReadOnlyObjectWrapper<>(cd.getValue().get("role")));
        colRole.setPrefWidth(100);

        TableColumn<Map<String, Object>, Void> colDel = new TableColumn<>("");
        colDel.setPrefWidth(90);
        colDel.setCellFactory(col -> new TableCell<>() {
            private final Button btn = new Button("🗑  Eliminar");
            {
                btn.getStyleClass().add("btn-danger");
                btn.setOnAction(e -> {
                    Map<String, Object> sel = getTableView().getItems().get(getIndex());
                    String username = Objects.toString(sel.get("username"), "");
                    if (username.equals(session.getUsername())) {
                        new Alert(Alert.AlertType.WARNING, "No puedes eliminar tu propio usuario.").show();
                        return;
                    }
                    deleteUser(username);
                });
            }
            @Override protected void updateItem(Void item, boolean empty) {
                super.updateItem(item, empty);
                setGraphic(empty ? null : btn);
            }
        });

        table.getColumns().addAll(colUser, colRole, colDel);
        items = FXCollections.observableArrayList();
        table.setItems(items);
        root.setCenter(table);
        root.setBottom(buildForm());
    }

    private VBox buildForm() {
        Label formTitle = new Label("Crear nuevo usuario:");
        formTitle.setStyle("-fx-font-weight: bold; -fx-text-fill: #1F2937;");

        TextField tfUser = new TextField();
        tfUser.setPromptText("Nombre de usuario");
        tfUser.setPrefWidth(160);

        PasswordField pfPass = new PasswordField();
        pfPass.setPromptText("Contraseña");
        pfPass.setPrefWidth(160);

        PasswordField pfConfirm = new PasswordField();
        pfConfirm.setPromptText("Confirmar contraseña");
        pfConfirm.setPrefWidth(160);

        ComboBox<String> cbRole = new ComboBox<>(
                FXCollections.observableArrayList("vendedor", "admin"));
        cbRole.setValue("vendedor");

        Button btnAdd = new Button("➕  Crear Usuario");
        btnAdd.getStyleClass().add("btn-success");
        btnAdd.setOnAction(e -> {
            String username = tfUser.getText().strip();
            String pass     = pfPass.getText();
            String confirm  = pfConfirm.getText();
            String role     = cbRole.getValue();

            if (username.isEmpty() || pass.isEmpty()) {
                new Alert(Alert.AlertType.WARNING, "Usuario y contraseña son requeridos.").show();
                return;
            }
            if (!pass.equals(confirm)) {
                new Alert(Alert.AlertType.WARNING, "Las contraseñas no coinciden.").show();
                return;
            }
            // Verificar que no exista
            List<Map<String, Object>> users = getUsers();
            boolean exists = users.stream()
                    .anyMatch(u -> username.equals(u.get("username")));
            if (exists) {
                new Alert(Alert.AlertType.WARNING, "El usuario '" + username + "' ya existe.").show();
                return;
            }

            Map<String, Object> newUser = new LinkedHashMap<>();
            newUser.put("username",      username);
            newUser.put("password_hash", ProfileService.sha256(pass));
            newUser.put("role",          role);
            users.add(newUser);
            saveUsers(users);
            syncUsersToFirebase(users);

            tfUser.clear(); pfPass.clear(); pfConfirm.clear();
            load();
            new Alert(Alert.AlertType.INFORMATION,
                    "✅ Usuario '" + username + "' creado como " + role + ".").show();
        });

        HBox row1 = new HBox(10, new Label("Usuario:"), tfUser,
                new Label("Rol:"), cbRole);
        row1.setAlignment(Pos.CENTER_LEFT);

        HBox row2 = new HBox(10, new Label("Contraseña:"), pfPass,
                new Label("Confirmar:"), pfConfirm, btnAdd);
        row2.setAlignment(Pos.CENTER_LEFT);

        VBox form = new VBox(8, formTitle, row1, row2);
        form.setPadding(new Insets(16, 0, 0, 0));
        return form;
    }

    private void deleteUser(String username) {
        Alert confirm = new Alert(Alert.AlertType.CONFIRMATION,
                "¿Eliminar usuario '" + username + "'?", ButtonType.YES, ButtonType.NO);
        confirm.setHeaderText(null);
        confirm.showAndWait().ifPresent(btn -> {
            if (btn == ButtonType.YES) {
                List<Map<String, Object>> users = getUsers();
                users.removeIf(u -> username.equals(u.get("username")));
                saveUsers(users);
                syncUsersToFirebase(users);
                load();
            }
        });
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> getUsers() {
        Map<String, Object> profile = profileService.getProfile(session.getProfileId());
        if (profile == null) return new ArrayList<>();
        Object raw = profile.get("users");
        if (raw instanceof List<?> l) {
            List<Map<String, Object>> result = new ArrayList<>();
            for (Object o : l) {
                if (o instanceof Map<?, ?> m) {
                    Map<String, Object> u = new LinkedHashMap<>();
                    m.forEach((k, v) -> u.put(k.toString(), v));
                    result.add(u);
                }
            }
            return result;
        }
        return new ArrayList<>();
    }

    private void saveUsers(List<Map<String, Object>> users) {
        List<Map<String, Object>> profiles = profileService.listProfiles();
        for (Map<String, Object> p : profiles) {
            if (session.getProfileId().equals(p.get("id"))) {
                p.put("users", users);
                break;
            }
        }
        // Guardar via ProfileService internamente
        profileService.saveProfiles(profiles);
    }

    public void load() {
        Thread t = new Thread(() -> {
            try {
                var doc = FirebaseService.getDataDb()
                        .collection("profiles")
                        .document(session.getProfileId())
                        .get().get();
                if (doc.exists()) {
                    Object rawUsers = doc.getData().get("users");
                    if (rawUsers instanceof List<?> l) {
                        List<Map<String, Object>> remoteUsers = new ArrayList<>();
                        for (Object o : l) {
                            if (o instanceof Map<?, ?> m) {
                                Map<String, Object> u = new LinkedHashMap<>();
                                m.forEach((k, v) -> u.put(k.toString(), v));
                                remoteUsers.add(u);
                            }
                        }
                        if (!remoteUsers.isEmpty()) saveUsers(remoteUsers);
                    }
                }
            } catch (Exception e) {
                System.err.println("[UsersView] Error cargando desde Firebase: " + e.getMessage());
            }
            javafx.application.Platform.runLater(this::populateTable);
        }, "load-users");
        t.setDaemon(true);
        t.start();
    }

    private void populateTable() {
        List<Map<String, Object>> users = getUsers();
        List<Map<String, Object>> display = new ArrayList<>();
        for (Map<String, Object> u : users) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("username", u.get("username"));
            row.put("role",     u.get("role"));
            display.add(row);
        }
        items.setAll(display);
    }

    private void syncUsersToFirebase(List<Map<String, Object>> users) {
        Thread t = new Thread(() -> {
            try {
                FirebaseService.getDataDb()
                        .collection("profiles")
                        .document(session.getProfileId())
                        .update("users", users)
                        .get();
                System.out.println("[Users] Sincronizado con Firebase: " + users.size() + " usuarios");
            } catch (Exception e) {
                System.err.println("[Users] Error sync Firebase: " + e.getMessage());
            }
        }, "sync-users");
        t.setDaemon(true);
        t.start();
    }

    public BorderPane getRoot() { return root; }
}
