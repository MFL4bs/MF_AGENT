// screens/sales_screen.dart
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/invoice.dart';
import '../services/firebase_service.dart';
import '../widgets/theme.dart';
import 'new_sale_screen.dart';

class SalesScreen extends StatelessWidget {
  final String profileId;
  const SalesScreen({super.key, required this.profileId});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Ventas'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => NewSaleScreen(profileId: profileId)),
            ),
          ),
        ],
      ),
      body: StreamBuilder<List<Invoice>>(
        stream: FirebaseService.invoicesStream(profileId),
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final invoices = snap.data ?? [];
          final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
          final todayInvoices = invoices.where((i) => i.timestamp.startsWith(today)).toList();
          final totalHoy = todayInvoices.fold(0.0, (s, i) => s + i.total);
          final totalAll = invoices.fold(0.0, (s, i) => s + i.total);

          return Column(
            children: [
              Container(
                color: kCard,
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    _StatChip(label: 'Hoy', value: '\$${totalHoy.toStringAsFixed(0)}', color: kSuccess),
                    const SizedBox(width: 8),
                    _StatChip(label: 'Pedidos hoy', value: '${todayInvoices.length}', color: kAccent),
                    const SizedBox(width: 8),
                    _StatChip(label: 'Total', value: '\$${totalAll.toStringAsFixed(0)}', color: kWarning),
                  ],
                ),
              ),
              Expanded(
                child: invoices.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.receipt_long_outlined, size: 64, color: kSubtext),
                            const SizedBox(height: 12),
                            Text('Sin ventas registradas', style: TextStyle(color: kSubtext)),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: invoices.length,
                        itemBuilder: (_, i) => _InvoiceCard(
                          invoice: invoices[i],
                          profileId: profileId,
                        ),
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  final String label, value;
  final Color color;
  const _StatChip({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Column(
            children: [
              Text(value, style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 16)),
              Text(label, style: TextStyle(color: kSubtext, fontSize: 11)),
            ],
          ),
        ),
      );
}

class _InvoiceCard extends StatelessWidget {
  final Invoice invoice;
  final String profileId;
  const _InvoiceCard({required this.invoice, required this.profileId});

  @override
  Widget build(BuildContext context) {
    final channelIcon = invoice.channel == 'whatsapp' ? '📱' : '🛒';
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Text(channelIcon, style: const TextStyle(fontSize: 28)),
        title: Text(invoice.customer.isEmpty ? 'Consumidor final' : invoice.customer,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Text(
          '${invoice.invoiceId} · ${invoice.timestamp.length >= 10 ? invoice.timestamp.substring(0, 10) : invoice.timestamp}',
          style: TextStyle(color: kSubtext, fontSize: 12),
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text('\$${invoice.total.toStringAsFixed(2)}',
                style: const TextStyle(fontWeight: FontWeight.w700, color: kSuccess, fontSize: 15)),
            Text('${invoice.items.length} items',
                style: TextStyle(color: kSubtext, fontSize: 11)),
          ],
        ),
        onTap: () => _showDetail(context),
      ),
    );
  }

  void _showDetail(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.6,
        maxChildSize: 0.92,
        minChildSize: 0.4,
        builder: (_, scrollCtrl) => SingleChildScrollView(
          controller: scrollCtrl,
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40, height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: kSubtext.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Text('Factura ${invoice.invoiceId}',
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
              const SizedBox(height: 4),
              Text('Cliente: ${invoice.customer.isEmpty ? "Consumidor final" : invoice.customer}',
                  style: TextStyle(color: kSubtext)),
              if (invoice.customerPhone.isNotEmpty) ...[
                const SizedBox(height: 2),
                Text('Tel: ${invoice.customerPhone}', style: TextStyle(color: kSubtext, fontSize: 12)),
              ],
              if (invoice.customerAddress.isNotEmpty) ...[
                const SizedBox(height: 2),
                Text('Dir: ${invoice.customerAddress}', style: TextStyle(color: kSubtext, fontSize: 12)),
              ],
              if (invoice.customerRfc.isNotEmpty) ...[
                const SizedBox(height: 2),
                Text('RFC: ${invoice.customerRfc}', style: TextStyle(color: kSubtext, fontSize: 12)),
              ],
              if (invoice.notes.isNotEmpty) ...[
                const SizedBox(height: 2),
                Text('Notas: ${invoice.notes}', style: TextStyle(color: kSubtext, fontSize: 12)),
              ],
              const Divider(height: 20),
              ...invoice.items.map((item) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            item.sku.startsWith('COT-')
                                ? '🔧 ${item.productName}'
                                : '${item.productName} x${item.quantity}',
                            style: TextStyle(
                              fontSize: 13,
                              color: item.sku.startsWith('COT-') ? kWarning : null,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text('\$${item.subtotal.toStringAsFixed(2)}',
                            style: const TextStyle(fontWeight: FontWeight.w600)),
                      ],
                    ),
                  )),
              const Divider(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('TOTAL', style: TextStyle(fontWeight: FontWeight.w800)),
                  Text('\$${invoice.total.toStringAsFixed(2)}',
                      style: const TextStyle(
                          fontWeight: FontWeight.w800, color: kSuccess, fontSize: 16)),
                ],
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () async {
                    Navigator.pop(context);
                    await FirebaseService.deleteInvoice(invoice.invoiceId, profileId);
                  },
                  style: OutlinedButton.styleFrom(
                      foregroundColor: kDanger,
                      side: const BorderSide(color: kDanger)),
                  child: const Text('Eliminar'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
