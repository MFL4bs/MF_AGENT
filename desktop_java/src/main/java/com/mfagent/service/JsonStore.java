package com.mfagent.service;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;

import java.io.IOException;
import java.lang.reflect.Type;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Utilidad base para leer/escribir archivos JSON locales.
 * Equivalente a _load() / _save() en local_inventory.py y local_sales.py
 */
public class JsonStore {

    private static final Gson GSON = new GsonBuilder()
            .setPrettyPrinting()
            .disableHtmlEscaping()
            .create();

    public static <T> List<T> readList(Path file, Class<T> clazz) {
        if (!Files.exists(file)) return new ArrayList<>();
        try {
            String json = Files.readString(file).trim();
            if (json.isEmpty() || json.equals("null")) return new ArrayList<>();
            Type listType = TypeToken.getParameterized(List.class, clazz).getType();
            List<T> result = GSON.fromJson(json, listType);
            return result != null ? result : new ArrayList<>();
        } catch (Exception e) {
            System.err.println("[JsonStore] Error leyendo " + file + ": " + e.getMessage());
            return new ArrayList<>();
        }
    }

    public static <T> void writeList(Path file, List<T> items) {
        try {
            Files.createDirectories(file.getParent());
            Files.writeString(file, GSON.toJson(items));
        } catch (IOException e) {
            System.err.println("[JsonStore] Error escribiendo " + file + ": " + e.getMessage());
        }
    }
}
