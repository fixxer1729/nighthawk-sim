import pytest

pytest.importorskip("ffsim")
pytest.importorskip("pyscf")
pytest.importorskip("qiskit_addon_sqd")

from nighthawk_sim import heron_r3  # noqa: E402
from nighthawk_sim import nighthawk_r2 as nk  # noqa: E402
from nighthawk_sim.chem import cas_hamiltonian, n2_problem, run_sqd, transpile_lucj  # noqa: E402


@pytest.fixture(scope="module")
def n2_sto6g():
    prob = n2_problem("sto-6g")
    return prob, cas_hamiltonian(prob)


def test_square_lattice_accepts_more_ab_pairs(n2_sto6g):
    prob, _ = n2_sto6g
    norb = prob["norb"]
    _, acc_sq = transpile_lucj(prob, nk.backend(), "square", [(p, p) for p in range(norb)])
    _, acc_hh = transpile_lucj(prob, heron_r3.backend(), "heavy-hex", [(p, p) for p in range(0, norb, 4)])
    assert len(acc_sq) == norb
    assert len(acc_hh) < len(acc_sq)


def test_run_sqd_on_r2(n2_sto6g):
    prob, ham = n2_sto6g
    norb = prob["norb"]
    # ノートブック 8.2 節と同じ設定（ショットを減らすと誤差が数十 mHa まで広がる）
    r = run_sqd(prob, ham, nk.backend(), "square", [(p, p) for p in range(norb)])
    assert 0.4 < r["valid_fraction"] <= 1.0
    assert r["energy"] >= ham["e_fci"] - 1e-6  # 変分原理
    assert r["error_mha"] < 50
