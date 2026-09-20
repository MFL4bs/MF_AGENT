package com.mfagent.model;

import com.google.gson.annotations.SerializedName;

public class InvoiceItem {
    private String sku;
    @SerializedName("product_name") private String productName;
    private int quantity;
    @SerializedName("unit_price")   private double unitPrice;
    private double subtotal;

    public InvoiceItem() {}

    public InvoiceItem(String sku, String productName, int quantity, double unitPrice) {
        this.sku = sku;
        this.productName = productName;
        this.quantity = quantity;
        this.unitPrice = unitPrice;
        this.subtotal = quantity * unitPrice;
    }

    public String getSku()                  { return sku; }
    public void setSku(String sku)          { this.sku = sku; }

    public String getProductName()                      { return productName; }
    public void setProductName(String productName)      { this.productName = productName; }

    public int getQuantity()                { return quantity; }
    public void setQuantity(int quantity)   { this.quantity = quantity; recalc(); }

    public double getUnitPrice()                    { return unitPrice; }
    public void setUnitPrice(double unitPrice)      { this.unitPrice = unitPrice; recalc(); }

    public double getSubtotal()             { return subtotal; }
    public void setSubtotal(double subtotal){ this.subtotal = subtotal; }

    private void recalc() {
        this.subtotal = quantity * unitPrice;
    }
}
