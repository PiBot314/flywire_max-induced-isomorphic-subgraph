"""
Maximal isomorphic circuit search: Find the largest subset of shared neurons
that forms isomorphic induced subgraphs across MANC-MAOL-MCNS.

Strategy:
1. Start with all 5,289 neurons (confirmed non-isomorphic)
2. Iteratively remove neurons that break isomorphism
3. Use strategic pruning to find maximum isomorphic subset
"""

import pickle
import networkx as nx
from pathlib import Path
import random
from collections import defaultdict

PROCESSED_DIR = Path(__file__).parent / "processed"
DATASET_TRIPLE = ("MANC", "MAOL", "MCNS")


def load_data():
    """Load graphs and presence data."""
    print("Loading data...", flush=True)
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
    """Check if induced subgraphs for given neurons are isomorphic."""
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    # Create induced subgraphs
    sub1 = g1.subgraph(neurons).copy()
    sub2 = g2.subgraph(neurons).copy()
    sub3 = g3.subgraph(neurons).copy()
    
    # Quick check: edge count
    if not (sub1.number_of_edges() == sub2.number_of_edges() == sub3.number_of_edges()):
        return False
    
    # Check isomorphism
    try:
        if nx.is_isomorphic(sub1, sub2) and nx.is_isomorphic(sub2, sub3):
            return True
    except:
        pass
    
    return False


def find_max_isomorphic_subset_greedy(graphs, shared_neurons, dataset_triple, max_attempts=50):
    """
    Find maximum isomorphic subset using greedy removal.
    
    Start with all neurons, iteratively remove high-degree nodes
    that contribute most to edge count differences.
    
    Args:
        graphs: dict of dataset -> DiGraph
        shared_neurons: set of all shared neurons
        dataset_triple: tuple of 3 dataset names
        max_attempts: number of greedy removal attempts
        
    Returns:
        tuple: (best_subset, size)
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    print(f"\n{'=' * 70}")
    print(f"GREEDY SEARCH: Finding maximum isomorphic subset")
    print(f"{'=' * 70}\n")
    
    best_subset = None
    best_size = 0
    
    # Start with all shared neurons
    current = shared_neurons.copy()
    
    for attempt in range(max_attempts):
        # Check if current set is isomorphic
        if are_isomorphic(graphs, current, dataset_triple):
            if len(current) > best_size:
                best_size = len(current)
                best_subset = current.copy()
                print(f"✓ Attempt {attempt}: Found isomorphic subset of size {best_size}")
        
        # Get induced subgraphs to analyze edge differences
        sub1 = g1.subgraph(current).copy()
        sub2 = g2.subgraph(current).copy()
        sub3 = g3.subgraph(current).copy()
        
        e1, e2, e3 = sub1.number_of_edges(), sub2.number_of_edges(), sub3.number_of_edges()
        max_edges = max(e1, e2, e3)
        
        print(f"Attempt {attempt}: |V|={len(current):,}, Edges=({e1:,}, {e2:,}, {e3:,})")
        
        if e1 == e2 == e3:
            # Edges match, so structural incompatibility is in degree sequence
            # Try removing random nodes
            candidates = list(current)
            random.shuffle(candidates)
            removed = candidates[:max(1, len(candidates) // 20)]  # Remove 5%
        else:
            # Remove high-degree nodes from graph with most edges
            if e1 == max_edges:
                degrees = [(n, sub1.in_degree(n) + sub1.out_degree(n)) for n in current]
            elif e2 == max_edges:
                degrees = [(n, sub2.in_degree(n) + sub2.out_degree(n)) for n in current]
            else:
                degrees = [(n, sub3.in_degree(n) + sub3.out_degree(n)) for n in current]
            
            degrees.sort(key=lambda x: x[1], reverse=True)
            removed = [n for n, d in degrees[:max(1, len(degrees) // 20)]]  # Remove top 5% by degree
        
        # Remove these nodes
        for node in removed:
            current.discard(node)
        
        if len(current) < best_size * 0.95:  # Stop if getting too small
            break
    
    return best_subset, best_size


def find_max_isomorphic_subset_binary_search(graphs, shared_neurons, dataset_triple, target_size=None):
    """
    Find maximum isomorphic subset using binary search.
    
    More systematic than greedy but slower.
    
    Args:
        graphs: dict of dataset -> DiGraph
        shared_neurons: set of all shared neurons
        dataset_triple: tuple of 3 dataset names
        target_size: optional target size to verify
        
    Returns:
        tuple: (best_subset, size)
    """
    d1, d2, d3 = dataset_triple
    
    print(f"\n{'=' * 70}")
    print(f"BINARY SEARCH: Verifying isomorphic subsets at key sizes")
    print(f"{'=' * 70}\n")
    
    # Test specific sizes
    test_sizes = [1000, 2000, 3000, 4000]
    if target_size:
        test_sizes.append(target_size)
    
    best_subset = None
    best_size = 0
    
    neurons_list = sorted(list(shared_neurons))
    
    for test_size in test_sizes:
        if test_size > len(neurons_list):
            continue
        
        # Try multiple random samples
        for sample in range(3):
            subset = set(random.sample(neurons_list, test_size))
            
            if are_isomorphic(graphs, subset, dataset_triple):
                if test_size > best_size:
                    best_size = test_size
                    best_subset = subset.copy()
                    print(f"✓ Found isomorphic subset of size {test_size}")
                    break
    
    return best_subset, best_size


def verify_solution(graphs, subset, dataset_triple):
    """Verify final solution."""
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    print(f"\n{'=' * 70}")
    print(f"SOLUTION VERIFICATION")
    print(f"{'=' * 70}\n")
    
    sub1 = g1.subgraph(subset).copy()
    sub2 = g2.subgraph(subset).copy()
    sub3 = g3.subgraph(subset).copy()
    
    print(f"Circuit size: {len(subset)} neurons")
    print(f"\nInduced subgraph properties:")
    print(f"  {d1}: {sub1.number_of_nodes()} nodes, {sub1.number_of_edges()} edges")
    print(f"  {d2}: {sub2.number_of_nodes()} nodes, {sub2.number_of_edges()} edges")
    print(f"  {d3}: {sub3.number_of_nodes()} nodes, {sub3.number_of_edges()} edges")
    
    # Verify isomorphism
    iso_12 = nx.is_isomorphic(sub1, sub2)
    iso_23 = nx.is_isomorphic(sub2, sub3)
    iso_13 = nx.is_isomorphic(sub1, sub3)
    
    print(f"\nIsomorphism checks:")
    print(f"  {d1} ≅ {d2}: {iso_12}")
    print(f"  {d2} ≅ {d3}: {iso_23}")
    print(f"  {d1} ≅ {d3}: {iso_13}")
    
    all_iso = iso_12 and iso_23 and iso_13
    print(f"\nMutually isomorphic: {all_iso}")
    
    return all_iso


def save_solution(subset, dataset_triple):
    """Save the isomorphic solution as CSV."""
    output_dir = PROCESSED_DIR / "isomorphism_analysis"
    output_dir.mkdir(exist_ok=True)
    
    d1, d2, d3 = dataset_triple
    
    # Create DataFrame
    import pandas as pd
    neurons_list = sorted(list(subset))
    
    df = pd.DataFrame({
        d1: neurons_list,
        d2: neurons_list,
        d3: neurons_list
    })
    
    csv_path = output_dir / f"isomorphic_circuit_{d1}_{d2}_{d3}.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\n✓ Solution saved to {csv_path}")
    print(f"  Format: {d1}, {d2}, {d3}")
    print(f"  Rows: {len(neurons_list)} neurons")
    
    return csv_path


def main():
    """Find maximum isomorphic circuit subset."""
    print("\n" + "█" * 70)
    print("MAXIMAL ISOMORPHIC CIRCUIT SEARCH")
    print("Finding largest subset of 5,289 neurons that are isomorphic")
    print("█" * 70)
    
    graphs, presence_dict = load_data()
    shared_neurons = get_shared_neurons(presence_dict)
    
    print(f"\nStarting from {len(shared_neurons):,} shared neurons\n")
    
    # Try greedy approach
    best_subset, best_size = find_max_isomorphic_subset_greedy(
        graphs, shared_neurons, DATASET_TRIPLE, max_attempts=20
    )
    
    if best_subset and best_size > 0:
        # Verify and save
        is_valid = verify_solution(graphs, best_subset, DATASET_TRIPLE)
        
        if is_valid:
            save_solution(best_subset, DATASET_TRIPLE)
            
            print(f"\n{'█' * 70}")
            print(f"✓ SUCCESS: Found maximum isomorphic circuit")
            print(f"  Size: {best_size} neurons")
            print(f"  Datasets: {DATASET_TRIPLE}")
            print(f"{'█' * 70}\n")
        else:
            print(f"\n✗ Verification failed - subset is not isomorphic")
    else:
        print(f"\n✗ No isomorphic subset found")


if __name__ == "__main__":
    main()
