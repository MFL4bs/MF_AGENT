package com.mfagent.service;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import com.mfagent.model.Product;

import java.io.*;
import java.nio.file.*;
import java.util.*;

/**
 * Motor del bot de WhatsApp.
 * Equivalente a bot.py — maneja estados por teléfono, menús, carrito y cupones.
 */
public class BotService {

    // Estados
    public static final String MENU_PRINCIPAL  = "menu_principal";
    public static final String MENU_CATALOGO   = "menu_catalogo";
    public static final String SELECCIONANDO   = "seleccionando";
    public static final String ESPERANDO_CUPON = "esperando_cupon";
    public static final String ESPERANDO_NOMBRE = "esperando_nombre";
    public static final String CALIFICANDO     = "calificando";

    private static final Gson GSON = new Gson();

    private final String profileId;
    private final LocalInventory inventory;
    private final CouponService coupons;

    public BotService(String profileId) {
        this.profileId = profileId;
        this.inventory = new LocalInventory(profileId);
        this.coupons   = new CouponService(profileId);
    }

    // ── Estado por teléfono ───────────────────────────────────────────────────

    private Path statesFile() {
        return ProfilePaths.dataDir(profileId).resolve("chat_states.json");
    }

    public Map<String, Object> getState(String phone) {
        Path f = statesFile();
        if (!Files.exists(f)) return defaultState();
        try {
            Map<String, Map<String, Object>> all = GSON.fromJson(
                    Files.readString(f), new TypeToken<Map<String, Map<String, Object>>>(){}.getType());
            return all.getOrDefault(phone, defaultState());
        } catch (Exception e) { return defaultState(); }
    }

    public void setState(String phone, String step, Map<String, Object> extra) {
        Path f = statesFile();
        Map<String, Map<String, Object>> all = new HashMap<>();
        if (Files.exists(f)) {
            try {
                all = GSON.fromJson(Files.readString(f),
                        new TypeToken<Map<String, Map<String, Object>>>(){}.getType());
            } catch (Exception ignored) {}
        }
        Map<String, Object> state = new HashMap<>();
        state.put("step", step);
        if (extra != null) state.putAll(extra);
        all.put(phone, state);
        try { Files.writeString(f, GSON.toJson(all)); } catch (Exception ignored) {}
    }

    private Map<String, Object> defaultState() {
        Map<String, Object> s = new HashMap<>();
        s.put("step", MENU_PRINCIPAL);
        return s;
    }

    // ── Menús ─────────────────────────────────────────────────────────────────

    public String menuPrincipal(String profileName) {
        String bienvenida = (profileName != null && !profileName.isEmpty())
                ? "Hola! Bienvenido a " + profileName + "."
                : "Hola! Bienvenido.";
        return bienvenida + " En que puedo ayudarte?\n\n"
                + "1. Ver catalogo de productos\n"
                + "2. Hablar con un asesor\n\n"
                + "Escribe el numero de tu opcion.";
    }

    public String menuCatalogo(List<Map<String, Object>> carrito) {
        List<Product> products = inventory.list().stream()
                .filter(p -> p.getStock() > 0).toList();
        if (products.isEmpty()) {
            return "No hay productos disponibles en este momento.\n\n"
                    + "Para mas informacion contacta a un asesor.\n\n0. Volver al menu";
        }
        StringBuilder sb = new StringBuilder("--- CATALOGO DE PRODUCTOS ---\n\n");
        for (int i = 0; i < products.size(); i++) {
            Product p = products.get(i);
            sb.append(i + 1).append(". ").append(p.getName()).append("\n")
              .append("   Precio: ").append(fmt(p.getPrice()))
              .append("  |  Stock: ").append(p.getStock()).append(" und");
            if (p.getDescription() != null && !p.getDescription().isEmpty())
                sb.append("\n   ").append(p.getDescription());
            sb.append("\n\n");
        }
        if (carrito != null && !carrito.isEmpty()) {
            sb.append("🛒 *Tu seleccion actual:*\n");
            double total = 0;
            for (Map<String, Object> item : carrito) {
                double price = ((Number) item.get("price")).doubleValue();
                int qty = ((Number) item.get("qty")).intValue();
                double sub = price * qty;
                total += sub;
                sb.append("  • ").append(item.get("name")).append(" x").append(qty)
                  .append(" = ").append(fmt(sub)).append("\n");
            }
            sb.append("  *Total estimado: ").append(fmt(total)).append("*\n\n");
            sb.append("Escribe el *numero* para agregar otro producto.\n");
            sb.append("Escribe *listo* para continuar con tu pedido.\n");
        } else {
            sb.append("Escribe el *numero* del producto que te interesa.\n");
            sb.append("Cuando termines escribe *listo*.\n");
        }
        sb.append("0. Volver al menu");
        return sb.toString();
    }

    private String resumenPedido(List<Map<String, Object>> carrito) {
        StringBuilder sb = new StringBuilder("📋 *RESUMEN DEL PEDIDO*\n\n");
        double total = 0;
        for (Map<String, Object> item : carrito) {
            double price = ((Number) item.get("price")).doubleValue();
            int qty = ((Number) item.get("qty")).intValue();
            double sub = price * qty;
            total += sub;
            sb.append("  • ").append(item.get("name")).append(" x").append(qty)
              .append(" — ").append(fmt(sub)).append("\n");
        }
        sb.append("\n*Total estimado: ").append(fmt(total)).append("*");
        return sb.toString();
    }

    private String fmt(double price) {
        return String.format("$%,.0f COP", price).replace(",", ".");
    }

    // ── Motor principal ───────────────────────────────────────────────────────

    /**
     * Procesa un mensaje entrante y retorna la respuesta.
     * @return BotReply con texto y evento opcional
     */
    @SuppressWarnings("unchecked")
    public BotReply reply(String phone, String message, String profileName) {
        String msg    = message.trim();
        String msgLow = msg.toLowerCase();
        Map<String, Object> state = getState(phone);
        String step = (String) state.getOrDefault("step", MENU_PRINCIPAL);

        // Volver al menú desde cualquier punto
        if (Set.of("0","menu","inicio","volver","cancelar","hola","buenas",
                   "buenos dias","buenas tardes","buenas noches").contains(msgLow)) {
            setState(phone, MENU_PRINCIPAL, null);
            return new BotReply(menuPrincipal(profileName), null);
        }

        // CALIFICANDO
        if (CALIFICANDO.equals(step)) {
            Map<String, String> ratings = Map.of("1","Excelente","2","Bueno","3","Regular","4","Malo");
            String rating = ratings.get(msgLow);
            setState(phone, MENU_PRINCIPAL, null);
            if (rating != null)
                return new BotReply("Gracias por tu calificacion: " + rating + "!\n"
                        + "Fue un placer atenderte. Hasta pronto!\n\nEscribe 0 si necesitas algo mas.",
                        new Object[]{"rating", rating});
            return new BotReply(menuCalificacion(), null);
        }

        // MENU PRINCIPAL
        if (MENU_PRINCIPAL.equals(step)) {
            if ("1".equals(msgLow)) {
                setState(phone, SELECCIONANDO, Map.of("carrito", new ArrayList<>()));
                return new BotReply(menuCatalogo(null), null);
            }
            if (Set.of("2","asesor","humano","persona").contains(msgLow)) {
                setState(phone, ESPERANDO_NOMBRE, null);
                return new BotReply("Con gusto te conecto con un asesor.\n\n"
                        + "Por favor enviame tu nombre y numero de celular:\n"
                        + "Ejemplo: Juan Perez 3001234567", null);
            }
            return new BotReply(menuPrincipal(profileName), null);
        }

        // SELECCIONANDO
        if (SELECCIONANDO.equals(step)) {
            List<Product> products = inventory.list().stream().filter(p -> p.getStock() > 0).toList();
            List<Map<String, Object>> carrito = (List<Map<String, Object>>) state.getOrDefault("carrito", new ArrayList<>());

            if (Set.of("listo","ya","continuar","siguiente","ok","confirmar").contains(msgLow)) {
                if (carrito.isEmpty())
                    return new BotReply("Aun no has seleccionado ningun producto.\n\n" + menuCatalogo(carrito), null);
                String resumen = resumenPedido(carrito);
                setState(phone, ESPERANDO_CUPON, Map.of("carrito", carrito));
                return new BotReply(resumen + "\n\nTienes un *cupon de descuento*?\n"
                        + "Escribe el codigo o escribe *no* para continuar.", null);
            }

            if (msgLow.matches("\\d+")) {
                int idx = Integer.parseInt(msgLow);
                if (idx >= 1 && idx <= products.size()) {
                    Product prod = products.get(idx - 1);
                    boolean found = false;
                    for (Map<String, Object> item : carrito) {
                        if (prod.getSku().equals(item.get("sku"))) {
                            item.put("qty", ((Number) item.get("qty")).intValue() + 1);
                            found = true; break;
                        }
                    }
                    if (!found) {
                        Map<String, Object> item = new HashMap<>();
                        item.put("sku", prod.getSku());
                        item.put("name", prod.getName());
                        item.put("price", prod.getPrice());
                        item.put("qty", 1);
                        carrito.add(item);
                    }
                    setState(phone, SELECCIONANDO, Map.of("carrito", carrito));
                    return new BotReply("✅ *" + prod.getName() + "* agregado.\n\n" + menuCatalogo(carrito), null);
                }
                return new BotReply("Numero no valido. Elige entre 1 y " + products.size()
                        + ".\n\n" + menuCatalogo(carrito), null);
            }

            if (msgLow.contains("asesor")) {
                setState(phone, ESPERANDO_NOMBRE, carrito.isEmpty() ? null : Map.of("carrito", carrito));
                return new BotReply("Con gusto te conecto con un asesor.\n\n"
                        + "Por favor enviame tu nombre y numero de celular:\n"
                        + "Ejemplo: Juan Perez 3001234567", null);
            }
            return new BotReply(menuCatalogo(carrito), null);
        }

        // ESPERANDO CUPÓN
        if (ESPERANDO_CUPON.equals(step)) {
            List<Map<String, Object>> carrito = (List<Map<String, Object>>) state.getOrDefault("carrito", new ArrayList<>());
            double total = carrito.stream().mapToDouble(i -> ((Number)i.get("price")).doubleValue() * ((Number)i.get("qty")).intValue()).sum();

            if (Set.of("no","no tengo","sin cupon","ninguno","n").contains(msgLow)) {
                setState(phone, ESPERANDO_NOMBRE, Map.of("carrito", carrito));
                return new BotReply("Perfecto! Para continuar necesito tus datos.\n"
                        + "Por favor enviame tu nombre y numero de celular:\n"
                        + "Ejemplo: Juan Perez 3001234567", null);
            }

            CouponService.CouponResult result = coupons.validate(msg.trim(), total);
            if (result.ok) {
                List<Map<String, Object>> carritoDesc = new ArrayList<>(carrito);
                Map<String, Object> desc = new HashMap<>();
                desc.put("sku", "DESC"); desc.put("name", "Descuento cupon " + msg.trim().toUpperCase());
                desc.put("price", -result.discount); desc.put("qty", 1);
                carritoDesc.add(desc);
                setState(phone, ESPERANDO_NOMBRE, Map.of("carrito", carritoDesc));
                return new BotReply(result.msg + "\n\nTotal original: " + fmt(total)
                        + "\nDescuento: -" + fmt(result.discount)
                        + "\n*Total final: " + fmt(result.finalTotal) + "*\n\n"
                        + "Para continuar necesito tus datos.\n"
                        + "Por favor enviame tu nombre y numero de celular:\n"
                        + "Ejemplo: Juan Perez 3001234567", null);
            }
            return new BotReply(result.msg + "\n\nIntenta con otro codigo o escribe *no* para continuar sin descuento.", null);
        }

        // ESPERANDO NOMBRE
        if (ESPERANDO_NOMBRE.equals(step)) {
            List<Map<String, Object>> carrito = (List<Map<String, Object>>) state.getOrDefault("carrito", new ArrayList<>());
            setState(phone, MENU_PRINCIPAL, null);
            String firstName = msg.trim().isEmpty() ? "" : msg.trim().split("\\s+")[0];
            if (!carrito.isEmpty()) {
                String resumen = resumenPedido(carrito);
                return new BotReply("Gracias " + firstName + "!\n\n"
                        + "Un asesor te contactara pronto con los detalles de tu pedido.\n\n"
                        + "Escribe 0 si necesitas algo mas.",
                        new Object[]{"transfer_con_pedido", msg.trim(), carrito, resumen});
            }
            return new BotReply("Gracias! Un asesor te contactara pronto.\n\n"
                    + "Escribe 0 si necesitas algo mas.",
                    new Object[]{"transfer_con_nombre", msg.trim()});
        }

        setState(phone, MENU_PRINCIPAL, null);
        return new BotReply(menuPrincipal(profileName), null);
    }

    public void triggerCalificacion(String phone) {
        setState(phone, CALIFICANDO, null);
    }

    private String menuCalificacion() {
        return "Como calificarias la atencion recibida?\n\n"
                + "1. Excelente\n2. Bueno\n3. Regular\n4. Malo\n\nEscribe el numero.";
    }

    // ── Asesores ──────────────────────────────────────────────────────────────

    public List<Map<String, Object>> loadAdvisors() {
        Path f = ProfilePaths.dataDir(profileId).resolve("advisors.json");
        if (!Files.exists(f)) return new ArrayList<>();
        try {
            return GSON.fromJson(Files.readString(f), new TypeToken<List<Map<String, Object>>>(){}.getType());
        } catch (Exception e) { return new ArrayList<>(); }
    }

    public void saveAdvisors(List<Map<String, Object>> advisors) {
        Path f = ProfilePaths.dataDir(profileId).resolve("advisors.json");
        try { Files.writeString(f, GSON.toJson(advisors)); } catch (Exception ignored) {}
    }

    // ── Manuales ──────────────────────────────────────────────────────────────

    public String loadManual(String manualName) {
        Path f = ProfilePaths.dataDir(profileId).resolve("manuals").resolve(manualName + ".txt");
        if (!Files.exists(f)) return "";
        try { return Files.readString(f); } catch (Exception e) { return ""; }
    }

    public void saveManual(String manualName, String content) {
        Path dir = ProfilePaths.dataDir(profileId).resolve("manuals");
        Path file = dir.resolve(manualName + ".txt");
        try {
            if (content == null) { Files.deleteIfExists(file); return; }
            Files.createDirectories(dir);
            Files.writeString(file, content);
        } catch (Exception ignored) {}
    }

    public List<String> listManuals() {
        Path dir = ProfilePaths.dataDir(profileId).resolve("manuals");
        if (!Files.exists(dir)) return new ArrayList<>();
        try {
            return Files.list(dir)
                    .filter(p -> p.toString().endsWith(".txt"))
                    .map(p -> p.getFileName().toString().replace(".txt", ""))
                    .toList();
        } catch (Exception e) { return new ArrayList<>(); }
    }

    // ── DTO ───────────────────────────────────────────────────────────────────

    public record BotReply(String text, Object[] event) {}
}
