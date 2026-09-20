package com.mfagent.service;

import com.mfagent.model.Product;

import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * CRUD de inventario local por perfil.
 * Equivalente a agent/local_inventory.py
 */
public class LocalInventory {

    private final Path file;

    public LocalInventory(String profileId) {
        this.file = ProfilePaths.dataDir(profileId).resolve("inventory.json");
    }

    public List<Product> list() {
        return JsonStore.readList(file, Product.class)
                .stream()
                .sorted(Comparator.comparing(p -> p.getName().toLowerCase()))
                .collect(Collectors.toList());
    }

    public Optional<Product> get(String sku) {
        return JsonStore.readList(file, Product.class)
                .stream()
                .filter(p -> sku.equals(p.getSku()))
                .findFirst();
    }

    public void upsert(Product product) {
        List<Product> items = JsonStore.readList(file, Product.class);
        items.removeIf(p -> p.getSku().equals(product.getSku()));
        items.add(product);
        JsonStore.writeList(file, items);
    }

    public void update(String sku, Product updates) {
        List<Product> items = JsonStore.readList(file, Product.class);
        for (Product p : items) {
            if (p.getSku().equals(sku)) {
                if (updates.getName() != null)        p.setName(updates.getName());
                if (updates.getDescription() != null) p.setDescription(updates.getDescription());
                if (updates.getPrice() > 0)           p.setPrice(updates.getPrice());
                if (updates.getCostPrice() >= 0)      p.setCostPrice(updates.getCostPrice());
                if (updates.getStock() >= 0)          p.setStock(updates.getStock());
                if (updates.getCategory() != null)    p.setCategory(updates.getCategory());
                if (updates.getImageUrl() != null)    p.setImageUrl(updates.getImageUrl());
                break;
            }
        }
        JsonStore.writeList(file, items);
    }

    public void updateStock(String sku, int newStock) {
        List<Product> items = JsonStore.readList(file, Product.class);
        items.stream().filter(p -> p.getSku().equals(sku))
                .findFirst().ifPresent(p -> p.setStock(newStock));
        JsonStore.writeList(file, items);
    }

    public void delete(String sku) {
        List<Product> items = JsonStore.readList(file, Product.class);
        items.removeIf(p -> p.getSku().equals(sku));
        JsonStore.writeList(file, items);
    }

    public List<Product> lowStock(int threshold) {
        return list().stream()
                .filter(p -> p.getStock() <= threshold)
                .collect(Collectors.toList());
    }

    /** Genera el siguiente SKU disponible (PROD-0001, PROD-0002, ...) */
    public String nextSku() {
        List<Product> items = JsonStore.readList(file, Product.class);
        int max = items.stream()
                .map(Product::getSku)
                .filter(s -> s != null && s.startsWith("PROD-"))
                .map(s -> s.substring(5))
                .filter(s -> s.matches("\\d+"))
                .mapToInt(Integer::parseInt)
                .max().orElse(0);
        return String.format("PROD-%04d", max + 1);
    }
}
