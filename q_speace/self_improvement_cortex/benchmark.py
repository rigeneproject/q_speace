"""GPU benchmark for Qiskit Aer with GPU acceleration (T46).

Usage:
    python -m q_speace.self_improvement_cortex.benchmark
    python -m q_speace.self_improvement_cortex.benchmark --min-qubits 4 --max-qubits 28
"""
from __future__ import annotations

import math
import time

import numpy as np


def benchmark_gpu(
    min_qubits: int = 4,
    max_qubits: int = 28,
    trials: int = 3,
) -> dict:
    """Benchmark entanglement simulation with GPU via Qiskit Aer.

    Measures execution time for Grover circuit across qubit counts.
    Falls back to numpy CPU estimation if Qiskit is unavailable.
    """
    results: dict[str, list] = {"qubits": [], "time_s": [], "device": []}
    qiskit_available = False

    try:
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator
        qiskit_available = True
    except ImportError:
        qiskit_available = False

    for n in range(min_qubits, max_qubits + 1):
        dim = 1 << n
        if dim > 2**20 and not qiskit_available:
            break
        times = []
        device_used = "cpu"
        for _t in range(trials):
            t0 = time.perf_counter()
            if qiskit_available:
                qc = QuantumCircuit(n, n)
                for i in range(n):
                    qc.h(i)
                    if i > 0:
                        qc.cx(i - 1, i)
                qc.measure_all()
                if n <= 26:
                    try:
                        sim = AerSimulator(method="statevector", device="GPU")
                        sim.run(qc, shots=256).result()
                        device_used = "gpu"
                    except Exception:
                        sim = AerSimulator(method="statevector", device="CPU")
                        sim.run(qc, shots=256).result()
                        device_used = "cpu"
                else:
                    sim = AerSimulator(method="statevector", device="CPU")
                    sim.run(qc, shots=256).result()
                    device_used = "cpu"
            else:
                _simulate_numpy_entanglement(n)
                device_used = "numpy_fallback"
            times.append(time.perf_counter() - t0)

        avg_time = np.mean(times)
        results["qubits"].append(n)
        results["time_s"].append(round(avg_time, 4))
        results["device"].append(device_used)

        print(f"  n={n:2d}  dim=2^{n}={dim:<8d}  avg={avg_time:.4f}s  device={device_used}")

    return results


def _simulate_numpy_entanglement(n: int) -> None:
    size = 1 << n
    state = np.zeros(size, dtype=np.complex128)
    state[0] = 1.0
    for i in range(n):
        step = 1 << i
        for j in range(0, size, step * 2):
            for k in range(step):
                a = j + k
                b = a + step
                state[a], state[b] = (state[a] + state[b]) / math.sqrt(2), (state[a] - state[b]) / math.sqrt(2)
    _ = np.abs(state) ** 2


def print_report(results: dict) -> None:
    print("\n=== QEE GPU Benchmark Report ===")
    print(f"{'Qubits':>6} | {'Dim':>10} | {'Time (s)':>10} | {'Device':>14}")
    print("-" * 46)
    for n, t, d in zip(results["qubits"], results["time_s"], results["device"], strict=False):
        dim = 1 << n
        print(f"{n:>6} | {dim:>10} | {t:>10.4f} | {d:>14}")

    gpu_times = [t for t, d in zip(results["time_s"], results["device"], strict=False) if d == "gpu"]
    if gpu_times:
        print(f"\nGPU available and used for {len(gpu_times)} data points.")
    else:
        print("\nGPU not used. Install qiskit-aer-gpu for GPU acceleration.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="QEE GPU Benchmark")
    parser.add_argument("--min-qubits", type=int, default=4)
    parser.add_argument("--max-qubits", type=int, default=28)
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()
    print(f"Benchmarking {args.min_qubits}-{args.max_qubits} qubits, {args.trials} trials each...")
    res = benchmark_gpu(args.min_qubits, args.max_qubits, args.trials)
    print_report(res)
