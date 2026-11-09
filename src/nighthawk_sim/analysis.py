"""バックエンドの数値を取り出す・回路を評価する・格子を描く関数。"""

from __future__ import annotations

import collections

import networkx as nx
import numpy as np

__all__ = [
    "undirected_graph",
    "median_error",
    "median_duration",
    "summarize",
    "edge_errors",
    "readout_errors",
    "esp",
    "cz_count",
    "two_qubit_depth",
    "coords_nighthawk",
    "coords_heron",
    "check_coords",
    "draw_lattice",
]


def undirected_graph(backend) -> nx.Graph:
    """カップリングマップを無向グラフにまとめる（(a,b) と (b,a) を1本の辺にする）。"""
    g = nx.Graph()
    g.add_nodes_from(range(backend.num_qubits))
    g.add_edges_from(backend.coupling_map.get_edges())
    return g


def median_error(backend, gate: str) -> float:
    """命令 ``gate`` の誤り率の中央値。"""
    errs = [p.error for p in backend.target[gate].values() if p is not None and p.error is not None]
    return float(np.median(errs))


def median_duration(backend, gate: str) -> float:
    """命令 ``gate`` の実行時間 [秒] の中央値。"""
    durs = [p.duration for p in backend.target[gate].values() if p is not None and p.duration is not None]
    return float(np.median(durs))


def summarize(backend) -> dict:
    """量子ビット数・カプラー数・誤り率の中央値・T1/T2 などをまとめた dict。

    ``pandas.DataFrame({"name": summarize(be), ...})`` で表にできる。
    """
    g = undirected_graph(backend)
    deg = collections.Counter(d for _, d in g.degree())
    nq = backend.num_qubits
    t1 = [backend.qubit_properties(q).t1 for q in range(nq)]
    t2 = [backend.qubit_properties(q).t2 for q in range(nq)]
    return {
        "num_qubits": nq,
        "num_couplers": g.number_of_edges(),
        "degree_histogram": dict(sorted(deg.items())),
        "native_gates": sorted(set(backend.operation_names) & {"cz", "sx", "x", "rz", "id"}),
        "cz_error_median": median_error(backend, "cz"),
        "sx_error_median": median_error(backend, "sx"),
        "readout_error_median": median_error(backend, "measure"),
        "t1_median_us": float(np.median(t1)) * 1e6,
        "t2_median_us": float(np.median(t2)) * 1e6,
    }


def edge_errors(backend) -> dict:
    """カプラーごとの CZ 誤り率 ``{(a, b): error}``（a < b、両向きのうち大きいほう）。"""
    out = {}
    for (a, b), p in backend.target["cz"].items():
        if p is not None and p.error is not None:
            key = tuple(sorted((a, b)))
            out[key] = max(out.get(key, 0.0), p.error)
    return out


def readout_errors(backend) -> dict:
    """量子ビットごとの読み出し誤り率 ``{q: error}``。"""
    return {q[0]: p.error for q, p in backend.target["measure"].items() if p is not None}


def esp(isa_circuit, backend) -> float:
    """Estimated Success Probability：全命令の (1 − 誤り率) の積。

    ``isa_circuit`` は ``backend`` 向けにトランスパイル済みの回路。
    """
    t = backend.target
    logp = 0.0
    for inst in isa_circuit.data:
        name = inst.operation.name
        if name in ("barrier", "delay") or name not in t.operation_names:
            continue
        qargs = tuple(isa_circuit.find_bit(q).index for q in inst.qubits)
        props = t[name].get(qargs)
        if props is not None and props.error is not None:
            logp += np.log1p(-min(props.error, 0.999999))
    return float(np.exp(logp))


def cz_count(isa_circuit) -> int:
    """トランスパイル済み回路の CZ ゲート数。"""
    return isa_circuit.count_ops().get("cz", 0)


def two_qubit_depth(isa_circuit) -> int:
    """2量子ビットゲートだけで数えた回路の深さ。"""
    return isa_circuit.depth(lambda x: x.operation.num_qubits == 2)


# ---------------------------------------------------------------- 格子の座標と描画


def coords_nighthawk(q: int, ncols: int = 10) -> tuple[int, int]:
    """Nighthawk（12×10 正方格子）の量子ビット ``q`` の (行, 列)。"""
    return (q // ncols, q % ncols)


def coords_heron(q: int) -> tuple[int, int]:
    """Heron（156 量子ビットのヘビーヘックス）の量子ビット ``q`` の (行, 列)。"""
    block, k = divmod(q, 20)  # 1ブロック = 横一列16個 + 橋渡し4個
    if k < 16:
        return (2 * block, k)
    cols = [3, 7, 11, 15] if block % 2 == 0 else [1, 5, 9, 13]
    return (2 * block + 1, cols[k - 16])


def check_coords(backend, coord_fn) -> bool:
    """座標上で隣同士の量子ビットだけが結合しているかを確かめる。違えば AssertionError。"""
    for a, b in backend.coupling_map.get_edges():
        (ra, ca), (rb, cb) = coord_fn(a), coord_fn(b)
        assert abs(ra - rb) + abs(ca - cb) == 1, (a, b)
    return True


def draw_lattice(backend, coord_fn, ax, title="", node_color=None, edge_color=None,
                 cmap="viridis", node_size=90):
    """実際の格子どおりの座標で結合グラフを描く（matplotlib が必要）。

    ``node_color``: ``{q: 値}``、``edge_color``: ``{(a, b): 値}``（a < b）。
    戻り値は (ノードの artist, 辺の artist)。カラーバーに使える。
    """
    import matplotlib.pyplot as plt

    g = undirected_graph(backend)
    pos = {q: (coord_fn(q)[1], -coord_fn(q)[0]) for q in g.nodes}
    ec = [edge_color[tuple(sorted(e))] for e in g.edges] if edge_color else "#888888"
    ed = nx.draw_networkx_edges(g, pos, ax=ax, edge_color=ec, width=2.0,
                                edge_cmap=plt.get_cmap(cmap) if edge_color else None)
    nc = [node_color[q] for q in g.nodes] if node_color else "#4C72B0"
    nd = nx.draw_networkx_nodes(g, pos, ax=ax, node_color=nc, node_size=node_size,
                                cmap=plt.get_cmap(cmap) if node_color else None)
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.axis("off")
    return nd, ed
