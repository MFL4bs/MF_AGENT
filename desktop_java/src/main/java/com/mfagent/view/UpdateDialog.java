package com.mfagent.view;

import com.mfagent.service.UpdateService;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.stage.Window;

public class UpdateDialog extends Dialog<Void> {

    public UpdateDialog(Window owner, UpdateService.UpdateInfo info) {
        setTitle("Nueva actualización disponible");
        initOwner(owner);
        getDialogPane().getStylesheets().add(
                getClass().getResource("/css/theme.css").toExternalForm());
        getDialogPane().setStyle("-fx-background-color: #FDFAF7;");
        getDialogPane().setPrefWidth(440);

        VBox layout = new VBox(14);
        layout.setPadding(new Insets(20));

        Label title = new Label("🚀  MF Agent " + info.version() + " disponible");
        title.setStyle("-fx-font-size: 16px; -fx-font-weight: bold; -fx-text-fill: #1B6CA8;");

        Label current = new Label("Versión actual: " + UpdateService.CURRENT_VERSION);
        current.setStyle("-fx-text-fill: #6B7280; -fx-font-size: 12px;");

        VBox changelogBox = new VBox(4);
        if (!info.changelog().isEmpty()) {
            Label logTitle = new Label("Novedades:");
            logTitle.setStyle("-fx-font-weight: bold; -fx-text-fill: #1F2937;");
            TextArea logArea = new TextArea(info.changelog());
            logArea.setEditable(false);
            logArea.setPrefHeight(100);
            logArea.setWrapText(true);
            logArea.setStyle("-fx-background-color: #EDE8E3; -fx-border-color: #D1CBC4;");
            changelogBox.getChildren().addAll(logTitle, logArea);
        }

        ProgressBar progress = new ProgressBar(0);
        progress.setMaxWidth(Double.MAX_VALUE);
        progress.setVisible(false);

        Label statusLabel = new Label("");
        statusLabel.setStyle("-fx-text-fill: #6B7280; -fx-font-size: 12px;");
        statusLabel.setVisible(false);

        layout.getChildren().addAll(title, current, changelogBox, progress, statusLabel);
        getDialogPane().setContent(layout);

        ButtonType updateBtn = new ButtonType("⬇️  Instalar ahora", ButtonBar.ButtonData.OK_DONE);
        ButtonType laterBtn  = new ButtonType("Más tarde", ButtonBar.ButtonData.CANCEL_CLOSE);
        getDialogPane().getButtonTypes().addAll(updateBtn, laterBtn);

        Button btnInstall = (Button) getDialogPane().lookupButton(updateBtn);
        btnInstall.addEventFilter(javafx.event.ActionEvent.ACTION, e -> {
            e.consume(); // no cerrar aún
            btnInstall.setDisable(true);
            progress.setVisible(true);
            statusLabel.setVisible(true);
            statusLabel.setText("Descargando...");

            new UpdateService().downloadAndInstall(info,
                pct -> Platform.runLater(() -> progress.setProgress(pct / 100.0)),
                ok  -> Platform.runLater(() -> {
                    if (ok) {
                        statusLabel.setText("✅ Descarga completa. La app se reiniciará.");
                        progress.setProgress(1.0);
                        // Cerrar la app para que el bat pueda reemplazar el exe
                        new javafx.animation.PauseTransition(javafx.util.Duration.seconds(2))
                            .setOnFinished(ev -> javafx.application.Platform.exit());
                    } else {
                        statusLabel.setText("❌ Error al descargar. Intenta de nuevo.");
                        btnInstall.setDisable(false);
                    }
                })
            );
        });

        setResultConverter(b -> null);
    }
}
