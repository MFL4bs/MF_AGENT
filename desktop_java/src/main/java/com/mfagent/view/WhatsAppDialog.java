package com.mfagent.view;

import com.mfagent.service.BridgeManager;
import com.mfagent.util.EnvConfig;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.stage.Modality;
import javafx.stage.Stage;
import javafx.stage.Window;

import java.util.Map;

public class WhatsAppDialog {

    private final Stage stage;
    private final boolean isAdmin;
    private final BridgeManager bridge;

    private TextArea console;
    private Label statusLabel;
    private Button btnStart;
    private Button btnStop;

    public WhatsAppDialog(Window owner, boolean isAdmin, BridgeManager bridge) {
        this.isAdmin = isAdmin;
        this.bridge  = bridge;
        stage = new Stage();
        stage.initOwner(owner);
        stage.initModality(Modality.NONE);
        stage.setTitle("WhatsApp Bridge");
        stage.setMinWidth(700);
        stage.setMinHeight(600);

        // Cerrar ventana NO detiene el bridge
        stage.setOnCloseRequest(e -> detachBridge());

        build();
        attachBridge();
    }

    private void build() {
        VBox layout = new VBox(14);
        layout.setPadding(new Insets(24));
        layout.setStyle("-fx-background-color: #F5F0EB;");

        Label title = new Label("📱  WhatsApp");
        title.setStyle("-fx-font-size: 18px; -fx-font-weight: bold; -fx-text-fill: #1F2937;");

        Label info = new Label(
                "Haz clic en Iniciar Bridge. Aparecerá un código QR abajo.\n" +
                "Ábrelo en WhatsApp → Dispositivos vinculados → Vincular dispositivo.");
        info.setStyle("-fx-text-fill: #6B7280; -fx-font-size: 12px;");
        info.setWrapText(true);

        // Número admin
        HBox numRow = new HBox(8);
        Label numLbl = new Label("📞  Número admin:");
        numLbl.setStyle("-fx-text-fill: #1F2937; -fx-font-weight: bold;");
        String currentNum = EnvConfig.get("ADMIN_PHONES", EnvConfig.get("OWNER_PHONE", ""));
        if (isAdmin) {
            TextField numField = new TextField(currentNum);
            numField.setPrefWidth(200);
            Button btnSave = new Button("💾");
            btnSave.getStyleClass().add("btn-primary");
            btnSave.setOnAction(e -> {
                String num = numField.getText().strip();
                if (!num.isEmpty()) {
                    EnvConfig.write(Map.of("ADMIN_PHONES", num, "OWNER_PHONE", num));
                    btnSave.setText("✅");
                    javafx.animation.PauseTransition pause = new javafx.animation.PauseTransition(javafx.util.Duration.seconds(2));
                    pause.setOnFinished(ev -> btnSave.setText("💾"));
                    pause.play();
                }
            });
            numRow.getChildren().addAll(numLbl, numField, btnSave);
        } else {
            Label numVal = new Label(currentNum.isEmpty() ? "No configurado" : currentNum);
            numVal.setStyle("-fx-text-fill: #6B7280;");
            numRow.getChildren().addAll(numLbl, numVal);
        }

        statusLabel = new Label();
        updateStatus();

        console = new TextArea();
        console.setEditable(false);
        console.setStyle("-fx-control-inner-background: #0d1117; -fx-text-fill: #e6edf3; " +
                "-fx-font-family: 'Consolas'; -fx-font-size: 11px;");
        VBox.setVgrow(console, Priority.ALWAYS);

        HBox btns = new HBox(10);
        btnStart = new Button("▶  Iniciar");
        btnStart.getStyleClass().add("btn-whatsapp");
        btnStart.setOnAction(e -> startBridge());

        btnStop = new Button("⏹  Detener");
        btnStop.getStyleClass().add("btn-danger");
        btnStop.setOnAction(e -> stopBridge());

        Button btnClose = new Button("Cerrar");
        btnClose.getStyleClass().add("btn-primary");
        btnClose.setOnAction(e -> stage.close());

        Region spacer = new Region();
        HBox.setHgrow(spacer, Priority.ALWAYS);
        btns.getChildren().addAll(btnStart, btnStop, spacer, btnClose);

        updateButtons();

        layout.getChildren().addAll(title, info, numRow, statusLabel, console, btns);

        Scene scene = new Scene(layout, 1000, 820);
        scene.getStylesheets().add(getClass().getResource("/css/theme.css").toExternalForm());
        stage.setScene(scene);
    }

    /** Conecta los callbacks del BridgeManager a esta UI. */
    private void attachBridge() {
        bridge.setOnOutput(line -> Platform.runLater(() -> {
            console.appendText(line + "\n");
        }));
        bridge.setOnConnected(() -> Platform.runLater(() -> {
            statusLabel.setText("🟢  WhatsApp conectado");
            statusLabel.setStyle("-fx-text-fill: #16A34A; -fx-font-weight: bold;");
            updateButtons();
        }));
        bridge.setOnStopped(() -> Platform.runLater(() -> {
            updateStatus();
            updateButtons();
        }));
    }

    /** Al cerrar la ventana desconecta los callbacks de UI pero NO mata el proceso. */
    private void detachBridge() {
        bridge.setOnOutput(line -> System.out.println("[Bridge] " + line));
        bridge.setOnConnected(null);
        bridge.setOnStopped(null);
    }

    private void startBridge() {
        bridge.start();
        updateStatus();
        updateButtons();
        statusLabel.setText("🟡  Iniciando bridge...");
        statusLabel.setStyle("-fx-text-fill: #D97706; -fx-font-weight: bold;");
    }

    private void stopBridge() {
        bridge.stop();
        updateStatus();
        updateButtons();
    }

    private void updateStatus() {
        if (bridge.isRunning()) {
            statusLabel.setText("🟢  Bridge activo");
            statusLabel.setStyle("-fx-text-fill: #16A34A; -fx-font-weight: bold;");
        } else {
            statusLabel.setText("⚪  Bridge detenido");
            statusLabel.setStyle("-fx-text-fill: #6B7280; -fx-font-weight: bold;");
        }
    }

    private void updateButtons() {
        boolean running = bridge.isRunning();
        btnStart.setDisable(running);
        btnStop.setDisable(!running);
    }

    public void show() {
        attachBridge(); // reconectar callbacks al reabrir
        updateStatus();
        updateButtons();
        stage.show();
        stage.toFront();
    }
}
