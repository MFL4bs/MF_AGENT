package com.mfagent.view;

import com.mfagent.model.Product;
import com.mfagent.service.FirestoreSync;
import com.mfagent.service.LocalInventory;
import javafx.geometry.Insets;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.stage.FileChooser;
import javafx.stage.Window;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Optional;

/**
 * Diálogo para agregar / editar producto.
 * Equivalente a ProductDialog en app.py
 */
public class ProductDialog extends Dialog<Product> {

    private final LocalInventory inventory;
    private final String profileId;
    private final Product existing;
    private final FirestoreSync firestoreSync;

    private TextField skuField;
    private TextField nameField;
    private TextField descField;
    private TextField priceField;
    private TextField costField;
    private Spinner<Integer> stockSpinner;
    private TextField categoryField;
    private String imagePath;

    public ProductDialog(Window owner, Product existing, LocalInventory inventory,
                         String profileId, FirestoreSync firestoreSync) {
        this.existing      = existing;
        this.inventory     = inventory;
        this.profileId     = profileId;
        this.firestoreSync = firestoreSync;

        setTitle(existing == null ? "Nuevo Producto" : "Editar Producto");
        initOwner(owner);
        getDialogPane().getStylesheets().add(
                getClass().getResource("/css/theme.css").toExternalForm());
        getDialogPane().setStyle("-fx-background-color: #FDFAF7;");

        buildContent();
        addButtons();
        setResultConverter(this::convert);
    }

    private void buildContent() {
        GridPane form = new GridPane();
        form.setHgap(12);
        form.setVgap(10);
        form.setPadding(new Insets(20));

        skuField = new TextField(existing != null ? existing.getSku() : inventory.nextSku());
        skuField.setEditable(false);
        skuField.setStyle("-fx-background-color: #EDE8E3; -fx-text-fill: #6B7280;");

        nameField     = new TextField(existing != null ? existing.getName() : "");
        nameField.setPromptText("Nombre del producto");

        descField     = new TextField(existing != null ? existing.getDescription() : "");
        descField.setPromptText("Descripción breve");

        priceField    = new TextField(existing != null ? String.valueOf(existing.getPrice()) : "0");
        priceField.setPromptText("Precio de venta");

        costField     = new TextField(existing != null ? String.valueOf(existing.getCostPrice()) : "0");
        costField.setPromptText("Precio de compra");

        stockSpinner  = new Spinner<>(0, 99999, existing != null ? existing.getStock() : 0);
        stockSpinner.setEditable(true);

        categoryField = new TextField(existing != null ? existing.getCategory() : "");
        categoryField.setPromptText("Categoría");

        imagePath = existing != null ? existing.getImageUrl() : null;

        Button btnPhoto = new Button("📷  Foto");
        btnPhoto.getStyleClass().add("btn-primary");
        btnPhoto.setOnAction(e -> pickImage());

        int row = 0;
        form.addRow(row++, new Label("SKU *"),        skuField);
        form.addRow(row++, new Label("Nombre *"),     nameField);
        form.addRow(row++, new Label("Descripción"),  descField);
        form.addRow(row++, new Label("Precio Compra"),costField);
        form.addRow(row++, new Label("Precio Venta *"),priceField);
        form.addRow(row++, new Label("Stock *"),      stockSpinner);
        form.addRow(row++, new Label("Categoría"),    categoryField);
        form.addRow(row,   new Label("Foto"),         btnPhoto);

        // Estilo labels
        form.getChildren().stream()
                .filter(n -> n instanceof Label)
                .forEach(n -> ((Label) n).setStyle("-fx-text-fill: #1F2937; -fx-font-size: 13px;"));

        getDialogPane().setContent(form);
        getDialogPane().setPrefWidth(460);
    }

    private void addButtons() {
        ButtonType saveBtn   = new ButtonType("Guardar", ButtonBar.ButtonData.OK_DONE);
        ButtonType cancelBtn = new ButtonType("Cancelar", ButtonBar.ButtonData.CANCEL_CLOSE);
        getDialogPane().getButtonTypes().addAll(saveBtn, cancelBtn);

        // Validar antes de cerrar
        Button save = (Button) getDialogPane().lookupButton(saveBtn);
        save.addEventFilter(javafx.event.ActionEvent.ACTION, e -> {
            if (nameField.getText().strip().isEmpty()) {
                new Alert(Alert.AlertType.WARNING, "El nombre es obligatorio.").show();
                e.consume();
            }
        });
    }

    private void pickImage() {
        FileChooser fc = new FileChooser();
        fc.setTitle("Seleccionar imagen");
        fc.getExtensionFilters().add(
                new FileChooser.ExtensionFilter("Imágenes", "*.png", "*.jpg", "*.jpeg", "*.webp"));
        File file = fc.showOpenDialog(getOwner());
        if (file != null) {
            try {
                Path destDir = Path.of("data", profileId, "images");
                Files.createDirectories(destDir);
                String ext = file.getName().substring(file.getName().lastIndexOf('.'));
                Path dest = destDir.resolve(skuField.getText() + ext);
                Files.copy(file.toPath(), dest, StandardCopyOption.REPLACE_EXISTING);
                imagePath = dest.toString();
            } catch (Exception ex) {
                imagePath = file.getAbsolutePath();
            }
        }
    }

    private Product convert(ButtonType btn) {
        if (btn.getButtonData() != ButtonBar.ButtonData.OK_DONE) return null;
        Product p = existing != null ? existing : new Product();
        p.setSku(skuField.getText().strip());
        p.setName(nameField.getText().strip());
        p.setDescription(descField.getText().strip());
        p.setPrice(parseDouble(priceField.getText()));
        p.setCostPrice(parseDouble(costField.getText()));
        p.setStock(stockSpinner.getValue());
        p.setCategory(categoryField.getText().strip());
        p.setImageUrl(imagePath);
        inventory.upsert(p);
        if (firestoreSync != null) firestoreSync.syncAll(null);
        return p;
    }

    private double parseDouble(String s) {
        try { return Double.parseDouble(s.replace(",", "").replace("$", "").strip()); }
        catch (NumberFormatException e) { return 0; }
    }
}
