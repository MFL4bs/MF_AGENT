package com.mfagent.util;

import okhttp3.*;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Envía mensajes WhatsApp a los números admin via el bridge Node.js.
 * Equivalente a _notify_all_admins() en app.py
 */
public class WhatsAppNotifier {

    private static final OkHttpClient HTTP = new OkHttpClient();
    private static final MediaType JSON_TYPE = MediaType.get("application/json");
    private static final ExecutorService POOL = Executors.newCachedThreadPool(r -> {
        Thread t = new Thread(r, "wa-notifier");
        t.setDaemon(true);
        return t;
    });

    public static void notifyAll(String message) {
        String raw = EnvConfig.get("ADMIN_PHONES", EnvConfig.get("OWNER_PHONE", ""));
        if (raw.isBlank()) return;
        List<String> phones = List.of(raw.split(","));
        for (String phone : phones) {
            String p = phone.strip();
            if (!p.isEmpty()) POOL.submit(() -> send(p, message));
        }
    }

    public static void notifySale(com.mfagent.model.Invoice inv, String origin) {
        if (inv == null) return;
        StringBuilder sb = new StringBuilder();
        sb.append("🛒 *Nueva venta registrada*");
        if (origin != null) sb.append(" (").append(origin).append(")");
        sb.append("\n");
        sb.append("ID: ").append(inv.getInvoiceId() != null ? inv.getInvoiceId() : "—").append("\n");
        sb.append("Cliente: ").append(inv.getCustomer() != null && !inv.getCustomer().isBlank()
                ? inv.getCustomer() : "Consumidor final").append("\n");
        if (inv.getItems() != null) {
            for (var item : inv.getItems()) {
                String name = item.getProductName() != null ? item.getProductName() : item.getSku();
                sb.append("  • ").append(name)
                  .append(" x").append(item.getQuantity())
                  .append(" = $").append(String.format("%,.0f", item.getSubtotal())).append("\n");
            }
        }
        sb.append("*Total: $").append(String.format("%,.0f", inv.getTotal())).append("*");
        notifyAll(sb.toString());
    }

    private static void send(String phone, String message) {
        int attempts = 2;
        for (int i = 0; i < attempts; i++) {
            try {
                String escaped = message
                        .replace("\\", "\\\\")
                        .replace("\"", "\\\"")
                        .replace("\n", "\\n")
                        .replace("\r", "");
                String body = "{\"phone\":\"" + phone + "\",\"message\":\"" + escaped + "\"}";
                Request req = new Request.Builder()
                        .url("http://127.0.0.1:3000/send")
                        .post(RequestBody.create(body, JSON_TYPE))
                        .build();
                try (Response resp = HTTP.newCall(req).execute()) {
                    if (resp.isSuccessful()) return;
                    System.err.println("[WhatsApp] Error enviando a " + phone + ": HTTP " + resp.code());
                }
            } catch (java.net.ConnectException e) {
                System.err.println("[WhatsApp] Bridge no activo (puerto 3000). Inicia WhatsApp desde la app.");
                return; // no reintentar si el bridge no está corriendo
            } catch (Exception e) {
                System.err.println("[WhatsApp] Error enviando a " + phone + ": " + e.getMessage());
            }
            if (i < attempts - 1) {
                try { Thread.sleep(2000); } catch (InterruptedException ignored) {}
            }
        }
    }
}
