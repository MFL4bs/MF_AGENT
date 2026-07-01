// models/invoice.dart
class InvoiceItem {
  final String sku;
  final String productName;
  final int quantity;
  final double unitPrice;
  final double subtotal;

  InvoiceItem({
    required this.sku,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    required this.subtotal,
  });

  factory InvoiceItem.fromMap(Map<String, dynamic> m) => InvoiceItem(
        sku: m['sku'] ?? '',
        productName: m['product_name'] ?? '',
        quantity: (m['quantity'] ?? 1).toInt(),
        unitPrice: (m['unit_price'] ?? 0).toDouble(),
        subtotal: (m['subtotal'] ?? 0).toDouble(),
      );

  Map<String, dynamic> toMap() => {
        'sku': sku,
        'product_name': productName,
        'quantity': quantity,
        'unit_price': unitPrice,
        'subtotal': subtotal,
      };
}

class Invoice {
  final String invoiceId;
  final String customer;
  final String customerPhone;
  final String customerAddress;
  final String customerRfc;
  final List<InvoiceItem> items;
  final double total;
  final String channel;
  final String timestamp;
  final String profileId;
  final String notes;
  final String? pdfUrl;

  Invoice({
    required this.invoiceId,
    required this.customer,
    this.customerPhone = '',
    this.customerAddress = '',
    this.customerRfc = '',
    required this.items,
    required this.total,
    this.channel = 'manual',
    required this.timestamp,
    required this.profileId,
    this.notes = '',
    this.pdfUrl,
  });

  factory Invoice.fromMap(Map<String, dynamic> m, String profileId) => Invoice(
        invoiceId: m['invoice_id'] ?? '',
        customer: m['customer'] ?? '',
        customerPhone: m['customer_phone'] ?? '',
        customerAddress: m['customer_address'] ?? '',
        customerRfc: m['customer_rfc'] ?? '',
        items: (m['items'] as List? ?? [])
            .map((i) => InvoiceItem.fromMap(i))
            .toList(),
        total: (m['total'] ?? 0).toDouble(),
        channel: m['channel'] ?? 'manual',
        timestamp: m['timestamp'] ?? '',
        profileId: profileId,
        notes: m['notes'] ?? '',
        pdfUrl: m['pdf_url'] as String?,
      );

  Map<String, dynamic> toMap() => {
        'invoice_id': invoiceId,
        'customer': customer,
        'customer_phone': customerPhone,
        'customer_address': customerAddress,
        'customer_rfc': customerRfc,
        'items': items.map((i) => i.toMap()).toList(),
        'total': total,
        'channel': channel,
        'timestamp': timestamp,
        'profile_id': profileId,
        'notes': notes,
      };
}
