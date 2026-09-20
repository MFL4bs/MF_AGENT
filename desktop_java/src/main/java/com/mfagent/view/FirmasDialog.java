package com.mfagent.view;

import com.mfagent.util.EnvConfig;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.control.*;
import javafx.scene.image.Image;
import javafx.scene.image.ImageView;
import javafx.scene.layout.*;
import javafx.stage.FileChooser;
import javafx.stage.Window;

import java.io.File;
import java.util.HashMap;
import java.util.Map;

/**
 * Diálogo para configurar etiquetas e imágenes de firmas en el PDF.
 * Guarda en .env:
 *   FIRMA1_LABEL, FIRMA1_IMAGE
 *   FIRMA2_LABEL, FIRMA2_IMAGE
 */
public class FirmasDialog extends Dialog<Void> {

    public FirmasDialog(Window owner) {
        setTitle("Configurar Firmas del PDF");
        initOwner(owner);
        getDialogPane().getStylesheets().add(
                getClass().getResource("/css/theme.css").toExternalForm());
        getDialogPane().setStyle("-fx-background-color: #FDFAF7;");
        getDialogPane().setPrefWidth(480);

        VBox content = new VBox(20);
        content.setPadding(new Insets(20));

        FirmaRow firma1Row = new FirmaRow(owner, "Firma izquierda (empresa):",
                EnvConfig.get("FIRMA1_LABEL", "Firma Empresa"),
                EnvConfig.get("FIRMA1_IMAGE", ""));

        FirmaRow firma2Row = new FirmaRow(owner, "Firma derecha (cliente):",
                EnvConfig.get("FIRMA2_LABEL", "Firma Cliente"),
                EnvConfig.get("FIRMA2_IMAGE", ""));

        content.getChildren().addAll(firma1Row, new Separator(), firma2Row);
        getDialogPane().setContent(content);

        ButtonType saveBtn   = new ButtonType("💾  Guardar", ButtonBar.ButtonData.OK_DONE);
        ButtonType cancelBtn = new ButtonType("Cancelar",   ButtonBar.ButtonData.CANCEL_CLOSE);
        getDialogPane().getButtonTypes().addAll(saveBtn, cancelBtn);

        setResultConverter(btn -> {
            if (btn.getButtonData() == ButtonBar.ButtonData.OK_DONE) {
                Map<String, String> vals = new HashMap<>();
                vals.put("FIRMA1_LABEL", firma1Row.getLabel());
                vals.put("FIRMA1_IMAGE", firma1Row.getImagePath());
                vals.put("FIRMA2_LABEL", firma2Row.getLabel());
                vals.put("FIRMA2_IMAGE", firma2Row.getImagePath());
                EnvConfig.write(vals);
            }
            return null;
        });
    }

    // ── Componente por firma ──────────────────────────────────────────────────

    private static class FirmaRow extends VBox {

        private final TextField tfLabel;
        private String imagePath;
        private final ImageView preview;
        private final Label pathLabel;

        FirmaRow(Window owner, String title, String currentLabel, String currentImage) {
            super(8);
            this.imagePath = currentImage;

            Label titleLbl = new Label(title);
            titleLbl.setStyle("-fx-font-weight: bold; -fx-text-fill: #1F2937;");

            // Etiqueta de texto
            HBox labelRow = new HBox(8);
            labelRow.setAlignment(Pos.CENTER_LEFT);
            Label lbl = new Label("Etiqueta:");
            lbl.setStyle("-fx-text-fill: #6B7280;");
            tfLabel = new TextField(currentLabel);
            tfLabel.setPrefWidth(220);
            labelRow.getChildren().addAll(lbl, tfLabel);

            // Preview imagen
            preview = new ImageView();
            preview.setFitWidth(120);
            preview.setFitHeight(60);
            preview.setPreserveRatio(true);
            preview.setStyle("-fx-border-color: #D1CBC4; -fx-border-width: 1;");

            pathLabel = new Label(currentImage.isEmpty() ? "Sin imagen" : new File(currentImage).getName());
            pathLabel.setStyle("-fx-text-fill: #6B7280; -fx-font-size: 11px;");

            if (!currentImage.isEmpty() && new File(currentImage).exists()) {
                loadPreview(currentImage);
            }

            // Botones
            Button btnPick = new Button("🖼  Seleccionar imagen");
            btnPick.getStyleClass().add("btn-primary");
            btnPick.setOnAction(e -> {
                FileChooser fc = new FileChooser();
                fc.setTitle("Seleccionar imagen de firma");
                fc.getExtensionFilters().add(
                        new FileChooser.ExtensionFilter("Imágenes", "*.png", "*.jpg", "*.jpeg"));
                File file = fc.showOpenDialog(owner);
                if (file != null) {
                    imagePath = file.getAbsolutePath();
                    pathLabel.setText(file.getName());
                    loadPreview(imagePath);
                }
            });

            Button btnClear = new Button("✕ Quitar");
            btnClear.getStyleClass().add("btn-danger");
            btnClear.setOnAction(e -> {
                imagePath = "";
                pathLabel.setText("Sin imagen");
                preview.setImage(null);
            });

            HBox imgRow = new HBox(10, preview, new VBox(6, pathLabel, btnPick, btnClear));
            imgRow.setAlignment(Pos.CENTER_LEFT);

            getChildren().addAll(titleLbl, labelRow, imgRow);
        }

        private void loadPreview(String path) {
            try {
                preview.setImage(new Image(new File(path).toURI().toString(),
                        120, 60, true, true));
            } catch (Exception ignored) {}
        }

        String getLabel() {
            String t = tfLabel.getText().strip();
            return t.isEmpty() ? tfLabel.getPromptText() : t;
        }

        String getImagePath() { return imagePath; }
    }
}
