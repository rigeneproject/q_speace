import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class NotificationScreen extends StatefulWidget {
  final ApiService api;

  const NotificationScreen({super.key, required this.api});

  @override
  State<NotificationScreen> createState() => _NotificationScreenState();
}

class _NotificationScreenState extends State<NotificationScreen> {
  List<dynamic> _notifications = [];
  bool _isLoading = true;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _load();
    _refreshTimer = Timer.periodic(const Duration(seconds: 10), (_) => _load());
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    final data = await widget.api.fetchNotifications(unreadOnly: false);
    if (mounted) {
      setState(() {
        _notifications = data?['notifications'] as List<dynamic>? ?? [];
        _isLoading = false;
      });
    }
  }

  Future<void> _markAllRead() async {
    final indices = List<int>.generate(_notifications.length, (i) => i);
    await widget.api.markNotificationsRead(indices);
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifiche'),
        actions: [
          IconButton(
            icon: const Icon(Icons.done_all),
            onPressed: _markAllRead,
            tooltip: 'Segna tutte come lette',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _notifications.isEmpty
              ? const Center(child: Text('Nessuna notifica'))
              : ListView.builder(
                  itemCount: _notifications.length,
                  itemBuilder: (context, index) {
                    final n = _notifications[index] as Map<String, dynamic>;
                    final read = n['read'] as bool? ?? false;
                    return ListTile(
                      leading: Icon(
                        read ? Icons.notifications_none : Icons.notifications_active,
                        color: read ? Colors.grey : Colors.red,
                      ),
                      title: Text(n['title']?.toString() ?? 'Notifica'),
                      subtitle: Text(n['body']?.toString() ?? ''),
                      trailing: read ? null : const Icon(Icons.circle, color: Colors.red, size: 10),
                    );
                  },
                ),
    );
  }
}
