"""
Complete isomorphism check: Verify if all neurons shared across MANC-MAOL-MCNS
form isomorphic induced directed subgraphs.

This script checks the theoretical maximum: all 5,289 shared neurons.
"""

import pickle
import networkx as nx
from pathlib import Path
from collections import defaultdict
import sys

PROCESSED_DIR = Path(__file__).parent / "processed"
DATASET_TRIPLE = ("MANC", "MAOL", "MCNS")


def load_graphs_and_presence():
    """Load all required data."""
    print("Loading graphs and presence data...", flush=True)
    
    with open(PROCESSED_DIR / "graphs.pkl", "rb") as f:
        graphs = pickle.load(f)
    
    with open(PROCESSED_DIR / "presence_dict.pkl", "rb") as f:
        presence_dict = pickle.load(f)
    
    return graphs, presence_dict


def get_all_shared_neurons(presence_dict):
    """
    Get all neurons present in all three datasets.
    
    Args:
        presence_dict: neuron_id -> set of datasets
        
    Returns:
        set: neurons in MANC, MAOL, and MCNS
    """
    d1, d2, d3 = DATASET_TRIPLE
    shared = set()
    
    for neuron, datasets in presence_dict.items():
        if d1 in datasets and d2 in datasets and d3 in datasets:
            shared.add(neuron)
    
    return shared


def verify_graph_properties(graphs, shared_neurons, dataset_triple):
    """
    Verify basic properties of induced subgraphs.
    
    Args:
        graphs: dict of dataset -> DiGraph
        shared_neurons: set of neurons
        dataset_triple: tuple of 3 dataset names
        
    Returns:
        dict: properties for each dataset
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    print("\n" + "=" * 70)
    print("INDUCED SUBGRAPH PROPERTIES")
    print("=" * 70 + "\n")
    
    properties = {}
    
    for idx, (d, g) in enumerate([(d1, g1), (d2, g2), (d3, g3)], 1):
        sub = g.subgraph(shared_neurons).copy()
        
        # Compute properties
        props = {
            "nodes": sub.number_of_nodes(),
            "edges": sub.number_of_edges(),
            "density": sub.number_of_edges() / (sub.number_of_nodes() * (sub.number_of_nodes() - 1)) 
                       if sub.number_of_nodes() > 1 else 0,
        }
        
        # In/out degree statistics
        in_degrees = [sub.in_degree(n) for n in sub.nodes()]
        out_degrees = [sub.out_degree(n) for n in sub.nodes()]
        
        if in_degrees:
            props["avg_in_degree"] = sum(in_degrees) / len(in_degrees)
            props["avg_out_degree"] = sum(out_degrees) / len(out_degrees)
            props["max_in_degree"] = max(in_degrees)
            props["max_out_degree"] = max(out_degrees)
        
        properties[d] = props
        
        print(f"{d}:")
        print(f"  Nodes: {props['nodes']:,}")
        print(f"  Edges: {props['edges']:,}")
        print(f"  Density: {props['density']:.6f}")
        print(f"  Avg in-degree: {props.get('avg_in_degree', 0):.2f}")
        print(f"  Avg out-degree: {props.get('avg_out_degree', 0):.2f}")
        print(f"  Max in-degree: {props.get('max_in_degree', 0)}")
        print(f"  Max out-degree: {props.get('max_out_degree', 0)}")
        print()
    
    return properties


def check_structural_compatibility(graphs, shared_neurons, dataset_triple):
    """
    Check if graphs have compatible structure before isomorphism test.
    
    Args:
        graphs: dict of dataset -> DiGraph
        shared_neurons: set of neurons
        dataset_triple: tuple of 3 dataset names
        
    Returns:
        bool: True if basic structure is compatible
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    sub1 = g1.subgraph(shared_neurons).copy()
    sub2 = g2.subgraph(shared_neurons).copy()
    sub3 = g3.subgraph(shared_neurons).copy()
    
    print("\n" + "=" * 70)
    print("STRUCTURAL COMPATIBILITY CHECK")
    print("=" * 70 + "\n")
    
    # Check 1: Same number of nodes
    same_nodes = (sub1.number_of_nodes() == sub2.number_of_nodes() == sub3.number_of_nodes())
    print(f"✓ Same node count (5,289): {same_nodes}")
    
    # Check 2: Same number of edges
    same_edges = (sub1.number_of_edges() == sub2.number_of_edges() == sub3.number_of_edges())
    print(f"{'✓' if same_edges else '✗'} Same edge count: {same_edges}")
    if not same_edges:
        print(f"  {d1}: {sub1.number_of_edges():,} edges")
        print(f"  {d2}: {sub2.number_of_edges():,} edges")
        print(f"  {d3}: {sub3.number_of_edges():,} edges")
    
    # Check 3: Degree sequence match
    deg_seq_1 = sorted([sub1.in_degree(n) + sub1.out_degree(n) for n in sub1.nodes()])
    deg_seq_2 = sorted([sub2.in_degree(n) + sub2.out_degree(n) for n in sub2.nodes()])
    deg_seq_3 = sorted([sub3.in_degree(n) + sub3.out_degree(n) for n in sub3.nodes()])
    
    same_deg_seq = (deg_seq_1 == deg_seq_2 == deg_seq_3)
    print(f"{'✓' if same_deg_seq else '✗'} Same degree sequence: {same_deg_seq}")
    
    compatible = same_nodes and same_edges and same_deg_seq
    print(f"\nStructural compatibility: {'✓ PASS' if compatible else '✗ FAIL'}")
    
    return compatible


def check_isomorphism(graphs, shared_neurons, dataset_triple):
    """
    Check if the three induced subgraphs are pairwise isomorphic.
    
    Uses NetworkX DiGraphMatcher with VF2 algorithm.
    
    Args:
        graphs: dict of dataset -> DiGraph
        shared_neurons: set of neurons
        dataset_triple: tuple of 3 dataset names
        
    Returns:
        dict: isomorphism results
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    print("\n" + "=" * 70)
    print("ISOMORPHISM VERIFICATION (VF2 Algorithm)")
    print("=" * 70 + "\n")
    
    # Create induced subgraphs
    sub1 = g1.subgraph(shared_neurons).copy()
    sub2 = g2.subgraph(shared_neurons).copy()
    sub3 = g3.subgraph(shared_neurons).copy()
    
    results = {
        "g1_vs_g2": False,
        "g2_vs_g3": False,
        "g1_vs_g3": False,
        "all_isomorphic": False
    }
    
    try:
        print(f"Checking {d1} vs {d2}...", flush=True)
        matcher_12 = nx.algorithms.isomorphism.DiGraphMatcher(sub1, sub2)
        iso_12 = matcher_12.is_isomorphic()
        results["g1_vs_g2"] = iso_12
        print(f"  {d1} ≅ {d2}: {'✓ YES' if iso_12 else '✗ NO'}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    try:
        print(f"Checking {d2} vs {d3}...", flush=True)
        matcher_23 = nx.algorithms.isomorphism.DiGraphMatcher(sub2, sub3)
        iso_23 = matcher_23.is_isomorphic()
        results["g2_vs_g3"] = iso_23
        print(f"  {d2} ≅ {d3}: {'✓ YES' if iso_23 else '✗ NO'}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    try:
        print(f"Checking {d1} vs {d3}...", flush=True)
        matcher_13 = nx.algorithms.isomorphism.DiGraphMatcher(sub1, sub3)
        iso_13 = matcher_13.is_isomorphic()
        results["g1_vs_g3"] = iso_13
        print(f"  {d1} ≅ {d3}: {'✓ YES' if iso_13 else '✗ NO'}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # All must be isomorphic for mutual isomorphism
    all_iso = results["g1_vs_g2"] and results["g2_vs_g3"] and results["g1_vs_g3"]
    results["all_isomorphic"] = all_iso
    
    print(f"\nMutually Isomorphic: {'✓ YES' if all_iso else '✗ NO'}")
    
    return results


def generate_isomorphism_mapping(graphs, shared_neurons, dataset_triple):
    """
    Generate and verify isomorphism mappings.
    
    Args:
        graphs: dict of dataset -> DiGraph
        shared_neurons: set of neurons
        dataset_triple: tuple of 3 dataset names
        
    Returns:
        dict: isomorphism mappings if found
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    sub1 = g1.subgraph(shared_neurons).copy()
    sub2 = g2.subgraph(shared_neurons).copy()
    sub3 = g3.subgraph(shared_neurons).copy()
    
    print("\n" + "=" * 70)
    print("ISOMORPHISM MAPPINGS")
    print("=" * 70 + "\n")
    
    mappings = {}
    
    try:
        matcher_12 = nx.algorithms.isomorphism.DiGraphMatcher(sub1, sub2)
        if matcher_12.is_isomorphic():
            mapping_12 = dict(matcher_12.mapping)
            mappings[f"{d1}_to_{d2}"] = mapping_12
            print(f"✓ Generated {d1} → {d2} mapping ({len(mapping_12)} nodes)")
    except:
        pass
    
    try:
        matcher_13 = nx.algorithms.isomorphism.DiGraphMatcher(sub1, sub3)
        if matcher_13.is_isomorphic():
            mapping_13 = dict(matcher_13.mapping)
            mappings[f"{d1}_to_{d3}"] = mapping_13
            print(f"✓ Generated {d1} → {d3} mapping ({len(mapping_13)} nodes)")
    except:
        pass
    
    return mappings


def save_results(graphs, shared_neurons, dataset_triple, iso_results, mappings):
    """
    Save complete isomorphism analysis results.
    
    Args:
        graphs: dict of dataset -> DiGraph
        shared_neurons: set of neurons
        dataset_triple: tuple of 3 dataset names
        iso_results: isomorphism check results
        mappings: isomorphism mappings
    """
    output_dir = PROCESSED_DIR / "isomorphism_analysis"
    output_dir.mkdir(exist_ok=True)
    
    # Save shared neurons list
    shared_list = sorted(list(shared_neurons))
    with open(output_dir / "shared_neurons.txt", "w") as f:
        f.write(f"All {len(shared_list)} neurons present in {dataset_triple}\n\n")
        for neuron in shared_list:
            f.write(f"{neuron}\n")
    
    # Save isomorphism results
    with open(output_dir / "isomorphism_results.txt", "w") as f:
        f.write("COMPLETE ISOMORPHISM ANALYSIS\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Dataset Triple: {dataset_triple}\n")
        f.write(f"Shared Neurons: {len(shared_neurons)}\n\n")
        
        f.write("Results:\n")
        f.write(f"  {dataset_triple[0]} ≅ {dataset_triple[1]}: {iso_results['g1_vs_g2']}\n")
        f.write(f"  {dataset_triple[1]} ≅ {dataset_triple[2]}: {iso_results['g2_vs_g3']}\n")
        f.write(f"  {dataset_triple[0]} ≅ {dataset_triple[2]}: {iso_results['g1_vs_g3']}\n")
        f.write(f"\nMutually Isomorphic: {iso_results['all_isomorphic']}\n")
    
    # Save pickled objects
    with open(output_dir / "shared_neurons.pkl", "wb") as f:
        pickle.dump(shared_neurons, f)
    
    with open(output_dir / "isomorphism_results.pkl", "wb") as f:
        pickle.dump(iso_results, f)
    
    with open(output_dir / "isomorphism_mappings.pkl", "wb") as f:
        pickle.dump(mappings, f)
    
    print(f"\nResults saved to {output_dir}/")


def main():
    """Run complete isomorphism analysis."""
    print("\n" + "█" * 70)
    print("COMPLETE ISOMORPHISM CHECK: MANC-MAOL-MCNS (All 5,289 Shared Neurons)")
    print("█" * 70 + "\n")
    
    # Load data
    graphs, presence_dict = load_graphs_and_presence()
    shared_neurons = get_all_shared_neurons(presence_dict)
    
    print(f"Analyzing {len(shared_neurons):,} neurons shared across all three datasets\n")
    
    # Verify graph properties
    properties = verify_graph_properties(graphs, shared_neurons, DATASET_TRIPLE)
    
    # Check structural compatibility
    compatible = check_structural_compatibility(graphs, shared_neurons, DATASET_TRIPLE)
    
    if not compatible:
        print("\n⚠ Graphs not structurally compatible - isomorphism unlikely")
        print("  (Different node or edge counts, incompatible degree sequences)")
        return
    
    # Check isomorphism
    print("\nProceeding to isomorphism check...\n")
    iso_results = check_isomorphism(graphs, shared_neurons, DATASET_TRIPLE)
    
    # Generate mappings if isomorphic
    mappings = {}
    if iso_results["all_isomorphic"]:
        mappings = generate_isomorphism_mapping(graphs, shared_neurons, DATASET_TRIPLE)
    
    # Save results
    save_results(graphs, shared_neurons, DATASET_TRIPLE, iso_results, mappings)
    
    # Final summary
    print("\n" + "█" * 70)
    print("ANALYSIS COMPLETE")
    print("█" * 70 + "\n")
    
    if iso_results["all_isomorphic"]:
        print(f"✓ SUCCESS: All {len(shared_neurons):,} shared neurons form")
        print(f"  MUTUALLY ISOMORPHIC induced subgraphs across {DATASET_TRIPLE}\n")
        print("This represents the MAXIMUM CIRCUIT SIZE for this dataset triple.")
    else:
        print(f"✗ The {len(shared_neurons):,} shared neurons do NOT form")
        print(f"  mutually isomorphic induced subgraphs.\n")
        print("Smaller isomorphic subgraphs may still exist (search other sizes).")
    
    print()


if __name__ == "__main__":
    main()
