import pytest

from nighthawk_sim import heron_r3, make_nighthawk_like, nighthawk_r1
from nighthawk_sim import nighthawk_r2 as nk
from nighthawk_sim.analysis import check_coords, coords_heron, coords_nighthawk, esp, median_error, summarize
from nighthawk_sim.circuits import ghz, ghz_success, ising_2d
from nighthawk_sim.public_values import R2


@pytest.mark.parametrize("method", ["scaled", "uniform"])
def test_r2_lattice_is_12x10_square(method):
    s = summarize(nk.backend(method))
    assert s["num_qubits"] == 120
    assert s["num_couplers"] == 218
    assert set(s["degree_histogram"]) <= {2, 3, 4}
    check_coords(nk.backend(method), coords_nighthawk)


def test_r2_error_rates():
    scaled, uniform, r1 = nk.backend("scaled"), nk.backend("uniform"), nighthawk_r1.backend()
    # 方法1：r1 の中央値に改善比を掛けた値
    assert median_error(scaled, "cz") == pytest.approx(median_error(r1, "cz") * nk.SCALE["cz"], rel=1e-9)
    assert median_error(scaled, "measure") == pytest.approx(
        median_error(r1, "measure") * nk.SCALE["measure"], rel=1e-9)
    # 方法2：公開値そのもの
    assert median_error(uniform, "cz") == pytest.approx(R2["2q_layered"])
    assert median_error(uniform, "measure") == pytest.approx(R2["readout"])


def test_backend_aliases_and_cache():
    assert nk.backend() is nk.backend("scaled") is nk.backend(1) is nk.backend("method1")
    assert nk.backend(2) is nk.backend("uniform")
    with pytest.raises(ValueError):
        nk.backend("nope")


def test_ghz_runs_with_noise():
    counts = nk.run(ghz(6), shots=500, seed=7, seed_transpiler=1)
    assert sum(counts.values()) == 500
    p = ghz_success(counts, 6)
    assert 0.7 < p < 1.0  # ノイズで少し落ちるが大半は成功


def test_run_list_and_isa():
    isa = nk.transpile([ghz(3), ghz(4)], seed=1)
    out = nk.run(isa, shots=100, seed=1, transpile=False)
    assert len(out) == 2 and all(sum(c.values()) == 100 for c in out)


def test_run_requires_measurement():
    from qiskit import QuantumCircuit

    with pytest.raises(ValueError):
        nk.run(QuantumCircuit(2))


def test_square_lattice_beats_heavy_hex_on_2d_ising():
    qc = ising_2d()
    r2_isa = nk.best_transpile(qc)
    heron_isa = heron_r3.best_transpile(qc)
    assert r2_isa.count_ops()["cz"] < heron_isa.count_ops()["cz"]
    assert esp(r2_isa, nk.backend()) > esp(heron_isa, heron_r3.backend())


def test_heron_coords_and_layered():
    check_coords(heron_r3.backend(), coords_heron)
    assert median_error(heron_r3.backend("layered"), "cz") == pytest.approx(2.410e-3)


def test_make_nighthawk_like_rejects_unknown_kwargs():
    be = make_nighthawk_like(4, 5, cz_error=1e-3)
    assert be.num_qubits == 20
    with pytest.raises(TypeError):
        make_nighthawk_like(cz_eror=1e-3)
