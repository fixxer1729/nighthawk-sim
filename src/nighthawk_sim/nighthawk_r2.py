"""Nighthawk r2（ibm_phoenix）をシミュレータ上で再現する。

使い方::

    from nighthawk_sim import nighthawk_r2 as nk

    be = nk.backend()                   # 方法1（既定）：FakeMiami の誤り率を r2 並みに縮めたもの
    be = nk.backend("uniform")          # 方法2：公開値（層状の誤り率）を一様に入れたもの

    isa = nk.transpile(qc)              # r2 向けにトランスパイル
    counts = nk.run(qc, shots=2000)     # トランスパイル＋ノイズ付き実行 → カウント
    sampler = nk.sampler(seed=7)        # SamplerV2(mode=AerSimulator.from_backend(r2))

2通りの作り方
-------------
``"scaled"``（方法1）
    FakeMiami（r1 の実機スナップショット）の量子ビットごとの誤り率に、公開値から求めた
    r1→r2 の改善比（CZ ×0.394、読み出し ×0.355）を掛ける。ばらつきが残る現実的な見積もり。
``"uniform"``（方法2）
    12×10 正方格子のすべての量子ビット・カプラーに、r2 の公開値
    （CZ 3.499e-3＝層状の値、読み出し 7.202e-3）を一律に入れる。控えめ（悲観的）な見積もり。

前提
----
- 格子（12×10、カプラー218本）は r1 と同じと仮定している。物理量子ビット数が r1 の 338 から
  ちょうど 120 増えて 458 になったことからの推測で、IBM の公式な説明ではない。
- 1量子ビットゲートの誤り率と T1/T2 は公開値がないので r1（FakeMiami）の値のまま。
- 高速リセット（実行速度の改善）はシミュレーションには現れない。
"""

from __future__ import annotations

from functools import lru_cache

from . import runner as _runner
from .backends import make_nighthawk_like, scale_backend
from .backends import _miami
from .public_values import PUBLIC, R1_TO_R2_SCALE, R2

__all__ = [
    "NAME", "NUM_QUBITS", "ROWS", "COLS", "METHODS", "PUBLIC", "SCALE",
    "backend", "simulator", "sampler", "transpile", "best_transpile", "run", "info",
]

NAME = "ibm_phoenix (Nighthawk r2)"
ROWS, COLS = 12, 10
NUM_QUBITS = ROWS * COLS
METHODS = ("scaled", "uniform")

#: r1 → r2 の誤り率の改善比（方法1で使う）
SCALE = dict(R1_TO_R2_SCALE)

_ALIASES = {"scaled": "scaled", "method1": "scaled", 1: "scaled",
            "uniform": "uniform", "method2": "uniform", 2: "uniform"}


def _normalize(method) -> str:
    try:
        return _ALIASES[method]
    except (KeyError, TypeError):
        raise ValueError(f"method must be one of {METHODS} (or 1/2), got {method!r}") from None


@lru_cache(maxsize=None)
def _build(method: str):
    if method == "scaled":
        return scale_backend(_miami(), SCALE, name="nighthawk_r2_scaled")
    return make_nighthawk_like(ROWS, COLS, name="nighthawk_r2_uniform",
                               cz_error=R2["2q_layered"], readout_error=R2["readout"])


def backend(method="scaled"):
    """Nighthawk r2 のバックエンドを返す（同じ method なら同じオブジェクトを使い回す）。

    ``method``: ``"scaled"``（方法1、既定）または ``"uniform"``（方法2）。1 / 2 でも可。
    """
    return _build(_normalize(method))


def simulator(method="scaled", seed: int | None = None, **kwargs):
    """r2 のノイズを写した ``AerSimulator``。"""
    return _runner.simulator_for(backend(method), seed=seed, **kwargs)


def sampler(method="scaled", seed: int | None = None, **kwargs):
    """r2 のノイズ付きシミュレータを ``mode`` にした ``SamplerV2``。"""
    return _runner.sampler_for(backend(method), seed=seed, **kwargs)


def transpile(circuits, method="scaled", optimization_level: int = 3, seed: int | None = None, **kwargs):
    """回路を r2 のネイティブゲート（CZ, SX, X, RZ）と正方格子に合わせて書き換える。"""
    return _runner.transpile_for(circuits, backend(method), optimization_level, seed=seed, **kwargs)


def best_transpile(circuit, method="scaled", seeds=(1, 2, 3)):
    """シードを変えて何回かトランスパイルし、CZ 数が一番少ない回路を返す。"""
    return _runner.best_transpile(circuit, backend(method), seeds=seeds)


def run(circuits, shots: int = 2000, method="scaled", seed: int | None = None,
        transpile: bool = True, seed_transpiler: int | None = None):
    """回路を r2 向けにトランスパイルし、ノイズ付きで実行してカウントを返す。

    回路1つなら dict、リストなら dict のリスト。トランスパイル済みなら ``transpile=False``。
    """
    return _runner.run_counts(circuits, backend(method), shots=shots, seed=seed,
                              transpile=transpile, seed_transpiler=seed_transpiler)


def info(method="scaled") -> dict:
    """r2 バックエンドの主な数値（量子ビット数・カプラー数・誤り率の中央値など）。"""
    from .analysis import summarize

    return {"method": _normalize(method), **summarize(backend(method))}
