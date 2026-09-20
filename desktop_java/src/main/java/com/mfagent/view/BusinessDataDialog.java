package com.mfagent.view;

import com.mfagent.util.EnvConfig;
import javafx.geometry.Insets;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.stage.DirectoryChooser;
import javafx.stage.Window;

import java.io.File;
import java.util.Map;

/**
 * Diálogo para editar datos de la empresa (aparecen en el PDF).
 * Equivalente a _manage_business_data() en app.py
 */
public class BusinessDataDialog extends Dialog<Void> {

    public BusinessDataDialog(Window owner) {
        setTitle("Datos de la Empresa");
        initOwner(owner);
        getDialogPane().getStylesheets().add(
                getClass().getResource("/css/theme.css").toExternalForm());
        getDialogPane().setStyle("-fx-background-color: #FDFAF7;");

        GridPane form = new GridPane();
        form.setHgap(12); form.setVgap(10);
        form.setPadding(new Insets(20));

        TextField nameField    = new TextField(EnvConfig.get("BUSINESS_NAME", ""));
        TextField phoneField   = new TextField(EnvConfig.get("BUSINESS_PHONE", ""));
        TextField emailField   = new TextField(EnvConfig.get("BUSINESS_EMAIL", ""));
        TextField addressField = new TextField(EnvConfig.get("BUSINESS_ADDRESS", ""));
        TextField pdfPathField = new TextField(EnvConfig.get("PDF_OUTPUT_DIR", ""));
        pdfPathField.setPromptText("Ej: C:\\Facturas");
        pdfPathField.setPrefWidth(260);
        pdfPathField.setEditable(false);

        Button btnBrowse = new Button("📁");
        btnBrowse.setOnAction(e -> {
            DirectoryChooser dc = new DirectoryChooser();
            dc.setTitle("Carpeta de PDFs");
            String current = pdfPathField.getText().strip();
            if (!current.isEmpty()) {
                File f = new File(current);
                if (f.exists()) dc.setInitialDirectory(f);
            }
            File dir = dc.showDialog(owner);
            if (dir != null) pdfPathField.setText(dir.getAbsolutePath());
        });

        nameField.setPromptText("Ej: Mi Empresa S.A.");
        phoneField.setPromptText("+52 55 1234 5678");
        emailField.setPromptText("contacto@miempresa.com");
        addressField.setPromptText("Calle 123, Ciudad");

        HBox pdfRow = new HBox(6, pdfPathField, btnBrowse);

        form.addRow(0, new Label("Nombre:"),       nameField);
        form.addRow(1, new Label("Teléfono:"),     phoneField);
        form.addRow(2, new Label("Email:"),        emailField);
        form.addRow(3, new Label("Dirección:"),    addressField);
        form.addRow(4, new Label("Carpeta PDFs:"), pdfRow);

        form.getChildren().stream().filter(n -> n instanceof Label)
                .forEach(n -> ((Label) n).setStyle("-fx-text-fill: #1F2937;"));

        getDialogPane().setContent(form);
        getDialogPane().setPrefWidth(440);

        ButtonType saveBtn   = new ButtonType("💾  Guardar", ButtonBar.ButtonData.OK_DONE);
        ButtonType cancelBtn = new ButtonType("Cancelar", ButtonBar.ButtonData.CANCEL_CLOSE);
        getDialogPane().getButtonTypes().addAll(saveBtn, cancelBtn);

        setResultConverter(btn -> {
            if (btn.getButtonData() == ButtonBar.ButtonData.OK_DONE) {
                EnvConfig.write(Map.of(
                        "BUSINESS_NAME",    nameField.getText().strip(),
                        "BUSINESS_PHONE",   phoneField.getText().strip(),
                        "BUSINESS_EMAIL",   emailField.getText().strip(),
                        "BUSINESS_ADDRESS", addressField.getText().strip(),
                        "PDF_OUTPUT_DIR",   pdfPathField.getText().strip()
                ));
            }
            return null;
        });
    }
}
