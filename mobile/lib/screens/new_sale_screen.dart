// screens/new_sale_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:uuid/uuid.dart';
import '../models/invoice.dart';
import '../models/product.dart';
import '../services/firebase_service.dart';
import '../widgets/theme.dart';

class NewSaleScreen extends StatefulWidget {
  final String profileId;
  const NewSaleScreen({super.key, required this.profileId});

  @override
  State<NewSaleScreen> createState() => _NewSaleScreenState();
}

class _NewSaleScreenState extends State<NewSaleScreen> {
  final _customerCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  final _rfcCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();

  // Cotización
  bool _showQuote = false;
  final _quoteDescCtrl = TextEditingController();
  final _quotePriceCtrl = TextEditingController();
  final _quoteMetersCtrl = TextEditingController();
  String _quoteUnit = 'm';

  List<Product> _products = [];
  final List<Map<String, dynamic>> _items = [];
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    FirebaseService.productsStream(widget.profileId).first.then((p) {
      if (mounted) setState(() => _products = p);
    });
  }

  @override
  void dispose() {
    _customerCtrl.dispose();
    _phoneCtrl.dispose();
    _addressCtrl.dispose();
    _rfcCtrl.dispose();
    _notesCtrl.dispose();
    _quoteDescCtrl.dispose();
    _quotePriceCtrl.dispose();
    _quoteMetersCtrl.dispose();
    super.dispose();
  }

  void _addItem(Product p) {
    final existing = _items.indexWhere((i) => i['sku'] == p.sku);
    setState(() {
      if (existing >= 0) {
        _items[existing]['qty']++;
      } else {
        _items.add({'sku': p.sku, 'name': p.name, 'price': p.price, 'qty': 1});
      }
    });
  }

  void _removeItem(String sku) => setState(() => _items.removeWhere((i) => i['sku'] == sku));

  double get _quoteTotal {
    final price = double.tryParse(_quotePriceCtrl.text) ?? 0;
    final meters = double.tryParse(_quoteMetersCtrl.text) ?? 0;
    return price * meters;
  }

  double get _total {
    final products = _items.fold(0.0, (s, i) => s + i['price'] * i['qty']);
    return products + (_showQuote ? _quoteTotal : 0);
  }

  void _addQuoteAsItem() {
    final desc = _quoteDescCtrl.text.trim();
    final price = double.tryParse(_quotePriceCtrl.text) ?? 0;
    final meters = double.tryParse(_quoteMetersCtrl.text) ?? 0;
    if (desc.isEmpty || price <= 0 || meters <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Completa descripción, precio y metros')),
      );
      return;
    }
    final total = price * meters;
    final sku = 'COT-${DateTime.now().millisecondsSinceEpoch % 1000000}';
    final name = '$desc | \$$price/$_quoteUnit x ${meters.toStringAsFixed(2)}$_quoteUnit';
    setState(() {
      _items.removeWhere((i) => (i['sku'] as String).startsWith('COT-'));
      _items.add({'sku': sku, 'name': name, 'price': total, 'qty': 1});
      _showQuote = false;
      _quoteDescCtrl.clear();
      _quotePriceCtrl.clear();
      _quoteMetersCtrl.clear();
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Cotización agregada: \$${total.toStringAsFixed(2)}'), backgroundColor: kSuccess),
    );
  }

  Future<void> _save() async {
    if (_items.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Agrega al menos un producto o cotización')),
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
      );
      await FirebaseService.saveInvoice(invoice);
      // Descontar stock solo de productos normales
      for (final item in _items) {
        if ((item['sku'] as String).startsWith('COT-')) continue;
        final p = _products.firstWhere((p) => p.sku == item['sku'],
            orElse: () => Product(sku: '', name: '', price: 0, stock: 0, profileId: widget.profileId));
        final qty = (item['qty'] as num).toInt();
        if (p.sku.isNotEmpty && p.stock >= qty) {
          await FirebaseService.updateProductStock(widget.profileId, item['sku'], p.stock - qty);
        }
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
                TextField(
                  controller: _customerCtrl,
                  decoration: const InputDecoration(labelText: 'Cliente (opcional)'),
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
                        decoration: const InputDecoration(labelText: 'RFC / ID fiscal'),
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
                const Text('Productos', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                SizedBox(
                  height: 48,
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    itemCount: _products.length,
                    itemBuilder: (_, i) {
                      final p = _products[i];
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ActionChip(
                          label: Text('${p.name} \$${p.price.toStringAsFixed(0)}',
                              style: const TextStyle(fontSize: 12)),
                          onPressed: () => _addItem(p),
                          backgroundColor: kSidebar,
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(height: 16),
                if (_items.isNotEmpty) ...[
                  const Text('Items', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  ..._items.map((item) {
                    final isCot = (item['sku'] as String).startsWith('COT-');
                    return Card(
                      margin: const EdgeInsets.only(bottom: 6),
                      child: ListTile(
                        dense: true,
                        leading: isCot
                            ? const Icon(Icons.construction, color: kWarning, size: 20)
                            : null,
                        title: Text(item['name'],
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: isCot ? kWarning : null,
                            )),
                        subtitle: isCot
                            ? null
                            : Text('\$${item['price']} x ${item['qty']}',
                                style: TextStyle(color: kSubtext, fontSize: 12)),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text('\$${(item['price'] * item['qty']).toStringAsFixed(2)}',
                                style: const TextStyle(fontWeight: FontWeight.w700, color: kSuccess)),
                            const SizedBox(width: 8),
                            GestureDetector(
                              onTap: () => _removeItem(item['sku']),
                              child: const Icon(Icons.close, size: 18, color: kDanger),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                  const SizedBox(height: 8),
                ],

                // ── Cotización de mano de obra ──────────────────────────────
                OutlinedButton.icon(
                  icon: Icon(_showQuote ? Icons.expand_less : Icons.construction, size: 18),
                  label: Text(_showQuote ? 'Ocultar cotización' : '🔧 Agregar cotización'),
                  onPressed: () => setState(() => _showQuote = !_showQuote),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: kWarning,
                    side: const BorderSide(color: kWarning),
                  ),
                ),

                if (_showQuote) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: kWarning.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: kWarning.withOpacity(0.3)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Cotización de mano de obra',
                            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                        const SizedBox(height: 10),
                        TextField(
                          controller: _quoteDescCtrl,
                          decoration: const InputDecoration(
                            labelText: 'Descripción *',
                            hintText: 'Ej: Instalación de piso',
                            isDense: true,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _quotePriceCtrl,
                                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[\d.]'))],
                                decoration: InputDecoration(
                                  labelText: 'Precio por $_quoteUnit *',
                                  prefixText: '\$ ',
                                  isDense: true,
                                ),
                                onChanged: (_) => setState(() {}),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: TextField(
                                controller: _quoteMetersCtrl,
                                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[\d.]'))],
                                decoration: const InputDecoration(
                                  labelText: 'Cantidad *',
                                  isDense: true,
                                ),
                                onChanged: (_) => setState(() {}),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            const Text('Unidad: ', style: TextStyle(fontSize: 13)),
                            const SizedBox(width: 8),
                            SegmentedButton<String>(
                              segments: const [
                                ButtonSegment(value: 'm', label: Text('m')),
                                ButtonSegment(value: 'm²', label: Text('m²')),
                                ButtonSegment(value: 'm³', label: Text('m³')),
                              ],
                              selected: {_quoteUnit},
                              onSelectionChanged: (s) => setState(() => _quoteUnit = s.first),
                              style: ButtonStyle(
                                visualDensity: VisualDensity.compact,
                              ),
                            ),
                          ],
                        ),
                        if (_quoteTotal > 0) ...[
                          const SizedBox(height: 10),
                          Text(
                            'Subtotal: \$${_quoteTotal.toStringAsFixed(2)}',
                            style: const TextStyle(
                                color: kWarning, fontWeight: FontWeight.w700, fontSize: 14),
                          ),
                        ],
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            icon: const Icon(Icons.add, size: 18),
                            label: const Text('Agregar al pedido'),
                            onPressed: _addQuoteAsItem,
                            style: ElevatedButton.styleFrom(backgroundColor: kWarning),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 12),
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
                    Text('\$${_total.toStringAsFixed(2)}',
                        style: const TextStyle(
                            fontWeight: FontWeight.w800, fontSize: 22, color: kSuccess)),
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
