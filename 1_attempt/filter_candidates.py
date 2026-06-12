"""
Filter candidate neurons for circuit discovery.

Uses node invariants (degree, degree signatures, local structure)
to prune unlikely matches across dataset triples.
"""

import pickle
import pandas as pd
from pathlib import Path
from collections import defaultdict
import networkx as nx

PROCESSED_DIR = Path(__file__).parent / "processed"


def load_graphs_and_presence():
    """
    Load graphs and presence data efficiently.
    
    Returns:
        tuple: (graphs_dict, presence_dict, all_neurons)
    """
    with open(PROCESSED_DIR / "graphs.pkl", "rb") as f:
        graphs = pickle.load(f)
    
    with open(PROCESSED_DIR / "presence_dict.pkl", "rb") as f:
        presence_dict = pickle.load(f)
    
    with open(PROCESSED_DIR / "all_neurons.pkl", "rb") as f:
        all_neurons = pickle.load(f)
    
    return graphs, presence_dict, all_neurons


def compute_degree_signature(graph, neuron):
    """
    Compute degree signature for a neuron: (in_degree, out_degree).
    
    Args:
        graph: NetworkX DiGraph
        neuron: neuron ID
        
    Returns:
        tuple: (in_degree, out_degree)
    """
    return (graph.in_degree(neuron), graph.out_degree(neuron))


def get_candidates_for_triple(graphs, presence_dict, dataset_triple):
    """
    Get neurons present in all three datasets of a triple.
    
    Args:
        graphs: dict of dataset -> DiGraph
        presence_dict: neuron_id -> set of datasets
        dataset_triple: tuple of 3 dataset names
        
    Returns:
        set: neurons appearing in all 3 datasets
    """
    d1, d2, d3 = dataset_triple
    candidates = set()
    
    for neuron, datasets in presence_dict.items():
        if d1 in datasets and d2 in datasets and d3 in datasets:
            candidates.add(neuron)
    
    return candidates


def filter_by_degree_signature(graphs, candidates, dataset_triple):
    """
    Group candidates by degree signature within each dataset.
    
    Neurons with matching signatures across all 3 datasets are more
    likely to be part of isomorphic subgraphs.
    
    Args:
        graphs: dict of dataset -> DiGraph
        candidates: set of neurons
        dataset_triple: tuple of 3 dataset names
        
    Returns:
        dict: signature -> list of neurons with that signature in all 3 datasets
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    signature_to_neurons = defaultdict(list)
    
    for neuron in candidates:
        if neuron not in g1 or neuron not in g2 or neuron not in g3:
            continue
        
        sig1 = compute_degree_signature(g1, neuron)
        sig2 = compute_degree_signature(g2, neuron)
        sig3 = compute_degree_signature(g3, neuron)
        
        # Only keep neurons with identical signatures across datasets
        if sig1 == sig2 == sig3:
            signature_to_neurons[sig1].append(neuron)
    
    return dict(signature_to_neurons)


def get_local_neighborhood(graph, neuron, depth=1):
    """
    Get local neighborhood structure around a neuron.
    
    Args:
        graph: NetworkX DiGraph
        neuron: neuron ID
        depth: neighborhood depth (1 = direct neighbors)
        
    Returns:
        set: neurons within depth hops
    """
    if neuron not in graph:
        return set()
    
    neighborhood = {neuron}
    current_layer = {neuron}
    
    for _ in range(depth):
        next_layer = set()
        for node in current_layer:
            next_layer.update(graph.predecessors(node))
            next_layer.update(graph.successors(node))
        next_layer -= neighborhood
        neighborhood.update(next_layer)
        current_layer = next_layer
    
    return neighborhood


def filter_candidates_summary(graphs, presence_dict, dataset_triples):
    """
    Generate filtering summary for all dataset triples.
    
    Args:
        graphs: dict of dataset -> DiGraph
        presence_dict: neuron_id -> set of datasets
        dataset_triples: list of 3-dataset tuples
        
    Returns:
        dict: triple -> filtering statistics
    """
    summary = {}
    
    for triple in dataset_triples:
        candidates = get_candidates_for_triple(graphs, presence_dict, triple)
        filtered = filter_by_degree_signature(graphs, candidates, triple)
        
        total_with_signature = sum(len(neurons) for neurons in filtered.values())
        num_signatures = len(filtered)
        
        summary[triple] = {
            "total_candidates": len(candidates),
            "matching_signatures": total_with_signature,
            "unique_signatures": num_signatures,
            "signature_groups": filtered
        }
    
    return summary


def save_filter_results(summary, output_path):
    """
    Save filtering results for later analysis.
    
    Args:
        summary: dict of filtering statistics
        output_path: path to save pickle
    """
    with open(output_path, "wb") as f:
        pickle.dump(summary, f)


def main():
    """Generate and save filtered candidates."""
    print("=" * 60)
    print("Filtering Candidate Neurons")
    print("=" * 60 + "\n")
    
    graphs, presence_dict, all_neurons = load_graphs_and_presence()
    
    # Generate all 3-dataset combinations
    dataset_names = ["BANC", "FAFB", "MANC", "MAOL", "MCNS"]
    from itertools import combinations
    dataset_triples = list(combinations(dataset_names, 3))
    
    print(f"Analyzing {len(dataset_triples)} dataset triples...\n")
    
    # Filter candidates for each triple
    summary = filter_candidates_summary(graphs, presence_dict, dataset_triples)
    
    # Print summary
    for triple in dataset_triples:
        stats = summary[triple]
        print(f"{triple}:")
        print(f"  Candidates in all 3: {stats['total_candidates']:,}")
        print(f"  With matching signatures: {stats['matching_signatures']:,}")
        print(f"  Unique degree signatures: {stats['unique_signatures']}")
        print()
    
    # Save results
    output_file = PROCESSED_DIR / "filtered_candidates.pkl"
    save_filter_results(summary, output_file)
    print(f"Filtering results saved to {output_file}\n")


if __name__ == "__main__":
    main()
