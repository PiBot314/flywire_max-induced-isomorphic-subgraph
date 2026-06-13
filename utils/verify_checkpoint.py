"""
Checkpoint Verifier
===================
Independently verifies if a JSON checkpoint file contains a valid, 
mutually isomorphic, weakly connected induced subgraph across 3 datasets.
"""

import json
import igraph as ig
from pathlib import Path
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path("/Users/arnav/agcode/flywire/qual_challenge")
GRAPHS_DIR = DATA_DIR / "processed" / "graph"

DATASET_PAIRS = {
    1: "BANC",
    2: "FAFB",
    3: "MANC",
    4: "MAOL",
    5: "MCNS"
}

def _has_directed_edge(graph: ig.Graph, src_name: str, tgt_name: str) -> bool:
    """Check if directed edge exists using string names."""
    try:
        res = graph.get_eid(str(src_name), str(tgt_name), directed=True, error=False)
        return res >= 0
    except (ValueError, ig.InternalError):
        return False

def verify(checkpoint_path: str):
    print(f"\n{'='*70}")
    print(f"VERIFYING CHECKPOINT: {checkpoint_path}")
    print(f"{'='*70}\n")

    path = Path(checkpoint_path)
    if not path.exists():
        print(f"✗ Error: Could not find {path}")
        sys.exit(1)

    # 1. Load Checkpoint JSON
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"✗ Error parsing JSON: {e}")
        sys.exit(1)

    if 'dataset_triple' not in data or 'mapping' not in data:
        print("✗ Error: JSON is missing required 'dataset_triple' or 'mapping' fields.")
        sys.exit(1)

    # Extract dataset names based on the indices saved in the checkpoint
    dataset_indices = data['dataset_triple']
    dataset_cols = [DATASET_PAIRS[idx] for idx in dataset_indices]
    
    print(f"✓ Found datasets: {', '.join(dataset_cols)}")
    
    # Extract mappings as a list of tuples: [(d1_node, d2_node, d3_node), ...]
    mapping_dict = data['mapping']
    mapping = []
    for key, nodes in mapping_dict.items():
        mapping.append((str(nodes[0]), str(nodes[1]), str(nodes[2])))
        
    print(f"✓ Found {len(mapping)} mapped neurons.")
    
    if len(mapping) == 0:
        print("✗ Checkpoint mapping is empty.")
        sys.exit(1)

    # 2. Load Graphs
    graphs = []
    for ds in dataset_cols:
        graph_file = GRAPHS_DIR / f"{ds}_graph.pkl"
        if not graph_file.exists():
            print(f"✗ Error: Missing graph file {graph_file}")
            sys.exit(1)
            
        print(f"  Loading {ds}...")
        try:
            graphs.append(ig.Graph.Read_Picklez(str(graph_file)))
        except Exception as e:
            print(f"✗ Error loading {ds}: {e}")
            sys.exit(1)
            
    G1, G2, G3 = graphs

    # 3. Verify Induced Isomorphism
    print("\nVerifying Induced Subgraph Isomorphism...")
    
    N = len(mapping)
    edges_found = 0
    mismatch_found = False
    
    # We will build a test graph of the shared circuit to check connectivity later
    circuit_edges = []

    for i in range(N):
        for j in range(N):
            if i == j:
                continue
                
            u1, u2, u3 = mapping[i]
            v1, v2, v3 = mapping[j]
            
            e1 = _has_directed_edge(G1, u1, v1)
            e2 = _has_directed_edge(G2, u2, v2)
            e3 = _has_directed_edge(G3, u3, v3)
            
            if not (e1 == e2 == e3):
                print(f"  ✗ Mismatch found!")
                print(f"    Edge Map {i} -> Map {j}:")
                print(f"      {dataset_cols[0]} ({u1} -> {v1}): {e1}")
                print(f"      {dataset_cols[1]} ({u2} -> {v2}): {e2}")
                print(f"      {dataset_cols[2]} ({u3} -> {v3}): {e3}")
                mismatch_found = True
                break
                
            if e1: # All three have the edge
                edges_found += 1
                circuit_edges.append((i, j))
                
        if mismatch_found:
            break

    if mismatch_found:
        print("\n✗ FAILED: The induced subgraphs in the checkpoint are NOT mutually isomorphic.")
        sys.exit(1)
    else:
        print(f"✓ Passed: All {N*(N-1)} possible directed connections match perfectly.")
        print(f"✓ Circuit contains {edges_found} directed edges.")

    # 4. Verify Connectivity
    print("\nVerifying Weak Connectivity...")
    
    # Create an igraph from the confirmed shared edges
    circuit = ig.Graph(n=N, edges=circuit_edges, directed=True)
    
    if circuit.is_connected(mode="weak"):
        print("✓ Passed: The isomorphic circuit is weakly connected.")
    else:
        print("✗ FAILED: The circuit is disjointed (contains isolated islands).")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"🏆 VERIFICATION SUCCESSFUL")
    print(f"The checkpoint is a valid weakly connected isomorphic circuit of size {N}.")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    # Look for a specific checkpoint file
    target_json = DATA_DIR / "results" / "checkpoints" / "checkpoint_1_2_4.json"
    
    if len(sys.argv) > 1:
        target_json = Path(sys.argv[1])
        
    verify(str(target_json))