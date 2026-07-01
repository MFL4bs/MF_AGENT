// screens/inventory_screen.dart
import 'package:flutter/material.dart';
import '../models/product.dart';
import '../services/firebase_service.dart';
import '../widgets/theme.dart';
import 'product_form_screen.dart';

class InventoryScreen extends StatefulWidget {
  final String profileId;
  final bool isAdmin;

  const InventoryScreen({
    super.key,
    required this.profileId,
    this.isAdmin = false,
  });

  @override
  State<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen> {
  String _search = '';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Inventario'),
        actions: [
          // Solo admin puede agregar productos
          if (widget.isAdmin)
            IconButton(
              icon: const Icon(Icons.add),
              tooltip: 'Nuevo producto',
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => ProductFormScreen(profileId: widget.profileId),
                ),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              decoration: const InputDecoration(
                hintText: 'Buscar producto...',
                prefixIcon: Icon(Icons.search),
                contentPadding: EdgeInsets.symmetric(vertical: 0, horizontal: 16),
              ),
              onChanged: (v) => setState(() => _search = v.toLowerCase()),
            ),
          ),
          Expanded(
            child: StreamBuilder<List<Product>>(
              stream: FirebaseService.productsStream(widget.profileId),
              builder: (context, snap) {
                if (snap.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                final products = (snap.data ?? [])
                    .where((p) =>
                        p.name.toLowerCase().contains(_search) ||
                        p.sku.toLowerCase().contains(_search) ||
                        p.category.toLowerCase().contains(_search))
                    .toList();

                if (products.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.inventory_2_outlined, size: 64, color: kSubtext),
                        const SizedBox(height: 12),
                        Text('Sin productos', style: TextStyle(color: kSubtext)),
                      ],
                    ),
                  );
                }

                return ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  itemCount: products.length,
                  itemBuilder: (_, i) => _ProductCard(
                    product: products[i],
                    profileId: widget.profileId,
                    isAdmin: widget.isAdmin,
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _ProductCard extends StatelessWidget {
  final Product product;
  final String profileId;
  final bool isAdmin;

  const _ProductCard({
    required this.product,
    required this.profileId,
    required this.isAdmin,
  });

  void _showProductDetail(BuildContext context, Product p) {
    final stockColor = p.stock == 0
        ? kDanger
        : p.stock <= 15
            ? kWarning
            : kSuccess;
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40, height: 4,
                decoration: BoxDecoration(
                  color: kBorder,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (p.imageUrl.isNotEmpty)
              Center(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.network(
                    p.imageUrl,
                    height: 120,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const SizedBox(),
                  ),
                ),
              ),
            const SizedBox(height: 12),
            Text(p.name,
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text('SKU: ${p.sku}  ·  ${p.category}',
                style: TextStyle(color: kSubtext, fontSize: 13)),
            if (p.description.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(p.description, style: TextStyle(color: kSubtext, fontSize: 13)),
            ],
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _DetailChip(
                    label: 'Precio',
                    value: '\$${p.price.toStringAsFixed(0)}',
                    color: kAccent,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _DetailChip(
                    label: 'Stock',
                    value: '${p.stock} uds.',
                    color: stockColor,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final stockColor = product.stock == 0
        ? kDanger
        : product.stock <= 15
            ? kWarning
            : kSuccess;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: kSidebar,
            borderRadius: BorderRadius.circular(8),
          ),
          child: product.imageUrl.isNotEmpty
              ? ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.network(
                    product.imageUrl,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) =>
                        const Icon(Icons.image_not_supported),
                  ),
                )
              : const Icon(Icons.inventory_2_outlined, color: kSubtext),
        ),
        title: Text(product.name,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Text('${product.sku} · ${product.category}',
            style: TextStyle(color: kSubtext, fontSize: 12)),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text('\$${product.price.toStringAsFixed(0)}',
                style: const TextStyle(
                    fontWeight: FontWeight.w700, color: kAccent)),
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: stockColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text('Stock: ${product.stock}',
                  style: TextStyle(
                      color: stockColor,
                      fontSize: 11,
                      fontWeight: FontWeight.w600)),
            ),
          ],
        ),
        onTap: () {
          if (isAdmin) {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ProductFormScreen(
                    profileId: profileId, product: product),
              ),
            );
          } else {
            _showProductDetail(context, product);
          }
        },
      ),
    );
  }
}

class _DetailChip extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  const _DetailChip({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Text(label, style: TextStyle(color: kSubtext, fontSize: 11)),
          const SizedBox(height: 4),
          Text(value,
              style: TextStyle(
                  color: color, fontSize: 16, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}
