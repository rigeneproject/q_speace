import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/dashboard_state.dart';

class ApiService {
  String baseUrl;
  String? deviceId;

  ApiService({this.baseUrl = 'http://127.0.0.1:8000'});

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    deviceId = prefs.getString('device_id');
    final savedUrl = prefs.getString('base_url');
    if (savedUrl != null && savedUrl.isNotEmpty) {
      baseUrl = savedUrl;
    }
  }

  Future<void> saveConfig() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url', baseUrl);
    if (deviceId != null) {
      await prefs.setString('device_id', deviceId!);
    }
  }

  // ------------------------------------------------------------------ #
  // Pairing
  // ------------------------------------------------------------------ #

  Future<String?> pair() async {
    final response = await http.post(Uri.parse('$baseUrl/api/mobile/pair'));
    if (response.statusCode == 200) {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      return body['token'] as String?;
    }
    return null;
  }

  Future<bool> verifyToken(String token) async {
    deviceId ??= 'mobile_${DateTime.now().millisecondsSinceEpoch}';
    final response = await http.post(
      Uri.parse('$baseUrl/api/mobile/verify'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'token': token, 'device_id': deviceId}),
    );
    if (response.statusCode == 200) {
      await saveConfig();
      return true;
    }
    return false;
  }

  Future<bool> heartbeat() async {
    if (deviceId == null) return false;
    final response = await http.post(
      Uri.parse('$baseUrl/api/mobile/heartbeat'),
      headers: {
        'Content-Type': 'application/json',
        'x-device-id': deviceId!,
      },
      body: jsonEncode({'device_id': deviceId}),
    );
    return response.statusCode == 200;
  }

  // ------------------------------------------------------------------ #
  // Dashboard
  // ------------------------------------------------------------------ #

  Future<DashboardState?> fetchDashboard() async {
    if (deviceId == null) return null;
    final response = await http.get(
      Uri.parse('$baseUrl/api/mobile/dashboard'),
      headers: {'x-device-id': deviceId!},
    );
    if (response.statusCode == 200) {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      return DashboardState.fromJson(body);
    }
    return null;
  }

  // ------------------------------------------------------------------ #
  // Dialogue (T120-B)
  // ------------------------------------------------------------------ #

  Future<Map<String, dynamic>?> sendMessage(String message) async {
    if (deviceId == null) return null;
    final response = await http.post(
      Uri.parse('$baseUrl/api/dialogue/message'),
      headers: {
        'Content-Type': 'application/json',
        'x-device-id': deviceId!,
      },
      body: jsonEncode({'message': message}),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  // ------------------------------------------------------------------ #
  // Sensor consent (T120-C)
  // ------------------------------------------------------------------ #

  Future<Map<String, dynamic>?> updateSensorConsent(Map<String, bool> consent) async {
    if (deviceId == null) return null;
    final response = await http.post(
      Uri.parse('$baseUrl/api/mobile/sensor_consent'),
      headers: {
        'Content-Type': 'application/json',
        'x-device-id': deviceId!,
      },
      body: jsonEncode({'consent': consent}),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<Map<String, dynamic>?> sendSensors(Map<String, dynamic> sensors) async {
    if (deviceId == null) return null;
    final response = await http.post(
      Uri.parse('$baseUrl/api/mobile/sensors'),
      headers: {
        'Content-Type': 'application/json',
        'x-device-id': deviceId!,
      },
      body: jsonEncode({'sensors': sensors}),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  // ------------------------------------------------------------------ #
  // Notifications (T120-D)
  // ------------------------------------------------------------------ #

  Future<Map<String, dynamic>?> fetchNotifications({bool unreadOnly = false}) async {
    if (deviceId == null) return null;
    final response = await http.get(
      Uri.parse('$baseUrl/api/mobile/notifications?unread_only=$unreadOnly'),
      headers: {'x-device-id': deviceId!},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  Future<bool> markNotificationsRead(List<int> indices) async {
    if (deviceId == null) return false;
    final response = await http.post(
      Uri.parse('$baseUrl/api/mobile/notifications/read'),
      headers: {
        'Content-Type': 'application/json',
        'x-device-id': deviceId!,
      },
      body: jsonEncode({'indices': indices}),
    );
    return response.statusCode == 200;
  }

  // ------------------------------------------------------------------ #
  // Multi-node (T120-E)
  // ------------------------------------------------------------------ #

  Future<Map<String, dynamic>?> fetchNodes() async {
    if (deviceId == null) return null;
    final response = await http.get(
      Uri.parse('$baseUrl/api/mobile/nodes'),
      headers: {'x-device-id': deviceId!},
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }

  // ------------------------------------------------------------------ #
  // QR Pairing (T120-F)
  // ------------------------------------------------------------------ #

  Future<Map<String, dynamic>?> fetchQrPayload() async {
    final response = await http.get(Uri.parse('$baseUrl/api/mobile/qr'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    return null;
  }
}
