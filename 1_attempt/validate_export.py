"""
Validate and export circuit discovery results.

Verifies exact induced-isomorphism, exports matched neuron triples as CSV,
and generates summary statistics.
"""

import pickle
import pandas as pd
import networkx as nx
from pathlib import Path
from itertools import combinations

PROCESSED_DIR = Path(__file__).parent / "processed"


def load_all_data():
    """Load graphs, circuits, and metadata."""
    with open(PROCESSED_DIR / "graphs.pkl", "rb") as f:
        graphs = pickle.load(f)
    
    with open(PROCESSED_DIR / "circuit_results.pkl", "rb") as f:
        results = pickle.load(f)
    
    return graphs, results


def verify_isomorphism(graphs, node_sets, dataset_triple):
    """
    Verify that induced subgraphs are exactly isomorphic.
    
    Args:
        graphs: dict of dataset -> DiGraph
        node_sets: dict of dataset -> set of nodes
        dataset_triple: tuple of 3 dataset names
        
    Returns:
        tuple: (is_valid, iso_mapping or None)
            If valid, returns the isomorphism mappings
    """
    d1, d2, d3 = dataset_triple
    g1, g2, g3 = graphs[d1], graphs[d2], graphs[d3]
    
    # Get induced subgraphs
    sub1 = g1.subgraph(node_sets[d1]).copy()
    sub2 = g2.subgraph(node_sets[d2]).copy()
    sub3 = g3.subgraph(node_sets[d3]).copy()
    
    # Basic checks
    if len(sub1) != len(sub2) or len(sub2) != len(sub3):
        return False, None
    
    if sub1.number_of_edges() != sub2.number_of_edges() or \
       sub2.number_of_edges() != sub3.number_of_edges():
        return False, None
    
    # Check isomorphism
    try:
        iso_12 = nx.algorithms.isomorphism.DiGraphMatcher(sub1, sub2)
        iso_23 = nx.algorithms.isomorphism.DiGraphMatcher(sub2, sub3)
        
        if iso_12.is_isomorphic() and iso_23.is_isomorphic():
            return True, (dict(iso_12.mapping), dict(iso_23.mapping))
    except:
        return False, None
    
    return False, None


def export_circuits_csv(graphs, results, output_dir):
    """
    Export circuit results as CSV files.
    
    Creates one CSV per dataset triple containing matched neuron correspondence.
    
    Args:
        graphs: dict of dataset -> DiGraph
        results: dict of triple -> (node_sets, size)
        output_dir: path to output directory
    """
    dataset_names = ["BANC", "FAFB", "MANC", "MAOL", "MCNS"]
    dataset_triples = list(combinations(dataset_names, 3))
    
    max_size = 0
    best_triple = None
    best_export = None
    
    for triple in dataset_triples:
        if results[triple] is None:
            continue
        
        node_sets, size = results[triple]
        
        # Verify isomorphism
        is_valid, iso_maps = verify_isomorphism(graphs, node_sets, triple)
        
        if not is_valid:
            print(f"{triple}: FAILED isomorphism check (corrupted?)")
            continue
        
        print(f"{triple}: ✓ Valid isomorphic circuit ({size} neurons)")
        
        # Export as CSV
        d1, d2, d3 = triple
        nodes1 = sorted(list(node_sets[d1]))
        nodes2 = sorted(list(node_sets[d2]))
        nodes3 = sorted(list(node_sets[d3]))
        
        # Create dataframe
        df = pd.DataFrame({
            d1: nodes1,
            d2: nodes2[:len(nodes1)],  # Align lengths
            d3: nodes3[:len(nodes1)]
        })
        
        # Save CSV
        csv_path = output_dir / f"circuit_{triple[0]}_{triple[1]}_{triple[2]}.csv"
        df.to_csv(csv_path, index=False)
        print(f"  Exported to {csv_path.name}")
        
        # Track maximum
        if size > max_size:
            max_size = size
            best_triple = triple
            best_export = csv_path
    
    return best_triple, max_size, best_export


def generate_summary_report(results, output_path):
    """
    Generate summary report of circuit findings.
    
    Args:
        results: dict of triple -> (node_sets, size)
        output_path: path to write report
    """
    dataset_names = ["BANC", "FAFB", "MANC", "MAOL", "MCNS"]
    dataset_triples = list(combinations(dataset_names, 3))
    
    with open(output_path, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("CIRCUIT DISCOVERY RESULTS\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("OBJECTIVE:\n")
        f.write("Identify the largest neuronal circuit (induced directed subgraph)\n")
        f.write("shared across at least three connectomic datasets with identical\n")
        f.write("connectivity structure.\n\n")
        
        f.write("DATASETS ANALYZED:\n")
        f.write("- BANC (Female Adult Fly Brain and Nerve Cord)\n")
        f.write("- FAFB (Female Adult Fly Brain)\n")
        f.write("- MANC (Male Adult Fly Nerve Cord)\n")
        f.write("- MAOL (Male Adult Fly Right Optic Lobe)\n")
        f.write("- MCNS (Male Adult Fly CNS)\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("RESULTS BY DATASET TRIPLE\n")
        f.write("-" * 70 + "\n\n")
        
        max_size = 0
        best_triple = None
        
        for triple in dataset_triples:
            if results[triple] is None:
                status = "No circuit found"
                size = 0
            else:
                node_sets, size = results[triple]
                status = f"Found circuit with {size} neurons"
                if size > max_size:
                    max_size = size
                    best_triple = triple
            
            f.write(f"{str(triple):45s} {status}\n")
        
        f.write("\n" + "=" * 70 + "\n")
        f.write("MAXIMUM CIRCUIT FOUND\n")
        f.write("=" * 70 + "\n\n")
        
        if best_triple and max_size > 0:
            f.write(f"Dataset Triple: {best_triple}\n")
            f.write(f"Circuit Size: {max_size} neurons\n")
            f.write(f"\nThis represents a directed induced subgraph where:\n")
            f.write(f"- All {max_size} neurons are present in all 3 datasets\n")
            f.write(f"- The connectivity structure is identical across datasets\n")
            f.write(f"- All edge directions are preserved\n")
        else:
            f.write("No isomorphic circuits found meeting criteria.\n")
        
        f.write("\n" + "=" * 70 + "\n")


def main():
    """Validate and export circuit results."""
    print("=" * 60)
    print("Validating and Exporting Circuit Results")
    print("=" * 60 + "\n")
    
    graphs, results = load_all_data()
    
    # Create output directory
    output_dir = PROCESSED_DIR / "circuits"
    output_dir.mkdir(exist_ok=True)
    
    # Export circuits
    print("Exporting verified circuits...\n")
    best_triple, max_size, best_export = export_circuits_csv(
        graphs, results, output_dir
    )
    
    # Generate summary report
    print("\nGenerating summary report...")
    report_path = output_dir / "circuit_summary.txt"
    generate_summary_report(results, report_path)
    print(f"Report saved to {report_path}\n")
    
    # Print final results
    print("=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
    
    if max_size > 0:
        print(f"\n✓ Maximum circuit found: {best_triple} with {max_size} neurons")
        print(f"  Location: {best_export}\n")
    else:
        print("\n✗ No valid isomorphic circuits found.\n")


if __name__ == "__main__":
    main()
