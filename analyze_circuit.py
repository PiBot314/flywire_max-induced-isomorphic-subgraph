"""
Circuit Topology Analyzer
=========================
Analyzes the 33-neuron isomorphic circuit from checkpoint data.
Extracts topology metrics, identifies hub neurons, and detects motifs.

Usage:
    python analyze_circuit.py
"""

import json
import pandas as pd
import igraph as ig
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path("c:/cglearn/arnav/flywirequal-find-max-isomorphic-subgraph")
GRAPHS_DIR = DATA_DIR / "processed" / "graph"
CHECKPOINT_FILE = DATA_DIR / "results" / "checkpoints" / "checkpoint_1_2_4.json"
OUTPUT_DIR = DATA_DIR / "analysis"

DATASET_NAMES = {
    1: "BANC",
    2: "FAFB", 
    3: "MANC",
    4: "MAOL",
    5: "MCNS"
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_checkpoint(checkpoint_path: Path) -> Dict:
    """Load checkpoint JSON with circuit mapping."""
    with open(checkpoint_path, 'r') as f:
        data = json.load(f)
    return data

def load_graph(dataset_idx: int) -> ig.Graph:
    """Load igraph from pickle file."""
    dataset_name = DATASET_NAMES[dataset_idx]
    graph_file = GRAPHS_DIR / f"{dataset_name}_graph.pkl"
    
    if not graph_file.exists():
        raise FileNotFoundError(f"Graph not found: {graph_file}")
    
    print(f"  Loading {dataset_name} graph...")
    return ig.Graph.Read_Picklez(str(graph_file))

def extract_induced_subgraph(graph: ig.Graph, neuron_ids: List[str]) -> ig.Graph:
    """Extract induced subgraph for given neuron IDs."""
    # Find vertex indices for the neuron IDs
    vertex_indices = []
    id_to_idx = {}
    
    for i, neuron_id in enumerate(neuron_ids):
        try:
            v = graph.vs.find(name=str(neuron_id))
            vertex_indices.append(v.index)
            id_to_idx[neuron_id] = i
        except ValueError:
            print(f"    Warning: Neuron {neuron_id} not found in graph")
    
    # Create induced subgraph
    subgraph = graph.induced_subgraph(vertex_indices)
    
    # Preserve original neuron IDs as names
    for i, v_idx in enumerate(vertex_indices):
        subgraph.vs[i]['name'] = graph.vs[v_idx]['name']
    
    return subgraph

# ============================================================================
# TOPOLOGY ANALYSIS
# ============================================================================

def calculate_basic_stats(subgraph: ig.Graph) -> Dict:
    """Calculate basic network statistics."""
    n_nodes = subgraph.vcount()
    n_edges = subgraph.ecount()
    
    stats = {
        'n_nodes': n_nodes,
        'n_edges': n_edges,
        'density': n_edges / (n_nodes * (n_nodes - 1)) if n_nodes > 1 else 0,
        'avg_degree': 2 * n_edges / n_nodes if n_nodes > 0 else 0,
        'is_connected': subgraph.is_connected(mode='weak'),
        'n_components': len(subgraph.connected_components(mode='weak'))
    }
    
    return stats

def analyze_degree_distribution(subgraph: ig.Graph) -> Dict:
    """Analyze in-degree and out-degree distributions."""
    in_degrees = subgraph.indegree()
    out_degrees = subgraph.outdegree()
    total_degrees = [i + o for i, o in zip(in_degrees, out_degrees)]
    
    # Get neuron IDs
    neuron_ids = subgraph.vs['name']
    
    # Create degree dataframe
    degree_data = []
    for i, (nid, in_deg, out_deg, tot_deg) in enumerate(zip(neuron_ids, in_degrees, out_degrees, total_degrees)):
        degree_data.append({
            'node_idx': i,
            'neuron_id': nid,
            'in_degree': in_deg,
            'out_degree': out_deg,
            'total_degree': tot_deg
        })
    
    df = pd.DataFrame(degree_data)
    
    stats = {
        'in_degree': {
            'mean': float(df['in_degree'].mean()),
            'std': float(df['in_degree'].std()),
            'min': int(df['in_degree'].min()),
            'max': int(df['in_degree'].max())
        },
        'out_degree': {
            'mean': float(df['out_degree'].mean()),
            'std': float(df['out_degree'].std()),
            'min': int(df['out_degree'].min()),
            'max': int(df['out_degree'].max())
        },
        'total_degree': {
            'mean': float(df['total_degree'].mean()),
            'std': float(df['total_degree'].std()),
            'min': int(df['total_degree'].min()),
            'max': int(df['total_degree'].max())
        }
    }
    
    return stats, df

def identify_hub_neurons(degree_df: pd.DataFrame, top_n: int = 10) -> List[Dict]:
    """Identify hub neurons with highest degrees."""
    top_hubs = degree_df.nlargest(top_n, 'total_degree')
    
    hubs = []
    for _, row in top_hubs.iterrows():
        hubs.append({
            'node_idx': int(row['node_idx']),
            'neuron_id': row['neuron_id'],
            'in_degree': int(row['in_degree']),
            'out_degree': int(row['out_degree']),
            'total_degree': int(row['total_degree'])
        })
    
    return hubs

def detect_3node_motifs(subgraph: ig.Graph) -> Dict:
    """Detect 3-node motifs in the circuit."""
    # Get all 3-node motifs using igraph's motif detection
    # Motif classes for directed graphs (16 possible 3-node motifs)
    motif_counts = subgraph.motifs_randesu(size=3)
    
    # Map motif IDs to descriptions
    motif_names = {
        0: "Empty (no edges)",
        1: "Single edge",
        2: "Mutual dyad",
        3: "Chain (A->B->C)",
        4: "Chain with back edge",
        5: "Fork out (A->B, A->C)",
        6: "Fork in (B->A, C->A)",
        7: "3-cycle",
        8: "Feedforward loop",
        9: "Feedback loop",
        10: "Regulated mutual",
        11: "Regulated fork",
        12: "Fully connected (no reciprocal)",
        13: "Fully connected (one reciprocal)",
        14: "Fully connected (two reciprocal)",
        15: "Fully connected (all reciprocal)"
    }
    
    motifs = {}
    for i, count in enumerate(motif_counts):
        if count and count > 0:
            motifs[motif_names.get(i, f"Motif_{i}")] = int(count)
    
    return motifs

def analyze_reciprocal_connections(subgraph: ig.Graph) -> Dict:
    """Analyze reciprocal (bidirectional) connections."""
    n_nodes = subgraph.vcount()
    reciprocal_pairs = []
    
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            # Check if both i->j and j->i exist
            has_ij = subgraph.are_connected(i, j)
            has_ji = subgraph.are_connected(j, i)
            
            if has_ij and has_ji:
                reciprocal_pairs.append((
                    subgraph.vs[i]['name'],
                    subgraph.vs[j]['name']
                ))
    
    return {
        'n_reciprocal_pairs': len(reciprocal_pairs),
        'reciprocal_pairs': reciprocal_pairs
    }

def calculate_clustering(subgraph: ig.Graph) -> Dict:
    """Calculate clustering coefficients."""
    # For directed graphs, use transitivity
    try:
        global_clustering = subgraph.transitivity_undirected(mode='zero')
        local_clustering = subgraph.transitivity_local_undirected(mode='zero')
        
        return {
            'global_clustering': float(global_clustering),
            'avg_local_clustering': float(sum(local_clustering) / len(local_clustering)) if local_clustering else 0.0
        }
    except Exception as e:
        print(f"    Warning: Could not calculate clustering: {e}")
        return {
            'global_clustering': 0.0,
            'avg_local_clustering': 0.0
        }

def analyze_path_lengths(subgraph: ig.Graph) -> Dict:
    """Analyze shortest path lengths."""
    try:
        # Get all shortest paths
        distances = subgraph.shortest_paths(mode='out')
        
        # Flatten and filter out infinite distances
        finite_distances = []
        for row in distances:
            for d in row:
                if d != float('inf') and d > 0:  # Exclude self-loops (0) and unreachable (inf)
                    finite_distances.append(d)
        
        if finite_distances:
            return {
                'avg_path_length': float(sum(finite_distances) / len(finite_distances)),
                'max_path_length': float(max(finite_distances)),
                'diameter': float(max(finite_distances))
            }
        else:
            return {
                'avg_path_length': 0.0,
                'max_path_length': 0.0,
                'diameter': 0.0
            }
    except Exception as e:
        print(f"    Warning: Could not calculate path lengths: {e}")
        return {
            'avg_path_length': 0.0,
            'max_path_length': 0.0,
            'diameter': 0.0
        }

# ============================================================================
# MAIN ANALYSIS
# ============================================================================

def analyze_circuit():
    """Main analysis function."""
    print("\n" + "="*70)
    print("CIRCUIT TOPOLOGY ANALYSIS")
    print("="*70 + "\n")
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Load checkpoint
    print("Loading checkpoint data...")
    checkpoint = load_checkpoint(CHECKPOINT_FILE)
    
    dataset_triple = checkpoint['dataset_triple']
    mapping = checkpoint['mapping']
    
    dataset_names = [DATASET_NAMES[d] for d in dataset_triple]
    print(f"  Datasets: {' - '.join(dataset_names)}")
    print(f"  Circuit size: {len(mapping)} neurons\n")
    
    # Extract neuron IDs for each dataset
    neuron_ids = {
        dataset_triple[0]: [mapping[str(i)][0] for i in range(len(mapping))],
        dataset_triple[1]: [mapping[str(i)][1] for i in range(len(mapping))],
        dataset_triple[2]: [mapping[str(i)][2] for i in range(len(mapping))]
    }
    
    # Analyze each dataset
    all_results = {}
    
    for dataset_idx in dataset_triple:
        dataset_name = DATASET_NAMES[dataset_idx]
        print(f"\nAnalyzing {dataset_name}...")
        print("-" * 70)
        
        # Load graph and extract subgraph
        graph = load_graph(dataset_idx)
        subgraph = extract_induced_subgraph(graph, neuron_ids[dataset_idx])
        
        print(f"  Extracted subgraph: {subgraph.vcount()} nodes, {subgraph.ecount()} edges")
        
        # Calculate statistics
        print("  Calculating topology metrics...")
        basic_stats = calculate_basic_stats(subgraph)
        degree_stats, degree_df = analyze_degree_distribution(subgraph)
        hub_neurons = identify_hub_neurons(degree_df, top_n=10)
        motifs = detect_3node_motifs(subgraph)
        reciprocal = analyze_reciprocal_connections(subgraph)
        clustering = calculate_clustering(subgraph)
        path_lengths = analyze_path_lengths(subgraph)
        
        # Compile results
        results = {
            'dataset': dataset_name,
            'basic_stats': basic_stats,
            'degree_stats': degree_stats,
            'hub_neurons': hub_neurons,
            'motifs': motifs,
            'reciprocal_connections': reciprocal,
            'clustering': clustering,
            'path_lengths': path_lengths
        }
        
        all_results[dataset_name] = results
        
        # Save degree distribution
        degree_df.to_csv(OUTPUT_DIR / f"{dataset_name}_degrees.csv", index=False)
        print(f"  Saved degree distribution to {dataset_name}_degrees.csv")
    
    # Save comprehensive results
    output_file = OUTPUT_DIR / "circuit_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"Analysis complete! Results saved to: {output_file}")
    print(f"{'='*70}\n")
    
    # Print summary
    print("\nSUMMARY")
    print("="*70)
    for dataset_name, results in all_results.items():
        print(f"\n{dataset_name}:")
        print(f"  Nodes: {results['basic_stats']['n_nodes']}")
        print(f"  Edges: {results['basic_stats']['n_edges']}")
        print(f"  Density: {results['basic_stats']['density']:.3f}")
        print(f"  Avg degree: {results['basic_stats']['avg_degree']:.2f}")
        print(f"  Connected: {results['basic_stats']['is_connected']}")
        print(f"  Reciprocal pairs: {results['reciprocal_connections']['n_reciprocal_pairs']}")
        print(f"  Top hub: {results['hub_neurons'][0]['neuron_id']} (degree={results['hub_neurons'][0]['total_degree']})")
    
    return all_results

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        results = analyze_circuit()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
