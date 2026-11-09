"""Nighthawk r1（ibm_miami）。中身は qiskit-ibm-runtime の ``FakeMiami``。

``nighthawk_r2`` と同じ書き方で使える::

    from nighthawk_sim import nighthawk_r1 as nk1
    counts = nk1.run(qc, shots=2000)
"""

from __future__ import annotations

from . import runner as _runner
from .backends import _miami

__all__ = ["NAME", "NUM_QUBITS", "backend", "simulator", "sampler", "transpile", "best_transpile", "run", "info"]

NAME = "ibm_miami (Nighthawk r1)"
NUM_QUBITS = 120


def backend():
    """``FakeMiami``（使い回し）。"""
    return _miami()


def simulator(seed: int | None = None, **kwargs):
    return _runner.simulator_for(backend(), seed=seed, **kwargs)


def sampler(seed: int | None = None, **kwargs):
    return _runner.sampler_for(backend(), seed=seed, **kwargs)


def transpile(circuits, optimization_level: int = 3, seed: int | None = None, **kwargs):
    return _runner.transpile_for(circuits, backend(), optimization_level, seed=seed, **kwargs)


def best_transpile(circuit, seeds=(1, 2, 3)):
    return _runner.best_transpile(circuit, backend(), seeds=seeds)


def run(circuits, shots: int = 2000, seed: int | None = None, transpile: bool = True,
        seed_transpiler: int | None = None):
    return _runner.run_counts(circuits, backend(), shots=shots, seed=seed,
                              transpile=transpile, seed_transpiler=seed_transpiler)


def info() -> dict:
    from .analysis import summarize

    return summarize(backend())
