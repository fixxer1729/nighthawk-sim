"""IBM Quantum Platform の機体一覧に公開されている誤り率（2026年10月時点）。

- ``2q_best``: 2量子ビットゲート誤り（最良の1本）
- ``2q_layered``: 2量子ビットゲート誤り（多数を同時に並べて動かしたときの1ゲートあたり）
- ``readout``: 読み出し誤り（中央値）
"""

PUBLIC = {
    "ibm_miami (r1)": {"2q_best": 1.045e-3, "2q_layered": 8.881e-3, "readout": 2.026e-2},
    "ibm_phoenix (r2)": {"2q_best": 7.244e-4, "2q_layered": 3.499e-3, "readout": 7.202e-3},
    "ibm_boston (Heron r3)": {"2q_best": 5.193e-4, "2q_layered": 2.410e-3, "readout": 3.540e-3},
}

R1 = PUBLIC["ibm_miami (r1)"]
R2 = PUBLIC["ibm_phoenix (r2)"]
HERON_R3 = PUBLIC["ibm_boston (Heron r3)"]

#: r1 → r2 の誤り率の改善比（方法1で FakeMiami の誤り率に掛ける値）
R1_TO_R2_SCALE = {
    "cz": R2["2q_layered"] / R1["2q_layered"],
    "measure": R2["readout"] / R1["readout"],
}
