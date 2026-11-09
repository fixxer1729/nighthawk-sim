# nighthawk-sim

IBM Quantum の正方格子プロセッサー **Nighthawk** を、Qiskit Aer 上のノイズ付きシミュレータとして再現するパッケージです。
公式のフェイクバックエンドがまだない **Nighthawk r2（ibm_phoenix）** を、IBM Quantum Platform の公開値から組み立てます。

元になったノートブックは [`notebooks/nighthawk_simulator.ipynb`](notebooks/nighthawk_simulator.ipynb) にあります（解説と実行結果つき）。

## インストール

private リポジトリなので、GitHub にログイン済みの環境で入れてください。

```bash
pip install "git+https://github.com/fixxer1729/nighthawk-sim.git"
```

量子化学（LUCJ＋SQD）や描画も使う場合:

```bash
pip install "nighthawk-sim[chem,plot] @ git+https://github.com/fixxer1729/nighthawk-sim.git"
```

手元で開発するとき:

```bash
git clone https://github.com/fixxer1729/nighthawk-sim.git && cd nighthawk-sim
uv venv && uv pip install -e ".[dev,plot]"
```

## 使い方

```python
from qiskit import QuantumCircuit
from nighthawk_sim import nighthawk_r2 as nk

qc = QuantumCircuit(3)
qc.h(0); qc.cx(0, 1); qc.cx(1, 2)
qc.measure_all()

counts = nk.run(qc, shots=2000)        # r2 向けにトランスパイル → ノイズ付き実行
print(counts)
```

| 関数 | 中身 |
|---|---|
| `nk.backend(method="scaled")` | r2 の `BackendV2`。`transpile()` や `AerSimulator.from_backend()` にそのまま渡せる |
| `nk.transpile(qc, seed=None)` | r2 のネイティブゲートと 12×10 正方格子に合わせて書き換える（`optimization_level=3`） |
| `nk.best_transpile(qc)` | シードを3つ試して CZ 数が最少の回路を返す |
| `nk.run(qc, shots=2000, seed=None)` | トランスパイル＋ノイズ付き実行 → カウント（回路のリストも可） |
| `nk.sampler(seed=None)` | `SamplerV2(mode=AerSimulator.from_backend(r2))`。実機と同じ書き方で使える |
| `nk.simulator(seed=None)` | r2 のノイズを写した `AerSimulator` |
| `nk.info()` | 量子ビット数・カプラー数・誤り率の中央値など |

### `method`：r2 の2通りの作り方

| | `"scaled"`（方法1、既定） | `"uniform"`（方法2） |
|---|---|---|
| 作り方 | FakeMiami（r1）の量子ビットごとの誤り率に r1→r2 の改善比を掛ける | 12×10 正方格子に r2 の公開値を一律に入れる |
| CZ 誤り率 | ×0.394（中央値 約 1.2×10⁻³） | 3.499×10⁻³（層状の値） |
| 読み出し誤り率 | ×0.355 | 7.202×10⁻³ |
| 性格 | ばらつきが残る現実的な見積もり | ばらつきなし・控えめ（悲観的）な見積もり |

実際の r2 はこの2つの間にあると考えられます。

```python
nk.run(qc, method="uniform")
```

### 比較用のバックエンド

```python
from nighthawk_sim import nighthawk_r1, heron_r3

nighthawk_r1.run(qc)              # Nighthawk r1（FakeMiami）
heron_r3.run(qc)                  # Heron r3（FakeBoston）
heron_r3.backend("layered")       # Heron r3 の誤り率を層状の公開値に合わせたもの（方法2との公平な比較用）
```

どれも `backend / transpile / best_transpile / run / sampler / simulator / info` を同じ名前で持っています。

### 誤り率を自由に決めた Nighthawk 型バックエンド

```python
from nighthawk_sim import make_nighthawk_like, scale_backend

be = make_nighthawk_like(cz_error=1e-3, readout_error=5e-3)   # 12×10、一様な誤り率
be = make_nighthawk_like(6, 6, cz_error=5e-4)                 # 格子の大きさも変えられる
r3_guess = scale_backend(nk.backend(), {"cz": 0.5}, name="r3?")  # r2 の CZ 誤り率をさらに半分に
```

### そのほか

- `nighthawk_sim.analysis`：`summarize`, `esp`（Estimated Success Probability）, `edge_errors`, `readout_errors`, `draw_lattice` など
- `nighthawk_sim.circuits`：`ghz`, `ising_1d`, `ising_2d`, `qaoa_3reg`, `qft`, `benchmark_circuits()`
- `nighthawk_sim.chem`（`[chem]` が必要）：`n2_problem`, `transpile_lucj`, `cas_hamiltonian`, `run_sqd`

[`examples/quickstart.py`](examples/quickstart.py) に、GHZ と 2D Ising を r2 / r1 / Heron r3 で比べる例があります。

## 前提と限界

- 公開値は 2026年10月時点の IBM Quantum Platform の機体一覧から取っています（`nighthawk_sim.PUBLIC`）。
- r2 の格子（12×10、カプラー218本）は r1 と同じと仮定しています。物理量子ビット数が 338 → 458 とちょうど 120 増えたことからの推測で、IBM の公式な説明ではありません。
- 1量子ビットゲートの誤り率と T1/T2 は公開値がないので、r1（FakeMiami）の値のままです。
- 高速リセットによる実行速度の改善は、シミュレーションには現れません。

## テスト

```bash
pytest
```

`[chem]` を入れていない環境では、量子化学のテスト（`tests/test_chem.py`）は自動でスキップされます。

動作確認した環境：Python 3.13、qiskit 2.4.2、qiskit-aer 0.17.2、qiskit-ibm-runtime 0.50.0、ffsim 0.0.86、pyscf 2.15.0、qiskit-addon-sqd 0.14.1
