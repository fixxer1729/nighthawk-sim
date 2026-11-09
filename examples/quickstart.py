"""nighthawk_sim の最小例: GHZ と 2D Ising を Nighthawk r2 / r1 / Heron r3 で比べる。

    python examples/quickstart.py
"""

from nighthawk_sim import heron_r3, nighthawk_r1
from nighthawk_sim import nighthawk_r2 as nk
from nighthawk_sim.analysis import cz_count, esp
from nighthawk_sim.circuits import ghz, ghz_success, ising_2d

print("== Nighthawk r2 の数値")
for method in nk.METHODS:
    i = nk.info(method)
    print(f"  {method:8s} qubits={i['num_qubits']} couplers={i['num_couplers']} "
          f"CZ={i['cz_error_median']:.2e} readout={i['readout_error_median']:.2e}")

print("\n== GHZ(16) 成功率")
qc = ghz(16)
for name, run in [("r2 scaled", lambda: nk.run(qc, seed=7, seed_transpiler=1)),
                  ("r2 uniform", lambda: nk.run(qc, method="uniform", seed=7, seed_transpiler=1)),
                  ("r1 (FakeMiami)", lambda: nighthawk_r1.run(qc, seed=7, seed_transpiler=1)),
                  ("Heron r3 (FakeBoston)", lambda: heron_r3.run(qc, seed=7, seed_transpiler=1))]:
    print(f"  {name:22s} {ghz_success(run(), 16):.3f}")

print("\n== 2D Ising 4x5: CZ 数と ESP")
qc = ising_2d()
for name, mod, be in [("r2 scaled", nk, nk.backend()),
                      ("r1 (FakeMiami)", nighthawk_r1, nighthawk_r1.backend()),
                      ("Heron r3 (FakeBoston)", heron_r3, heron_r3.backend())]:
    isa = mod.best_transpile(qc)
    print(f"  {name:22s} CZ={cz_count(isa):4d}  ESP={esp(isa, be):.3f}")
