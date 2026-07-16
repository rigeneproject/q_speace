import 'dart:async';
import 'package:flutter/material.dart';
import 'package:battery_plus/battery_plus.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'package:geolocator/geolocator.dart';
import '../services/api_service.dart';

class SensorScreen extends StatefulWidget {
  final ApiService api;

  const SensorScreen({super.key, required this.api});

  @override
  State<SensorScreen> createState() => _SensorScreenState();
}

class _SensorScreenState extends State<SensorScreen> {
  final Map<String, bool> _consent = {
    'battery': false,
    'network': false,
    'accelerometer': false,
    'location': false,
  };

  final Map<String, dynamic> _readings = {};
  bool _isSending = false;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 10), (_) => _collectAndSend());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _updateConsent() async {
    await widget.api.updateSensorConsent(_consent);
  }

  Future<void> _collectAndSend() async {
    if (_isSending) return;
    setState(() => _isSending = true);
    final sensors = <String, dynamic>{};

    if (_consent['battery'] == true) {
      try {
        final level = await Battery().batteryLevel;
        sensors['battery'] = level / 100.0;
        _readings['battery'] = '$level%';
      } catch (_) {}
    }

    if (_consent['network'] == true) {
      try {
        final result = await Connectivity().checkConnectivity();
        sensors['network'] = result.toString();
        _readings['network'] = result.toString();
      } catch (_) {}
    }

    if (_consent['accelerometer'] == true) {
      try {
        final event = await accelerometerEvents.first;
        sensors['accelerometer'] = [event.x, event.y, event.z];
        _readings['accelerometer'] = 'x:${event.x.toStringAsFixed(2)} y:${event.y.toStringAsFixed(2)} z:${event.z.toStringAsFixed(2)}';
      } catch (_) {}
    }

    if (_consent['location'] == true) {
      try {
        final pos = await Geolocator.getCurrentPosition();
        sensors['location'] = {'lat': pos.latitude, 'lon': pos.longitude};
        _readings['location'] = '${pos.latitude.toStringAsFixed(4)}, ${pos.longitude.toStringAsFixed(4)}';
      } catch (_) {}
    }

    if (sensors.isNotEmpty) {
      await widget.api.sendSensors(sensors);
    }

    if (mounted) {
      setState(() => _isSending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Sensori')),
      body: ListView(
        children: [
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text(
              'Consenti l\'invio dei dati sensori a SPEACE. Microfono sempre disabilitato.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ),
          ..._consent.keys.map((k) {
            return SwitchListTile(
              title: Text(k[0].toUpperCase() + k.substring(1)),
              subtitle: Text(_readings[k]?.toString() ?? '—'),
              value: _consent[k] ?? false,
              onChanged: (v) {
                setState(() => _consent[k] = v);
                _updateConsent();
              },
            );
          }),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: ElevatedButton(
              onPressed: _isSending ? null : _collectAndSend,
              child: _isSending
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Invia ora'),
            ),
          ),
        ],
      ),
    );
  }
}
