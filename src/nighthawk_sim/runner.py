"""任意のバックエンドに対する トランスパイル → ノイズ付き実行 の共通処理。"""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit import transpile as _qiskit_transpile

__all__ = ["transpile_for", "best_transpile", "simulator_for", "sampler_for", "run_counts"]


def transpile_for(circuits, backend, optimization_level: int = 3, seed: int | None = None, **kwargs):
    """``backend`` のネイティブゲートと格子に合わせて回路を書き換える。"""
    return _qiskit_transpile(circuits, backend, optimization_level=optimization_level,
                             seed_transpiler=seed, **kwargs)


def best_transpile(circuit: QuantumCircuit, backend, seeds=(1, 2, 3), optimization_level: int = 3):
    """シードを変えて何回かトランスパイルし、CZ 数が一番少ない回路を返す。"""
    cands = [transpile_for(circuit, backend, optimization_level, seed=s) for s in seeds]
    return min(cands, key=lambda c: c.count_ops().get("cz", 0))


def simulator_for(backend, seed: int | None = None, **kwargs):
    """``backend`` の誤り率・T1/T2 を写したノイズ付き ``AerSimulator``。"""
    from qiskit_aer import AerSimulator

    if seed is not None:
        kwargs["seed_simulator"] = seed
    return AerSimulator.from_backend(backend, **kwargs)


def sampler_for(backend, seed: int | None = None, **kwargs):
    """ノイズ付きシミュレータを ``mode`` にした ``SamplerV2``。実機と同じ書き方で使える。"""
    from qiskit_ibm_runtime import SamplerV2

    return SamplerV2(mode=simulator_for(backend, seed=seed, **kwargs))


def run_counts(circuits, backend, shots: int = 2000, seed: int | None = None,
               transpile: bool = True, seed_transpiler: int | None = None):
    """回路をトランスパイルしてノイズ付きで実行し、カウント（dict）を返す。

    ``circuits`` が1つなら dict を、リストなら dict のリストを返す。
    すでに ISA 回路（トランスパイル済み）なら ``transpile=False`` を指定する。
    """
    single = isinstance(circuits, QuantumCircuit)
    circs = [circuits] if single else list(circuits)
    for c in circs:
        if c.num_clbits == 0:
            raise ValueError(f"circuit {c.name!r} has no measurements; add qc.measure_all()")
    if transpile:
        circs = transpile_for(circs, backend, seed=seed_transpiler)
    result = simulator_for(backend, seed=seed).run(circs, shots=shots).result()
    counts = [result.get_counts(i) for i in range(len(circs))]
    return counts[0] if single else counts
