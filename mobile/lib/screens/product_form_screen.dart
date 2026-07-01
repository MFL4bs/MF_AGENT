// screens/product_form_screen.dart
import 'package:flutter/material.dart';
import '../models/product.dart';
import '../services/firebase_service.dart';
import '../widgets/theme.dart';

class ProductFormScreen extends StatefulWidget {
  final String profileId;
  final Product? product;
  const ProductFormScreen({super.key, required this.profileId, this.product});

  @override
  State<ProductFormScreen> createState() => _ProductFormScreenState();
}

class _ProductFormScreenState extends State<ProductFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _name, _sku, _desc, _price, _stock, _category;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final p = widget.product;
    _name     = TextEditingController(text: p?.name ?? '');
    _sku      = TextEditingController(text: p?.sku ?? '');
    _desc     = TextEditingController(text: p?.description ?? '');
    _price    = TextEditingController(text: p?.price.toString() ?? '');
    _stock    = TextEditingController(text: p?.stock.toString() ?? '0');
    _category = TextEditingController(text: p?.category ?? 'general');
  }

  @override
  void dispose() {
    _name.dispose(); _sku.dispose(); _desc.dispose();
    _price.dispose(); _stock.dispose(); _category.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final product = Product(
        sku: _sku.text.trim(),
        name: _name.text.trim(),
        description: _desc.text.trim(),
        price: double.tryParse(_price.text) ?? 0,
        stock: int.tryParse(_stock.text) ?? 0,
        category: _category.text.trim(),
        profileId: widget.profileId,
      );
      await FirebaseService.upsertProduct(product);
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: kDanger),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _delete() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Eliminar producto'),
        content: Text('¿Eliminar ${widget.product!.name}?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Eliminar', style: TextStyle(color: kDanger)),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await FirebaseService.deleteProduct(widget.profileId, widget.product!.sku);
      if (mounted) Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isEdit = widget.product != null;
    return Scaffold(
      appBar: AppBar(
        title: Text(isEdit ? 'Editar Producto' : 'Nuevo Producto'),
        actions: [
          if (isEdit)
            IconButton(
              icon: const Icon(Icons.delete_outline, color: kDanger),
              onPressed: _delete,
            ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _field(_name, 'Nombre *', validator: (v) => v!.isEmpty ? 'Requerido' : null),
            _field(_sku, 'SKU *', validator: (v) => v!.isEmpty ? 'Requerido' : null,
                enabled: !isEdit),
            _field(_desc, 'Descripción'),
            _field(_price, 'Precio *',
                keyboardType: TextInputType.number,
                validator: (v) => double.tryParse(v ?? '') == null ? 'Número inválido' : null),
            _field(_stock, 'Stock *',
                keyboardType: TextInputType.number,
                validator: (v) => int.tryParse(v ?? '') == null ? 'Número inválido' : null),
            _field(_category, 'Categoría'),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _saving ? null : _save,
                child: _saving
                    ? const SizedBox(height: 20, width: 20,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : Text(isEdit ? 'Guardar Cambios' : 'Crear Producto'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _field(
    TextEditingController ctrl,
    String label, {
    TextInputType? keyboardType,
    String? Function(String?)? validator,
    bool enabled = true,
  }) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextFormField(
          controller: ctrl,
          enabled: enabled,
          keyboardType: keyboardType,
          validator: validator,
          decoration: InputDecoration(labelText: label),
        ),
      );
}
