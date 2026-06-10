"""
Optimized circuit search for MANC-MAOL-MCNS.

Focuses on the only dataset triple with neuron overlap (5,289 neurons).
Uses smart graph motif discovery and structural matching.
"""

import pickle
import networkx as nx
from pathlib import Path
import numpy as np
from collections import defaultdict

PROCESSED_DIR = Path(__file__).parent / "processed"


def load_data():
    """Load graphs and presence data."""
    with open(PROCESSED_DIR / "graphs.pkl", "rb") as f:
        graphs = pickle.load(f)
    
    with open(PROCESSED_DIR / "presence_dict.pkl", "rb") as f:
        presence_dict = pickle.load(f)
    
    return graphs, presence_dict


def get_shared_neurons():
    """Get the 5289 neurons in all three datasets."""
    with open(PROCESSED_DIR / "presence_dict.pkl", "rb") as f:
        presence_dict = pickle.load(f)
    
    neurons = [n for n, d in presence_dict.items()
               if 'MANC' in d and 'MAOL' in d and 'MCNS' in d]
    return set(neurons)


def find_motifs_by_local_structure(graphs, shared_neurons, dataset_triple, motif_size=4):
    """
    Find candidate motifs using local structure matching.
    
    Groups neurons by their local network patterns (neighbors) and
    looks for patterns that might be isomorphic across datasets.
    
    Args:
        graphs: dict of dataset -> DiGraph
        shared_neurons: set of neurons in all 3 datasets
        dataset_triple: tuple of 3 dataset names
        motif_size: size of motifs to find
        
    Returns:
        list: list of (subgraph_sets, size) tuples
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    shared_neurons_set = shared_neurons if isinstance(shared_neurons, set) else set(shared_neurons)
    shared_neurons_list = list(shared_neurons_set)
    print(f"  Searching {len(shared_neurons_list)} shared neurons for motifs...")
    
    found_circuits = []
    checked_count = 0
    
    # Strategy: Start from high-degree neurons as they're more likely to be in larger circuits
    degrees = [(n, g1.degree(n) + g2.degree(n) + g3.degree(n)) 
               for n in shared_neurons_list]
    degrees.sort(key=lambda x: x[1], reverse=True)
    
    # Try neighborhoods around high-degree nodes
    checked_neighborhoods = set()
    
    for seed_neuron, _ in degrees[:100]:  # Top 100 by degree
        # Get local neighborhood in each graph
        pred1 = set(g1.predecessors(seed_neuron))
        succ1 = set(g1.successors(seed_neuron))
        neighborhood1 = (pred1 | succ1) & shared_neurons_set
        
        pred2 = set(g2.predecessors(seed_neuron))
        succ2 = set(g2.successors(seed_neuron))
        neighborhood2 = (pred2 | succ2) & shared_neurons_set
        
        pred3 = set(g3.predecessors(seed_neuron))
        succ3 = set(g3.successors(seed_neuron))
        neighborhood3 = (pred3 | succ3) & shared_neurons_set
        
        # Find common neighbors across all three
        common_neighbors = neighborhood1 & neighborhood2 & neighborhood3
        
        if len(common_neighbors) >= motif_size - 1:
            candidates = {seed_neuron} | common_neighbors
            
            # Extract all k-subsets from candidates
            from itertools import combinations
            for subset in combinations(sorted(candidates), motif_size):
                subset_set = set(subset)
                
                # Skip if already checked
                state_hash = frozenset(subset_set)
                if state_hash in checked_neighborhoods:
                    continue
                checked_neighborhoods.add(state_hash)
                
                checked_count += 1
                
                # Get induced subgraphs
                sub1 = g1.subgraph(subset_set).copy()
                sub2 = g2.subgraph(subset_set).copy()
                sub3 = g3.subgraph(subset_set).copy()
                
                # Quick filter: same structure
                if sub1.number_of_edges() != sub2.number_of_edges() or \
                   sub2.number_of_edges() != sub3.number_of_edges():
                    continue
                
                # Check isomorphism
                try:
                    if nx.is_isomorphic(sub1, sub2) and nx.is_isomorphic(sub2, sub3):
                        found_circuits.append(({
                            d1: subset_set,
                            d2: subset_set,
                            d3: subset_set
                        }, motif_size))
                        print(f"    ✓ Found isomorphic motif of size {motif_size}!", flush=True)
                except:
                    pass
                
                if checked_count % 10000 == 0:
                    print(f"    Checked {checked_count} candidates...", flush=True)
    
    print(f"  Total candidates checked: {checked_count}")
    return found_circuits


def grow_circuits(graphs, shared_neurons, dataset_triple, base_circuits, max_growth=5):
    """
    Grow found circuits by adding compatible neurons.
    
    Args:
        graphs: dict of dataset -> DiGraph
        shared_neurons: set of shared neurons
        dataset_triple: tuple of 3 dataset names
        base_circuits: list of (node_sets, size) tuples
        max_growth: maximum growth iterations
        
    Returns:
        list: list of (node_sets, size) tuples for grown circuits
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    shared_neurons_set = shared_neurons if isinstance(shared_neurons, set) else set(shared_neurons)
    
    grown = []
    
    for node_sets, size in base_circuits:
        current_sets = {d1: node_sets[d1].copy(), 
                       d2: node_sets[d2].copy(),
                       d3: node_sets[d3].copy()}
        current_size = size
        
        # Try to grow
        for iteration in range(max_growth):
            best_new_node = None
            
            # Find candidates that could be added
            candidates = shared_neurons_set - current_sets[d1]
            
            for candidate in list(candidates)[:500]:
                test_sets = {d: current_sets[d].copy() for d in [d1, d2, d3]}
                test_sets[d1].add(candidate)
                test_sets[d2].add(candidate)
                test_sets[d3].add(candidate)
                
                # Check if still isomorphic
                sub1 = g1.subgraph(test_sets[d1]).copy()
                sub2 = g2.subgraph(test_sets[d2]).copy()
                sub3 = g3.subgraph(test_sets[d3]).copy()
                
                try:
                    if sub1.number_of_edges() == sub2.number_of_edges() == sub3.number_of_edges() and \
                       nx.is_isomorphic(sub1, sub2) and nx.is_isomorphic(sub2, sub3):
                        best_new_node = candidate
                        break
                except:
                    pass
            
            if best_new_node:
                current_sets[d1].add(best_new_node)
                current_sets[d2].add(best_new_node)
                current_sets[d3].add(best_new_node)
                current_size += 1
                print(f"    → Grew circuit to size {current_size}", flush=True)
            else:
                break
        
        grown.append((current_sets, current_size))
    
    return grown


def main():
    """Optimized circuit search for MANC-MAOL-MCNS."""
    print("=" * 70)
    print("Optimized Circuit Search: MANC-MAOL-MCNS")
    print("=" * 70 + "\n")
    
    graphs, presence_dict = load_data()
    shared_neurons = get_shared_neurons()  # Returns a set
    
    dataset_triple = ("MANC", "MAOL", "MCNS")
    d1, d2, d3 = dataset_triple
    
    print(f"Shared neurons: {len(shared_neurons)}")
    print(f"Graph sizes: {graphs[d1].number_of_nodes()}, " +
          f"{graphs[d2].number_of_nodes()}, {graphs[d3].number_of_nodes()}\n")
    
    max_size = 0
    best_circuits = []
    
    # Search for increasingly larger motifs
    for motif_size in [4, 5, 6, 7]:
        print(f"\nSearching for motifs of size {motif_size}...")
        print("-" * 70)
        
        circuits = find_motifs_by_local_structure(
            graphs, shared_neurons, dataset_triple, motif_size=motif_size
        )
        
        if not circuits:
            print(f"No motifs of size {motif_size} found")
        else:
            print(f"Found {len(circuits)} isomorphic motifs of size {motif_size}")
            
            # Try to grow them
            grown = grow_circuits(graphs, shared_neurons, dataset_triple, circuits, max_growth=3)
            
            for node_sets, size in grown:
                if size > max_size:
                    max_size = size
                    best_circuits = [(node_sets, size)]
                elif size == max_size:
                    best_circuits.append((node_sets, size))
    
    # Save results
    print("\n" + "=" * 70)
    print(f"Best circuits found: {len(best_circuits)} circuits of size {max_size}")
    print("=" * 70 + "\n")
    
    if best_circuits:
        output_file = PROCESSED_DIR / "optimized_circuits.pkl"
        with open(output_file, "wb") as f:
            pickle.dump({dataset_triple: (best_circuits[0], max_size)}, f)
        print(f"Results saved to {output_file}\n")
    else:
        print("No circuits found\n")


if __name__ == "__main__":
    main()
