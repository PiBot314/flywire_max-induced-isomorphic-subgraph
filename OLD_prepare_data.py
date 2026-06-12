"""
Prepare datasets: 
load the five edge lists, normalize neuron identifiers, and record presence/absence per dataset.
with each neuron attach following properties for easy check of a graph:
    
"""

import pandas as pd
import pickle
from pathlib import Path
from collections import defaultdict
import networkx as nx

DATA_DIR = Path(__file__).parent / "data"
DATASETS = ["BANC", "FAFB", "MANC", "MAOL", "MCNS"]

all_neurons = set()
presence = defaultdict(set)

def load_datasets():
    """
    Load all five edgelist datasets.
    
    Returns:
        dict: Mapping of dataset name -> list of edges (source, target tuples)
    """
    datasets = {}
    
    for dataset_name in DATASETS:
        filepath = DATA_DIR / f"{dataset_name}_edgelist.csv"
        print(f"Loading {dataset_name}...", end=" ", flush=True) 
        # flush = true because these datasets are huge
        
        # Read CSV with source and target neuron IDs
        df = pd.read_csv(filepath)
        
        # Normalize column names (strip whitespace)
        df.columns = df.columns.str.strip()
        
        # Convert to tuples for edges (already normalized as integers)
        edges = list(zip(df['source neuron id'], df['target neuron id']))

        datasets[dataset_name] = edges
        
        print(f"({len(edges)} edges)", end="\n")
    
    return datasets


def normalize_neuron_ids(datasets):
    """
    Normalize neuron identifiers across datasets.
    FlyWire IDs are already standardized 64-bit integers, so minimal
    normalization needed. Ensure consistent type (int).
    
    Args:
        datasets: dict mapping dataset name -> list of edges
        
    Returns:
        dict: Normalized datasets with integer IDs
    """
    normalized = {}
    
    for dataset_name, edges in datasets.items():
        # Convert all IDs to int (should already be)
        normalized_edges = [(int(src), int(tgt)) for src, tgt in edges]
        normalized[dataset_name] = normalized_edges
    
    return normalized


def get_neuron_presence(datasets):
    """
    Record presence/absence of neurons across all datasets.
    
    Args:
        datasets: dict mapping dataset name -> list of edges
        
    Returns:
        tuple: (all_neurons_set, presence_dict)
            - all_neurons_set: set of all unique neurons across all datasets
            - presence_dict: mapping neuron_id -> set of dataset names containing it
    """
    all_neurons = set()
    presence = defaultdict(set)
    
    for dataset_name, edges in datasets.items():
        # Extract all neurons from edges
        neurons_in_dataset = set()
        for src, tgt in edges:
            neurons_in_dataset.add(src)
            neurons_in_dataset.add(tgt)
            presence[src].add(dataset_name)
            presence[tgt].add(dataset_name)
        
        all_neurons.update(neurons_in_dataset)
        print(f"{dataset_name}: {len(neurons_in_dataset)} unique neurons")
    
    return all_neurons, dict(presence)


def create_presence_matrix(all_neurons, presence_dict, datasets):
    """
    Create a presence/absence matrix for all neurons across datasets.
    
    Args:
        all_neurons: set of all unique neurons
        presence_dict: dict mapping neuron_id -> set of datasets
        datasets: dict of datasets (for reference)
        
    Returns:
        pd.DataFrame: Matrix with neurons as rows, datasets as columns,
                      1 if present, 0 if absent
    """
    matrix = {}
    for dataset_name in DATASETS:
        matrix[dataset_name] = [
            1 if dataset_name in presence_dict.get(neuron, set()) else 0
            for neuron in sorted(all_neurons)
        ]
    
    df = pd.DataFrame(matrix, index=sorted(all_neurons))
    df.index.name = 'neuron_id'
    return df


def create_graph_structures(datasets):
    """
    Create NetworkX directed graphs for each dataset.
    
    Args:
        datasets: dict mapping dataset name -> list of edges
        
    Returns:
        dict: Mapping dataset name -> DiGraph
    """
    graphs = {}
    
    for dataset_name, edges in datasets.items():
        G = nx.DiGraph()
        G.add_edges_from(edges)
        graphs[dataset_name] = G
        print(f"{dataset_name}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    return graphs


def save_results(datasets, graphs, all_neurons, presence_dict, presence_matrix):
    """
    Save all processed data structures for later analysis.
    
    Args:
        datasets: Raw edge lists
        graphs: NetworkX graphs
        all_neurons: Set of all neurons
        presence_dict: Neuron presence mapping
        presence_matrix: Presence/absence DataFrame
    """
    output_dir = Path(__file__).parent / "processed"
    output_dir.mkdir(exist_ok=True)
    
    # Save pickled objects for later use
    with open(output_dir / "datasets.pkl", "wb") as f:
        pickle.dump(datasets, f)
    
    with open(output_dir / "graphs.pkl", "wb") as f:
        pickle.dump(graphs, f)
    
    with open(output_dir / "all_neurons.pkl", "wb") as f:
        pickle.dump(all_neurons, f)
    
    with open(output_dir / "presence_dict.pkl", "wb") as f:
        pickle.dump(presence_dict, f)
    
    # Save presence matrix as CSV for inspection
    presence_matrix.to_csv(output_dir / "presence_matrix.csv")
    
    # Save summary statistics
    with open(output_dir / "summary.txt", "w") as f:
        f.write("Dataset Preparation Summary\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Total unique neurons: {len(all_neurons)}\n")
        f.write(f"Neurons in all 5 datasets: {sum(1 for p in presence_dict.values() if len(p) == 5)}\n")
        f.write(f"Neurons in 4 datasets: {sum(1 for p in presence_dict.values() if len(p) == 4)}\n")
        f.write(f"Neurons in 3 datasets: {sum(1 for p in presence_dict.values() if len(p) == 3)}\n")
        f.write("\n")
        
        for dataset_name in DATASETS:
            neurons_in_dataset = sum(1 for p in presence_dict.values() if dataset_name in p)
            f.write(f"{dataset_name}: {neurons_in_dataset} neurons\n")
    
    print(f"\nResults saved to {output_dir}")


def main():
    """Main execution pipeline."""
    print("=" * 60)
    print("FlyWire Dataset Preparation")
    print("=" * 60 + "\n")
    
    # Load datasets
    print("STEP 1: Loading edge lists")
    print("-" * 60)
    datasets = load_datasets()
    print()
    
    # due to the LARGE amount of data, and the fact that the data should already be 
    # normalized in the load_dataset function, I'm skipping the normalize data function
    # I don't want to rerun through the entire dataset again

    # Normalize neuron IDs 
    # print("STEP 2: Normalizing neuron identifiers")
    # print("-" * 60)
    # datasets = normalize_neuron_ids(datasets)
    # print("Normalization complete (FlyWire IDs are standardized)\n")
    
    # Track neuron presence
    print("STEP 3: Recording neuron presence/absence per dataset")
    print("-" * 60)
    all_neurons, presence_dict = get_neuron_presence(datasets)
    print(f"Total unique neurons: {len(all_neurons)}\n")
    
    # Create presence matrix
    print("STEP 4: Creating presence matrix")
    print("-" * 60)
    presence_matrix = create_presence_matrix(all_neurons, presence_dict, datasets)
    print(f"Presence matrix shape: {presence_matrix.shape}\n")
    
    # Create graph structures for circuit analysis
    print("STEP 5: Creating NetworkX graph structures")
    print("-" * 60)
    graphs = create_graph_structures(datasets)
    print()
    
    # Save all results
    print("STEP 6: Saving processed data")
    print("-" * 60)
    save_results(datasets, graphs, all_neurons, presence_dict, presence_matrix)
    
    print("\n" + "=" * 60)
    print("Dataset preparation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
