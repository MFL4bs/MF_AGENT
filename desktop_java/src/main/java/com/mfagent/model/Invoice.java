package com.mfagent.model;

import com.google.gson.annotations.SerializedName;
import java.util.ArrayList;
import java.util.List;

/**
 * Equivalente al dict de factura/venta en Python.
 */
public class Invoice {
    @SerializedName("invoice_id")    private String invoiceId;
    private String timestamp;
    private String customer;
    @SerializedName("customer_phone")   private String customerPhone;
    @SerializedName("customer_address") private String customerAddress;
    @SerializedName("customer_rfc")     private String customerRfc;
    private String notes;
    private String channel;
    @SerializedName("registered_by")  private String registeredBy;
    @SerializedName("business_name")  private String businessName;
    private double total;
    private List<InvoiceItem> items = new ArrayList<>();

    public Invoice() {}

    // Getters y setters
    public String getInvoiceId()                    { return invoiceId; }
    public void setInvoiceId(String invoiceId)      { this.invoiceId = invoiceId; }

    public String getTimestamp()                    { return timestamp; }
    public void setTimestamp(String timestamp)      { this.timestamp = timestamp; }

    public String getCustomer()                     { return customer; }
    public void setCustomer(String customer)        { this.customer = customer; }

    public String getCustomerPhone()                        { return customerPhone; }
    public void setCustomerPhone(String customerPhone)      { this.customerPhone = customerPhone; }

    public String getCustomerAddress()                          { return customerAddress; }
    public void setCustomerAddress(String customerAddress)      { this.customerAddress = customerAddress; }

    public String getCustomerRfc()                  { return customerRfc; }
    public void setCustomerRfc(String customerRfc)  { this.customerRfc = customerRfc; }

    public String getNotes()                { return notes; }
    public void setNotes(String notes)      { this.notes = notes; }

    public String getChannel()              { return channel; }
    public void setChannel(String channel)  { this.channel = channel; }

    public String getRegisteredBy()                     { return registeredBy; }
    public void setRegisteredBy(String registeredBy)    { this.registeredBy = registeredBy; }

    public String getBusinessName()                     { return businessName; }
    public void setBusinessName(String businessName)    { this.businessName = businessName; }

    public double getTotal()                { return total; }
    public void setTotal(double total)      { this.total = total; }

    public List<InvoiceItem> getItems()             { return items; }
    public void setItems(List<InvoiceItem> items)   { this.items = items; }

    public void recalcTotal() {
        this.total = items.stream().mapToDouble(InvoiceItem::getSubtotal).sum();
    }
}
