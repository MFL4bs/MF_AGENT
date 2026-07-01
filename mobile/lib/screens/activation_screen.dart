import 'package:flutter/material.dart';
import '../services/license_service.dart';
import '../widgets/theme.dart';

class ActivationScreen extends StatefulWidget {
  final Function(LicenseResult) onActivated;
  const ActivationScreen({super.key, required this.onActivated});

  @override
  State<ActivationScreen> createState() => _ActivationScreenState();
}

class _ActivationScreenState extends State<ActivationScreen> {
  final _keyCtrl = TextEditingController();
  String _msg = '';
  Color _msgColor = kSubtext;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _autoValidate();
  }

  Future<void> _autoValidate() async {
    final result = await LicenseService.validate();
    if (!mounted) return;
    if (result.ok) {
      _showSuccess(result);
    } else {
      setState(() {
        _loading = false;
        _msg = 'Ingresa tu clave de licencia.';
        _msgColor = kSubtext;
      });
    }
  }

  Future<void> _activate() async {
    final key = _keyCtrl.text.trim().toUpperCase();
    if (key.isEmpty) return;
    setState(() { _loading = true; _msg = 'Validando...'; _msgColor = kSubtext; });
    final result = await LicenseService.activate(key);
    if (!mounted) return;
    if (result.ok) {
      _showSuccess(result);
    } else {
      setState(() {
        _loading = false;
        _msg = '❌  ${result.msg}';
        _msgColor = kDanger;
      });
    }
  }

  void _showSuccess(LicenseResult result) {
    String msg;
    Color color;
    if (result.daysLeft == null) {
      msg = '✅  Licencia permanente activa.';
      color = kSuccess;
    } else if (result.daysLeft! <= 7) {
      msg = '⚠️  Vence en ${result.daysLeft} días. Renueva pronto.';
      color = kWarning;
    } else {
      msg = '✅  Licencia activa. Vence en ${result.daysLeft} días.';
      color = kSuccess;
    }
    setState(() { _msg = msg; _msgColor = color; _loading = false; });
    Future.delayed(const Duration(milliseconds: 1200), () => widget.onActivated(result));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 80, height: 80,
                  decoration: BoxDecoration(
                    color: kAccent,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Icon(Icons.inventory_2_rounded, color: Colors.white, size: 44),
                ),
                const SizedBox(height: 24),
                Text('MF Agent', style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.w800, color: kText,
                )),
                const SizedBox(height: 8),
                Text('Ingresa tu clave de licencia', style: TextStyle(color: kSubtext, fontSize: 14)),
                const SizedBox(height: 32),
                TextField(
                  controller: _keyCtrl,
                  textCapitalization: TextCapitalization.characters,
                  textAlign: TextAlign.center,
                  style: const TextStyle(letterSpacing: 2, fontWeight: FontWeight.w600),
                  decoration: const InputDecoration(
                    hintText: 'MF-XXXX-XXXX-XXXX-XXXX',
                    hintStyle: TextStyle(letterSpacing: 1),
                  ),
                  onSubmitted: (_) => _activate(),
                ),
                const SizedBox(height: 16),
                if (_msg.isNotEmpty)
                  Text(_msg, style: TextStyle(color: _msgColor, fontSize: 13),
                      textAlign: TextAlign.center),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _loading ? null : _activate,
                    child: _loading
                        ? const SizedBox(height: 20, width: 20,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Text('Activar Licencia'),
                  ),
                ),
                const SizedBox(height: 16),
                Text('¿No tienes una key? Contacta a tu proveedor.',
                    style: TextStyle(color: kSubtext, fontSize: 12)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
