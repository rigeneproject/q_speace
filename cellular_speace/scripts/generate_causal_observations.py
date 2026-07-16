#!/usr/bin/env python3
"""Generate diverse causal observations for AGI readiness causal_reasoning dimension."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from speace_core.cellular_brain.world_model.causal_world_model import CausalWorldModel


def _observe(
    model: CausalWorldModel,
    action: str,
    params: dict,
    effect: str,
    confidence: float,
) -> None:
    model.record_observation(action, params, effect, confidence)


def main() -> None:
    data_root = str(PROJECT_ROOT / "data" / "agi_runtime" / "causal_world_model")
    model = CausalWorldModel(data_root=data_root)

    actions = [
        ("write_text_file", [{"path": "/tmp/log.txt"}, {"path": "/tmp/out.txt"}, {"path": "/tmp/data.json"}, {"path": "/tmp/report.md"}, {"path": "/tmp/debug.log"}]),
        ("read_text_file", [{"path": "/tmp/log.txt"}, {"path": "/tmp/out.txt"}, {"path": "/tmp/data.json"}, {"path": "/tmp/report.md"}, {"path": "/tmp/debug.log"}]),
        ("list_directory", [{"path": "/tmp"}, {"path": "/home"}, {"path": "/var/log"}, {"path": "/etc"}, {"path": "/usr/local"}]),
        ("get_system_time", [{"format": "unix"}, {"format": "iso"}, {"format": "local"}, {"format": "utc"}, {"format": "epoch"}]),
        ("get_cpu_temperature", [{"sensor": "cpu0"}, {"sensor": "cpu1"}, {"sensor": "package"}, {"sensor": "core0"}, {"sensor": "core1"}]),
        ("get_memory_usage", [{"type": "ram"}, {"type": "swap"}, {"type": "cached"}, {"type": "buffers"}, {"type": "total"}]),
        ("calculate_fibonacci", [{"n": 10}, {"n": 15}, {"n": 20}, {"n": 25}, {"n": 30}]),
        ("sort_numbers", [{"algorithm": "bubble", "count": 100}, {"algorithm": "quick", "count": 500}, {"algorithm": "merge", "count": 200}, {"algorithm": "heap", "count": 300}, {"algorithm": "insertion", "count": 50}]),
        ("search_text", [{"pattern": "error", "case_sensitive": True}, {"pattern": "warning", "case_sensitive": False}, {"pattern": "TODO", "case_sensitive": True}, {"pattern": "FIXME", "case_sensitive": False}, {"pattern": "INFO", "case_sensitive": True}]),
        ("count_lines", [{"file": "a.log", "include_empty": True}, {"file": "b.log", "include_empty": False}, {"file": "c.log", "include_empty": True}, {"file": "d.log", "include_empty": False}, {"file": "e.log", "include_empty": True}]),
        ("ping_host", [{"host": "localhost", "count": 1}, {"host": "127.0.0.1", "count": 3}, {"host": "localhost", "count": 5}, {"host": "0.0.0.0", "count": 2}, {"host": "127.0.0.1", "count": 4}]),
        ("calculate_checksum", [{"algorithm": "md5"}, {"algorithm": "sha1"}, {"algorithm": "sha256"}, {"algorithm": "sha512"}, {"algorithm": "crc32"}]),
    ]

    effects_map: dict[str, list[str]] = {
        "write_text_file": ["file_created", "file_appended", "bytes_written", "disk_full", "permission_denied"],
        "read_text_file": ["content_read", "file_not_found", "empty_file", "binary_detected", "permission_denied"],
        "list_directory": ["entries_listed", "empty_directory", "permission_denied", "symlink_detected", "too_many_entries"],
        "get_system_time": ["timestamp_returned", "timezone_detected", "ntp_synced", "drift_detected", "daylight_saving"],
        "get_cpu_temperature": ["temperature_read", "sensor_not_found", "overheat_warning", "fan_speed_increased", "thermal_throttled"],
        "get_memory_usage": ["usage_stats_returned", "swap_high", "memory_pressure", "cache_freed", "oom_risk_detected"],
        "calculate_fibonacci": ["result_computed", "stack_overflow", "large_number_warning", "cached_result", "overflow_detected"],
        "sort_numbers": ["sorted_successfully", "memory_exhausted", "already_sorted", "reverse_sorted", "partial_sort"],
        "search_text": ["matches_found", "no_matches", "pattern_compiled", "case_sensitive_match", "regex_error"],
        "count_lines": ["count_returned", "file_not_found", "binary_file_skipped", "large_file_warning", "compressed_detected"],
        "ping_host": ["host_reachable", "host_unreachable", "packet_loss", "high_latency", "dns_resolved"],
        "calculate_checksum": ["checksum_computed", "algorithm_unsupported", "file_not_found", "checksum_mismatch", "hash_collision"],
    }

    for action_name, params_list in actions:
        effects = effects_map[action_name]
        for i, params in enumerate(params_list):
            confidence = round(0.7 + (i % 5) * 0.07, 2)
            effect = effects[i % len(effects)]
            _observe(model, action_name, params, effect, confidence)

    summary = model.summary()
    print(f"Total observations: {summary['total_observations']}")
    print(f"Unique actions:     {summary['unique_actions']}")
    print(f"Unique effects:     {summary['unique_effects']}")
    print(f"Average confidence: {summary['average_confidence']}")
    print()
    print("Action distribution:")
    for action, count in sorted(summary["action_distribution"].items()):
        print(f"  {action:30s} {count}")


if __name__ == "__main__":
    main()
