import 'package:flutter/material.dart';
import 'screens/dashboard_screen.dart';
import 'screens/dialogue_screen.dart';
import 'screens/notification_screen.dart';
import 'screens/nodes_screen.dart';
import 'screens/pairing_screen.dart';
import 'screens/qr_scan_screen.dart';
import 'screens/sensor_screen.dart';
import 'services/api_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final api = ApiService();
  await api.init();
  runApp(SpeaceCompanionApp(api: api));
}

class SpeaceCompanionApp extends StatefulWidget {
  final ApiService api;

  const SpeaceCompanionApp({super.key, required this.api});

  @override
  State<SpeaceCompanionApp> createState() => _SpeaceCompanionAppState();
}

class _SpeaceCompanionAppState extends State<SpeaceCompanionApp> {
  bool _isPaired = false;
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    _checkPaired();
  }

  Future<void> _checkPaired() async {
    final ok = await widget.api.heartbeat();
    if (mounted) {
      setState(() => _isPaired = ok);
    }
  }

  void _onPaired() {
    setState(() => _isPaired = true);
  }

  void _onLogout() async {
    setState(() => _isPaired = false);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SPEACE Companion',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: _isPaired ? _buildMainScaffold() : _buildPairingFlow(),
    );
  }

  Widget _buildPairingFlow() {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Accoppia con SPEACE'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Token', icon: Icon(Icons.keyboard)),
              Tab(text: 'QR', icon: Icon(Icons.qr_code_scanner)),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            PairingScreen(api: widget.api, onPaired: _onPaired),
            QrScanScreen(api: widget.api, onPaired: _onPaired),
          ],
        ),
      ),
    );
  }

  Widget _buildMainScaffold() {
    final screens = [
      DashboardScreen(api: widget.api),
      DialogueScreen(api: widget.api),
      SensorScreen(api: widget.api),
      NotificationScreen(api: widget.api),
      NodesScreen(api: widget.api),
    ];
    return Scaffold(
      body: screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) => setState(() => _currentIndex = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard), label: 'Dashboard'),
          NavigationDestination(icon: Icon(Icons.chat), label: 'Dialogo'),
          NavigationDestination(icon: Icon(Icons.sensors), label: 'Sensori'),
          NavigationDestination(icon: Icon(Icons.notifications), label: 'Notifiche'),
          NavigationDestination(icon: Icon(Icons.computer), label: 'Nodi'),
        ],
      ),
      floatingActionButton: FloatingActionButton.small(
        onPressed: _onLogout,
        tooltip: 'Disconnetti',
        child: const Icon(Icons.logout),
      ),
    );
  }
}
