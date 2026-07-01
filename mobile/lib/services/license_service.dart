// services/license_service.dart
import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'firebase_service.dart';

const _secret = 'MF-4g9zK2#pL8mXqR5vN1wJ7cT0bY6hD';
const _prefKey = 'mf_license';
const _warnDays = 7;

class LicenseResult {
  final bool ok;
  final String msg;
  final int? daysLeft;
  final bool warn;
  final String? type;
  final String profileId;
  final String key;

  LicenseResult({
    required this.ok,
    required this.msg,
    this.daysLeft,
    this.warn = false,
    this.type,
    this.profileId = '',
    this.key = '',
  });
}

class LicenseService {
  static Future<String> getDeviceId() async {
    final info = DeviceInfoPlugin();
    if (Platform.isAndroid) {
      final android = await info.androidInfo;
      final raw = '${android.model}-${android.id}-${android.serialNumber}';
      return sha256.convert(utf8.encode(raw)).toString().substring(0, 32);
    } else if (Platform.isIOS) {
      final ios = await info.iosInfo;
      final raw = '${ios.name}-${ios.identifierForVendor}';
      return sha256.convert(utf8.encode(raw)).toString().substring(0, 32);
    }
    return 'unknown';
  }

  static String _sign(String key, String deviceId) {
    final payload = '$key:$deviceId';
    final hmac = Hmac(sha256, utf8.encode(_secret));
    return hmac.convert(utf8.encode(payload)).toString();
  }

  static Future<void> _saveLocal(String key, String deviceId, String profileId) async {
    final prefs = await SharedPreferences.getInstance();
    final sig = _sign(key, deviceId);
    await prefs.setString(_prefKey, jsonEncode({
      'key': key,
      'device_id': deviceId,
      'profile_id': profileId,
      'sig': sig,
    }));
  }

  static Future<Map<String, dynamic>?> _loadLocal() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_prefKey);
    if (raw == null) return null;
    try {
      final data = jsonDecode(raw) as Map<String, dynamic>;
      final expected = _sign(data['key'], data['device_id']);
      if (data['sig'] != expected) return null;
      return data;
    } catch (_) {
      return null;
    }
  }

  static Future<String> _getIp() async {
    try {
      final interfaces = await NetworkInterface.list();
      for (final i in interfaces) {
        for (final addr in i.addresses) {
          if (addr.type == InternetAddressType.IPv4 && !addr.isLoopback) {
            return addr.address;
          }
        }
      }
    } catch (_) {}
    return 'desconocida';
  }

  static Future<LicenseResult> activate(String key) async {
    final deviceId = await getDeviceId();

    final lic = await FirebaseService.getLicense(key);
    if (lic == null) return LicenseResult(ok: false, msg: 'Key inválida.');
    if (lic['active'] != true) return LicenseResult(ok: false, msg: 'Key desactivada.');

    // Verificar expiración
    int? daysLeft;
    final expiresAt = lic['expires_at'];
    if (expiresAt != null && expiresAt != 'never') {
      final exp = DateTime.parse(expiresAt).toUtc();
      final now = DateTime.now().toUtc();
      if (now.isAfter(exp)) return LicenseResult(ok: false, msg: 'Key vencida.');
      daysLeft = exp.difference(now).inDays;
    }

    // Verificar plataforma
    final platform = lic['platform'] ?? 'both';
    if (platform == 'pc') {
      return LicenseResult(ok: false, msg: 'Esta key es solo para PC.');
    }

    // Verificar dispositivos
    final devices = await FirebaseService.getDevicesForKey(key);
    final deviceIds = devices.map((d) => d['device_id']).toList();
    final maxDevices = (lic['max_devices'] ?? 1) as int;

    final profileId = (lic['profile_id'] ?? '') as String;

    if (deviceIds.contains(deviceId)) {
      await _saveLocal(key, deviceId, profileId);
      return LicenseResult(ok: true, msg: 'Licencia válida.', daysLeft: daysLeft, type: lic['type'], profileId: profileId, key: key);
    }

    if (devices.length >= maxDevices) {
      return LicenseResult(
        ok: false,
        msg: 'Límite de dispositivos alcanzado ($maxDevices). Contacta al administrador.',
      );
    }

    // Registrar dispositivo
    final info = DeviceInfoPlugin();
    String hostname = 'Android';
    if (Platform.isAndroid) {
      final android = await info.androidInfo;
      hostname = '${android.brand} ${android.model}';
    } else if (Platform.isIOS) {
      final ios = await info.iosInfo;
      hostname = ios.name;
    }

    await FirebaseService.registerDevice({
      'device_id': deviceId,
      'key_id': key,
      'platform': Platform.isIOS ? 'ios' : 'mobile',
      'hostname': hostname,
      'ip': await _getIp(),
      'registered_at': DateTime.now().toUtc().toIso8601String(),
      'last_seen': DateTime.now().toUtc().toIso8601String(),
    });

    await _saveLocal(key, deviceId, profileId);
    return LicenseResult(ok: true, msg: 'Licencia activada.', daysLeft: daysLeft, type: lic['type'], profileId: profileId, key: key);
  }

  static Future<LicenseResult> validate() async {
    final local = await _loadLocal();
    if (local == null) return LicenseResult(ok: false, msg: 'No hay licencia activada.');

    final deviceId = await getDeviceId();
    if (local['device_id'] != deviceId) {
      return LicenseResult(ok: false, msg: 'Licencia no válida para este dispositivo.');
    }

    try {
      final lic = await FirebaseService.getLicense(local['key']);
      if (lic == null) return LicenseResult(ok: false, msg: 'Key no encontrada.');
      if (lic['active'] != true) return LicenseResult(ok: false, msg: 'Licencia revocada.');

      int? daysLeft;
      bool warn = false;
      final expiresAt = lic['expires_at'];
      if (expiresAt != null && expiresAt != 'never') {
        final exp = DateTime.parse(expiresAt).toUtc();
        final now = DateTime.now().toUtc();
        if (now.isAfter(exp)) return LicenseResult(ok: false, msg: 'Licencia vencida. Renueva tu plan.');
        daysLeft = exp.difference(now).inDays;
        warn = daysLeft <= _warnDays;
      }

      await FirebaseService.updateDeviceLastSeen(deviceId, await _getIp());
      return LicenseResult(ok: true, msg: 'Licencia válida.', daysLeft: daysLeft, warn: warn, type: lic['type'], profileId: local['profile_id'] ?? '', key: local['key'] ?? '');
    } catch (e) {
      return LicenseResult(ok: false, msg: 'Error al validar: $e');
    }
  }

  static Future<void> saveSession(Map<String, dynamic> session) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('mf_session', jsonEncode(session));
  }

  static Future<Map<String, dynamic>?> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('mf_session');
    if (raw == null) return null;
    try {
      return jsonDecode(raw) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  static Future<void> clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('mf_session');
  }
}
