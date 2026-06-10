"""
Revised circuit search: Flexible candidate matching and circuit discovery.

Given the data characteristics (neurons present in multiple datasets but with
varying degree signatures), we use a more flexible approach:
1. Find neurons present in dataset triples
2. Generate induced subgraphs of small fixed sizes
3. Check for isomorphic matches across triples
"""

import pickle
import networkx as nx
from pathlib import Path
from itertools import combinations, product
import sys

PROCESSED_DIR = Path(__file__).parent / "processed"


def load_required_data():
    """Load graphs and presence data."""
    with open(PROCESSED_DIR / "graphs.pkl", "rb") as f:
        graphs = pickle.load(f)
    
    with open(PROCESSED_DIR / "presence_dict.pkl", "rb") as f:
        presence_dict = pickle.load(f)
    
    return graphs, presence_dict


def get_neurons_in_triple(presence_dict, dataset_triple):
    """
    Get neurons present in all three datasets of a triple.
    
    Args:
        presence_dict: neuron_id -> set of dataset names
        dataset_triple: tuple of 3 dataset names
        
    Returns:
        list: neuron IDs present in all 3 datasets
    """
    d1, d2, d3 = dataset_triple
    neurons = []
    
    for neuron, datasets in presence_dict.items():
        if d1 in datasets and d2 in datasets and d3 in datasets:
            neurons.append(neuron)
    
    return neurons


def find_isomorphic_subgraphs_size_k(graphs, neurons, dataset_triple, k=3, sample_size=5000):
    """
    Find all isomorphic induced subgraphs of size k.
    
    Args:
        graphs: dict of dataset -> DiGraph
        neurons: list of neurons in all 3 datasets
        dataset_triple: tuple of 3 dataset names
        k: subgraph size to search for
        sample_size: max neurons to sample for efficiency
        
    Returns:
        list: list of (subgraph_sets, size) tuples
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    # Sample neurons for efficiency
    if len(neurons) > sample_size:
        import random
        neurons = random.sample(neurons, sample_size)
    
    found = []
    
    # Try all k-subsets of neurons
    neuron_combinations = list(combinations(neurons, k))
    print(f"    Checking {len(neuron_combinations)} subsets of size {k}...", flush=True)
    
    if len(neuron_combinations) > 100000:
        # Sample if too many
        import random
        neuron_combinations = random.sample(neuron_combinations, 100000)
        print(f"    (sampled to {len(neuron_combinations)})", flush=True)
    
    for idx, subset in enumerate(neuron_combinations):
        if idx % max(1, len(neuron_combinations)//10) == 0 and idx > 0:
            print(f"      {idx}/{len(neuron_combinations)}...", flush=True)
        
        subset_set = set(subset)
        
        # Get induced subgraphs
        sub1 = g1.subgraph(subset_set).copy()
        sub2 = g2.subgraph(subset_set).copy()
        sub3 = g3.subgraph(subset_set).copy()
        
        # Quick check: same edge count
        if sub1.number_of_edges() != sub2.number_of_edges() or \
           sub2.number_of_edges() != sub3.number_of_edges():
            continue
        
        # Check isomorphism
        try:
            if nx.is_isomorphic(sub1, sub2) and nx.is_isomorphic(sub2, sub3):
                found.append(({
                    d1: subset_set,
                    d2: subset_set,
                    d3: subset_set
                }, k))
                print(f"    ✓ Found isomorphic circuit of size {k}!", flush=True)
        except:
            pass
    
    return found


def search_all_triples_size_k(graphs, presence_dict, k=3):
    """
    Search all dataset triples for isomorphic subgraphs of size k.
    
    Args:
        graphs: dict of dataset -> DiGraph
        presence_dict: neuron_id -> set of datasets
        k: subgraph size
        
    Returns:
        dict: triple -> list of found isomorphic subgraphs
    """
    dataset_names = ["BANC", "FAFB", "MANC", "MAOL", "MCNS"]
    dataset_triples = list(combinations(dataset_names, 3))
    
    results = {}
    
    for triple in dataset_triples:
        print(f"  {triple}:")
        neurons = get_neurons_in_triple(presence_dict, triple)
        
        if len(neurons) < k:
            print(f"    Only {len(neurons)} neurons, need {k}")
            results[triple] = []
            continue
        
        print(f"    Found {len(neurons)} neurons in all 3 datasets")
        
        found = find_isomorphic_subgraphs_size_k(
            graphs, neurons, triple, k=k, sample_size=10000
        )
        results[triple] = found
    
    return results


def main():
    """Revised circuit search."""
    print("=" * 60)
    print("Flexible Circuit Search")
    print("=" * 60 + "\n")
    
    graphs, presence_dict = load_required_data()
    
    # Start with small fixed sizes and grow
    for k in [3, 4, 5]:
        print(f"\nSearching for isomorphic subgraphs of size {k}...")
        print("-" * 60)
        
        results = search_all_triples_size_k(graphs, presence_dict, k=k)
        
        # Check if any found
        total_found = sum(len(v) for v in results.values())
        if total_found > 0:
            print(f"\n✓ Found {total_found} isomorphic subgraphs of size {k}")
            
            # Save results
            output_file = PROCESSED_DIR / f"circuits_size_{k}.pkl"
            with open(output_file, "wb") as f:
                pickle.dump(results, f)
            print(f"  Saved to {output_file}")
        else:
            print(f"\n✗ No isomorphic subgraphs of size {k} found")
    
    print("\n" + "=" * 60)
    print("Flexible search complete")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
