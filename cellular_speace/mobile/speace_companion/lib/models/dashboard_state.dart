class DashboardState {
  final Map<String, dynamic> health;
  final Map<String, dynamic> runtime;
  final List<dynamic> alerts;
  final int alertCount;
  final Map<String, dynamic> nodes;
  final double timestamp;

  DashboardState({
    required this.health,
    required this.runtime,
    required this.alerts,
    required this.alertCount,
    required this.nodes,
    required this.timestamp,
  });

  factory DashboardState.fromJson(Map<String, dynamic> json) {
    return DashboardState(
      health: json['health'] as Map<String, dynamic>? ?? {},
      runtime: json['runtime'] as Map<String, dynamic>? ?? {},
      alerts: json['alerts'] as List<dynamic>? ?? [],
      alertCount: json['alert_count'] as int? ?? 0,
      nodes: json['nodes'] as Map<String, dynamic>? ?? {},
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
    );
  }

  String get runtimeState => runtime['state']?.toString() ?? 'unknown';
  int get tickCount => runtime['tick_count'] as int? ?? 0;
  String get circadianPhase => runtime['circadian_phase']?.toString() ?? 'unknown';
  double get healthScore => (health['health_score'] as num?)?.toDouble() ?? 0.0;
  bool get isRunning => runtime['status']?.toString() != 'not_running';
}
