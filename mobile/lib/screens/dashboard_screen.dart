import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/firebase_service.dart';
import '../widgets/theme.dart';

class DashboardScreen extends StatelessWidget {
  final String profileId;
  final String profileName;
  final String username;
  final bool isAdmin;
  const DashboardScreen({
    super.key,
    required this.profileId,
    required this.profileName,
    this.username = '',
    this.isAdmin = false,
  });

  Future<void> _forceSync(BuildContext context) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('mf_license');
    if (raw == null) return;
    final data = jsonDecode(raw) as Map<String, dynamic>;
    final key = (data['key'] ?? '') as String;
    if (key.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('⚠️  No hay licencia activa.'), backgroundColor: kWarning),
      );
      return;
    }
    final profiles = await FirebaseService.getProfilesByKey(key);
    final profile = profiles.isNotEmpty ? profiles.firstWhere((p) => p['id'] == profileId, orElse: () => profiles.first) : null;
    final pid = profile?['id'] ?? '';
    final products = pid.isNotEmpty ? await FirebaseService.productsStream(pid).first : [];
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(profile != null
            ? '✅  ${profile["name"]} · ${products.length} productos cargados'
            : '⚠️  Perfil no encontrado. Inicia sesión en el PC primero.'),
        backgroundColor: profile != null ? kSuccess : kWarning,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
    return Scaffold(
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Stats inventario
          StreamBuilder(
            stream: FirebaseService.productsStream(profileId),
            builder: (_, snap) {
              final products = snap.data ?? [];
              final total = products.length;
              final lowStock = products.where((p) => p.stock > 0 && p.stock <= 15).length;
              final outStock = products.where((p) => p.stock == 0).length;
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Inventario', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      _DashCard(icon: Icons.inventory_2, label: 'Productos', value: '$total', color: kAccent),
                      const SizedBox(width: 10),
                      _DashCard(icon: Icons.warning_amber, label: 'Stock bajo', value: '$lowStock', color: kWarning),
                      const SizedBox(width: 10),
                      _DashCard(icon: Icons.remove_circle_outline, label: 'Sin stock', value: '$outStock', color: kDanger),
                    ],
                  ),
                  if (lowStock > 0 || outStock > 0) ...[
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: kWarning.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: kWarning.withOpacity(0.3)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.warning_amber, color: kWarning, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Atención: $outStock sin stock, $lowStock con stock bajo.',
                              style: const TextStyle(color: kWarning, fontSize: 12, fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              );
            },
          ),
          const SizedBox(height: 24),
          // Stats ventas
          StreamBuilder(
            stream: FirebaseService.invoicesStream(profileId),
            builder: (_, snap) {
              final invoices = snap.data ?? [];
              final todayInv = invoices.where((i) => i.timestamp.startsWith(today)).toList();
              final totalHoy = todayInv.fold(0.0, (s, i) => s + i.total);
              final totalAll = invoices.fold(0.0, (s, i) => s + i.total);
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Ventas', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      _DashCard(icon: Icons.today, label: 'Hoy', value: '\$${totalHoy.toStringAsFixed(0)}', color: kSuccess),
                      const SizedBox(width: 10),
                      _DashCard(icon: Icons.receipt_long, label: 'Pedidos hoy', value: '${todayInv.length}', color: kAccent),
                      const SizedBox(width: 10),
                      _DashCard(icon: Icons.bar_chart, label: 'Total', value: '\$${totalAll.toStringAsFixed(0)}', color: kWarning),
                    ],
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _DashCard extends StatelessWidget {
  final IconData icon;
  final String label, value;
  final Color color;
  const _DashCard({required this.icon, required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) => Expanded(
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: kCard,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 8)],
          ),
          child: Column(
            children: [
              Icon(icon, color: color, size: 28),
              const SizedBox(height: 6),
              Text(value, style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 16)),
              Text(label, style: TextStyle(color: kSubtext, fontSize: 10), textAlign: TextAlign.center),
            ],
          ),
        ),
      );
}
