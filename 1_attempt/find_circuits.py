"""
Find isomorphic circuits across dataset triples.

Uses seed growth with backtracking to find the largest induced
isomorphic subgraph across three connectome datasets.
"""

import pickle
import networkx as nx
from pathlib import Path
from itertools import combinations, product
import sys

PROCESSED_DIR = Path(__file__).parent / "processed"


def load_required_data():
    """Load graphs and filtered candidates."""
    with open(PROCESSED_DIR / "graphs.pkl", "rb") as f:
        graphs = pickle.load(f)
    
    with open(PROCESSED_DIR / "filtered_candidates.pkl", "rb") as f:
        filtered = pickle.load(f)
    
    return graphs, filtered


def get_induced_subgraph(graph, nodes):
    """
    Get induced subgraph for given nodes.
    
    Args:
        graph: NetworkX DiGraph
        nodes: set of node IDs
        
    Returns:
        NetworkX DiGraph: induced subgraph
    """
    return graph.subgraph(nodes).copy()


def graphs_are_isomorphic(g1, g2):
    """
    Check if two directed graphs are isomorphic.
    
    Args:
        g1, g2: NetworkX DiGraph objects
        
    Returns:
        bool: True if isomorphic
    """
    return nx.is_isomorphic(g1, g2)


def can_extend_isomorphism(graphs, node_sets, dataset_triple, new_nodes):
    """
    Check if adding new nodes maintains isomorphism across all 3 graphs.
    
    Args:
        graphs: dict of dataset -> DiGraph
        node_sets: dict of dataset -> current node set
        dataset_triple: tuple of 3 dataset names
        new_nodes: tuple of 3 new nodes (one per dataset)
        
    Returns:
        bool: True if isomorphism maintained
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    n1, n2, n3 = new_nodes
    
    # Check if nodes exist in their graphs
    if n1 not in g1 or n2 not in g2 or n3 not in g3:
        return False
    
    # Get induced subgraphs with new nodes
    nodes1 = node_sets[d1] | {n1}
    nodes2 = node_sets[d2] | {n2}
    nodes3 = node_sets[d3] | {n3}
    
    sub1 = get_induced_subgraph(g1, nodes1)
    sub2 = get_induced_subgraph(g2, nodes2)
    sub3 = get_induced_subgraph(g3, nodes3)
    
    # Check isomorphism
    return (graphs_are_isomorphic(sub1, sub2) and 
            graphs_are_isomorphic(sub2, sub3))


def seed_growth(graphs, candidate_sets, dataset_triple, max_seed_size=20000):
    """
    Grow isomorphic circuits from seeds using greedy extension.
    
    Args:
        graphs: dict of dataset -> DiGraph
        candidate_sets: list of 3 sets of candidate neurons
        dataset_triple: tuple of 3 dataset names
        max_seed_size: maximum seed combinations to try
        
    Returns:
        list: list of (node_set_dict, size) for found isomorphic subgraphs
    """
    d1, d2, d3 = dataset_triple
    cand1, cand2, cand3 = candidate_sets
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    found_circuits = []
    
    # Find matching degree triples to seed growth
    degree_to_nodes = [{}, {}, {}]
    for node in cand1:
        deg = (g1.in_degree(node), g1.out_degree(node))
        if deg not in degree_to_nodes[0]:
            degree_to_nodes[0][deg] = []
        degree_to_nodes[0][deg].append(node)
    
    for node in cand2:
        deg = (g2.in_degree(node), g2.out_degree(node))
        if deg not in degree_to_nodes[1]:
            degree_to_nodes[1][deg] = []
        degree_to_nodes[1][deg].append(node)
    
    for node in cand3:
        deg = (g3.in_degree(node), g3.out_degree(node))
        if deg not in degree_to_nodes[2]:
            degree_to_nodes[2][deg] = []
        degree_to_nodes[2][deg].append(node)
    
    # Seeds: triples with matching degrees
    seeds = []
    common_degrees = set(degree_to_nodes[0].keys()) & \
                     set(degree_to_nodes[1].keys()) & \
                     set(degree_to_nodes[2].keys())
    
    for deg in common_degrees:
        for n1 in degree_to_nodes[0][deg][:50]:  # Sample per degree
            for n2 in degree_to_nodes[1][deg][:50]:
                for n3 in degree_to_nodes[2][deg][:50]:
                    seeds.append(({d1: {n1}, d2: {n2}, d3: {n3}}, 1))
                    if len(seeds) >= max_seed_size:
                        break
                if len(seeds) >= max_seed_size:
                    break
            if len(seeds) >= max_seed_size:
                break
        if len(seeds) >= max_seed_size:
            break
    
    print(f"    Starting with {len(seeds)} seed triplets", flush=True)
    
    # Greedy growth from seeds
    max_circuit = None
    max_size = 0
    
    for seed_idx, (node_sets, size) in enumerate(seeds):
        if seed_idx % max(1, len(seeds)//10) == 0:
            print(f"    Processing seed {seed_idx}/{len(seeds)}...", flush=True)
        
        current_sets = {d: node_sets[d].copy() for d in [d1, d2, d3]}
        current_size = size
        
        # Greedy expand
        improved = True
        rounds = 0
        while improved and rounds < 100:
            improved = False
            rounds += 1
            
            # Find candidates for expansion
            remaining1 = cand1 - current_sets[d1]
            remaining2 = cand2 - current_sets[d2]
            remaining3 = cand3 - current_sets[d3]
            
            # Try to add one node at a time
            for n1 in list(remaining1)[:100]:
                for n2 in list(remaining2)[:100]:
                    for n3 in list(remaining3)[:100]:
                        new_nodes = (n1, n2, n3)
                        if can_extend_isomorphism(graphs, current_sets, 
                                                  dataset_triple, new_nodes):
                            current_sets[d1].add(n1)
                            current_sets[d2].add(n2)
                            current_sets[d3].add(n3)
                            current_size += 1
                            improved = True
                            break
                    if improved:
                        break
                if improved:
                    break
        
        # Track maximum
        if current_size > max_size:
            max_size = current_size
            max_circuit = current_sets
            print(f"    → Found circuit of size {current_size}", flush=True)
    
    if max_circuit:
        found_circuits.append((max_circuit, max_size))
    
    return found_circuits


def find_max_circuits(graphs, filtered_data, dataset_triples):
    """
    Find maximum isomorphic circuits for each dataset triple.
    
    Args:
        graphs: dict of dataset -> DiGraph
        filtered_data: dict of triple -> candidate info
        dataset_triples: list of 3-dataset tuples
        
    Returns:
        dict: triple -> (best_node_sets, size)
    """
    results = {}
    
    for triple in dataset_triples:
        print(f"\nFinding circuits for {triple}:")
        
        if triple not in filtered_data:
            print(f"  No filtered candidates found")
            results[triple] = None
            continue
        
        stats = filtered_data[triple]
        sig_groups = stats.get("signature_groups", {})
        
        if not sig_groups:
            print(f"  No candidate groups found")
            results[triple] = None
            continue
        
        max_circuit = None
        max_size = 0
        
        # Try each signature group
        for sig_idx, (signature, neurons) in enumerate(sig_groups.items()):
            if sig_idx > 20:  # Limit number of signature groups to explore
                break
            
            if len(neurons) < 3:
                continue
            
            print(f"  Group {sig_idx}: {len(neurons)} neurons with sig {signature}", flush=True)
            
            # Take subset for efficiency
            candidate_set = set(neurons[:100])  # Limit size for efficiency
            
            # Create candidate sets for each dataset
            candidate_sets = [candidate_set, candidate_set, candidate_set]
            
            # Run seed growth
            circuits = seed_growth(graphs, candidate_sets, triple)
            
            # Find maximum
            for node_sets, size in circuits:
                if size > max_size:
                    max_size = size
                    max_circuit = node_sets
                    print(f"    Found circuit of size {size}", flush=True)
        
        results[triple] = (max_circuit, max_size) if max_circuit else None
    
    return results


def save_circuit_results(results, output_path):
    """Save circuit finding results."""
    with open(output_path, "wb") as f:
        pickle.dump(results, f)


def main():
    """Main circuit discovery pipeline."""
    print("=" * 60)
    print("Finding Isomorphic Circuits")
    print("=" * 60 + "\n")
    
    graphs, filtered_data = load_required_data()
    
    # Generate all 3-dataset combinations
    dataset_names = ["BANC", "FAFB", "MANC", "MAOL", "MCNS"]
    from itertools import combinations
    dataset_triples = list(combinations(dataset_names, 3))
    
    print(f"Searching across {len(dataset_triples)} dataset triples...\n")
    
    results = find_max_circuits(graphs, filtered_data, dataset_triples)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Circuit Discovery Summary")
    print("=" * 60)
    max_overall = 0
    best_triple = None
    
    for triple in dataset_triples:
        if results[triple]:
            node_sets, size = results[triple]
            print(f"{triple}: {size} neurons")
            if size > max_overall:
                max_overall = size
                best_triple = triple
        else:
            print(f"{triple}: No circuit found")
    
    print(f"\nLargest circuit: {best_triple} with {max_overall} neurons")
    
    # Save results
    output_file = PROCESSED_DIR / "circuit_results.pkl"
    save_circuit_results(results, output_file)
    print(f"\nResults saved to {output_file}\n")


if __name__ == "__main__":
    main()
