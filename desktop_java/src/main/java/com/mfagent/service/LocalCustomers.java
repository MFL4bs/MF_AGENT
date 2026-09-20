package com.mfagent.service;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;

import java.nio.file.*;
import java.util.*;

/**
 * CRUD de clientes local por perfil.
 * Equivalente a agent/local_customers.py
 */
public class LocalCustomers {

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private final String profileId;

    public LocalCustomers(String profileId) {
        this.profileId = profileId;
    }

    private Path file() {
        return ProfilePaths.dataDir(profileId).resolve("customers.json");
    }

    private List<Map<String, Object>> load() {
        if (!Files.exists(file())) return new ArrayList<>();
        try {
            return GSON.fromJson(Files.readString(file()),
                    new TypeToken<List<Map<String, Object>>>(){}.getType());
        } catch (Exception e) { return new ArrayList<>(); }
    }

    private void save(List<Map<String, Object>> customers) {
        try {
            Files.createDirectories(file().getParent());
            Files.writeString(file(), GSON.toJson(customers));
        } catch (Exception e) { System.err.println("[Customers] " + e.getMessage()); }
    }

    public List<Map<String, Object>> list() {
        List<Map<String, Object>> all = load();
        all.sort(Comparator.comparing(c -> c.getOrDefault("name", "").toString().toLowerCase()));
        return all;
    }

    public List<Map<String, Object>> search(String query) {
        String q = query.toLowerCase();
        return load().stream().filter(c ->
                c.getOrDefault("name",    "").toString().toLowerCase().contains(q) ||
                c.getOrDefault("phone",   "").toString().toLowerCase().contains(q) ||
                c.getOrDefault("address", "").toString().toLowerCase().contains(q)
        ).toList();
    }

    public Map<String, Object> upsert(Map<String, Object> customer) {
        List<Map<String, Object>> all = load();
        if (customer.get("id") == null || customer.get("id").toString().isEmpty())
            customer.put("id", UUID.randomUUID().toString().substring(0, 8));
        all.removeIf(c -> c.get("id").equals(customer.get("id")));
        all.add(customer);
        save(all);
        return customer;
    }

    public void delete(String id) {
        List<Map<String, Object>> all = load();
        all.removeIf(c -> id.equals(c.get("id")));
        save(all);
    }

    /** Importa clientes únicos desde el historial de ventas. Retorna cantidad agregada. */
    public int importFromSales() {
        List<Map<String, Object>> existing = load();
        Set<String> keys = new HashSet<>();
        for (Map<String, Object> c : existing)
            keys.add(c.getOrDefault("name","").toString().trim().toLowerCase()
                    + "|" + c.getOrDefault("phone","").toString().trim());

        int added = 0;
        for (var inv : new LocalSales(profileId).list(9999)) {
            String name  = inv.getCustomer()      != null ? inv.getCustomer().trim()         : "";
            String phone = inv.getCustomerPhone() != null ? inv.getCustomerPhone().trim()    : "";
            if (name.isEmpty()) continue;
            String key = name.toLowerCase() + "|" + phone;
            if (keys.contains(key)) continue;
            keys.add(key);
            Map<String, Object> c = new LinkedHashMap<>();
            c.put("id",      UUID.randomUUID().toString().substring(0, 8));
            c.put("name",    name);
            c.put("phone",   phone);
            c.put("address", inv.getCustomerAddress() != null ? inv.getCustomerAddress().trim() : "");
            c.put("rfc",     inv.getCustomerRfc()     != null ? inv.getCustomerRfc().trim()     : "");
            existing.add(c);
            added++;
        }
        if (added > 0) save(existing);
        return added;
    }
}
