import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'screens/activation_screen.dart';
import 'screens/home_screen.dart';
import 'services/license_service.dart';
import 'services/firebase_service.dart';
import 'widgets/theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(const MFAgentApp());
}

class MFAgentApp extends StatelessWidget {
  const MFAgentApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MF Agent',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      initialRoute: '/',
      routes: {
        '/': (_) => const _LicenseGate(),
      },
    );
  }
}

class _LicenseGate extends StatefulWidget {
  const _LicenseGate();

  @override
  State<_LicenseGate> createState() => _LicenseGateState();
}

class _LicenseGateState extends State<_LicenseGate> {
  bool _checking = true;
  bool _licensed = false;
  int? _daysLeft;
  String _profileId = '';
  String _profileName = '';
  String _username = '';
  String _role = '';

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    // 1. Intentar cargar sesión guardada
    final session = await LicenseService.loadSession();
    if (session != null && mounted) {
      // Validar que la licencia sigue activa
      final result = await LicenseService.validate();
      if (result.ok && mounted) {
        setState(() {
          _checking = false;
          _licensed = true;
          _daysLeft = result.daysLeft;
          _profileId = session['profile_id'] ?? '';
          _profileName = session['profile_name'] ?? '';
          _username = session['username'] ?? '';
          _role = session['role'] ?? 'vendedor';
        });
        return;
      }
      // Licencia inválida — borrar sesión y pedir de nuevo
      await LicenseService.clearSession();
    }
    // 2. Sin sesión guardada — flujo normal
    final result = await LicenseService.validate();
    if (!mounted) return;
    if (result.ok) {
      await _loadProfileFromKey(result.key, result.daysLeft);
    } else {
      setState(() { _checking = false; _licensed = false; });
    }
  }

  Future<void> _loadProfileFromKey(String key, int? daysLeft) async {
    setState(() => _checking = true);
    final profiles = await FirebaseService.getProfilesByKey(key);
    if (!mounted) return;

    if (profiles.isEmpty) {
      setState(() { _checking = false; _licensed = false; });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('❌ No se encontraron perfiles vinculados a esta key.'),
            backgroundColor: Colors.red,
          ),
        );
      }
      return;
    }

    // 1. Seleccionar perfil (si hay más de uno)
    Map<String, dynamic>? selected;
    if (profiles.length > 1) {
      selected = await showDialog<Map<String, dynamic>>(
        context: context,
        barrierDismissible: false,
        builder: (_) => _ProfilePickerDialog(profiles: profiles),
      );
    } else {
      selected = profiles.first;
    }

    if (selected == null || !mounted) return;

    // 2. Login de usuario
    final loginResult = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _UserLoginDialog(
        profileId: selected!['id'] as String,
        profileName: selected['name'] as String? ?? '',
      ),
    );

    if (loginResult == null || !mounted) return;

    setState(() {
      _checking = false;
      _licensed = true;
      _daysLeft = daysLeft;
      _profileId = selected!['id'] ?? '';
      _profileName = selected['name'] ?? '';
      _username = loginResult['username'] ?? '';
      _role = loginResult['role'] ?? 'vendedor';
    });
    // Guardar sesión para no pedir login la próxima vez
    await LicenseService.saveSession({
      'profile_id': _profileId,
      'profile_name': _profileName,
      'username': _username,
      'role': _role,
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (!_licensed) {
      return ActivationScreen(
        onActivated: (result) async {
          if (mounted) await _loadProfileFromKey(result.key, result.daysLeft);
        },
      );
    }

    return HomeScreen(
      profileId: _profileId,
      profileName: _profileName,
      username: _username,
      role: _role,
      daysLeft: _daysLeft,
    );
  }
}

// ── Dialog: Seleccionar Perfil ────────────────────────────────────────────────
class _ProfilePickerDialog extends StatelessWidget {
  final List<Map<String, dynamic>> profiles;
  const _ProfilePickerDialog({required this.profiles});

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Seleccionar perfil'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: profiles
            .map((p) => ListTile(
                  leading: const Icon(Icons.business, color: kAccent),
                  title: Text(p['name'] ?? p['id']),
                  onTap: () => Navigator.of(context).pop(p),
                ))
            .toList(),
      ),
    );
  }
}

// ── Dialog: Login de Usuario ──────────────────────────────────────────────────
class _UserLoginDialog extends StatefulWidget {
  final String profileId;
  final String profileName;
  const _UserLoginDialog({required this.profileId, required this.profileName});

  @override
  State<_UserLoginDialog> createState() => _UserLoginDialogState();
}

class _UserLoginDialogState extends State<_UserLoginDialog> {
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _loading = false;
  bool _obscure = true;
  String _error = '';

  @override
  void dispose() {
    _userCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final user = _userCtrl.text.trim();
    final pass = _passCtrl.text;
    if (user.isEmpty || pass.isEmpty) {
      setState(() => _error = 'Completa usuario y contraseña.');
      return;
    }
    setState(() { _loading = true; _error = ''; });
    try {
      final result = await FirebaseService.authenticateUser(
        widget.profileId, user, pass,
      );
      if (!mounted) return;
      if (result != null) {
        Navigator.of(context).pop(result);
      } else {
        setState(() {
          _loading = false;
          _error = 'Usuario o contraseña incorrectos.';
          _passCtrl.clear();
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'Error de conexión. Verifica tu internet.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Logo / ícono
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: kAccent.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Icon(Icons.lock_outline, color: kAccent, size: 28),
            ),
            const SizedBox(height: 14),
            Text(
              widget.profileName,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              'Inicia sesión para continuar',
              style: TextStyle(fontSize: 13, color: kSubtext),
            ),
            const SizedBox(height: 20),

            // Campo usuario
            TextField(
              controller: _userCtrl,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(
                labelText: 'Usuario',
                prefixIcon: Icon(Icons.person_outline),
              ),
              onSubmitted: (_) => FocusScope.of(context).nextFocus(),
            ),
            const SizedBox(height: 12),

            // Campo contraseña
            TextField(
              controller: _passCtrl,
              obscureText: _obscure,
              textInputAction: TextInputAction.done,
              decoration: InputDecoration(
                labelText: 'Contraseña',
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility),
                  onPressed: () => setState(() => _obscure = !_obscure),
                ),
              ),
              onSubmitted: (_) => _login(),
            ),

            // Error
            if (_error.isNotEmpty) ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  const Icon(Icons.error_outline, color: kDanger, size: 16),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(_error,
                        style: const TextStyle(color: kDanger, fontSize: 12)),
                  ),
                ],
              ),
            ],

            const SizedBox(height: 20),

            // Botón
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _loading ? null : _login,
                child: _loading
                    ? const SizedBox(
                        height: 20, width: 20,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : const Text('Entrar'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
