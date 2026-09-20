package com.mfagent.service;

import com.google.cloud.firestore.Firestore;
import com.google.cloud.firestore.QueryDocumentSnapshot;
import com.google.cloud.firestore.QuerySnapshot;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

/**
 * Validación y activación de licencias contra Firebase.
 * Equivalente a lic_manager/license_manager.py
 *
 * - HMAC-SHA256 para firmar el .license local
 * - Hardware ID vinculado al dispositivo
 * - Soporte multi-dispositivo (max_devices)
 * - Aviso cuando quedan ≤7 días
 */
public class LicenseService {

    private static final byte[] SECRET = "MF-4g9zK2#pL8mXqR5vN1wJ7cT0bY6hD".getBytes();
    private static final int WARN_DAYS = 7;
    private static final Gson GSON = new Gson();

    // ── Hardware ID ───────────────────────────────────────────────────────────

    public String getHardwareId() {
        try {
            String raw = InetAddress.getLocalHost().getHostName()
                    + "-" + System.getProperty("os.arch")
                    + "-" + getMacAddress();
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(raw.getBytes());
            StringBuilder sb = new StringBuilder();
            for (byte b : hash) sb.append(String.format("%02x", b));
            return sb.substring(0, 32);
        } catch (Exception e) {
            return "unknown-device";
        }
    }

    private String getMacAddress() {
        try {
            NetworkInterface ni = NetworkInterface.getByInetAddress(InetAddress.getLocalHost());
            if (ni == null) return "00:00:00:00:00:00";
            byte[] mac = ni.getHardwareAddress();
            if (mac == null) return "00:00:00:00:00:00";
            StringBuilder sb = new StringBuilder();
            for (byte b : mac) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            return "00:00:00:00:00:00";
        }
    }

    // ── HMAC firma ────────────────────────────────────────────────────────────

    private String sign(String key, String deviceId) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(SECRET, "HmacSHA256"));
            byte[] hash = mac.doFinal((key + ":" + deviceId).getBytes());
            StringBuilder sb = new StringBuilder();
            for (byte b : hash) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }

    // ── .license local ────────────────────────────────────────────────────────

    private Path licenseFile() {
        return ProfilePaths.licenseFile();
    }

    public void saveLocal(String key, String deviceId, String profileId) {
        Map<String, String> data = new HashMap<>();
        data.put("key",        key);
        data.put("device_id",  deviceId);
        data.put("profile_id", profileId);
        data.put("sig",        sign(key, deviceId));
        try {
            Files.writeString(licenseFile(), GSON.toJson(data));
        } catch (Exception e) {
            System.err.println("[License] Error guardando .license: " + e.getMessage());
        }
    }

    public Map<String, String> loadLocal() {
        try {
            if (!Files.exists(licenseFile())) return Map.of();
            String json = Files.readString(licenseFile());
            Map<String, String> data = GSON.fromJson(json,
                    new TypeToken<Map<String, String>>(){}.getType());
            // Verificar firma
            String expected = sign(data.get("key"), data.get("device_id"));
            if (!expected.equals(data.get("sig"))) return Map.of();
            return data;
        } catch (Exception e) {
            return Map.of();
        }
    }

    public String loadLocalKey() {
        return loadLocal().getOrDefault("key", null);
    }

    public String loadLocalProfileId() {
        return loadLocal().getOrDefault("profile_id", null);
    }

    // ── Activar key ───────────────────────────────────────────────────────────

    public LicenseResult activate(String key) {
        try {
            Firestore db = FirebaseService.getLicDb();
            String deviceId = getHardwareId();

            var licDoc = db.collection("licenses").document(key).get().get();
            if (!licDoc.exists()) return LicenseResult.fail("Key inválida.");

            Map<String, Object> data = licDoc.getData();
            if (!Boolean.TRUE.equals(data.get("active")))
                return LicenseResult.fail("Key desactivada.");

            // Verificar plataforma
            String platform = str(data, "platform");
            if ("mobile".equals(platform))
                return LicenseResult.fail("Esta key es solo para dispositivos móviles.");

            // Verificar expiración
            Integer daysLeft = null;
            String expiresAt = str(data, "expires_at");
            if (expiresAt != null && !expiresAt.isEmpty() && !"never".equals(expiresAt)) {
                ZonedDateTime exp = ZonedDateTime.parse(expiresAt, DateTimeFormatter.ISO_DATE_TIME)
                        .withZoneSameInstant(ZoneOffset.UTC);
                ZonedDateTime now = ZonedDateTime.now(ZoneOffset.UTC);
                if (now.isAfter(exp)) return LicenseResult.fail("Key vencida.");
                daysLeft = (int) ChronoUnit.DAYS.between(now, exp);
            }

            // Verificar dispositivos
            QuerySnapshot devSnap = db.collection("devices")
                    .whereEqualTo("key_id", key).get().get();
            List<QueryDocumentSnapshot> devices = devSnap.getDocuments();
            List<String> deviceIds = devices.stream()
                    .map(d -> { String v = d.getString("device_id"); return v != null ? v : ""; })
                    .toList();

            int maxDevices = ((Number) data.getOrDefault("max_devices", 1)).intValue();

            if (!deviceIds.contains(deviceId) && deviceIds.size() >= maxDevices)
                return LicenseResult.fail("Límite de dispositivos alcanzado (" + maxDevices + ").");

            // Registrar dispositivo si es nuevo
            if (!deviceIds.contains(deviceId)) {
                Map<String, Object> devData = new HashMap<>();
                devData.put("device_id",     deviceId);
                devData.put("key_id",         key);
                devData.put("platform",       "pc");
                devData.put("hostname",       InetAddress.getLocalHost().getHostName());
                devData.put("registered_at",  Instant.now().toString());
                devData.put("last_seen",      Instant.now().toString());
                db.collection("devices").document(deviceId).set(devData).get();
            }

            String profileId = str(data, "profile_id");
            saveLocal(key, deviceId, profileId != null ? profileId : "");
            return LicenseResult.ok(profileId, daysLeft);

        } catch (Exception e) {
            return LicenseResult.fail("Error al activar: " + e.getMessage());
        }
    }

    // ── Validar licencia guardada ─────────────────────────────────────────────

    public LicenseResult validate() {
        Map<String, String> local = loadLocal();
        if (local.isEmpty()) return LicenseResult.fail("No hay licencia activada.");

        String key      = local.get("key");
        String deviceId = local.get("device_id");

        if (!getHardwareId().equals(deviceId))
            return LicenseResult.fail("Licencia no válida para este equipo.");

        try {
            Firestore db = FirebaseService.getLicDb();
            var licDoc = db.collection("licenses").document(key).get().get();
            if (!licDoc.exists()) return LicenseResult.fail("Key no encontrada.");

            Map<String, Object> data = licDoc.getData();
            if (!Boolean.TRUE.equals(data.get("active")))
                return LicenseResult.fail("Licencia revocada.");

            Integer daysLeft = null;
            boolean warn = false;
            String expiresAt = str(data, "expires_at");
            if (expiresAt != null && !expiresAt.isEmpty() && !"never".equals(expiresAt)) {
                ZonedDateTime exp = ZonedDateTime.parse(expiresAt, DateTimeFormatter.ISO_DATE_TIME)
                        .withZoneSameInstant(ZoneOffset.UTC);
                ZonedDateTime now = ZonedDateTime.now(ZoneOffset.UTC);
                if (now.isAfter(exp)) return LicenseResult.fail("Licencia vencida. Renueva tu plan.");
                daysLeft = (int) ChronoUnit.DAYS.between(now, exp);
                warn = daysLeft <= WARN_DAYS;
            }

            // Actualizar last_seen
            db.collection("devices").document(deviceId)
                    .update("last_seen", Instant.now().toString());

            String profileId = local.get("profile_id");
            return LicenseResult.ok(profileId, daysLeft).withWarn(warn);

        } catch (Exception e) {
            return LicenseResult.fail("Error al validar: " + e.getMessage());
        }
    }

    private String str(Map<String, Object> m, String key) {
        Object v = m.get(key); return v != null ? v.toString() : null;
    }

    // ── Resultado ─────────────────────────────────────────────────────────────

    public static class LicenseResult {
        public final boolean ok;
        public final String  message;
        public final String  profileId;
        public final Integer daysLeft;
        public boolean warn;

        private LicenseResult(boolean ok, String message, String profileId, Integer daysLeft) {
            this.ok = ok; this.message = message;
            this.profileId = profileId; this.daysLeft = daysLeft;
        }

        public static LicenseResult ok(String profileId, Integer daysLeft) {
            return new LicenseResult(true, "Licencia válida.", profileId, daysLeft);
        }
        public static LicenseResult fail(String msg) {
            return new LicenseResult(false, msg, null, null);
        }
        public LicenseResult withWarn(boolean w) { this.warn = w; return this; }
    }
}
