import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../services/api_service.dart';

class QrScanScreen extends StatefulWidget {
  final ApiService api;
  final VoidCallback onPaired;

  const QrScanScreen({super.key, required this.api, required this.onPaired});

  @override
  State<QrScanScreen> createState() => _QrScanScreenState();
}

class _QrScanScreenState extends State<QrScanScreen> {
  bool _isVerifying = false;
  String? _error;

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_isVerifying) return;
    final barcode = capture.barcodes.firstOrNull;
    if (barcode == null || barcode.rawValue == null) return;

    setState(() {
      _isVerifying = true;
      _error = null;
    });

    try {
      final payload = jsonDecode(barcode.rawValue!) as Map<String, dynamic>;
      final token = payload['token'] as String?;
      if (token == null || token.isEmpty) {
        throw Exception('QR non valido');
      }
      final ok = await widget.api.verifyToken(token);
      if (ok) {
        widget.onPaired();
      } else {
        setState(() => _error = 'Token scaduto o non valido');
      }
    } catch (e) {
      setState(() => _error = 'Errore: $e');
    } finally {
      if (mounted) {
        setState(() => _isVerifying = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scansiona QR SPEACE')),
      body: Column(
        children: [
          Expanded(
            child: MobileScanner(
              onDetect: _onDetect,
            ),
          ),
          if (_isVerifying)
            const Padding(
              padding: EdgeInsets.all(16.0),
              child: CircularProgressIndicator(),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text(
              'Inquadra il QR code mostrato sul nodo SPEACE.',
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}
