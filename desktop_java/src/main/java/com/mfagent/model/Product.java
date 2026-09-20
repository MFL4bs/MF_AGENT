package com.mfagent.model;

/**
 * Equivalente al dict de producto en Python.
 * Campos: sku, name, description, price, cost_price, stock, category, image_url
 */
public class Product {
    private String sku;
    private String name;
    private String description;
    private double price;
    private double costPrice;
    private int stock;
    private String category;
    private String imageUrl;

    public Product() {}

    public Product(String sku, String name, double price, int stock) {
        this.sku = sku;
        this.name = name;
        this.price = price;
        this.stock = stock;
    }

    // Getters y setters
    public String getSku()              { return sku; }
    public void setSku(String sku)      { this.sku = sku; }

    public String getName()             { return name; }
    public void setName(String name)    { this.name = name; }

    public String getDescription()                  { return description; }
    public void setDescription(String description)  { this.description = description; }

    public double getPrice()            { return price; }
    public void setPrice(double price)  { this.price = price; }

    public double getCostPrice()                { return costPrice; }
    public void setCostPrice(double costPrice)  { this.costPrice = costPrice; }

    public int getStock()               { return stock; }
    public void setStock(int stock)     { this.stock = stock; }

    public String getCategory()                 { return category; }
    public void setCategory(String category)    { this.category = category; }

    public String getImageUrl()                 { return imageUrl; }
    public void setImageUrl(String imageUrl)    { this.imageUrl = imageUrl; }

    /** Rentabilidad: precio - costo */
    public double getMargin() {
        return price - costPrice;
    }

    /** Rentabilidad en % */
    public double getMarginPct() {
        return costPrice > 0 ? (getMargin() / costPrice) * 100 : 0;
    }

    public boolean isLowStock() {
        return stock > 0 && stock <= 15;
    }

    public boolean isOutOfStock() {
        return stock == 0;
    }
}
