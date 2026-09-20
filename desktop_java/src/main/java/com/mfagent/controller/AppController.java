package com.mfagent.controller;

import com.mfagent.model.Session;
import com.mfagent.service.BotService;
import com.mfagent.service.BridgeManager;
import com.mfagent.service.FirestoreSync;
import com.mfagent.service.WebhookServer;
import com.mfagent.view.ActivationView;
import com.mfagent.view.MainWindow;
import javafx.application.Platform;
import javafx.scene.Scene;
import javafx.scene.image.Image;
import javafx.stage.Stage;

import java.nio.file.Paths;

public class AppController {

    private final Stage stage;
    private MainWindow mainWindow;
    private FirestoreSync firestoreSync;
    private WebhookServer webhookServer;
    private BridgeManager bridgeManager;

    public AppController(Stage stage) {
        this.stage = stage;
    }

    public void init() {
        stage.setTitle("MF Agent");
        stage.setMinWidth(520);
        stage.setMinHeight(400);
        setIcon();
        bridgeManager = new BridgeManager(); // persiste entre sesiones
        stage.setOnCloseRequest(e -> { if (bridgeManager != null) bridgeManager.stop(); });
        showActivation();
        stage.show();
    }

    private void showActivation() {
        ActivationView activation = new ActivationView();
        activation.setOnActivated(this::onActivated);
        Scene scene = new Scene(activation.getRoot(), 520, 520);
        scene.getStylesheets().add(getClass().getResource("/css/theme.css").toExternalForm());
        stage.setScene(scene);
        stage.setTitle("MF Agent — Activación");
    }

    private void onActivated(Session session) {
        firestoreSync  = new FirestoreSync(session.getProfileId());
        BotService botService = new BotService(session.getProfileId());

        webhookServer = new WebhookServer((phone, message) ->
                botService.reply(phone, message, session.getProfileName()).text());
        webhookServer.start();

        Platform.runLater(() -> {
            launchMainWindow(session);
            firestoreSync.pullAll(() -> Platform.runLater(() -> mainWindow.refreshAll()));
            checkForUpdates();
        });
    }

    private void checkForUpdates() {
        Thread t = new Thread(() -> {
            com.mfagent.service.UpdateService svc = new com.mfagent.service.UpdateService();
            com.mfagent.service.UpdateService.UpdateInfo info = svc.checkForUpdate();
            if (info != null)
                Platform.runLater(() ->
                    new com.mfagent.view.UpdateDialog(stage, info).show());
        }, "update-check");
        t.setDaemon(true);
        t.start();
    }

    private void launchMainWindow(Session session) {
        mainWindow = new MainWindow(session, bridgeManager);
        mainWindow.setOnLogout(this::onLogout);
        mainWindow.setFirestoreSync(firestoreSync);

        Scene scene = new Scene(mainWindow.getRoot());
        scene.getStylesheets().add(getClass().getResource("/css/theme.css").toExternalForm());
        stage.setScene(scene);
        stage.setTitle("MF Agent — " + session.getProfileName() + "  [" + session.getUsername() + "]");
        stage.setMaximized(true);

        mainWindow.start();

        firestoreSync.startInventoryListener(() -> Platform.runLater(() -> mainWindow.refreshInventory()));
        firestoreSync.startInvoiceListener(
            inv -> Platform.runLater(() -> {
                mainWindow.refreshSales();
                com.mfagent.util.WhatsAppNotifier.notifySale(inv, "Móvil");
                // Verificar stock bajo por cada item de la venta
                if (inv.getItems() != null) {
                    com.mfagent.service.LocalInventory inv2 = new com.mfagent.service.LocalInventory(session.getProfileId());
                    for (com.mfagent.model.InvoiceItem item : inv.getItems()) {
                        inv2.get(item.getSku()).ifPresent(p -> {
                            if (p.getStock() <= 15)
                                com.mfagent.util.WhatsAppNotifier.notifyAll(
                                    "\u26a0\ufe0f *Stock bajo*\nProducto: " + p.getName() +
                                    " [" + p.getSku() + "]\nStock actual: " + p.getStock() + " unidades");
                        });
                    }
                }
            }),
            id -> Platform.runLater(() -> mainWindow.refreshSales())
        );
        firestoreSync.startCustomerListener(null);
    }

    private void onLogout() {
        // bridgeManager NO se detiene — conserva la sesión WhatsApp entre logins
        if (firestoreSync  != null) { firestoreSync.stopListeners(); firestoreSync = null; }
        if (webhookServer  != null) { webhookServer.stop(); webhookServer = null; }
        if (mainWindow     != null) { mainWindow.stop(); mainWindow = null; }
        Platform.runLater(this::showActivation);
    }

    private void setIcon() {
        var ico = Paths.get("MF_LABS.png");
        if (ico.toFile().exists())
            stage.getIcons().add(new Image(ico.toUri().toString()));
    }
}