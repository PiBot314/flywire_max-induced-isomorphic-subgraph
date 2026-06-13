import os
import json
import pandas as pd
import igraph as ig
from pathlib import Path

# ============================================================================
# CONFIGURATION (Matches your architecture)
# ============================================================================
DATA_DIR = Path("/Users/arnav/agcode/flywire/qual_challenge")
GRAPHS_DIR = DATA_DIR / "processed" / "graph"
DEGREES_DIR = DATA_DIR / "processed" / "degrees"

DATASET_PAIRS = {
    1: "BANC",
    2: "FAFB",
    3: "MANC",
    4: "MAOL",
    5: "MCNS"
}

def remove_all_self_loops():
    """
    Natively strips out self-loops (autapses) from serialized igraph files 
    and regenerates completely clean degree sequence CSV metrics.
    """
    print("======================================================================")
    # Stripping self-loops natively using igraph's C-backend.
    print("STARTING GRAPH PURGE: Removing all self-loops (autapses)")
    print("======================================================================\n")

    for dataset_idx, dataset_name in DATASET_PAIRS.items():
        graph_file = GRAPHS_DIR / f"{dataset_name}_graph.pkl"
        degree_file = DEGREES_DIR / f"neuron_degrees_{dataset_idx}.csv"

        if not graph_file.exists():
            print(f"⚠ Skipping {dataset_name}: Graph file not found at {graph_file}")
            continue

        print(f"Processing {dataset_name} connectome...")
        
        # 1. Load the igraph instance from disk
        try:
            # Use ig.Graph.Read_Picklez for compressed serialization formats 
            g = ig.Graph.Read_Picklez(str(graph_file))
            initial_edges = g.ecount()
        except Exception as e:
            print(f"  ✗ Error reading {graph_file}: {e}")
            continue

        # 2. Purge self-loops natively at C-speed
        # loops=True deletes all edges where source == target (autapses)
        # multiple=False keeps your duplicate parallel edges untouched
        g = g.simplify(multiple=False, loops=True) 
        removed_loops = initial_edges - g.ecount()
        print(f"  ✓ Purged {removed_loops:,} self-loops from graph structure.")

        # 3. Reserialize the cleaned graph back to disk
        try:
            g.write_picklez(str(graph_file))
            print(f"  ✓ Overwrote clean serialized graph to: {graph_file}")
        except Exception as e:
            print(f"  ✗ Failed to save modified graph: {e}")
            continue

        # 4. Extract node names and recalculate directed degree properties
        # This fixes the invariant inflation bug on your candidate mappings
        nodes = g.vs['name']
        in_degrees = g.indegree() 
        out_degrees = g.outdegree() 

        # 5. Overwrite the degree metric files with pristine, non-inflated columns
        degree_df = pd.DataFrame({
            'neuron_id': nodes,
            'in_degree': in_degrees,
            'out_degree': out_degrees
        })
        
        try:
            degree_df.to_csv(degree_file, index=False)
            print(f"  ✓ Regenerated non-inflated degree mappings at: {degree_file}\n")
        except Exception as e:
            print(f"  ✗ Failed to save clean degree sequence: {e}\n")

    print("======================================================================")
    print("✓ PURGE COMPLETED SUCCESSFULLY: Connectomes are ready for Isomorphic Search.")
    print("======================================================================")

if __name__ == "__main__":
    # Ensure directories exist before running the migration function
    GRAPHS_DIR.mkdir(exist_ok=True, parents=True)
    DEGREES_DIR.mkdir(exist_ok=True, parents=True)
    
    remove_all_self_loops()