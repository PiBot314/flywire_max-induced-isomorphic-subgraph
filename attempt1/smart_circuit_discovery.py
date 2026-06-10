"""
Smart isomorphic circuit discovery: Find and verify circuits of increasing size.

This approach:
1. Extracts circuits from local network neighborhoods
2. Verifies isomorphism for each candidate
3. Grows circuits by adding compatible nodes
4. Tracks the maximum size found
"""

import pickle
import networkx as nx
from pathlib import Path
from collections import defaultdict
import random

PROCESSED_DIR = Path(__file__).parent / "processed"
DATASET_TRIPLE = ("MANC", "MAOL", "MCNS")


def load_data():
    """Load graphs and presence data."""
    with open(PROCESSED_DIR / "graphs.pkl", "rb") as f:
        graphs = pickle.load(f)
    
    with open(PROCESSED_DIR / "presence_dict.pkl", "rb") as f:
        presence_dict = pickle.load(f)
    
    return graphs, presence_dict


def get_shared_neurons(presence_dict):
    """Get all neurons shared across MANC-MAOL-MCNS."""
    d1, d2, d3 = DATASET_TRIPLE
    return {n for n, datasets in presence_dict.items() 
            if d1 in datasets and d2 in datasets and d3 in datasets}


def are_isomorphic(graphs, neurons, dataset_triple):
    """Quick check: are induced subgraphs isomorphic?"""
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    sub1 = g1.subgraph(neurons).copy()
    sub2 = g2.subgraph(neurons).copy()
    sub3 = g3.subgraph(neurons).copy()
    
    # Quick checks
    if not (sub1.number_of_edges() == sub2.number_of_edges() == sub3.number_of_edges()):
        return False
    
    if not (sub1.number_of_nodes() == sub2.number_of_nodes() == sub3.number_of_nodes()):
        return False
    
    # Isomorphism check
    try:
        return nx.is_isomorphic(sub1, sub2) and nx.is_isomorphic(sub2, sub3)
    except:
        return False


def find_circuits_by_neighborhood(graphs, shared_neurons, dataset_triple, seed_size=4, num_seeds=500):
    """
    Find isomorphic circuits by examining neighborhoods around seed nodes.
    
    This strategy works well when local neighborhoods are more likely to be isomorphic.
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    print(f"\nFinding circuits by neighborhood expansion...")
    print(f"  Seed size: {seed_size} nodes")
    print(f"  Number of seeds: {num_seeds}\n")
    
    circuits = []
    checked = set()
    
    # Select seed nodes: those with many neighbors
    neighbors_count = {}
    for n in shared_neurons:
        pred1 = set(g1.predecessors(n)) & shared_neurons
        succ1 = set(g1.successors(n)) & shared_neurons
        neighbors_count[n] = len(pred1) + len(succ1)
    
    top_seeds = sorted(neighbors_count.items(), key=lambda x: x[1], reverse=True)[:num_seeds]
    
    checked_count = 0
    
    for seed_idx, (seed_node, _) in enumerate(top_seeds):
        if seed_idx % 100 == 0:
            print(f"  Processing seed {seed_idx}/{len(top_seeds)}...", flush=True)
        
        # Get neighborhood in all three graphs
        pred1 = set(g1.predecessors(seed_node)) & shared_neurons
        succ1 = set(g1.successors(seed_node)) & shared_neurons
        neighbors1 = {seed_node} | pred1 | succ1
        
        pred2 = set(g2.predecessors(seed_node)) & shared_neurons
        succ2 = set(g2.successors(seed_node)) & shared_neurons
        neighbors2 = {seed_node} | pred2 | succ2
        
        pred3 = set(g3.predecessors(seed_node)) & shared_neurons
        succ3 = set(g3.successors(seed_node)) & shared_neurons
        neighbors3 = {seed_node} | pred3 | succ3
        
        # Find common neighbors
        common = neighbors1 & neighbors2 & neighbors3
        
        if len(common) < seed_size:
            continue
        
        # Try subsets
        candidates = list(common)
        for _ in range(min(100, len(candidates) // 2)):  # Random sampling
            subset = set(random.sample(candidates, min(seed_size, len(candidates))))
            
            state = frozenset(subset)
            if state in checked:
                continue
            checked.add(state)
            checked_count += 1
            
            # Check isomorphism
            if are_isomorphic(graphs, subset, dataset_triple):
                circuits.append(subset)
                if len(circuits) % 100 == 0:
                    print(f"    ✓ Found {len(circuits)} isomorphic circuits", flush=True)
    
    print(f"  Checked {checked_count} candidates, found {len(circuits)} isomorphic circuits")
    return circuits


def grow_circuit(graphs, circuit, shared_neurons, dataset_triple, max_size=200):
    """
    Greedily grow an isomorphic circuit by adding compatible nodes.
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    current = circuit.copy()
    
    for iteration in range(100):  # Max iterations
        improved = False
        candidates = list(shared_neurons - current)
        
        # Random sample for efficiency
        candidates_to_try = random.sample(candidates, min(100, len(candidates)))
        
        for candidate in candidates_to_try:
            test_set = current | {candidate}
            
            if are_isomorphic(graphs, test_set, dataset_triple):
                current.add(candidate)
                improved = True
                break
        
        if not improved or len(current) >= max_size:
            break
    
    return current


def main():
    """Smart circuit discovery."""
    print("\n" + "█" * 70)
    print("SMART ISOMORPHIC CIRCUIT DISCOVERY")
    print("█" * 70)
    
    graphs, presence_dict = load_data()
    shared_neurons = get_shared_neurons(presence_dict)
    
    print(f"\nSearching {len(shared_neurons):,} shared neurons for isomorphic circuits\n")
    
    # Find small circuits by neighborhood
    circuits = find_circuits_by_neighborhood(
        graphs, shared_neurons, DATASET_TRIPLE, 
        seed_size=4, num_seeds=200
    )
    
    if not circuits:
        print("\n✗ No isomorphic circuits found in neighborhoods")
        return
    
    print(f"\n{'=' * 70}")
    print(f"GROWING CIRCUITS")
    print(f"{'=' * 70}\n")
    
    # Grow circuits
    best_circuit = None
    best_size = 0
    
    for idx, circuit in enumerate(circuits[:100]):  # Try growing top 100
        if idx % 10 == 0:
            print(f"Growing circuit {idx}/{min(100, len(circuits))}...", flush=True)
        
        grown = grow_circuit(graphs, circuit, shared_neurons, DATASET_TRIPLE, max_size=500)
        
        if len(grown) > best_size:
            best_size = len(grown)
            best_circuit = grown
            print(f"  ✓ Grew to size {best_size}", flush=True)
    
    # Verify and save best
    if best_circuit and best_size > 0:
        print(f"\n{'=' * 70}")
        print(f"SOLUTION")
        print(f"{'=' * 70}\n")
        
        d1, d2, d3 = DATASET_TRIPLE
        g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
        
        sub1 = g1.subgraph(best_circuit).copy()
        sub2 = g2.subgraph(best_circuit).copy()
        sub3 = g3.subgraph(best_circuit).copy()
        
        print(f"Circuit size: {best_size} neurons\n")
        print(f"Properties:")
        print(f"  {d1}: {sub1.number_of_nodes()} nodes, {sub1.number_of_edges()} edges")
        print(f"  {d2}: {sub2.number_of_nodes()} nodes, {sub2.number_of_edges()} edges")
        print(f"  {d3}: {sub3.number_of_nodes()} nodes, {sub3.number_of_edges()} edges")
        
        # Final verification
        iso_12 = nx.is_isomorphic(sub1, sub2)
        iso_23 = nx.is_isomorphic(sub2, sub3)
        iso_13 = nx.is_isomorphic(sub1, sub3)
        
        print(f"\nIsomorphism verification:")
        print(f"  {d1} ≅ {d2}: {iso_12}")
        print(f"  {d2} ≅ {d3}: {iso_23}")
        print(f"  {d1} ≅ {d3}: {iso_13}")
        
        if iso_12 and iso_23 and iso_13:
            print(f"\n✓ VALID ISOMORPHIC CIRCUIT\n")
            
            # Export
            import pandas as pd
            output_dir = PROCESSED_DIR / "isomorphism_analysis"
            output_dir.mkdir(exist_ok=True)
            
            neurons_list = sorted(list(best_circuit))
            df = pd.DataFrame({
                d1: neurons_list,
                d2: neurons_list,
                d3: neurons_list
            })
            
            csv_path = output_dir / f"isomorphic_circuit_{best_size}.csv"
            df.to_csv(csv_path, index=False)
            
            print(f"✓ Saved to {csv_path}")
        else:
            print(f"\n✗ Verification failed")
    else:
        print(f"\n✗ No circuits found")


if __name__ == "__main__":
    main()
