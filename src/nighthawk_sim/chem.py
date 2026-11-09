"""量子化学（LUCJ 回路＋SQD）用の関数。

``pip install "nighthawk-sim[chem]"`` で入る ffsim / pyscf / qiskit-addon-sqd が必要。
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister

__all__ = ["n2_problem", "lucj_circuit", "transpile_lucj", "valid_fraction", "cas_hamiltonian", "run_sqd"]


def n2_problem(basis: str, bond: float = 1.1, n_frozen: int = 2) -> dict:
    """N₂ 分子の RHF と CCSD を解いて、LUCJ に必要な情報を dict で返す。"""
    import pyscf
    import pyscf.cc
    import pyscf.scf

    mol = pyscf.gto.Mole()
    mol.build(atom=[["N", (0, 0, 0)], ["N", (bond, 0, 0)]], basis=basis, symmetry="Dooh", verbose=0)
    scf = pyscf.scf.RHF(mol).run()
    frozen = list(range(n_frozen))
    active = [i for i in range(mol.nao_nr()) if i not in frozen]
    norb = len(active)
    nelec = (int(sum(scf.mo_occ[active]) // 2),) * 2
    ccsd = pyscf.cc.CCSD(scf, frozen=frozen).run()
    return dict(mol=mol, scf=scf, active=active, norb=norb, nelec=nelec, ccsd=ccsd)


def lucj_circuit(prob: dict, pairs_aa, pairs_ab, n_reps: int = 1) -> QuantumCircuit:
    """CCSD 振幅から作った LUCJ 回路（Hartree–Fock 状態の準備＋測定つき）。"""
    import ffsim

    op = ffsim.UCJOpSpinBalanced.from_t_amplitudes(
        prob["ccsd"].t2, t1=prob["ccsd"].t1, n_reps=n_reps, interaction_pairs=(pairs_aa, pairs_ab))
    q = QuantumRegister(2 * prob["norb"], "q")
    qc = QuantumCircuit(q)
    qc.append(ffsim.qiskit.PrepareHartreeFockJW(prob["norb"], prob["nelec"]), q)
    qc.append(ffsim.qiskit.UCJOpSpinBalancedJW(op), q)
    qc.measure_all()
    return qc


def transpile_lucj(prob: dict, backend, connectivity: str, requested_ab, seed: int = 1, n_reps: int = 1):
    """格子に合わせて α–β ペアを選び、LUCJ 回路をトランスパイルする。

    ``connectivity`` は ``"square"``（Nighthawk）か ``"heavy-hex"``（Heron）。
    戻り値は (ISA 回路, 実際に採用された α–β ペアのリスト)。
    """
    import ffsim

    norb = prob["norb"]
    pairs_aa = [(p, p + 1) for p in range(norb - 1)]
    pm, accepted_ab = ffsim.qiskit.generate_lucj_pass_manager(
        backend, norb, connectivity, interaction_pairs=(pairs_aa, requested_ab),
        optimization_level=3, seed_transpiler=seed)
    pm.pre_init = ffsim.qiskit.PRE_INIT
    isa = pm.run(lucj_circuit(prob, pairs_aa, accepted_ab, n_reps=n_reps))
    return isa, accepted_ab


def valid_fraction(bit_array, norb: int, nelec) -> float:
    """正しい電子数（α, β とも）のサンプルの割合。"""
    bits = bit_array.get_bitstrings()
    # Qiskit のビット列は右端が q0。q0..q(norb-1) が α、残りが β
    na = np.array([b[norb:].count("1") for b in bits])
    nb = np.array([b[:norb].count("1") for b in bits])
    return float(np.mean((na == nelec[0]) & (nb == nelec[1])))


def cas_hamiltonian(prob: dict) -> dict:
    """活性空間のハミルトニアン（h1, h2, ecore）と FCI エネルギー。"""
    import pyscf.ao2mo
    import pyscf.mcscf

    norb, nelec = prob["norb"], prob["nelec"]
    cas = pyscf.mcscf.CASCI(prob["scf"], norb, nelec)
    mo = cas.sort_mo(prob["active"], base=0)
    h1, ecore = cas.get_h1cas(mo)
    h2 = pyscf.ao2mo.restore(1, cas.get_h2cas(mo), norb)
    e_fci = cas.kernel(mo)[0]
    return dict(h1=h1, h2=h2, ecore=ecore, e_fci=e_fci)


def run_sqd(prob: dict, ham: dict, backend, connectivity: str, requested_ab, shots: int = 1000,
            seed: int = 11, samples_per_batch: int = 300, num_batches: int = 3, max_iterations: int = 5) -> dict:
    """LUCJ をノイズ付きでサンプリングし、SQD でエネルギーを求める（ノートブック 8.2 節）。"""
    from qiskit_addon_sqd.fermion import diagonalize_fermionic_hamiltonian

    from .runner import sampler_for

    norb, nelec = prob["norb"], prob["nelec"]
    isa, acc = transpile_lucj(prob, backend, connectivity, requested_ab)
    bit_array = sampler_for(backend, seed=seed).run([isa], shots=shots).result()[0].data.meas
    sqd = diagonalize_fermionic_hamiltonian(
        ham["h1"], ham["h2"], bit_array, samples_per_batch=samples_per_batch, norb=norb, nelec=nelec,
        num_batches=num_batches, max_iterations=max_iterations, seed=seed)
    e = sqd.energy + ham["ecore"]
    return {
        "num_ab_pairs": len(acc),
        "cz": isa.count_ops().get("cz", 0),
        "valid_fraction": valid_fraction(bit_array, norb, nelec),
        "energy": e,
        "error_mha": (e - ham["e_fci"]) * 1000,
    }
