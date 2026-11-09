"""比較相手の Heron r3（ibm_boston、ヘビーヘックス）。中身は ``FakeBoston``。

::

    from nighthawk_sim import heron_r3
    be = heron_r3.backend()             # FakeBoston（1個ずつ測った誤り率）
    be = heron_r3.backend("layered")    # 誤り率の中央値を層状の公開値に合わせたもの

``"layered"`` は ``nighthawk_r2.backend("uniform")`` と公平に比べるためのもの（ノートブック 9.2 節）。
"""

from __future__ import annotations

from functools import lru_cache

from . import runner as _runner
from .analysis import median_error
from .backends import scale_backend
from .public_values import HERON_R3

__all__ = ["NAME", "NUM_QUBITS", "backend", "simulator", "sampler", "transpile", "best_transpile", "run", "info"]

NAME = "ibm_boston (Heron r3)"
NUM_QUBITS = 156


@lru_cache(maxsize=None)
def _boston():
    from qiskit_ibm_runtime.fake_provider import FakeBoston

    return FakeBoston()


@lru_cache(maxsize=None)
def _layered():
    b = _boston()
    scale = {"cz": HERON_R3["2q_layered"] / median_error(b, "cz"),
             "measure": HERON_R3["readout"] / median_error(b, "measure")}
    return scale_backend(b, scale, name="heron_r3_layered")


def backend(method: str = "fake"):
    """``"fake"``（FakeBoston、既定）または ``"layered"``。"""
    if method == "fake":
        return _boston()
    if method == "layered":
        return _layered()
    raise ValueError(f"method must be 'fake' or 'layered', got {method!r}")


def simulator(method: str = "fake", seed: int | None = None, **kwargs):
    return _runner.simulator_for(backend(method), seed=seed, **kwargs)


def sampler(method: str = "fake", seed: int | None = None, **kwargs):
    return _runner.sampler_for(backend(method), seed=seed, **kwargs)


def transpile(circuits, method: str = "fake", optimization_level: int = 3, seed: int | None = None, **kwargs):
    return _runner.transpile_for(circuits, backend(method), optimization_level, seed=seed, **kwargs)


def best_transpile(circuit, method: str = "fake", seeds=(1, 2, 3)):
    return _runner.best_transpile(circuit, backend(method), seeds=seeds)


def run(circuits, shots: int = 2000, method: str = "fake", seed: int | None = None,
        transpile: bool = True, seed_transpiler: int | None = None):
    return _runner.run_counts(circuits, backend(method), shots=shots, seed=seed,
                              transpile=transpile, seed_transpiler=seed_transpiler)


def info(method: str = "fake") -> dict:
    from .analysis import summarize

    return summarize(backend(method))
