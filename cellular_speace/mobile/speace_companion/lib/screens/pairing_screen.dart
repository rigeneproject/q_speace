import 'package:flutter/material.dart';
import '../services/api_service.dart';

class PairingScreen extends StatefulWidget {
  final ApiService api;
  final VoidCallback onPaired;

  const PairingScreen({super.key, required this.api, required this.onPaired});

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  final _urlController = TextEditingController(text: 'http://192.168.1.100:8000');
  final _tokenController = TextEditingController();
  bool _isLoading = false;
  String? _error;

  Future<void> _verify() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    widget.api.baseUrl = _urlController.text.trim();
    final ok = await widget.api.verifyToken(_tokenController.text.trim());
    setState(() => _isLoading = false);
    if (ok) {
      widget.onPaired();
    } else {
      setState(() => _error = 'Token non valido o scaduto.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Accoppia con SPEACE')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _urlController,
              decoration: const InputDecoration(
                labelText: 'Indirizzo nodo SPEACE',
                hintText: 'http://192.168.1.100:8000',
              ),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _tokenController,
              decoration: const InputDecoration(
                labelText: 'Token di pairing (6 cifre)',
              ),
              keyboardType: TextInputType.number,
              maxLength: 6,
            ),
            const SizedBox(height: 16),
            if (_error != null)
              Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isLoading ? null : _verify,
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Verifica'),
            ),
            const SizedBox(height: 24),
            const Text(
              'Istruzioni:\n'
              '1. Assicurati che SPEACE sia in esecuzione.\n'
              '2. Genera un token dal nodo (API /api/mobile/pair).\n'
              '3. Inserisci l\'indirizzo e il token qui sopra.\n'
              '4. Il telefono diventa un organo periferico read-only.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}
