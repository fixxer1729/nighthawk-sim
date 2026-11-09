"""IBM Quantum Nighthawk（正方格子プロセッサー）を Qiskit Aer 上で再現するパッケージ。

::

    from nighthawk_sim import nighthawk_r2 as nk

    counts = nk.run(qc, shots=2000)

モジュール
----------
- :mod:`nighthawk_sim.nighthawk_r2` — Nighthawk r2（ibm_phoenix）を公開値から再現
- :mod:`nighthawk_sim.nighthawk_r1` — Nighthawk r1（FakeMiami）
- :mod:`nighthawk_sim.heron_r3` — 比較用の Heron r3（FakeBoston）
- :mod:`nighthawk_sim.backends` — 誤り率を自由に決められる Nighthawk 型バックエンド
- :mod:`nighthawk_sim.analysis` — 誤り率の集計・ESP・格子の描画
- :mod:`nighthawk_sim.circuits` — GHZ / Ising / QAOA / QFT のベンチマーク回路
- :mod:`nighthawk_sim.chem` — LUCJ＋SQD（``[chem]`` extra が必要）
"""

from . import analysis, circuits, heron_r3, nighthawk_r1, nighthawk_r2
from .analysis import esp, summarize
from .backends import NighthawkLike, make_nighthawk_like, scale_backend
from .public_values import PUBLIC

__version__ = "0.1.0"

__all__ = [
    "nighthawk_r1", "nighthawk_r2", "heron_r3", "analysis", "circuits",
    "NighthawkLike", "make_nighthawk_like", "scale_backend", "summarize", "esp", "PUBLIC",
]
