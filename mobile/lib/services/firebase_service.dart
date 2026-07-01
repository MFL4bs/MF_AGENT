// services/firebase_service.dart
import 'dart:convert';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:crypto/crypto.dart';
import '../models/product.dart';
import '../models/invoice.dart';

class FirebaseService {
  static final _db = FirebaseFirestore.instance;

  // ── Licencias ─────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>?> getLicense(String keyId) async {
    final doc = await _db.collection('licenses').doc(keyId).get();
    if (!doc.exists) return null;
    return {'id': doc.id, ...doc.data()!};
  }

  static Future<List<Map<String, dynamic>>> getDevicesForKey(String keyId) async {
    final snap = await _db
        .collection('devices')
        .where('key_id', isEqualTo: keyId)
        .get();
    return snap.docs.map((d) => {'id': d.id, ...d.data()}).toList();
  }

  static Future<void> registerDevice(Map<String, dynamic> data) async {
    await _db.collection('devices').doc(data['device_id']).set(data);
  }

  static Future<void> updateDeviceLastSeen(String deviceId, String ip) async {
    await _db.collection('devices').doc(deviceId).update({
      'last_seen': DateTime.now().toUtc().toIso8601String(),
      'ip': ip,
    });
  }

  // ── Usuarios / Auth ───────────────────────────────────────────────────────

  /// SHA-256 idéntico al que usa Python: hashlib.sha256(password.encode()).hexdigest()
  static String _sha256hex(String input) {
    final bytes = utf8.encode(input);
    return sha256.convert(bytes).toString();
  }

  /// Lee los usuarios del perfil desde profiles/{profileId}.users (sincronizado por el PC).
  static Future<List<Map<String, dynamic>>> getUsersForProfile(String profileId) async {
    final doc = await _db.collection('profiles').doc(profileId).get();
    if (!doc.exists) return [];
    final data = doc.data()!;
    final users = data['users'] as List<dynamic>? ?? [];
    return users.map((u) => Map<String, dynamic>.from(u as Map)).toList();
  }

  /// Autentica usuario contra el hash SHA-256 guardado en Firestore.
  /// Retorna {username, role, profile_id} si es válido, null si no.
  static Future<Map<String, dynamic>?> authenticateUser(
      String profileId, String username, String password) async {
    final users = await getUsersForProfile(profileId);
    final hash = _sha256hex(password);
    for (final u in users) {
      final storedUser = (u['username'] as String? ?? '').toLowerCase();
      final storedHash = u['password_hash'] as String? ?? '';
      if (storedUser == username.toLowerCase() && storedHash == hash) {
        return {
          'username': u['username'],
          'role': u['role'] ?? 'vendedor',
          'profile_id': profileId,
        };
      }
    }
    return null;
  }

  // ── Perfiles ──────────────────────────────────────────────────────────────

  static Future<List<Map<String, dynamic>>> getProfilesByKey(String key) async {
    final snap = await _db
        .collection('profiles')
        .where('key', isEqualTo: key)
        .get();
    return snap.docs.map((d) => {'id': d.id, ...d.data()}).toList();
  }

  static Future<Map<String, dynamic>?> getProfileById(String profileId) async {
    final doc = await _db.collection('profiles').doc(profileId).get();
    if (!doc.exists) return null;
    return {'id': doc.id, ...doc.data()!};
  }

  // ── Inventario ────────────────────────────────────────────────────────────

  static Stream<List<Product>> productsStream(String profileId) {
    return _db
        .collection('inventory')
        .snapshots()
        .map((snap) => snap.docs
            .where((d) => d.data()['profile_id'] == profileId)
            .map((d) => Product.fromMap(d.data(), profileId))
            .toList());
  }

  static Future<void> upsertProduct(Product product) async {
    await _db
        .collection('inventory')
        .doc('${product.profileId}_${product.sku}')
        .set(product.toMap(), SetOptions(merge: true));
  }

  static Future<void> updateProductStock(
      String profileId, String sku, int newStock) async {
    await _db
        .collection('inventory')
        .doc('${profileId}_$sku')
        .update({'stock': newStock});
  }

  static Future<void> deleteProduct(String profileId, String sku) async {
    await _db.collection('inventory').doc('${profileId}_$sku').delete();
  }

  // ── Ventas ────────────────────────────────────────────────────────────────

  static Stream<List<Invoice>> invoicesStream(String profileId) {
    return _db
        .collection('invoices')
        .orderBy('timestamp', descending: true)
        .snapshots()
        .map((snap) => snap.docs
            .where((d) => d.data()['profile_id'] == profileId)
            .map((d) => Invoice.fromMap(d.data(), profileId))
            .toList());
  }

  static Future<void> saveInvoice(Invoice invoice) async {
    await _db
        .collection('invoices')
        .doc(invoice.invoiceId)
        .set(invoice.toMap());
  }

  static Future<void> deleteInvoice(String invoiceId, String profileId) async {
    final doc = await _db.collection('invoices').doc(invoiceId).get();
    if (doc.exists) {
      final items = (doc.data()?['items'] as List? ?? []);
      for (final item in items) {
        final sku = item['sku'] as String? ?? '';
        if (sku.startsWith('COT-') || sku.isEmpty) continue;
        final qty = (item['quantity'] as num?)?.toInt() ?? 0;
        if (qty <= 0) continue;
        final invDoc = await _db
            .collection('inventory')
            .doc('${profileId}_$sku')
            .get();
        if (invDoc.exists) {
          final currentStock = (invDoc.data()?['stock'] as num?)?.toInt() ?? 0;
          await _db
              .collection('inventory')
              .doc('${profileId}_$sku')
              .update({'stock': currentStock + qty});
        }
      }
    }
    await _db.collection('invoices').doc(invoiceId).delete();
  }

  // ── Sync desde JSON local (PC → Firestore) ────────────────────────────────

  static Future<void> syncProductsFromLocal(
      String profileId, List<Map<String, dynamic>> products) async {
    final batch = _db.batch();
    for (final p in products) {
      p['profile_id'] = profileId;
      final ref = _db.collection('inventory').doc('${profileId}_${p['sku']}');
      batch.set(ref, p, SetOptions(merge: true));
    }
    await batch.commit();
  }

  static Future<void> syncInvoicesFromLocal(
      String profileId, List<Map<String, dynamic>> invoices) async {
    final batch = _db.batch();
    for (final inv in invoices) {
      inv['profile_id'] = profileId;
      final ref = _db.collection('invoices').doc(inv['invoice_id'] ?? '');
      if (inv['invoice_id'] != null) batch.set(ref, inv, SetOptions(merge: true));
    }
    await batch.commit();
  }
}
