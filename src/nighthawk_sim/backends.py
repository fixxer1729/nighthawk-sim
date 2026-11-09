"""Nighthawk 型バックエンドを組み立てる道具。

- :class:`NighthawkLike`: ``Target`` を持つだけの最小限の ``BackendV2``。実行は Aer に任せる。
- :func:`make_nighthawk_like`: 正方格子＋一様な誤り率のバックエンドを作る。
- :func:`scale_backend`: 既存バックエンドの誤り率を命令ごとに何倍かにしたコピーを作る。
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from qiskit.circuit import Delay, Measure, Parameter
from qiskit.circuit.library import CZGate, IGate, RZGate, SXGate, XGate
from qiskit.providers import BackendV2, Options, QubitProperties
from qiskit.transpiler import CouplingMap, InstructionProperties, Target

from .analysis import median_duration, median_error

__all__ = ["NighthawkLike", "make_nighthawk_like", "scale_backend", "miami_defaults"]


class NighthawkLike(BackendV2):
    """``Target`` を持つだけの最小限のバックエンド。``run()`` は Aer に任せる。

    トランスパイル（``qiskit.transpile``）にも ``AerSimulator.from_backend`` にも、
    フェイクバックエンドと同じように渡せる。
    """

    def __init__(self, target: Target, name: str = "nighthawk_like"):
        super().__init__(name=name)
        self._target = target

    @property
    def target(self) -> Target:
        return self._target

    @property
    def max_circuits(self):
        return None

    @classmethod
    def _default_options(cls):
        return Options(shots=1024)

    def run(self, run_input, **options):
        from qiskit_aer import AerSimulator

        return AerSimulator.from_backend(self).run(run_input, **options)


@lru_cache(maxsize=None)
def _miami():
    from qiskit_ibm_runtime.fake_provider import FakeMiami

    return FakeMiami()


@lru_cache(maxsize=None)
def miami_defaults() -> dict:
    """FakeMiami（Nighthawk r1）の中央値。:func:`make_nighthawk_like` の既定値になる。"""
    ref = _miami()
    nq = ref.num_qubits
    return dict(
        cz_error=median_error(ref, "cz"),
        sq_error=median_error(ref, "sx"),
        readout_error=median_error(ref, "measure"),
        t1=float(np.median([ref.qubit_properties(q).t1 for q in range(nq)])),
        t2=float(np.median([ref.qubit_properties(q).t2 for q in range(nq)])),
        cz_duration=median_duration(ref, "cz"),
        sq_duration=median_duration(ref, "sx"),
        meas_duration=median_duration(ref, "measure"),
        dt=ref.target.dt,
    )


def make_nighthawk_like(rows: int = 12, cols: int = 10, name: str = "nighthawk_like", **overrides) -> NighthawkLike:
    """正方格子＋一様な誤り率の Nighthawk 型バックエンドを作る。

    量子ビット番号は ``q = 行 * cols + 列``（FakeMiami と同じ番号づけ）。
    すべての量子ビット・カプラーに同じ値を入れるので、場所によるばらつきはない。

    Parameters
    ----------
    rows, cols:
        格子の大きさ。既定は 12×10（120 量子ビット、Nighthawk と同じ）。
    **overrides:
        ``cz_error``, ``sq_error``, ``readout_error``（誤り率）、
        ``t1``, ``t2``（秒）、``cz_duration``, ``sq_duration``, ``meas_duration``（秒）、``dt``。
        指定しなかったものは FakeMiami の中央値（:func:`miami_defaults`）。
    """
    defaults = miami_defaults()
    unknown = set(overrides) - set(defaults)
    if unknown:
        raise TypeError(f"unknown parameter(s): {sorted(unknown)}; allowed: {sorted(defaults)}")
    p = {**defaults, **overrides}

    n = rows * cols
    cmap = CouplingMap.from_grid(rows, cols)
    qprops = [QubitProperties(t1=p["t1"], t2=min(p["t2"], 2 * p["t1"]), frequency=5e9) for _ in range(n)]
    target = Target(num_qubits=n, dt=p["dt"], qubit_properties=qprops)
    target.add_instruction(
        CZGate(), {e: InstructionProperties(p["cz_duration"], p["cz_error"]) for e in cmap.get_edges()}
    )
    for gate in (SXGate(), XGate(), IGate()):
        target.add_instruction(
            gate, {(q,): InstructionProperties(p["sq_duration"], p["sq_error"]) for q in range(n)}
        )
    # RZ は仮想 Z ゲートなので時間も誤りも 0
    target.add_instruction(RZGate(Parameter("θ")), {(q,): InstructionProperties(0.0, 0.0) for q in range(n)})
    target.add_instruction(
        Measure(), {(q,): InstructionProperties(p["meas_duration"], p["readout_error"]) for q in range(n)}
    )
    target.add_instruction(Delay(Parameter("t")), {(q,): None for q in range(n)})
    return NighthawkLike(target, name=name)


def scale_backend(src, scale: dict, name: str) -> NighthawkLike:
    """``src`` の Target を1命令ずつコピーし、``scale`` に書かれた命令だけ誤り率を何倍かにする。

    例: ``scale_backend(FakeMiami(), {"cz": 0.39, "measure": 0.36}, name="r2")``
    量子ビットごとのばらつきはそのまま残る。誤り率は 1 を上限に切り詰める。
    """
    t = src.target
    new_t = Target(
        num_qubits=t.num_qubits,
        dt=t.dt,
        qubit_properties=[src.qubit_properties(q) for q in range(t.num_qubits)],
    )
    for op_name in t.operation_names:
        op = t.operation_from_name(op_name)
        if isinstance(op, type):  # if_else などの制御フロー命令（全量子ビット共通・誤り率なし）
            new_t.add_instruction(op, name=op_name)
            continue
        props = {}
        for qargs, prop in t[op_name].items():
            if prop is None:
                props[qargs] = None
                continue
            err = prop.error
            if err is not None and op_name in scale:
                err = min(err * scale[op_name], 1.0)
            props[qargs] = InstructionProperties(duration=prop.duration, error=err)
        new_t.add_instruction(op, props, name=op_name)
    return NighthawkLike(new_t, name=name)
