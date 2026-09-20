package com.mfagent.service;

import com.google.gson.Gson;
import com.sun.net.httpserver.HttpServer;

import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.function.BiFunction;

/**
 * Servidor HTTP liviano en puerto 8000.
 * Recibe mensajes del bridge Node.js y retorna la respuesta del bot.
 */
public class WebhookServer {

    private static final int PORT = 8000;
    private static final Gson GSON = new Gson();

    private HttpServer server;
    // (phone, message) → reply
    private final BiFunction<String, String, String> onMessage;

    public WebhookServer(BiFunction<String, String, String> onMessage) {
        this.onMessage = onMessage;
    }

    public void start() {
        try {
            // Liberar puerto si está ocupado
            try {
                new ProcessBuilder("cmd", "/c",
                    "for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :" + PORT + " ^| findstr LISTENING') do taskkill /F /PID %a")
                    .start().waitFor();
            } catch (Exception ignored) {}

            server = HttpServer.create(new InetSocketAddress(PORT), 0);

            server.createContext("/webhook/whatsapp", exchange -> {
                if (!"POST".equals(exchange.getRequestMethod())) {
                    exchange.sendResponseHeaders(405, -1);
                    return;
                }
                try {
                    String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
                    Map<?, ?> data = GSON.fromJson(body, Map.class);
                    String phone   = str(data, "From");
                    String message = str(data, "Body");

                    String reply = "";
                    if (phone != null && message != null && onMessage != null)
                        reply = onMessage.apply(phone, message);

                    byte[] resp = GSON.toJson(Map.of("reply", reply != null ? reply : ""))
                            .getBytes(StandardCharsets.UTF_8);
                    exchange.getResponseHeaders().set("Content-Type", "application/json");
                    exchange.sendResponseHeaders(200, resp.length);
                    try (OutputStream os = exchange.getResponseBody()) { os.write(resp); }
                } catch (Exception e) {
                    System.err.println("[Webhook] Error: " + e.getMessage());
                    exchange.sendResponseHeaders(500, -1);
                }
            });

            server.createContext("/bridge/status", exchange -> {
                exchange.getRequestBody().readAllBytes();
                exchange.sendResponseHeaders(200, -1);
            });

            server.setExecutor(java.util.concurrent.Executors.newFixedThreadPool(4));
            server.start();
            System.out.println("[WebhookServer] Escuchando en puerto " + PORT);
        } catch (Exception e) {
            System.err.println("[WebhookServer] Error al iniciar: " + e.getMessage());
        }
    }

    public void stop() {
        if (server != null) server.stop(0);
    }

    private String str(Map<?, ?> m, String key) {
        Object v = m.get(key);
        return v != null ? v.toString() : null;
    }
}
