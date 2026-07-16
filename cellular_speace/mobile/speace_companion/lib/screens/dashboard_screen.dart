import 'dart:async';
import 'package:flutter/material.dart';
import '../models/dashboard_state.dart';
import '../services/api_service.dart';

class DashboardScreen extends StatefulWidget {
  final ApiService api;

  const DashboardScreen({super.key, required this.api});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  DashboardState? _state;
  String? _error;
  bool _isLoading = true;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _load();
    _refreshTimer = Timer.periodic(const Duration(seconds: 5), (_) => _load());
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    final data = await widget.api.fetchDashboard();
    if (mounted) {
      setState(() {
        _state = data;
        _isLoading = false;
        _error = data == null ? 'Errore caricamento dati' : null;
      });
    }
  }

  Color _healthColor(double score) {
    if (score >= 0.8) return Colors.green;
    if (score >= 0.5) return Colors.orange;
    return Colors.red;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('SPEACE Companion'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _load,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _state == null
              ? Center(child: Text(_error!))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16.0),
                    children: [
                      // Runtime status card
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Runtime', style: Theme.of(context).textTheme.titleMedium),
                              const SizedBox(height: 8),
                              _buildRow('Stato', _state?.runtimeState ?? '—'),
                              _buildRow('Tick', '${_state?.tickCount ?? 0}'),
                              _buildRow('Fase circadiana', _state?.circadianPhase ?? '—'),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      // Health card
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Salute', style: Theme.of(context).textTheme.titleMedium),
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  Expanded(
                                    child: LinearProgressIndicator(
                                      value: (_state?.healthScore ?? 0).clamp(0.0, 1.0),
                                      backgroundColor: Colors.grey[300],
                                      valueColor: AlwaysStoppedAnimation(
                                        _healthColor(_state?.healthScore ?? 0),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Text(
                                    '${((_state?.healthScore ?? 0) * 100).toStringAsFixed(0)}%',
                                    style: TextStyle(
                                      color: _healthColor(_state?.healthScore ?? 0),
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      // Alerts card
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Alert', style: Theme.of(context).textTheme.titleMedium),
                              const SizedBox(height: 8),
                              if (_state == null || _state!.alerts.isEmpty)
                                const Text('Nessun alert attivo'),
                              else
                                ..._state!.alerts.take(5).map((a) {
                                  final msg = (a as Map<String, dynamic>?)?['message']?.toString() ?? 'Alert';
                                  final sev = (a as Map<String, dynamic>?)?['severity']?.toString() ?? 'info';
                                  return ListTile(
                                    dense: true,
                                    leading: Icon(
                                      sev == 'critical' ? Icons.error : Icons.warning,
                                      color: sev == 'critical' ? Colors.red : Colors.orange,
                                    ),
                                    title: Text(msg, style: const TextStyle(fontSize: 13)),
                                  );
                                }),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      // Nodes card
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Nodi', style: Theme.of(context).textTheme.titleMedium),
                              const SizedBox(height: 8),
                              _buildRow('Nodi attivi', '${(_state?.nodes['node_count'] as int?) ?? 0}'),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.0),
      child: Row(
        children: [
          Text('$label: ', style: const TextStyle(fontWeight: FontWeight.w500)),
          Text(value),
        ],
      ),
    );
  }
}
