package com.mfagent.service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.file.Path;
import java.util.function.Consumer;

/**
 * Gestiona el proceso Node.js del bridge de WhatsApp.
 * Vive en AppController — independiente del diálogo UI.
 */
public class BridgeManager {

    private Process process;
    private Thread readerThread;
    private Consumer<String> onOutput;
    private Runnable onConnected;
    private Runnable onStopped;

    public void setOnOutput(Consumer<String> cb)   { this.onOutput    = cb; }
    public void setOnConnected(Runnable cb)         { this.onConnected = cb; }
    public void setOnStopped(Runnable cb)           { this.onStopped   = cb; }

    public boolean isRunning() {
        return process != null && process.isAlive();
    }

    public void start() {
        if (isRunning()) return;

        Path bridgeDir = Path.of("whatsapp_bridge");
        if (!bridgeDir.resolve("index.js").toFile().exists()) {
            emit("[Bridge] No se encontró whatsapp_bridge/index.js");
            return;
        }

        // Liberar puerto 3000 si está ocupado
        try {
            new ProcessBuilder("cmd", "/c",
                "for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do taskkill /F /PID %a")
                .start().waitFor();
        } catch (Exception ignored) {}

        try {
            process = new ProcessBuilder("node", "index.js")
                    .directory(bridgeDir.toFile())
                    .redirectErrorStream(true)
                    .start();

            readerThread = new Thread(() -> {
                try (BufferedReader br = new BufferedReader(
                        new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = br.readLine()) != null) {
                        final String l = line;
                        emit(l);
                        String lower = l.toLowerCase();
                        if (lower.contains("listo") || lower.contains("ready") || lower.contains("conectado")) {
                            if (onConnected != null) onConnected.run();
                        }
                    }
                } catch (Exception ignored) {}
                // Proceso terminó
                if (onStopped != null) onStopped.run();
            }, "bridge-reader");
            readerThread.setDaemon(true);
            readerThread.start();

            emit("[Bridge] Iniciado (PID " + process.pid() + ")");
        } catch (Exception e) {
            emit("[Bridge] Error al iniciar: " + e.getMessage());
        }
    }

    public void stop() {
        if (process != null) {
            long pid = process.pid();
            try {
                new ProcessBuilder("taskkill", "/F", "/T", "/PID", String.valueOf(pid))
                        .start().waitFor();
            } catch (Exception ignored) {}
            process.destroyForcibly();
            process = null;
        }
        if (readerThread != null) {
            readerThread.interrupt();
            readerThread = null;
        }
        emit("[Bridge] Detenido");
        if (onStopped != null) onStopped.run();
    }

    private void emit(String line) {
        if (onOutput != null) onOutput.accept(line);
    }
}
