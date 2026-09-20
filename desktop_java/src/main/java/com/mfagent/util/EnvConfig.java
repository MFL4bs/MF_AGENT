package com.mfagent.util;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

import com.mfagent.service.ProfilePaths;

/**
 * Lee y escribe el archivo .env del proyecto.
 * Equivalente a _read_env() / _write_env() en app.py
 */
public class EnvConfig {

    private static Map<String, String> cache = null;

    public static Map<String, String> read() {
        if (cache != null) return cache;
        cache = new HashMap<>();
        Path envFile = ProfilePaths.envFile();
        if (!Files.exists(envFile)) return cache;
        try {
            for (String line : Files.readAllLines(envFile)) {
                line = line.strip();
                if (line.isEmpty() || line.startsWith("#") || !line.contains("=")) continue;
                int idx = line.indexOf('=');
                cache.put(line.substring(0, idx).strip(), line.substring(idx + 1).strip());
            }
        } catch (IOException e) {
            System.err.println("[EnvConfig] Error leyendo .env: " + e.getMessage());
        }
        return cache;
    }

    public static String get(String key, String defaultValue) {
        return read().getOrDefault(key, defaultValue);
    }

    public static void set(String key, String value) {
        write(Map.of(key, value));
    }

    public static void write(Map<String, String> updates) {
        Path envFile = ProfilePaths.envFile();
        try {
            java.util.List<String> lines = Files.exists(envFile)
                    ? new java.util.ArrayList<>(Files.readAllLines(envFile))
                    : new java.util.ArrayList<>();

            java.util.Set<String> written = new java.util.HashSet<>();
            for (int i = 0; i < lines.size(); i++) {
                String line = lines.get(i).strip();
                if (!line.isEmpty() && !line.startsWith("#") && line.contains("=")) {
                    String key = line.substring(0, line.indexOf('=')).strip();
                    if (updates.containsKey(key)) {
                        lines.set(i, key + "=" + updates.get(key));
                        written.add(key);
                    }
                }
            }
            for (Map.Entry<String, String> e : updates.entrySet()) {
                if (!written.contains(e.getKey())) {
                    lines.add(e.getKey() + "=" + e.getValue());
                }
            }
            Files.writeString(envFile, String.join("\n", lines) + "\n");
            cache = null; // invalidar caché para que la próxima lectura tome los valores nuevos
        } catch (IOException e) {
            System.err.println("[EnvConfig] Error escribiendo .env: " + e.getMessage());
        }
    }
}
