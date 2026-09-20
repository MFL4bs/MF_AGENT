// screens/new_sale_screen.dart
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';
import '../models/invoice.dart';
import '../models/product.dart';
import '../services/firebase_service.dart';
import '../widgets/theme.dart';

class NewSaleScreen extends StatefulWidget {
  final String profileId;
  final String username;
  const NewSaleScreen({super.key, required this.profileId, this.username = ''});

  @override
  State<NewSaleScreen> createState() => _NewSaleScreenState();
}

class _NewSaleScreenState extends State<NewSaleScreen> {
  final _customerCtrl = TextEditingController();
  final _phoneCtrl    = TextEditingController();
  final _addressCtrl  = TextEditingController();
  final _rfcCtrl      = TextEditingController();
  final _notesCtrl    = TextEditingController();
  final _searchCtrl   = TextEditingController();

  List<Product> _products = [];
  List<Product> _filtered = [];
  List<Map<String, dynamic>> _customers = [];
  List<Map<String, dynamic>> _customerSuggestions = [];
  bool _showSuggestions = false;
  final List<Map<String, dynamic>> _items = [];
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    FirebaseService.productsStream(widget.profileId).listen((p) {
      if (mounted) setState(() { _products = p; _filtered = p; });
    });
    FirebaseService.fetchCustomers(widget.profileId).then((c) {
      if (mounted) setState(() => _customers = c);
    });
    _searchCtrl.addListener(_filterProducts);
    _customerCtrl.addListener(_onCustomerType);
  }

  void _onCustomerType() {
    final q = _customerCtrl.text.toLowerCase();
    setState(() {
      _customerSuggestions = q.isEmpty
          ? _customers
          : _customers.where((c) =>
              (c['name'] ?? '').toString().toLowerCase().contains(q) ||
              (c['phone'] ?? '').toString().contains(q)).toList();
    });
  }

  void _selectCustomer(Map<String, dynamic> c) {
    setState(() {
      _customerCtrl.text = c['name'] ?? '';
      _phoneCtrl.text    = c['phone'] ?? '';
      _addressCtrl.text  = c['address'] ?? '';
      _rfcCtrl.text      = c['rfc'] ?? '';
      _showSuggestions   = false;
    });
  }

  @override
  void dispose() {
    _customerCtrl.dispose(); _phoneCtrl.dispose();
    _addressCtrl.dispose();  _rfcCtrl.dispose();
    _notesCtrl.dispose();    _searchCtrl.dispose();
    super.dispose();
  }

  void _filterProducts() {
    final q = _searchCtrl.text.toLowerCase().trim();
    setState(() {
      _filtered = q.isEmpty
          ? _products
          : _products.where((p) =>
              p.name.toLowerCase().contains(q) ||
              p.sku.toLowerCase().contains(q)).toList();
    });
  }

  void _addItem(Product p) {
    final idx = _items.indexWhere((i) => i['sku'] == p.sku);
    setState(() {
      if (idx >= 0) {
        _items[idx]['qty']++;
      } else {
        _items.add({'sku': p.sku, 'name': p.name, 'price': p.price, 'qty': 1});
      }
    });
  }

  void _removeItem(String sku) => setState(() => _items.removeWhere((i) => i['sku'] == sku));

  double get _total => _items.fold(0.0, (s, i) => s + i['price'] * i['qty']);

  Future<void> _save() async {
    if (_items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Agrega al menos un producto')),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      final invoiceId = 'INV-${const Uuid().v4().substring(0, 6).toUpperCase()}';
      final invoice = Invoice(
        invoiceId: invoiceId,
        customer: _customerCtrl.text.trim(),
        customerPhone: _phoneCtrl.text.trim(),
        customerAddress: _addressCtrl.text.trim(),
        customerRfc: _rfcCtrl.text.trim(),
        items: _items.map((i) => InvoiceItem(
          sku: i['sku'],
          productName: i['name'],
          quantity: i['qty'],
          unitPrice: i['price'],
          subtotal: i['price'] * i['qty'],
        )).toList(),
        total: _total,
        timestamp: DateTime.now().toIso8601String(),
        profileId: widget.profileId,
        notes: _notesCtrl.text.trim(),
        registeredBy: widget.username,
      );
      await FirebaseService.saveInvoice(invoice);
      // Guardar cliente
      final name = _customerCtrl.text.trim();
      if (name.isNotEmpty) {
        final existing = _customers.firstWhere(
          (c) => (c['name'] ?? '').toString().toLowerCase() == name.toLowerCase() &&
                 (c['phone'] ?? '') == _phoneCtrl.text.trim(),
          orElse: () => {},
        );
        final customerId = existing['id'] as String? ??
            DateTime.now().millisecondsSinceEpoch.toRadixString(16).substring(0, 8);
        await FirebaseService.upsertCustomer(widget.profileId, {
          'id':      customerId,
          'name':    name,
          'phone':   _phoneCtrl.text.trim(),
          'address': _addressCtrl.text.trim(),
          'rfc':     _rfcCtrl.text.trim(),
        });
      }
      for (final item in _items) {
        final p = _products.firstWhere((p) => p.sku == item['sku'],
            orElse: () => Product(sku: '', name: '', price: 0, stock: 0, profileId: widget.profileId));
        final qty = (item['qty'] as num).toInt();
        if (p.sku.isNotEmpty && p.stock >= qty)
          await FirebaseService.updateProductStock(widget.profileId, item['sku'], p.stock - qty);
      }
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: kDanger),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nueva Venta')),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // ── Cliente con autocomplete ──────────────────────────────
                TextField(
                  controller: _customerCtrl,
                  decoration: const InputDecoration(labelText: 'Cliente (opcional)'),
                  onTap: () => setState(() {
                    _showSuggestions = true;
                    _customerSuggestions = _customers;
                  }),
                  onChanged: (_) => setState(() => _showSuggestions = true),
                ),
                if (_showSuggestions && _customerSuggestions.isNotEmpty)
                  Card(
                    margin: const EdgeInsets.only(top: 2),
                    elevation: 4,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxHeight: 180),
                      child: ListView(
                        shrinkWrap: true,
                        padding: EdgeInsets.zero,
                        children: _customerSuggestions.map((c) => ListTile(
                          dense: true,
                          leading: const Icon(Icons.person_outline, color: kAccent, size: 20),
                          title: Text(c['name'] ?? '', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                          subtitle: Text(c['phone'] ?? '', style: TextStyle(fontSize: 11, color: kSubtext)),
                          onTap: () => _selectCustomer(c),
                        )).toList(),
                      ),
                    ),
                  ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _phoneCtrl,
                        keyboardType: TextInputType.phone,
                        decoration: const InputDecoration(labelText: 'Teléfono'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        controller: _rfcCtrl,
                        decoration: const InputDecoration(labelText: 'RFC'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _addressCtrl,
                  decoration: const InputDecoration(labelText: 'Dirección'),
                ),
                const SizedBox(height: 16),

                // ── Buscador de productos ─────────────────────────────────
                const Text('Productos', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                TextField(
                  controller: _searchCtrl,
                  decoration: InputDecoration(
                    hintText: 'Buscar por nombre o SKU...',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _searchCtrl.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear),
                            onPressed: () { _searchCtrl.clear(); _filterProducts(); })
                        : null,
                    isDense: true,
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  constraints: const BoxConstraints(maxHeight: 200),
                  decoration: BoxDecoration(
                    border: Border.all(color: kBorder),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: _filtered.isEmpty
                      ? const Padding(
                          padding: EdgeInsets.all(16),
                          child: Text('Sin resultados', style: TextStyle(color: kSubtext)),
                        )
                      : ListView.builder(
                          shrinkWrap: true,
                          itemCount: _filtered.length,
                          itemBuilder: (_, i) {
                            final p = _filtered[i];
                            return ListTile(
                              dense: true,
                              title: Text(p.name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                              subtitle: Text('SKU: ${p.sku}  ·  Stock: ${p.stock}',
                                  style: TextStyle(fontSize: 11, color: kSubtext)),
                              trailing: Text('\$${p.price.toStringAsFixed(0)}',
                                  style: const TextStyle(color: kSuccess, fontWeight: FontWeight.w700)),
                              onTap: () => _addItem(p),
                            );
                          },
                        ),
                ),
                const SizedBox(height: 16),

                // ── Items agregados ───────────────────────────────────────
                if (_items.isNotEmpty) ...[
                  const Text('Items seleccionados', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  ..._items.map((item) => Card(
                        margin: const EdgeInsets.only(bottom: 6),
                        child: ListTile(
                          dense: true,
                          title: Text(item['name'], style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                          subtitle: Text('\$${item['price']} x ${item['qty']}',
                              style: TextStyle(color: kSubtext, fontSize: 12)),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text('\$${(item['price'] * item['qty']).toStringAsFixed(0)}',
                                  style: const TextStyle(fontWeight: FontWeight.w700, color: kSuccess)),
                              const SizedBox(width: 8),
                              GestureDetector(
                                onTap: () => _removeItem(item['sku']),
                                child: const Icon(Icons.close, size: 18, color: kDanger),
                              ),
                            ],
                          ),
                        ),
                      )),
                  const SizedBox(height: 8),
                ],

                TextField(
                  controller: _notesCtrl,
                  decoration: const InputDecoration(labelText: 'Notas (opcional)'),
                ),
                const SizedBox(height: 80),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              color: kCard,
              boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8, offset: Offset(0, -2))],
            ),
            child: Row(
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('TOTAL', style: TextStyle(color: kSubtext, fontSize: 12)),
                    Text('\$${_total.toStringAsFixed(0)}',
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 22, color: kSuccess)),
                  ],
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _saving ? null : _save,
                    child: _saving
                        ? const SizedBox(height: 20, width: 20,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Text('Registrar Venta'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
