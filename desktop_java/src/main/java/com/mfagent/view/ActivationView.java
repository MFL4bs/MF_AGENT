package com.mfagent.view;

import com.mfagent.model.Session;
import com.mfagent.service.LicenseService;
import com.mfagent.service.ProfileService;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.layout.*;

import java.util.*;
import java.util.function.Consumer;

/**
 * Pantalla de activación de licencia + login.
 *
 * Flujo:
 *  1. Validar .license guardado → si ok → login directo
 *  2. Key nueva → activate() → si perfil sin usuarios → crear admin
 *  3. Perfil existente con usuarios → login normal
 */
public class ActivationView {

    private final VBox root;
    private Consumer<Session> onActivated;

    private VBox stepKey;
    private VBox stepSetupAdmin;
    private VBox stepLogin;

    private TextField  keyField;
    private TextField  userField;
    private PasswordField passField;
    private Label errorLabel;
    private Label loginErrorLabel;
    private Label businessLabel;
    private Label warnLabel;

    // Setup admin
    private PasswordField setupPassField;
    private PasswordField setupConfirmField;
    private Label setupErrorLabel;
    private Label setupBusinessLabel;

    private String profileId;
    private String profileName;
    private String licenseKey;
    private int loginAttempts = 0;

    private final LicenseService licenseService = new LicenseService();
    private final ProfileService profileService = new ProfileService();

    public ActivationView() {
        root = new VBox(24);
        root.setAlignment(Pos.CENTER);
        root.setPadding(new Insets(40));
        root.setStyle("-fx-background-color: #F5F0EB;");

        buildStepKey();
        buildStepSetupAdmin();
        buildStepLogin();
        root.getChildren().addAll(buildHeader(), stepKey, stepSetupAdmin, stepLogin);

        Thread t = new Thread(this::tryAutoLogin, "auto-login");
        t.setDaemon(true);
        t.start();
    }

    // ── Auto-login ────────────────────────────────────────────────────────────

    private void tryAutoLogin() {
        LicenseService.LicenseResult result = licenseService.validate();
        Platform.runLater(() -> {
            if (result.ok) {
                profileId  = result.profileId;
                licenseKey = licenseService.loadLocalKey();
                loadProfileName();
                if (result.warn && result.daysLeft != null)
                    showWarn("⚠️ Tu licencia vence en " + result.daysLeft + " días.");
                showLoginStep();
            } else {
                show(stepKey);
            }
        });
    }

    private void loadProfileName() {
        if (profileId == null) return;
        var profile = profileService.getProfile(profileId);
        profileName = profile != null
                ? profile.getOrDefault("name", profileId).toString()
                : profileId;
    }

    // ── UI ────────────────────────────────────────────────────────────────────

    private VBox buildHeader() {
        VBox header = new VBox(6);
        header.setAlignment(Pos.CENTER);
        Label title = new Label("MF Agent");
        title.setStyle("-fx-font-size: 28px; -fx-font-weight: bold; -fx-text-fill: #1F2937;");
        Label subtitle = new Label("Sistema de gestión comercial");
        subtitle.setStyle("-fx-font-size: 13px; -fx-text-fill: #6B7280;");
        header.getChildren().addAll(title, subtitle);
        return header;
    }

    private void buildStepKey() {
        stepKey = new VBox(14);
        stepKey.setAlignment(Pos.CENTER);
        stepKey.setMaxWidth(380);
        hide(stepKey);

        Label lbl = new Label("Ingresa tu clave de licencia:");
        lbl.setStyle("-fx-font-size: 14px; -fx-text-fill: #1F2937; -fx-font-weight: bold;");

        keyField = new TextField();
        keyField.setPromptText("XXXX-XXXX-XXXX-XXXX");
        keyField.getStyleClass().add("text-field");
        keyField.setMaxWidth(320);

        Button btnActivate = new Button("Activar");
        btnActivate.getStyleClass().add("btn-primary");
        btnActivate.setOnAction(e -> validateKey(btnActivate));
        keyField.setOnAction(e -> validateKey(btnActivate));

        errorLabel = new Label();
        errorLabel.setStyle("-fx-text-fill: #DC2626; -fx-font-size: 12px;");
        errorLabel.setVisible(false);

        stepKey.getChildren().addAll(lbl, keyField, btnActivate, errorLabel);
    }

    private void buildStepSetupAdmin() {
        stepSetupAdmin = new VBox(14);
        stepSetupAdmin.setAlignment(Pos.CENTER);
        stepSetupAdmin.setMaxWidth(380);
        hide(stepSetupAdmin);

        setupBusinessLabel = new Label();
        setupBusinessLabel.setStyle("-fx-font-size: 16px; -fx-font-weight: bold; -fx-text-fill: #1B6CA8;");

        Label info = new Label("¡Bienvenido! Es la primera vez que activas esta licencia.\nCrea la contraseña del administrador:");
        info.setStyle("-fx-text-fill: #6B7280; -fx-font-size: 12px;");
        info.setWrapText(true);

        setupPassField = new PasswordField();
        setupPassField.setPromptText("Contraseña del admin");
        setupPassField.getStyleClass().add("text-field");
        setupPassField.setMaxWidth(320);

        setupConfirmField = new PasswordField();
        setupConfirmField.setPromptText("Confirmar contraseña");
        setupConfirmField.getStyleClass().add("text-field");
        setupConfirmField.setMaxWidth(320);

        setupErrorLabel = new Label();
        setupErrorLabel.setStyle("-fx-text-fill: #DC2626; -fx-font-size: 12px;");
        setupErrorLabel.setVisible(false);

        Button btnCreate = new Button("✅  Crear administrador");
        btnCreate.getStyleClass().add("btn-success");
        btnCreate.setOnAction(e -> createAdminUser());
        setupConfirmField.setOnAction(e -> createAdminUser());

        stepSetupAdmin.getChildren().addAll(
                setupBusinessLabel, info, setupPassField, setupConfirmField,
                btnCreate, setupErrorLabel);
    }

    private void buildStepLogin() {
        stepLogin = new VBox(14);
        stepLogin.setAlignment(Pos.CENTER);
        stepLogin.setMaxWidth(380);
        hide(stepLogin);

        businessLabel = new Label();
        businessLabel.setStyle("-fx-font-size: 16px; -fx-font-weight: bold; -fx-text-fill: #1B6CA8;");

        warnLabel = new Label();
        warnLabel.setStyle("-fx-text-fill: #D97706; -fx-font-size: 12px;");
        warnLabel.setVisible(false);

        Label lbl = new Label("Inicia sesión:");
        lbl.setStyle("-fx-font-size: 14px; -fx-text-fill: #1F2937; -fx-font-weight: bold;");

        userField = new TextField();
        userField.setPromptText("Usuario");
        userField.getStyleClass().add("text-field");
        userField.setMaxWidth(320);

        passField = new PasswordField();
        passField.setPromptText("Contraseña");
        passField.getStyleClass().add("text-field");
        passField.setMaxWidth(320);

        Button btnLogin = new Button("Entrar");
        btnLogin.getStyleClass().add("btn-primary");
        btnLogin.setOnAction(e -> doLogin());
        passField.setOnAction(e -> doLogin());

        Button btnChangeKey = new Button("Cambiar licencia");
        btnChangeKey.setStyle("-fx-background-color: transparent; -fx-text-fill: #6B7280; " +
                "-fx-font-size: 11px; -fx-cursor: hand; -fx-underline: true;");
        btnChangeKey.setOnAction(e -> show(stepKey));

        loginErrorLabel = new Label();
        loginErrorLabel.setStyle("-fx-text-fill: #DC2626; -fx-font-size: 12px;");
        loginErrorLabel.setVisible(false);

        stepLogin.getChildren().addAll(businessLabel, warnLabel, lbl, userField, passField,
                btnLogin, loginErrorLabel, btnChangeKey);
    }

    // ── Lógica ────────────────────────────────────────────────────────────────

    private void validateKey(Button btnActivate) {
        String key = keyField.getText().strip();
        if (key.isEmpty()) { showKeyError("Ingresa una clave de licencia."); return; }

        btnActivate.setDisable(true);
        btnActivate.setText("Validando...");
        errorLabel.setVisible(false);

        Thread t = new Thread(() -> {
            LicenseService.LicenseResult result = licenseService.activate(key);
            Platform.runLater(() -> {
                btnActivate.setDisable(false);
                btnActivate.setText("Activar");
                if (!result.ok) { showKeyError(result.message); return; }

                licenseKey = key;
                profileId  = result.profileId;

                if (result.warn && result.daysLeft != null)
                    showWarn("⚠️ Tu licencia vence en " + result.daysLeft + " días.");

                // Perfil ya existe localmente con usuarios → login directo
                if (profileHasUsers()) {
                    loadProfileName();
                    showLoginStep();
                    return;
                }

                // Perfil nuevo o sin usuarios → restaurar desde Firestore
                showKeyError("Restaurando datos desde la nube...");
                errorLabel.setStyle("-fx-text-fill: #1B6CA8; -fx-font-size: 12px;");
                errorLabel.setVisible(true);

                Thread r = new Thread(() -> {
                    ProfileService.RestoreResult restore =
                            profileService.restoreFromFirestore(key, profileId);
                    Platform.runLater(() -> {
                        errorLabel.setStyle("-fx-text-fill: #DC2626; -fx-font-size: 12px;");
                        errorLabel.setVisible(false);
                        profileName = restore.ok ? restore.profileName : profileId;

                        if (restore.ok && profileHasUsers()) {
                            // Firestore tenía usuarios → login normal
                            showLoginStep();
                        } else {
                            // Negocio nuevo sin usuarios → crear admin
                            showSetupAdmin();
                        }
                    });
                }, "restore-profile");
                r.setDaemon(true);
                r.start();
            });
        }, "activate-key");
        t.setDaemon(true);
        t.start();
    }

    private void createAdminUser() {
        String pass    = setupPassField.getText();
        String confirm = setupConfirmField.getText();

        if (pass.isEmpty()) {
            setupErrorLabel.setText("La contraseña no puede estar vacía.");
            setupErrorLabel.setVisible(true);
            return;
        }
        if (!pass.equals(confirm)) {
            setupErrorLabel.setText("Las contraseñas no coinciden.");
            setupErrorLabel.setVisible(true);
            return;
        }

        // Crear perfil con solo el usuario admin
        Map<String, Object> adminUser = new LinkedHashMap<>();
        adminUser.put("username",      "admin");
        adminUser.put("password_hash", ProfileService.sha256(pass));
        adminUser.put("role",          "admin");

        List<Map<String, Object>> profiles = profileService.listProfiles();
        profiles.removeIf(p -> profileId.equals(p.get("id")));
        Map<String, Object> newProfile = new LinkedHashMap<>();
        newProfile.put("id",    profileId);
        newProfile.put("name",  profileName != null ? profileName : profileId);
        newProfile.put("users", List.of(adminUser));
        profiles.add(newProfile);
        profileService.saveProfiles(profiles);

        // Ir directo al login con usuario pre-llenado
        showLoginStep();
        userField.setText("admin");
        passField.requestFocus();
    }

    private void doLogin() {
        String username = userField.getText().strip();
        String password = passField.getText();
        if (username.isEmpty() || password.isEmpty()) {
            showLoginError("Completa usuario y contraseña."); return;
        }

        Session session = profileService.authenticate(profileId, username, password);
        if (session == null) {
            loginAttempts++;
            if (loginAttempts >= 3) { Platform.exit(); return; }
            showLoginError("Credenciales incorrectas. Intento " + loginAttempts + "/3.");
            passField.clear();
            return;
        }

        Session full = new Session(session.getUsername(), session.getRole(),
                session.getProfileId(), session.getProfileName(), licenseKey);
        if (onActivated != null) onActivated.accept(full);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private boolean profileHasUsers() {
        var profile = profileService.getProfile(profileId);
        if (profile == null) return false;
        Object raw = profile.get("users");
        return raw instanceof List<?> l && !l.isEmpty();
    }

    private void showLoginStep() {
        show(stepLogin);
        businessLabel.setText("🏢  " + (profileName != null ? profileName : profileId));
        loginErrorLabel.setVisible(false);
        userField.clear();
        passField.clear();
    }

    private void showSetupAdmin() {
        show(stepSetupAdmin);
        setupBusinessLabel.setText("🏢  " + (profileName != null ? profileName : profileId));
        setupErrorLabel.setVisible(false);
        setupPassField.clear();
        setupConfirmField.clear();
    }

    private void show(VBox step) {
        for (VBox s : new VBox[]{stepKey, stepSetupAdmin, stepLogin}) {
            s.setVisible(s == step);
            s.setManaged(s == step);
        }
    }

    private void showKeyError(String msg) {
        errorLabel.setText(msg);
        errorLabel.setVisible(true);
    }

    private void showLoginError(String msg) {
        loginErrorLabel.setText(msg);
        loginErrorLabel.setVisible(true);
    }

    private void showWarn(String msg) {
        warnLabel.setText(msg);
        warnLabel.setVisible(true);
    }

    private void hide(VBox v) { v.setVisible(false); v.setManaged(false); }

    public VBox getRoot() { return root; }
    public void setOnActivated(Consumer<Session> handler) { this.onActivated = handler; }
}
