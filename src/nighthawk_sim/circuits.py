"""ベンチマーク用の回路。"""

from __future__ import annotations

import networkx as nx
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate

__all__ = ["ghz", "ghz_success", "ising_1d", "ising_2d", "qaoa_3reg", "qft", "benchmark_circuits"]


def ghz(n: int) -> QuantumCircuit:
    """n 量子ビットの GHZ 状態を作って測定する回路（鎖状）。"""
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    qc.measure_all()
    return qc


def ghz_success(counts: dict, n: int) -> float:
    """``00…0`` と ``11…1`` が出た割合（GHZ 成功率）。"""
    shots = sum(counts.values())
    return (counts.get("0" * n, 0) + counts.get("1" * n, 0)) / shots


def ising_1d(n: int = 20, steps: int = 4, dt: float = 0.1) -> QuantumCircuit:
    """1次元横磁場イジング模型の時間発展（隣同士だけ）。"""
    qc = QuantumCircuit(n)
    for _ in range(steps):
        for parity in (0, 1):
            for i in range(parity, n - 1, 2):
                qc.rzz(2 * dt, i, i + 1)
        qc.rx(2 * dt, range(n))
    qc.measure_all()
    return qc


def ising_2d(rows: int = 4, cols: int = 5, steps: int = 4, dt: float = 0.1) -> QuantumCircuit:
    """2次元横磁場イジング模型の時間発展（上下左右の隣）。"""
    n = rows * cols
    qc = QuantumCircuit(n)
    edges = [(r * cols + c, r * cols + c + 1) for r in range(rows) for c in range(cols - 1)] + \
            [(r * cols + c, (r + 1) * cols + c) for r in range(rows - 1) for c in range(cols)]
    for _ in range(steps):
        for a, b in edges:
            qc.rzz(2 * dt, a, b)
        qc.rx(2 * dt, range(n))
    qc.measure_all()
    return qc


def qaoa_3reg(n: int = 20, seed: int = 3, gamma: float = 0.4, beta: float = 0.3) -> QuantumCircuit:
    """ランダム3正則グラフの QAOA（1層）。"""
    g = nx.random_regular_graph(3, n, seed=seed)
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for a, b in g.edges:
        qc.rzz(2 * gamma, a, b)
    qc.rx(2 * beta, range(n))
    qc.measure_all()
    return qc


def qft(n: int = 12) -> QuantumCircuit:
    """量子フーリエ変換（全員と全員が相互作用する）。"""
    qc = QuantumCircuit(n)
    qc.h(range(n))
    qc.append(QFTGate(n), range(n))
    qc.measure_all()
    return qc


def benchmark_circuits() -> dict:
    """ノートブック7章の4種類のベンチマーク回路。"""
    return {
        "1D Ising (20q)": ising_1d(),
        "2D Ising 4x5 (20q)": ising_2d(),
        "QAOA 3-regular (20q)": qaoa_3reg(),
        "QFT (12q)": qft(),
    }
