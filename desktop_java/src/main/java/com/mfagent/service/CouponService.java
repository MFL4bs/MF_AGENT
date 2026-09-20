package com.mfagent.service;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Gestión de cupones de descuento por perfil.
 * Equivalente a agent/coupons.py
 */
public class CouponService {

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private final String profileId;

    public CouponService(String profileId) {
        this.profileId = profileId;
    }

    private Path file() {
        return ProfilePaths.dataDir(profileId).resolve("coupons.json");
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> load() {
        if (!Files.exists(file())) return new ArrayList<>();
        try {
            return GSON.fromJson(Files.readString(file()),
                    new TypeToken<List<Map<String, Object>>>(){}.getType());
        } catch (Exception e) {
            return new ArrayList<>();
        }
    }

    private void save(List<Map<String, Object>> coupons) {
        try {
            Files.createDirectories(file().getParent());
            Files.writeString(file(), GSON.toJson(coupons));
        } catch (Exception e) {
            System.err.println("[Coupons] Error guardando: " + e.getMessage());
        }
    }

    public List<Map<String, Object>> list() { return load(); }

    /** Alias público para CouponsView */
    public List<Map<String, Object>> loadAll() { return load(); }
    public void saveAll(List<Map<String, Object>> coupons) { save(coupons); }

    public Map<String, Object> add(String code, String type, double value,
                                    double minTotal, int maxUses, String expiresAt) {
        List<Map<String, Object>> coupons = load();
        String upper = code.strip().toUpperCase();
        if (coupons.stream().anyMatch(c -> upper.equals(c.get("code"))))
            return Map.of("ok", false, "msg", "El cupón '" + upper + "' ya existe.");

        Map<String, Object> coupon = new java.util.HashMap<>();
        coupon.put("code",       upper);
        coupon.put("type",       type);
        coupon.put("value",      value);
        coupon.put("min_total",  minTotal);
        coupon.put("active",     true);
        coupon.put("uses",       0);
        coupon.put("max_uses",   maxUses);
        coupon.put("expires_at", expiresAt != null ? expiresAt.strip() : "");
        coupons.add(coupon);
        save(coupons);
        return Map.of("ok", true, "coupon", coupon);
    }

    public void delete(String code) {
        List<Map<String, Object>> coupons = load();
        coupons.removeIf(c -> code.toUpperCase().equals(c.get("code")));
        save(coupons);
    }

    public boolean toggle(String code) {
        List<Map<String, Object>> coupons = load();
        for (Map<String, Object> c : coupons) {
            if (code.toUpperCase().equals(c.get("code"))) {
                boolean current = Boolean.TRUE.equals(c.get("active"));
                c.put("active", !current);
                save(coupons);
                return !current;
            }
        }
        return false;
    }

    public CouponResult validate(String code, double total) {
        String upper = code.strip().toUpperCase();
        List<Map<String, Object>> coupons = load();
        Map<String, Object> coupon = coupons.stream()
                .filter(c -> upper.equals(c.get("code")))
                .findFirst().orElse(null);

        if (coupon == null)
            return CouponResult.fail("El cupón *" + upper + "* no existe.", total);

        if (!Boolean.TRUE.equals(coupon.get("active")))
            return CouponResult.fail("El cupón *" + upper + "* está desactivado.", total);

        // Fecha límite
        String expiresAt = str(coupon, "expires_at");
        if (expiresAt != null && !expiresAt.isEmpty()) {
            try {
                if (LocalDate.now().isAfter(LocalDate.parse(expiresAt)))
                    return CouponResult.fail("El cupón *" + upper + "* venció el " + expiresAt + ".", total);
            } catch (Exception ignored) {}
        }

        // Límite de usos
        int maxUses = num(coupon, "max_uses");
        int uses    = num(coupon, "uses");
        if (maxUses > 0 && uses >= maxUses)
            return CouponResult.fail("El cupón *" + upper + "* ya alcanzó su límite de usos.", total);

        // Monto mínimo
        double minTotal = dbl(coupon, "min_total");
        if (total < minTotal)
            return CouponResult.fail("El cupón requiere un monto mínimo de $" + String.format("%,.0f", minTotal) + ".", total);

        // Calcular descuento
        double discount;
        String type = str(coupon, "type");
        if ("percent".equals(type)) {
            discount = total * (dbl(coupon, "value") / 100);
        } else {
            discount = Math.min(dbl(coupon, "value"), total);
        }
        double finalTotal = Math.max(0, total - discount);

        // Registrar uso
        coupon.put("uses", uses + 1);
        save(coupons);

        String label = "percent".equals(type)
                ? String.format("%.0f%%", dbl(coupon, "value"))
                : String.format("$%,.0f", dbl(coupon, "value"));
        return CouponResult.ok("✅ Cupón *" + upper + "* aplicado — " + label + " de descuento.",
                discount, finalTotal);
    }

    private String str(Map<String, Object> m, String key) {
        Object v = m.get(key); return v != null ? v.toString() : "";
    }
    private double dbl(Map<String, Object> m, String key) {
        Object v = m.get(key); if (v instanceof Number n) return n.doubleValue(); return 0;
    }
    private int num(Map<String, Object> m, String key) {
        Object v = m.get(key); if (v instanceof Number n) return n.intValue(); return 0;
    }

    public static class CouponResult {
        public final boolean ok;
        public final String  msg;
        public final double  discount;
        public final double  finalTotal;

        private CouponResult(boolean ok, String msg, double discount, double finalTotal) {
            this.ok = ok; this.msg = msg; this.discount = discount; this.finalTotal = finalTotal;
        }
        public static CouponResult ok(String msg, double discount, double finalTotal) {
            return new CouponResult(true, msg, discount, finalTotal);
        }
        public static CouponResult fail(String msg, double total) {
            return new CouponResult(false, msg, 0, total);
        }
    }
}
