package com.mfagent.service;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.QueryDocumentSnapshot;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import com.mfagent.model.Session;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.*;

/**
 * Gestión de perfiles y autenticación de usuarios.
 * Equivalente a agent/profiles.py
 *
 * profiles.json:
 * { "profiles": [{ "id": "...", "name": "...", "users": [{ "username", "password_hash", "role" }] }] }
 */
public class ProfileService {

    private static final Gson GSON = new Gson();

    // ── Leer / escribir profiles.json ─────────────────────────────────────────

    private Map<String, Object> load() {
        Path f = ProfilePaths.profilesFile();
        if (!Files.exists(f)) return Map.of("profiles", new ArrayList<>());
        try {
            return GSON.fromJson(Files.readString(f),
                    new TypeToken<Map<String, Object>>(){}.getType());
        } catch (Exception e) {
            return Map.of("profiles", new ArrayList<>());
        }
    }

    @SuppressWarnings("unchecked")
    private void save(Map<String, Object> data) {
        try {
            Files.createDirectories(ProfilePaths.profilesFile().getParent());
            Files.writeString(ProfilePaths.profilesFile(), GSON.toJson(data));
        } catch (Exception e) {
            System.err.println("[ProfileService] Error guardando profiles.json: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> listProfiles() {
        Object raw = load().get("profiles");
        if (raw instanceof List<?> l) return (List<Map<String, Object>>) l;
        return new ArrayList<>();
    }

    public void saveProfiles(List<Map<String, Object>> profiles) {
        Map<String, Object> data = new HashMap<>(load());
        data.put("profiles", profiles);
        save(data);
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getProfile(String profileId) {
        return listProfiles().stream()
                .filter(p -> profileId.equals(p.get("id")))
                .findFirst().orElse(null);
    }

    // ── Autenticación ─────────────────────────────────────────────────────────

    /**
     * Autentica usuario contra profiles.json local.
     * Equivalente a authenticate() en profiles.py
     */
    @SuppressWarnings("unchecked")
    public Session authenticate(String profileId, String username, String password) {
        Map<String, Object> profile = getProfile(profileId);
        if (profile == null) return null;

        String hash = sha256(password);
        Object rawUsers = profile.get("users");
        if (!(rawUsers instanceof List<?> users)) return null;

        for (Object u : users) {
            if (!(u instanceof Map<?, ?> user)) continue;
            if (username.equals(user.get("username"))
                    && hash.equals(user.get("password_hash"))) {
                String role = Objects.toString(user.get("role"), "vendedor");
                String name = Objects.toString(profile.getOrDefault("name", profileId), profileId);
                return new Session(username, role, profileId, name, null);
            }
        }
        return null;
    }

    // ── Restaurar desde Firestore (PC nuevo) ──────────────────────────────────

    /**
     * Descarga perfil + usuarios + inventario + ventas desde Firestore.
     * Equivalente a RestoreWorker en firestore_sync.py
     */
    public RestoreResult restoreFromFirestore(String key, String profileId) {
        try {
            Firestore db = FirebaseService.getDataDb();

            // 1. Perfil
            var profDoc = db.collection("profiles").document(profileId).get().get();
            if (!profDoc.exists()) return RestoreResult.fail("No se encontró el perfil en Firestore.");

            Map<String, Object> profData = profDoc.getData();
            String profileName = str(profData, "name");

            // 2. Usuarios desde profile_users
            var usersSnap = db.collection("profile_users")
                    .whereEqualTo("profile_id", profileId).get().get();
            List<Map<String, Object>> users = new ArrayList<>();
            for (QueryDocumentSnapshot doc : usersSnap.getDocuments()) {
                Map<String, Object> u = new HashMap<>();
                u.put("username",      doc.getString("username"));
                u.put("password_hash", doc.getString("password_hash"));
                u.put("role",          doc.getString("role"));
                users.add(u);
            }
            if (users.isEmpty()) {
                Object rawUsers = profData.get("users");
                if (rawUsers instanceof List<?> l) {
                    for (Object item : l) {
                        if (item instanceof Map<?, ?> m) {
                            Map<String, Object> u = new HashMap<>();
                            m.forEach((k, v) -> u.put(k.toString(), v));
                            users.add(u);
                        }
                    }
                }
            }

            // 3. Guardar profiles.json
            Map<String, Object> existing = load();
            List<Map<String, Object>> profiles = listProfiles();
            profiles.removeIf(p -> profileId.equals(p.get("id")));
            Map<String, Object> newProfile = new HashMap<>();
            newProfile.put("id",    profileId);
            newProfile.put("name",  profileName);
            newProfile.put("users", users);
            profiles.add(newProfile);
            Map<String, Object> toSave = new HashMap<>(existing);
            toSave.put("profiles", profiles);
            save(toSave);

            // 4. Inventario
            var invSnap = db.collection("inventory")
                    .whereEqualTo("profile_id", profileId).get().get();
            List<Map<String, Object>> products = new ArrayList<>();
            for (QueryDocumentSnapshot doc : invSnap.getDocuments()) {
                if (doc.contains("sku")) products.add(doc.getData());
            }
            Path profileDir = ProfilePaths.dataDir(profileId);
            Files.createDirectories(profileDir);
            Files.writeString(profileDir.resolve("inventory.json"), GSON.toJson(products));

            // 5. Ventas
            var salesSnap = db.collection("invoices")
                    .whereEqualTo("profile_id", profileId).get().get();
            List<Map<String, Object>> invoices = new ArrayList<>();
            for (QueryDocumentSnapshot doc : salesSnap.getDocuments()) {
                if (doc.contains("invoice_id")) invoices.add(doc.getData());
            }
            Files.writeString(profileDir.resolve("sales.json"), GSON.toJson(invoices));

            return RestoreResult.ok(profileName, products.size(), invoices.size(), users.size());

        } catch (Exception e) {
            return RestoreResult.fail("Error al restaurar: " + e.getMessage());
        }
    }

    // ── Hash ──────────────────────────────────────────────────────────────────

    public static String sha256(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(input.getBytes());
            StringBuilder sb = new StringBuilder();
            for (byte b : hash) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }

    private String str(Map<String, Object> m, String key) {
        Object v = m.get(key); return v != null ? v.toString() : "";
    }

    // ── Resultado restauración ────────────────────────────────────────────────

    public static class RestoreResult {
        public final boolean ok;
        public final String  message;
        public final String  profileName;

        private RestoreResult(boolean ok, String message, String profileName) {
            this.ok = ok; this.message = message; this.profileName = profileName;
        }
        public static RestoreResult ok(String name, int products, int invoices, int users) {
            return new RestoreResult(true,
                    "✅ Restaurado: " + products + " productos, " + invoices + " ventas, " + users + " usuarios",
                    name);
        }
        public static RestoreResult fail(String msg) {
            return new RestoreResult(false, msg, null);
        }
    }
}
