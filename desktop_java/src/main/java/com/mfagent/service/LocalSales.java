package com.mfagent.service;

import com.mfagent.model.Invoice;

import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

/**
 * CRUD de ventas/facturas locales por perfil.
 * Equivalente a agent/local_sales.py
 */
public class LocalSales {

    private final Path file;

    public LocalSales(String profileId) {
        this.file = ProfilePaths.dataDir(profileId).resolve("sales.json");
    }

    public List<Invoice> list(int limit) {
        return JsonStore.readList(file, Invoice.class)
                .stream()
                .sorted(Comparator.comparing(
                        (Invoice i) -> i.getTimestamp() != null ? i.getTimestamp() : "")
                        .reversed())
                .limit(limit)
                .collect(Collectors.toList());
    }

    public List<Invoice> list() {
        return list(200);
    }

    public void record(Invoice invoice) {
        List<Invoice> records = JsonStore.readList(file, Invoice.class);
        // Evitar duplicados por invoice_id
        String id = invoice.getInvoiceId();
        if (id != null && records.stream().anyMatch(r -> id.equals(r.getInvoiceId()))) {
            return;
        }
        records.add(invoice);
        JsonStore.writeList(file, records);
    }

    public void delete(String invoiceId) {
        if (invoiceId == null) return;
        List<Invoice> records = JsonStore.readList(file, Invoice.class);
        records.removeIf(r -> invoiceId.equals(r.getInvoiceId()));
        JsonStore.writeList(file, records);
    }

    /** Borra por referencia de objeto (para facturas sin invoiceId). */
    public void deleteByRef(Invoice target) {
        List<Invoice> records = JsonStore.readList(file, Invoice.class);
        // Identificar por timestamp + customer + total
        records.removeIf(r ->
            java.util.Objects.equals(r.getTimestamp(), target.getTimestamp()) &&
            java.util.Objects.equals(r.getCustomer(),  target.getCustomer())  &&
            r.getTotal() == target.getTotal()
        );
        JsonStore.writeList(file, records);
    }

    public void update(String invoiceId, Invoice updated) {
        List<Invoice> records = JsonStore.readList(file, Invoice.class);
        for (int i = 0; i < records.size(); i++) {
            if (invoiceId.equals(records.get(i).getInvoiceId())) {
                records.set(i, updated);
                break;
            }
        }
        JsonStore.writeList(file, records);
    }
}
