package com.mfagent.service;

import com.google.cloud.firestore.*;
import com.mfagent.model.Product;
import com.mfagent.model.Invoice;

import java.util.*;
import java.util.concurrent.ExecutionException;
import java.util.function.Consumer;

/**
 * Sincronización bidireccional PC ↔ Firestore.
 * Equivalente a SyncWorker, PullWorker, FirestoreListener en firestore_sync.py
 */
public class FirestoreSync {

    private final String profileId;
    private final LocalInventory inventory;
    private final LocalSales sales;
    private final LocalCustomers customers;
    private ListenerRegistration invoiceListener;
    private ListenerRegistration inventoryListener;
    private ListenerRegistration customerListener;

    public FirestoreSync(String profileId) {
        this.profileId = profileId;
        this.inventory  = new LocalInventory(profileId);
        this.sales      = new LocalSales(profileId);
        this.customers  = new LocalCustomers(profileId);
    }

    // ── Push: local → Firestore ───────────────────────────────────────────────

    public void syncAll(Runnable onDone) {
        Thread t = new Thread(() -> {
            try {
                Firestore db = FirebaseService.getDataDb();
                pushInventory(db);
                pushSales(db);
                pushCustomers(db);
                pushProfile(db);
                System.out.println("[Sync] OK: inventario + ventas + clientes + perfil");
            } catch (Exception e) {
                System.err.println("[Sync] Error: " + e.getMessage());
            } finally {
                if (onDone != null) onDone.run();
            }
        }, "firestore-sync");
        t.setDaemon(true);
        t.start();
    }

    private void pushInventory(Firestore db) throws Exception {
        List<Product> products = inventory.list();
        if (products.isEmpty()) return;
        WriteBatch batch = db.batch();
        for (Product p : products) {
            Map<String, Object> data = productToMap(p);
            data.put("profile_id", profileId);
            DocumentReference ref = db.collection("inventory")
                    .document(profileId + "_" + p.getSku());
            batch.set(ref, data, SetOptions.merge());
        }
        batch.commit().get();
    }

    private void pushSales(Firestore db) throws Exception {
        List<Invoice> invoices = sales.list();
        if (invoices.isEmpty()) return;
        WriteBatch batch = db.batch();
        for (Invoice inv : invoices) {
            Map<String, Object> data = invoiceToMap(inv);
            data.put("profile_id", profileId);
            if (inv.getInvoiceId() != null) {
                DocumentReference ref = db.collection("invoices").document(inv.getInvoiceId());
                batch.set(ref, data, SetOptions.merge());
            }
        }
        batch.commit().get();
    }

    private void pushCustomers(Firestore db) throws Exception {
        List<Map<String, Object>> list = customers.list();
        if (list.isEmpty()) return;
        WriteBatch batch = db.batch();
        for (Map<String, Object> c : list) {
            String id = c.getOrDefault("id", "").toString();
            if (id.isEmpty()) continue;
            Map<String, Object> data = new HashMap<>(c);
            data.put("profile_id", profileId);
            batch.set(db.collection("customers").document(profileId + "_" + id), data, SetOptions.merge());
        }
        batch.commit().get();
    }

    private void pullCustomers(Firestore db) throws Exception {
        QuerySnapshot snap = db.collection("customers")
                .whereEqualTo("profile_id", profileId).get().get();
        for (QueryDocumentSnapshot doc : snap.getDocuments()) {
            Map<String, Object> data = new HashMap<>(doc.getData());
            data.remove("profile_id");
            if (data.get("id") != null) customers.upsert(data);
        }
    }

    public void syncInvoice(Invoice inv) {
        Thread t = new Thread(() -> {
            try {
                Map<String, Object> data = invoiceToMap(inv);
                data.put("profile_id", profileId);
                FirebaseService.getDataDb()
                        .collection("invoices")
                        .document(inv.getInvoiceId())
                        .set(data).get();
                System.out.println("[Sync] Factura subida: " + inv.getInvoiceId() + " by " + inv.getRegisteredBy());
            } catch (Exception e) {
                System.err.println("[Sync] Error subiendo factura: " + e.getMessage());
            }
        }, "fs-sync-invoice");
        t.setDaemon(true);
        t.start();
    }

    public void syncCustomer(Map<String, Object> customer) {
        Thread t = new Thread(() -> {
            try {
                String id = customer.getOrDefault("id", "").toString();
                if (id.isEmpty()) return;
                Map<String, Object> data = new HashMap<>(customer);
                data.put("profile_id", profileId);
                FirebaseService.getDataDb()
                        .collection("customers")
                        .document(profileId + "_" + id)
                        .set(data, SetOptions.merge()).get();
            } catch (Exception e) {
                System.err.println("[Firestore] Error sync cliente: " + e.getMessage());
            }
        }, "fs-sync-customer");
        t.setDaemon(true);
        t.start();
    }

    private void pushProfile(Firestore db) throws Exception {
        LicenseService licService = new LicenseService();
        String key = licService.loadLocalKey();
        if (key == null) return;

        Map<String, Object> data = new HashMap<>();
        data.put("id", profileId);
        data.put("key", key);
        db.collection("profiles").document(profileId).set(data, SetOptions.merge()).get();
    }

    // ── Pull: Firestore → local ───────────────────────────────────────────────

    public void pullAll(Runnable onDone) {
        Thread t = new Thread(() -> {
            try {
                Firestore db = FirebaseService.getDataDb();
                pullInventory(db);
                pullSales(db);
                pullCustomers(db);
                System.out.println("[Pull] OK");
            } catch (Exception e) {
                System.err.println("[Pull] Error: " + e.getMessage());
            } finally {
                if (onDone != null) onDone.run();
            }
        }, "firestore-pull");
        t.setDaemon(true);
        t.start();
    }

    private void pullInventory(Firestore db) throws Exception {
        QuerySnapshot snap = db.collection("inventory")
                .whereEqualTo("profile_id", profileId).get().get();
        if (snap.isEmpty()) return;
        Map<String, Product> map = new LinkedHashMap<>();
        for (Product p : inventory.list()) map.put(p.getSku(), p);
        for (QueryDocumentSnapshot doc : snap.getDocuments()) {
            Product p = mapToProduct(doc.getData());
            if (p.getSku() != null) map.put(p.getSku(), p);
        }
        JsonStore.writeList(ProfilePaths.dataDir(profileId).resolve("inventory.json"),
                new ArrayList<>(map.values()));
        System.out.println("[Pull] Inventario: " + map.size() + " productos");
    }

    private void pullSales(Firestore db) throws Exception {
        QuerySnapshot snap = db.collection("invoices")
                .whereEqualTo("profile_id", profileId).get().get();
        if (snap.isEmpty()) return;
        for (QueryDocumentSnapshot doc : snap.getDocuments()) {
            Invoice inv = mapToInvoice(doc.getData());
            if (inv.getInvoiceId() != null) sales.record(inv);
        }
    }

    // ── Listeners en tiempo real ──────────────────────────────────────────────

    public void startInvoiceListener(Consumer<Invoice> onNew, Consumer<String> onDeleted) {
        Firestore db = FirebaseService.getDataDb();
        // Solo registrar IDs conocidos ANTES de arrancar — el primer snapshot
        // (estado inicial) los marcará como ya vistos sin notificar.
        Set<String> knownIds = new HashSet<>();
        final boolean[] initialized = {false};

        invoiceListener = db.collection("invoices")
                .whereEqualTo("profile_id", profileId)
                .addSnapshotListener((snap, e) -> {
                    if (e != null || snap == null) return;

                    if (!initialized[0]) {
                        // Primer disparo: cargar estado actual sin notificar
                        for (DocumentChange change : snap.getDocumentChanges()) {
                            if (change.getType() == DocumentChange.Type.ADDED) {
                                String docId = change.getDocument().getId();
                                knownIds.add(docId);
                                Invoice inv = mapToInvoice(change.getDocument().getData());
                                if (inv.getInvoiceId() != null) sales.record(inv);
                            }
                        }
                        initialized[0] = true;
                        return;
                    }

                    for (DocumentChange change : snap.getDocumentChanges()) {
                        String docId = change.getDocument().getId();
                        switch (change.getType()) {
                            case REMOVED -> {
                                knownIds.remove(docId);
                                sales.delete(docId);
                                if (onDeleted != null) onDeleted.accept(docId);
                            }
                            case ADDED -> {
                                if (knownIds.contains(docId)) break;
                                knownIds.add(docId);
                                Invoice inv = mapToInvoice(change.getDocument().getData());
                                if (inv.getInvoiceId() == null) break;
                                sales.record(inv);
                                String ch = inv.getChannel();
                                boolean fromPc = "pc".equals(ch) || "manual".equals(ch);
                                if (!fromPc && onNew != null) onNew.accept(inv);
                            }
                            case MODIFIED -> {
                                Invoice inv = mapToInvoice(change.getDocument().getData());
                                if (inv.getInvoiceId() != null) {
                                    sales.delete(inv.getInvoiceId());
                                    sales.record(inv);
                                }
                            }
                        }
                    }
                });
    }

    public void startInventoryListener(Runnable onChange) {
        Firestore db = FirebaseService.getDataDb();
        final boolean[] initialized = {false};
        inventoryListener = db.collection("inventory")
                .whereEqualTo("profile_id", profileId)
                .addSnapshotListener((snap, e) -> {
                    if (e != null || snap == null) return;
                    if (!initialized[0]) {
                        // Primer disparo: ignorar, el pullAll ya cargó todo
                        initialized[0] = true;
                        return;
                    }
                    boolean changed = false;
                    for (DocumentChange change : snap.getDocumentChanges()) {
                        Map<String, Object> data = change.getDocument().getData();
                        switch (change.getType()) {
                            case ADDED, MODIFIED -> {
                                Product p = mapToProduct(data);
                                if (p.getSku() != null) { inventory.upsert(p); changed = true; }
                            }
                            case REMOVED -> {
                                String sku = str(data, "sku");
                                if (sku != null) { inventory.delete(sku); changed = true; }
                            }
                        }
                    }
                    if (changed && onChange != null) onChange.run();
                });
    }

    public void startCustomerListener(Runnable onChange) {
        Firestore db = FirebaseService.getDataDb();
        customerListener = db.collection("customers")
                .whereEqualTo("profile_id", profileId)
                .addSnapshotListener((snap, e) -> {
                    if (e != null || snap == null) return;
                    for (DocumentChange change : snap.getDocumentChanges()) {
                        Map<String, Object> data = new HashMap<>(change.getDocument().getData());
                        data.remove("profile_id");
                        switch (change.getType()) {
                            case ADDED, MODIFIED -> {
                                if (data.get("id") != null) customers.upsert(data);
                            }
                            case REMOVED -> {
                                String id = change.getDocument().getId().replace(profileId + "_", "");
                                customers.delete(id);
                            }
                        }
                    }
                    if (onChange != null) onChange.run();
                });
    }

    public void stopListeners() {
        if (invoiceListener   != null) { invoiceListener.remove();   invoiceListener   = null; }
        if (inventoryListener != null) { inventoryListener.remove(); inventoryListener = null; }
        if (customerListener  != null) { customerListener.remove();  customerListener  = null; }
    }

    // ── Operaciones puntuales ─────────────────────────────────────────────────

    public void deleteProduct(String sku) {
        Thread t = new Thread(() -> {
            try {
                FirebaseService.getDataDb()
                        .collection("inventory")
                        .document(profileId + "_" + sku)
                        .delete().get();
            } catch (Exception e) {
                System.err.println("[Firestore] Error borrando producto " + sku + ": " + e.getMessage());
            }
        }, "fs-delete");
        t.setDaemon(true);
        t.start();
    }

    public void deleteInvoice(String invoiceId) {
        Thread t = new Thread(() -> {
            try {
                FirebaseService.getDataDb()
                        .collection("invoices")
                        .document(invoiceId)
                        .delete().get();
            } catch (Exception e) {
                System.err.println("[Firestore] Error borrando factura " + invoiceId + ": " + e.getMessage());
            }
        }, "fs-delete-inv");
        t.setDaemon(true);
        t.start();
    }

    public void updateStock(String sku, int newStock) {
        Thread t = new Thread(() -> {
            try {
                FirebaseService.getDataDb()
                        .collection("inventory")
                        .document(profileId + "_" + sku)
                        .update("stock", newStock).get();
            } catch (Exception e) {
                System.err.println("[Firestore] Error actualizando stock " + sku + ": " + e.getMessage());
            }
        }, "fs-stock");
        t.setDaemon(true);
        t.start();
    }

    // ── Conversores ───────────────────────────────────────────────────────────

    private Map<String, Object> productToMap(Product p) {
        Map<String, Object> m = new HashMap<>();
        m.put("sku",         p.getSku());
        m.put("name",        p.getName());
        m.put("description", p.getDescription());
        m.put("price",       p.getPrice());
        m.put("cost_price",  p.getCostPrice());
        m.put("stock",       p.getStock());
        m.put("category",    p.getCategory());
        m.put("image_url",   p.getImageUrl());
        return m;
    }

    private Product mapToProduct(Map<String, Object> m) {
        Product p = new Product();
        p.setSku(str(m, "sku"));
        p.setName(str(m, "name"));
        p.setDescription(str(m, "description"));
        p.setPrice(dbl(m, "price"));
        p.setCostPrice(dbl(m, "cost_price"));
        p.setStock((int) lng(m, "stock"));
        p.setCategory(str(m, "category"));
        p.setImageUrl(str(m, "image_url"));
        return p;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> invoiceToMap(Invoice inv) {
        Map<String, Object> m = new HashMap<>();
        m.put("invoice_id",       inv.getInvoiceId());
        m.put("timestamp",        inv.getTimestamp());
        m.put("customer",         inv.getCustomer());
        m.put("customer_phone",   inv.getCustomerPhone());
        m.put("customer_address", inv.getCustomerAddress());
        m.put("customer_rfc",     inv.getCustomerRfc());
        m.put("notes",            inv.getNotes());
        m.put("channel",          inv.getChannel());
        m.put("registered_by",    inv.getRegisteredBy());
        m.put("business_name",    inv.getBusinessName());
        m.put("total",            inv.getTotal());
        List<Map<String, Object>> items = new ArrayList<>();
        if (inv.getItems() != null) {
            for (var item : inv.getItems()) {
                Map<String, Object> im = new HashMap<>();
                im.put("sku",          item.getSku());
                im.put("product_name", item.getProductName());
                im.put("quantity",     item.getQuantity());
                im.put("unit_price",   item.getUnitPrice());
                im.put("subtotal",     item.getSubtotal());
                items.add(im);
            }
        }
        m.put("items", items);
        return m;
    }

    @SuppressWarnings("unchecked")
    private Invoice mapToInvoice(Map<String, Object> m) {
        Invoice inv = new Invoice();
        inv.setInvoiceId(str(m, "invoice_id"));
        inv.setTimestamp(str(m, "timestamp"));
        inv.setCustomer(str(m, "customer"));
        inv.setCustomerPhone(str(m, "customer_phone"));
        inv.setCustomerAddress(str(m, "customer_address"));
        inv.setCustomerRfc(str(m, "customer_rfc"));
        inv.setNotes(str(m, "notes"));
        inv.setChannel(str(m, "channel"));
        inv.setRegisteredBy(str(m, "registered_by"));
        inv.setBusinessName(str(m, "business_name"));
        inv.setTotal(dbl(m, "total"));
        List<com.mfagent.model.InvoiceItem> items = new ArrayList<>();
        Object rawItems = m.get("items");
        if (rawItems instanceof List<?> list) {
            for (Object o : list) {
                if (o instanceof Map<?, ?> im) {
                    Map<String, Object> imap = (Map<String, Object>) im;
                    com.mfagent.model.InvoiceItem item = new com.mfagent.model.InvoiceItem();
                    item.setSku(str(imap, "sku"));
                    item.setProductName(str(imap, "product_name"));
                    item.setQuantity((int) lng(imap, "quantity"));
                    item.setUnitPrice(dbl(imap, "unit_price"));
                    item.setSubtotal(dbl(imap, "subtotal"));
                    items.add(item);
                }
            }
        }
        inv.setItems(items);
        return inv;
    }

    private String str(Map<String, Object> m, String key) {
        Object v = m.get(key); return v != null ? v.toString() : null;
    }
    private double dbl(Map<String, Object> m, String key) {
        Object v = m.get(key); if (v == null) return 0;
        if (v instanceof Number n) return n.doubleValue(); return 0;
    }
    private long lng(Map<String, Object> m, String key) {
        Object v = m.get(key); if (v == null) return 0;
        if (v instanceof Number n) return n.longValue(); return 0;
    }
    private boolean equals(Product a, Product b) {
        return a.getStock() == b.getStock()
                && a.getPrice() == b.getPrice()
                && Objects.equals(a.getName(), b.getName());
    }
}
