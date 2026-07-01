// models/product.dart
class Product {
  final String sku;
  final String name;
  final String description;
  final double price;
  final int stock;
  final String category;
  final String imageUrl;
  final String profileId;

  Product({
    required this.sku,
    required this.name,
    this.description = '',
    required this.price,
    required this.stock,
    this.category = 'general',
    this.imageUrl = '',
    required this.profileId,
  });

  factory Product.fromMap(Map<String, dynamic> map, String profileId) => Product(
        sku: map['sku'] ?? '',
        name: map['name'] ?? '',
        description: map['description'] ?? '',
        price: (map['price'] ?? 0).toDouble(),
        stock: (map['stock'] ?? 0).toInt(),
        category: map['category'] ?? 'general',
        imageUrl: map['image_url'] ?? '',
        profileId: profileId,
      );

  Map<String, dynamic> toMap() => {
        'sku': sku,
        'name': name,
        'description': description,
        'price': price,
        'stock': stock,
        'category': category,
        'image_url': imageUrl,
        'profile_id': profileId,
      };
}
