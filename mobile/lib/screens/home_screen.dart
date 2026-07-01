// screens/home_screen.dart
import 'package:flutter/material.dart';
import '../services/license_service.dart';
import '../widgets/theme.dart';
import 'dashboard_screen.dart';
import 'inventory_screen.dart';
import 'sales_screen.dart';

class HomeScreen extends StatefulWidget {
  final String profileId;
  final String profileName;
  final String username;
  final String role;
  final int? daysLeft;

  const HomeScreen({
    super.key,
    required this.profileId,
    required this.profileName,
    required this.username,
    required this.role,
    this.daysLeft,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  bool get _isAdmin => widget.role == 'admin';

  @override
  void initState() {
    super.initState();
    if (widget.daysLeft != null && widget.daysLeft! <= 7) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('⚠️ Tu licencia vence en ${widget.daysLeft} días. Renueva pronto.'),
            backgroundColor: kWarning,
            duration: const Duration(seconds: 5),
          ),
        );
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      DashboardScreen(
        profileId: widget.profileId,
        profileName: widget.profileName,
        username: widget.username,
        isAdmin: _isAdmin,
      ),
      InventoryScreen(
        profileId: widget.profileId,
        isAdmin: _isAdmin,
      ),
      SalesScreen(profileId: widget.profileId),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.profileName),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 4),
            child: Chip(
              avatar: Icon(
                _isAdmin ? Icons.admin_panel_settings : Icons.person,
                size: 16,
                color: _isAdmin ? kWarning : kSubtext,
              ),
              label: Text(widget.username, style: const TextStyle(fontSize: 12)),
              backgroundColor: kSidebar,
              padding: EdgeInsets.zero,
            ),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Cerrar sesión',
            onPressed: () async {
              final confirm = await showDialog<bool>(
                context: context,
                builder: (_) => AlertDialog(
                  title: const Text('Cerrar sesión'),
                  content: Text('¿Salir de la cuenta de ${widget.username}?'),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: const Text('Cancelar'),
                    ),
                    TextButton(
                      onPressed: () => Navigator.pop(context, true),
                      child: const Text('Salir', style: TextStyle(color: kDanger)),
                    ),
                  ],
                ),
              );
              if (confirm == true && context.mounted) {
                await LicenseService.clearSession();
                if (context.mounted) {
                  Navigator.of(context).pushReplacementNamed('/');
                }
              }
            },
          ),
        ],
      ),
      body: screens[_index],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        backgroundColor: kCard,
        indicatorColor: kAccent.withOpacity(0.15),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard, color: kAccent),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.inventory_2_outlined),
            selectedIcon: Icon(Icons.inventory_2, color: kAccent),
            label: 'Inventario',
          ),
          NavigationDestination(
            icon: Icon(Icons.receipt_long_outlined),
            selectedIcon: Icon(Icons.receipt_long, color: kAccent),
            label: 'Ventas',
          ),
        ],
      ),
    );
  }
}
