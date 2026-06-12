"""
Direct search for isomorphic circuits using random sampling.
Tests specific sizes and reports findings.
"""

import pickle
import networkx as nx
from pathlib import Path
import random
import sys

PROCESSED_DIR = Path(__file__).parent / "processed"


def load_data():
    """Load graphs and presence data."""
    with open(PROCESSED_DIR / "graphs.pkl", "rb") as f:
        graphs = pickle.load(f)
    with open(PROCESSED_DIR / "presence_dict.pkl", "rb") as f:
        presence_dict = pickle.load(f)
    return graphs, presence_dict


def get_shared_neurons(presence_dict):
    """Get neurons shared in MANC-MAOL-MCNS."""
    d1, d2, d3 = ("MANC", "MAOL", "MCNS")
    return {n for n, datasets in presence_dict.items() 
            if d1 in datasets and d2 in datasets and d3 in datasets}


def check_isomorphic_fast(graphs, neurons, dataset_triple):
    """Fast isomorphism check with early exit."""
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    # Get induced subgraphs
    sub1 = g1.subgraph(neurons)
    sub2 = g2.subgraph(neurons)
    sub3 = g3.subgraph(neurons)
    
    e1, e2, e3 = sub1.number_of_edges(), sub2.number_of_edges(), sub3.number_of_edges()
    
    # Early exit on edge count mismatch
    if not (e1 == e2 == e3):
        return False, (e1, e2, e3)
    
    # Check isomorphism
    try:
        if not nx.is_isomorphic(sub1, sub2):
            return False, (e1, e2, e3)
        if not nx.is_isomorphic(sub2, sub3):
            return False, (e1, e2, e3)
        return True, (e1, e2, e3)
    except:
        return False, (e1, e2, e3)


def search_size(graphs, shared_neurons, size, num_trials=1000):
    """Search for isomorphic circuits of specific size."""
    shared_list = list(shared_neurons)
    dataset_triple = ("MANC", "MAOL", "MCNS")
    
    print(f"\nTesting size {size} ({num_trials} trials)...")
    
    found = []
    edge_patterns = {}
    
    for trial in range(num_trials):
        if trial % 100 == 0:
            print(f"  Trial {trial}/{num_trials}...", flush=True)
        
        subset = set(random.sample(shared_list, size))
        iso, edges = check_isomorphic_fast(graphs, subset, dataset_triple)
        
        # Track edge patterns
        if edges not in edge_patterns:
            edge_patterns[edges] = 0
        edge_patterns[edges] += 1
        
        if iso:
            found.append(subset)
            print(f"    ✓ Found isomorphic circuit!", flush=True)
    
    # Show top edge patterns
    top_patterns = sorted(edge_patterns.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"  Top edge patterns: {top_patterns}")
    
    return found


def main():
    print("\n" + "=" * 70)
    print("DIRECT ISOMORPHIC CIRCUIT SEARCH")
    print("=" * 70)
    
    graphs, presence_dict = load_data()
    shared_neurons = get_shared_neurons(presence_dict)
    
    print(f"\nShared neurons: {len(shared_neurons):,}\n")
    
    # Test sizes 4, 5, 6, 8, 10, 15, 20
    sizes_to_test = [4, 5, 6, 8, 10, 15, 20]
    
    all_found = {}
    
    for size in sizes_to_test:
        if size > len(shared_neurons):
            break
        
        found = search_size(graphs, shared_neurons, size, num_trials=500)
        all_found[size] = found
        
        if found:
            print(f"\n  ✓✓✓ SUCCESS: Found {len(found)} isomorphic circuits of size {size}")
            break
        else:
            print(f"  ✗ No isomorphic circuits of size {size}")
    
    # Report
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for size, circuits in all_found.items():
        if circuits:
            print(f"Size {size}: ✓ {len(circuits)} circuits found")
            
            # Verify and save best
            dataset_triple = ("MANC", "MAOL", "MCNS")
            best = circuits[0]
            
            iso, edges = check_isomorphic_fast(graphs, best, dataset_triple)
            print(f"  Edges: {edges}")
            
            # Export
            import pandas as pd
            output_dir = PROCESSED_DIR / "isomorphism_analysis"
            output_dir.mkdir(exist_ok=True)
            
            neurons_list = sorted(list(best))
            df = pd.DataFrame({
                "MANC": neurons_list,
                "MAOL": neurons_list,
                "MCNS": neurons_list
            })
            
            csv_path = output_dir / f"isomorphic_circuit_{size}.csv"
            df.to_csv(csv_path, index=False)
            print(f"  Saved to {csv_path}")
            break
        else:
            print(f"Size {size}: ✗ No circuits found")


if __name__ == "__main__":
    main()
