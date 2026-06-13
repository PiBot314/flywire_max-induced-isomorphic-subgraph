"""
Circuit Report Generator
========================
Loads the ag.json checkpoint (MANC, MAOL, MCNS — 5-node isomorphic circuit),
extracts the induced subgraph edges, prints topology, and saves a network
visualization to results/circuit_visualization.png.
"""

import pickle
import gzip
import json
import igraph as ig
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent
GRAPHS   = ROOT / "processed" / "graph"
DEGREES  = ROOT / "processed" / "degrees"
CKPT     = ROOT / "results" / "checkpoints" / "ag.json"
OUT_IMG  = ROOT / "results" / "circuit_visualization.png"

DATASET_NAMES = {3: "MANC", 4: "MAOL", 5: "MCNS"}
GRAPH_FILES   = {3: "MANC_graph.pkl", 4: "MAOL_graph.pkl", 5: "MCNS_graph.pkl"}

# ── Load checkpoint ───────────────────────────────────────────────────────────
with open(CKPT) as f:
    ckpt = json.load(f)

triple   = ckpt["dataset_triple"]           # [3, 4, 5]
mapping  = ckpt["mapping"]                  # {"0": [ds3_id, ds4_id, ds5_id], ...}
n_nodes  = ckpt["size"]

print(f"Circuit: {n_nodes} nodes across {[DATASET_NAMES[d] for d in triple]}")
print(f"Timestamp: {ckpt['timestamp']}\n")

node_ids = {ds_idx: [mapping[str(i)][j] for i in range(n_nodes)]
            for j, ds_idx in enumerate(triple)}

for ds_idx, ids in node_ids.items():
    print(f"  {DATASET_NAMES[ds_idx]}: {ids}")

# ── Load graphs ───────────────────────────────────────────────────────────────
graphs = {}
for ds_idx in triple:
    pkl = GRAPHS / GRAPH_FILES[ds_idx]
    try:
        with gzip.open(pkl, "rb") as f:
            graphs[ds_idx] = pickle.load(f)
    except Exception:
        with open(pkl, "rb") as f:
            graphs[ds_idx] = pickle.load(f)
    print(f"\nLoaded {DATASET_NAMES[ds_idx]}: "
          f"{graphs[ds_idx].vcount()} vertices, "
          f"{graphs[ds_idx].ecount()} edges")

# ── Extract induced subgraph edges ────────────────────────────────────────────
def get_edges(g: ig.Graph, id_list: list[str]) -> list[tuple[int, int]]:
    """Return (src_local, dst_local) pairs among the listed neuron IDs."""
    # igraph vertex names are stored as the 'name' attribute when built from
    # a VertexSeq with names; fall back to integer index matching if needed.
    try:
        vnames = g.vs["name"]
        name_to_idx = {str(n): i for i, n in enumerate(vnames)}
        v_idx = [name_to_idx[nid] for nid in id_list if nid in name_to_idx]
    except (KeyError, ig.InternalError):
        # names not stored; try integer vertex IDs
        v_idx = [int(nid) for nid in id_list]

    id_set = set(v_idx)
    edges_out = []
    for src in v_idx:
        for dst in g.successors(src):
            if dst in id_set:
                edges_out.append((v_idx.index(src), v_idx.index(dst)))
    return edges_out

edge_sets = {}
for ds_idx in triple:
    edges = get_edges(graphs[ds_idx], node_ids[ds_idx])
    edge_sets[ds_idx] = edges
    print(f"\n{DATASET_NAMES[ds_idx]} induced edges:")
    for (s, d) in edges:
        print(f"  node_{s} ({node_ids[ds_idx][s]}) → node_{d} ({node_ids[ds_idx][d]})")

# ── Verify isomorphism (same abstract edge set) ────────────────────────────────
abstract = [frozenset(edge_sets[triple[0]]), frozenset(edge_sets[triple[1]]), frozenset(edge_sets[triple[2]])]
if abstract[0] == abstract[1] == abstract[2]:
    print("\n✓ Edge sets are identical across all 3 datasets — isomorphism confirmed.")
else:
    print("\n⚠ Edge sets differ — check checkpoint validity.")
    for i, ds_idx in enumerate(triple):
        print(f"  {DATASET_NAMES[ds_idx]}: {sorted(edge_sets[ds_idx])}")

# ── Build degree table ─────────────────────────────────────────────────────────
import pandas as pd

print("\n── Degree table (within-circuit) ────────────────────────────────────────")
edge_list = list(edge_sets[triple[0]])   # use any; all identical
in_deg  = {i: 0 for i in range(n_nodes)}
out_deg = {i: 0 for i in range(n_nodes)}
for (s, d) in edge_list:
    out_deg[s] += 1
    in_deg[d]  += 1

rows = []
for i in range(n_nodes):
    row = {"node": f"node_{i}",
           "in_circuit_in":  in_deg[i],
           "in_circuit_out": out_deg[i]}
    for j, ds_idx in enumerate(triple):
        row[DATASET_NAMES[ds_idx]] = node_ids[ds_idx][i]
    rows.append(row)
df = pd.DataFrame(rows)
print(df.to_string(index=False))

# ── Visualization ──────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle(
    "5-Neuron Isomorphic Circuit Shared Across MANC · MAOL · MCNS\n"
    "(Drosophila melanogaster connectomes)",
    fontsize=13, fontweight="bold", y=1.01
)

COLORS = {
    0: "#E07B54",   # orange-red
    1: "#5B9BD5",   # blue
    2: "#70AD47",   # green
    3: "#FFC000",   # amber
    4: "#9B59B6",   # purple
}

# Circular layout
angles = [2 * np.pi * i / n_nodes for i in range(n_nodes)]
pos = {i: (np.cos(a), np.sin(a)) for i, a in enumerate(angles)}

for ax, ds_idx in zip(axes, triple):
    ds_name = DATASET_NAMES[ds_idx]
    nids    = node_ids[ds_idx]
    edges   = edge_sets[ds_idx]

    # draw edges
    for (s, d) in edges:
        xs, ys = pos[s]
        xd, yd = pos[d]
        ax.annotate(
            "", xy=(xd, yd), xytext=(xs, ys),
            arrowprops=dict(
                arrowstyle="-|>",
                color="#555555",
                lw=1.5,
                shrinkA=14, shrinkB=14,
                connectionstyle="arc3,rad=0.1"
            )
        )

    # draw nodes
    for i in range(n_nodes):
        x, y = pos[i]
        circle = plt.Circle((x, y), 0.13, color=COLORS[i], zorder=3, linewidth=1.5,
                             edgecolor="white")
        ax.add_patch(circle)
        ax.text(x, y, f"N{i}", ha="center", va="center",
                fontsize=9, fontweight="bold", color="white", zorder=4)
        # neuron ID label outside
        lx = 1.28 * x
        ly = 1.28 * y
        ax.text(lx, ly, nids[i], ha="center", va="center",
                fontsize=6.5, color="#333333", zorder=4)

    ax.set_xlim(-1.7, 1.7)
    ax.set_ylim(-1.7, 1.7)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(ds_name, fontsize=12, fontweight="bold", pad=8)

# shared legend
legend_patches = [
    mpatches.Patch(color=COLORS[i], label=f"N{i} — {[node_ids[ds][i] for ds in triple]}")
    for i in range(n_nodes)
]
fig.legend(handles=legend_patches, loc="lower center", ncol=5,
           fontsize=7.5, title="Node mapping (MANC / MAOL / MCNS)",
           bbox_to_anchor=(0.5, -0.06))

plt.tight_layout()
plt.savefig(OUT_IMG, dpi=180, bbox_inches="tight")
print(f"\nVisualization saved → {OUT_IMG}")
