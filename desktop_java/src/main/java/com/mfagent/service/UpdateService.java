package com.mfagent.service;

import com.google.cloud.firestore.DocumentSnapshot;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

import java.io.*;
import java.nio.file.*;
import java.util.function.Consumer;

/**
 * Verifica actualizaciones en Firestore (app_config/desktop)
 * y descarga el nuevo .exe desde la URL almacenada.
 *
 * Documento Firestore esperado:
 *   app_config/desktop → { version: "1.0.1", update_url: "https://...", changelog: "..." }
 */
public class UpdateService {

    public static final String CURRENT_VERSION = "1.0.0";
    private static final String DOC_PATH_COL   = "app_config";
    private static final String DOC_PATH_ID    = "desktop";

    public record UpdateInfo(String version, String url, String changelog) {}

    /** Consulta Firestore. Devuelve UpdateInfo si hay versión nueva, null si está al día. */
    public UpdateInfo checkForUpdate() {
        try {
            DocumentSnapshot doc = FirebaseService.getDataDb()
                    .collection(DOC_PATH_COL).document(DOC_PATH_ID)
                    .get().get();
            if (!doc.exists()) return null;
            String remote = doc.getString("version");
            String url    = doc.getString("update_url");
            String log    = doc.getString("changelog");
            if (remote == null || url == null) return null;
            if (isNewer(remote, CURRENT_VERSION)) return new UpdateInfo(remote, url, log != null ? log : "");
        } catch (Exception e) {
            System.err.println("[Update] Error consultando Firestore: " + e.getMessage());
        }
        return null;
    }

    /**
     * Descarga el nuevo exe a un archivo temporal y lanza un script .bat
     * que espera a que la app cierre, reemplaza el exe y la reinicia.
     *
     * @param info       datos de la actualización
     * @param onProgress callback con porcentaje 0-100
     * @param onDone     callback al terminar (éxito=true / error=false)
     */
    public void downloadAndInstall(UpdateInfo info, Consumer<Integer> onProgress, Consumer<Boolean> onDone) {
        Thread t = new Thread(() -> {
            try {
                // Ruta del exe actual
                Path exePath = resolveExePath();
                Path tempExe = exePath.getParent().resolve("MF_AGENT_new.exe");

                // Descargar
                OkHttpClient client = new OkHttpClient.Builder()
                        .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
                        .readTimeout(5, java.util.concurrent.TimeUnit.MINUTES)
                        .build();
                Request req = new Request.Builder().url(info.url()).build();
                try (Response resp = client.newCall(req).execute()) {
                    if (!resp.isSuccessful() || resp.body() == null)
                        throw new IOException("HTTP " + resp.code());
                    long total = resp.body().contentLength();
                    try (InputStream in = resp.body().byteStream();
                         OutputStream out = Files.newOutputStream(tempExe)) {
                        byte[] buf = new byte[8192];
                        long downloaded = 0;
                        int n;
                        while ((n = in.read(buf)) != -1) {
                            out.write(buf, 0, n);
                            downloaded += n;
                            if (total > 0 && onProgress != null)
                                onProgress.accept((int) (downloaded * 100 / total));
                        }
                    }
                }

                // Script bat: espera cierre de la app, reemplaza exe, reinicia
                Path batPath = exePath.getParent().resolve("mf_update.bat");
                String bat = "@echo off\r\n" +
                        "timeout /t 2 /nobreak >nul\r\n" +
                        "move /y \"" + tempExe.toAbsolutePath() + "\" \"" + exePath.toAbsolutePath() + "\"\r\n" +
                        "start \"\" \"" + exePath.toAbsolutePath() + "\"\r\n" +
                        "del \"%~f0\"\r\n";
                Files.writeString(batPath, bat);

                // Lanzar bat y cerrar la app
                new ProcessBuilder("cmd", "/c", "start", "", batPath.toAbsolutePath().toString())
                        .start();

                if (onDone != null) onDone.accept(true);
            } catch (Exception e) {
                System.err.println("[Update] Error descargando: " + e.getMessage());
                if (onDone != null) onDone.accept(false);
            }
        }, "updater");
        t.setDaemon(true);
        t.start();
    }

    private Path resolveExePath() {
        try {
            Path jar = Path.of(UpdateService.class.getProtectionDomain()
                    .getCodeSource().getLocation().toURI());
            // jpackage: app/mf-agent-desktop-1.0.0.jar → ../MF_AGENT.exe
            Path exe = jar.getParent().getParent().resolve("MF_AGENT.exe");
            if (exe.toFile().exists()) return exe;
        } catch (Exception ignored) {}
        return Path.of("MF_AGENT.exe");
    }

    /** Compara versiones semánticas: "1.0.1" > "1.0.0" → true */
    private boolean isNewer(String remote, String current) {
        int[] r = parse(remote), c = parse(current);
        for (int i = 0; i < 3; i++) {
            if (r[i] > c[i]) return true;
            if (r[i] < c[i]) return false;
        }
        return false;
    }

    private int[] parse(String v) {
        String[] parts = v.split("\\.");
        int[] n = new int[3];
        for (int i = 0; i < Math.min(3, parts.length); i++) {
            try { n[i] = Integer.parseInt(parts[i].trim()); } catch (Exception ignored) {}
        }
        return n;
    }
}
