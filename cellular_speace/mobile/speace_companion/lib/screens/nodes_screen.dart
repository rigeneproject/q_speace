import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class NodesScreen extends StatefulWidget {
  final ApiService api;

  const NodesScreen({super.key, required this.api});

  @override
  State<NodesScreen> createState() => _NodesScreenState();
}

class _NodesScreenState extends State<NodesScreen> {
  Map<String, dynamic>? _nodes;
  bool _isLoading = true;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _load();
    _refreshTimer = Timer.periodic(const Duration(seconds: 15), (_) => _load());
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    final data = await widget.api.fetchNodes();
    if (mounted) {
      setState(() {
        _nodes = data;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nodi SPEACE')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16.0),
                children: [
                  if (_nodes == null)
                    const Text('Nessun nodo disponibile')
                  else ..._buildNodeTiles(),
                ],
              ),
            ),
    );
  }

  List<Widget> _buildNodeTiles() {
    final nodesData = _nodes?['nodes'] as Map<String, dynamic>? ?? {};
    if (nodesData.isEmpty) {
      return [const Text('Nessun nodo registrato')];
    }
    return nodesData.entries.map((e) {
      final node = e.value as Map<String, dynamic>? ?? {};
      return Card(
        child: ListTile(
          leading: const Icon(Icons.computer),
          title: Text(e.key),
          subtitle: Text('Trust: ${node['trust_score']?.toString() ?? '—'}'),
          trailing: node['online'] == true
              ? const Icon(Icons.check_circle, color: Colors.green)
              : const Icon(Icons.cancel, color: Colors.red),
        ),
      );
    }).toList();
  }
}
