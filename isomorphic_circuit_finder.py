"""
Isomorphic Circuit Finder
========================
Finds the largest isomorphic directed subgraph across 3 connectome datasets.

Uses seed 3-node motifs and expands greedily by selecting highest-degree nodes.
Includes checkpointing for graceful failure and resumption.

Algorithm:
1. Load graphs, degrees, and seed motifs
2. For each 3-dataset combination:
   - For each seed motif:
     - Expand using highest-degree node selection
     - Verify isomorphism preservation
     - Track best result
3. Save results and summary

Usage:
    python isomorphic_circuit_finder.py
"""

import pickle
import pandas as pd
import igraph as ig
from pathlib import Path
from collections import defaultdict
from typing import Dict, Tuple, Set, List, Optional
import json
import sys
from datetime import datetime
import traceback


# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path("/Users/arnav/agcode/flywire/qual_challenge")
GRAPHS_DIR = DATA_DIR / "processed" / "graph"
DEGREES_DIR = DATA_DIR / "processed" / "degrees"
MOTIFS_DIR = DATA_DIR / "data" / "neuron_properties" / "motifs_3neuron"
OUTPUT_DIR = DATA_DIR / "results"

DATASETS = ["BANC", "FAFB", "MANC", "MAOL", "MCNS"]
DATASET_PAIRS = {
    1: "BANC",
    2: "FAFB",
    3: "MANC",
    4: "MAOL",
    5: "MCNS"
}

# Best dataset trio (from prior work)
PRIORITY_TRIOS = [
    (3, 4, 5),  # MANC, MAOL, MCNS (male datasets)
    (2, 3, 4),  # FAFB, MANC, MAOL
    (1, 2, 3),  # BANC, FAFB, MANC
]

CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
CHECKPOINT_INTERVAL = 10  # Save checkpoint every N seed expansions

# ============================================================================
# DATA LOADING
# ============================================================================

class DataLoader:
    """Loads graphs, degrees, and seed motifs with caching."""
    
    def __init__(self):
        self.graphs = {}
        self.degrees = {}
        self.motifs = {}
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Create output directories if they don't exist."""
        OUTPUT_DIR.mkdir(exist_ok=True)
        CHECKPOINT_DIR.mkdir(exist_ok=True)
    
    def load_graph(self, dataset_idx: int) -> ig.Graph:
        """Load an igraph Graph from a pickle file."""
        if dataset_idx in self.graphs:
            return self.graphs[dataset_idx]
        
        dataset_name = DATASET_PAIRS[dataset_idx]
        graph_file = GRAPHS_DIR / f"{dataset_name}_graph.pkl"
        
        if not graph_file.exists():
            raise FileNotFoundError(f"Graph not found: {graph_file}")
        
        print(f"  Loading {dataset_name} graph...", flush=True)
        # Line 90: Use ig.Graph.Read_Picklez instead of pickle.load
        try:
            # Line 92: igraph's native compressed pickle reader
            graph = ig.Graph.Read_Picklez(str(graph_file)) 
        except Exception as e:
            # Line 94: Fallback or error logging
            raise RuntimeError(f"Failed to load compressed pickle for {dataset_name}: {e}")
            
        self.graphs[dataset_idx] = graph
        return graph
    
    def load_degrees(self, dataset_idx: int) -> Dict[int, Tuple[int, int]]:
        """Load degree information as {neuron_id: (in_degree, out_degree)}."""
        if dataset_idx in self.degrees:
            return self.degrees[dataset_idx]
        
        dataset_name = DATASET_PAIRS[dataset_idx]
        degree_file = DEGREES_DIR / f"neuron_degrees_{dataset_idx}.csv"
        
        if not degree_file.exists():
            raise FileNotFoundError(f"Degrees not found: {degree_file}")
        
        print(f"  Loading {dataset_name} degrees...", flush=True)
        df = pd.read_csv(degree_file)
        
        degree_dict = {}
        for _, row in df.iterrows():
            neuron_id = int(row['neuron_id'])
            degree_dict[neuron_id] = (int(row['in_degree']), int(row['out_degree']))
        
        self.degrees[dataset_idx] = degree_dict
        print(f"    ✓ {len(degree_dict)} neurons with degree info")
        return degree_dict
    
    def load_motifs(self, dataset_idx: int) -> List[Tuple[str, str, str, str]]:
        """Load seed motifs as list of (neuron_a, neuron_b, neuron_c, motif_type)."""
        if dataset_idx in self.motifs:
            return self.motifs[dataset_idx]
        
        dataset_name = DATASET_PAIRS[dataset_idx]
        motif_file = MOTIFS_DIR / f"{dataset_name.lower()}_motif.csv"
        
        if not motif_file.exists():
            print(f"    ⚠ Motifs not found: {motif_file}")
            return []
        
        print(f"  Loading {dataset_name} motifs...", flush=True)
        df = pd.read_csv(motif_file)
        
        # Line 18: Clean column names to strip out hidden spaces, tabs, or BOM characters
        df.columns = df.columns.str.strip().str.replace('﻿', '') 
        
        motifs = []
        for _, row in df.iterrows():
            try:
                motif = (
                    str(row['neuron_a_id']).strip(),
                    str(row['neuron_b_id']).strip(),
                    str(row['neuron_c_id']).strip(),
                    str(row['type']).strip()
                )
                motifs.append(motif)
            except Exception as e:
                print(f"    ⚠ Error parsing motif row: {e}")
                continue
        
        self.motifs[dataset_idx] = motifs
        print(f"    ✓ {len(motifs)} seed motifs")
        return motifs


# ============================================================================
# CORE ALGORITHM
# ============================================================================

class IsomorphicCircuitFinder:
    """Main algorithm for finding isomorphic subgraphs."""
    
    def __init__(self, loader: DataLoader):
        self.loader = loader
        self.best_result = None
        self.best_size = 0
        self.stats = defaultdict(int)
    
    def can_add_to_mapping(
        self,
        n1: int, n2: int, n3: int,
        current_mapping: Dict[int, Tuple[int, int, int]],
        G1: ig.Graph, G2: ig.Graph, G3: ig.Graph
    ) -> bool:
        """
        Check if adding (n1, n2, n3) preserves isomorphism.
        
        For all existing nodes (m1, m2, m3) in mapping:
        - Edge existence must be consistent across all graphs
        - Edge direction must be preserved
        """
        for existing_mapping in current_mapping.values():
            m1, m2, m3 = existing_mapping
            
            # Check forward edges (existing -> new)
            edge_fwd_g1 = G1.are_adjacent(m1, n1)
            edge_fwd_g2 = G2.are_adjacent(m2, n2)
            edge_fwd_g3 = G3.are_adjacent(m3, n3)
            
            if not (edge_fwd_g1 == edge_fwd_g2 == edge_fwd_g3):
                return False
            
            # Check backward edges (new -> existing)
            edge_bwd_g1 = G1.are_adjacent(n1, m1)
            edge_bwd_g2 = G2.are_adjacent(n2, m2)
            edge_bwd_g3 = G3.are_adjacent(n3, m3)
            
            if not (edge_bwd_g1 == edge_bwd_g2 == edge_bwd_g3):
                return False
        
        return True
    
    def find_highest_degree_candidates(
        self,
        current_nodes_1: Set[int],
        current_nodes_2: Set[int],
        current_nodes_3: Set[int],
        G1: ig.Graph,
        G2: ig.Graph,
        G3: ig.Graph,
        deg_1: Dict[int, Tuple[int, int]],
        deg_2: Dict[int, Tuple[int, int]],
        deg_3: Dict[int, Tuple[int, int]]
    ) -> List[Tuple[int, int, int]]:
        """
        Find candidate nodes with matching degree sequences.
        Prioritize by total degree (in + out).
        """
        # Get neighbors of current subgraph
        neighbors_1 = set()
        neighbors_2 = set()
        neighbors_3 = set()
        
        for node in current_nodes_1:
            neighbors_1.update(G1.predecessors(node))
            neighbors_1.update(G1.successors(node))
        neighbors_1 -= current_nodes_1
        
        for node in current_nodes_2:
            neighbors_2.update(G2.predecessors(node))
            neighbors_2.update(G2.successors(node))
        neighbors_2 -= current_nodes_2
        
        for node in current_nodes_3:
            neighbors_3.update(G3.predecessors(node))
            neighbors_3.update(G3.successors(node))
        neighbors_3 -= current_nodes_3
        
        # Group by degree sequence
        degree_to_nodes = defaultdict(lambda: [[], [], []])
        
        for n1 in neighbors_1:
            if n1 in deg_1:
                deg = deg_1[n1]
                degree_to_nodes[deg][0].append(n1)
        
        for n2 in neighbors_2:
            if n2 in deg_2:
                deg = deg_2[n2]
                degree_to_nodes[deg][1].append(n2)
        
        for n3 in neighbors_3:
            if n3 in deg_3:
                deg = deg_3[n3]
                degree_to_nodes[deg][2].append(n3)
        
        # Build candidates for matching degree sequences
        candidates = []
        for deg_seq, (nodes1, nodes2, nodes3) in degree_to_nodes.items():
            if nodes1 and nodes2 and nodes3:
                # Sort by total degree (in + out) descending
                total_deg = deg_seq[0] + deg_seq[1]
                
                for n1 in nodes1[:min(10, len(nodes1))]:  # Limit to top 10 per degree
                    for n2 in nodes2[:min(10, len(nodes2))]:
                        for n3 in nodes3[:min(10, len(nodes3))]:
                            candidates.append((n1, n2, n3, total_deg))
        
        # Sort by total degree descending
        candidates.sort(key=lambda x: x[3], reverse=True)
        
        return [(n1, n2, n3) for n1, n2, n3, _ in candidates]
    
    def expand_from_seed(
        self,
        seed_mapping: Dict[int, Tuple[int, int, int]],
        G1: ig.Graph,
        G2: ig.Graph,
        G3: ig.Graph,
        deg_1: Dict[int, Tuple[int, int]],
        deg_2: Dict[int, Tuple[int, int]],
        deg_3: Dict[int, Tuple[int, int]],
        max_iterations: int = 1000
    ) -> Dict[int, Tuple[int, int, int]]:
        """
        Greedily expand seed mapping by adding highest-degree compatible nodes.
        Persists by attempting many candidates before giving up.
        """
        current_mapping = seed_mapping.copy()
        iterations = 0
        no_progress_count = 0
        max_no_progress = 5  # Try this many times before giving up
        
        while iterations < max_iterations and no_progress_count < max_no_progress:
            iterations += 1
            
            current_nodes_1 = {m[0] for m in current_mapping.values()}
            current_nodes_2 = {m[1] for m in current_mapping.values()}
            current_nodes_3 = {m[2] for m in current_mapping.values()}
            
            # Find candidate nodes
            candidates = self.find_highest_degree_candidates(
                current_nodes_1, current_nodes_2, current_nodes_3,
                G1, G2, G3,
                deg_1, deg_2, deg_3
            )
            
            if not candidates:
                break
            
            # Try each candidate in order of degree
            expanded = False
            attempts = min(100, len(candidates))  # Try up to 100 candidates
            
            for n1, n2, n3 in candidates[:attempts]:
                try:
                    if self.can_add_to_mapping(n1, n2, n3, current_mapping, G1, G2, G3):
                        new_idx = len(current_mapping)
                        current_mapping[new_idx] = (n1, n2, n3)
                        expanded = True
                        no_progress_count = 0
                        break
                except Exception:
                    continue
            
            if not expanded:
                no_progress_count += 1
        
        return current_mapping
    
    def find_circuit(
        self,
        dataset_triple: Tuple[int, int, int],
        resume_from: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Find the largest isomorphic circuit for a 3-dataset combination.
        
        Algorithm:
        1. Load graphs and degrees for all 3 datasets
        2. Load seed motifs from first dataset
        3. For each seed motif, find matching structure in other datasets
        4. Expand each matched seed triplet using highest-degree strategy
        5. Return best result
        """
        d1, d2, d3 = dataset_triple
        dataset_names = tuple(DATASET_PAIRS[d] for d in dataset_triple)
        
        print(f"\n{'='*70}")
        print(f"Processing: {' - '.join(dataset_names)}")
        print(f"{'='*70}")
        
        try:
            # Load data
            print(f"Loading data...")
            graphs = {
                d1: self.loader.load_graph(d1),
                d2: self.loader.load_graph(d2),
                d3: self.loader.load_graph(d3)
            }
            
            degrees = {
                d1: self.loader.load_degrees(d1),
                d2: self.loader.load_degrees(d2),
                d3: self.loader.load_degrees(d3)
            }
            
            G1, G2, G3 = graphs[d1], graphs[d2], graphs[d3]
            deg_1, deg_2, deg_3 = degrees[d1], degrees[d2], degrees[d3]
            
            # Load seed motifs
            motifs_1 = self.loader.load_motifs(d1)
            
            if not motifs_1:
                print(f"⚠ No motifs found for {DATASET_PAIRS[d1]}. Skipping.")
                return None
            
            best_result = None
            best_size = 0
            processed_count = 0
            
            print(f"\nExpanding from {len(motifs_1)} seed motifs...")
            print(f"Strategy: Highest-degree node expansion with motif matching\n")
            
            for seed_idx, (a1, b1, c1, motif_type) in enumerate(motifs_1):
                if seed_idx % max(1, len(motifs_1) // 10) == 0:
                    print(f"  Progress: {seed_idx}/{len(motifs_1)} seeds processed", flush=True)
                
                try:
                    # Find matching motifs in datasets 2 and 3
                    motifs_d2 = self._load_motifs_by_type(d2, motif_type)
                    motifs_d3 = self._load_motifs_by_type(d3, motif_type)
                    
                    if not motifs_d2 or not motifs_d3:
                        continue
                    
                    # For each combination of matching motifs
                    struct_1 = self._get_motif_structure(a1, b1, c1, G1)
                    
                    for a2, b2, c2, _ in motifs_d2:
                        struct_2 = self._get_motif_structure(a2, b2, c2, G2)
                        
                        if struct_2 != struct_1:
                            continue
                        
                        for a3, b3, c3, _ in motifs_d3:
                            struct_3 = self._get_motif_structure(a3, b3, c3, G3)
                            
                            if struct_3 != struct_1:
                                continue
                            
                            # Found matching triplet! Create seed and expand
                            seed_mapping = {
                                0: (a1, a2, a3),
                                1: (b1, b2, b3),
                                2: (c1, c2, c3)
                            }
                            
                            result = self.expand_from_seed(
                                seed_mapping, G1, G2, G3,
                                deg_1, deg_2, deg_3,
                                max_iterations=1000
                            )
                            
                            if len(result) > best_size:
                                best_size = len(result)
                                best_result = {
                                    'mapping': result,
                                    'size': len(result),
                                    'seed_idx': seed_idx,
                                    'motif_type': motif_type,
                                    'datasets': dataset_names,
                                    'dataset_indices': dataset_triple
                                }
                                print(f"    ✓ New best: {best_size} nodes (seed {seed_idx}, type={motif_type})")
                
                except Exception as e:
                    print(f"    ⚠ Error processing seed {seed_idx}: {str(e)[:80]}")
                    continue
                
                processed_count += 1
                if processed_count % CHECKPOINT_INTERVAL == 0:
                    self._save_checkpoint(dataset_triple, best_result)
            
            return best_result
        
        except Exception as e:
            print(f"✗ Error processing {dataset_names}: {e}")
            traceback.print_exc()
            return None
    
    def _get_motif_structure(self, n1: int, n2: int, n3: int, graph: ig.Graph) -> Tuple:
        """Get structural signature of a 3-node motif."""
        edge_pattern = (
            graph.are_adjacent(n1, n2),
            graph.are_adjacent(n1, n3),
            graph.are_adjacent(n2, n1),
            graph.are_adjacent(n2, n3),
            graph.are_adjacent(n3, n1),
            graph.are_adjacent(n3, n2)
        )
        return edge_pattern
    
    def _load_motifs_by_type(self, dataset_idx: int, motif_type: str) -> List[Tuple]:
        """Load all motifs of a specific type from a dataset."""
        dataset_name = DATASET_PAIRS[dataset_idx]
        motif_file = MOTIFS_DIR / f"{dataset_name.lower()}_motif.csv"
        
        if not motif_file.exists():
            return []
        
        try:
            df = pd.read_csv(motif_file)
            motifs = []
            
            for _, row in df.iterrows():
                if str(row['type']).strip() == motif_type.strip():
                    motifs.append((
                        int(row['neuron_a_id']),
                        int(row['neuron_b_id']),
                        int(row['neuron_c_id']),
                        row['type'].strip()
                    ))
            
            return motifs
        except Exception:
            return []
    
    def _save_checkpoint(self, dataset_triple: Tuple[int, int, int], result: Optional[Dict]):
        """Save partial result as checkpoint."""
        try:
            checkpoint_file = CHECKPOINT_DIR / f"checkpoint_{dataset_triple[0]}_{dataset_triple[1]}_{dataset_triple[2]}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'dataset_triple': dataset_triple,
                    'result': result
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"  ⚠ Failed to save checkpoint: {e}")
    
    def run(self):
        """Main execution loop."""
        print(f"\n{'#'*70}")
        print(f"# Isomorphic Circuit Finder")
        print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*70}\n")
        
        all_results = []
        
        for dataset_triple in PRIORITY_TRIOS:
            result = self.find_circuit(dataset_triple)
            if result:
                all_results.append(result)
                if result['size'] > self.best_size:
                    self.best_size = result['size']
                    self.best_result = result
        
        return all_results
    
    def save_results(self, results: List[Dict]):
        """Save results to CSV and summary."""
        if not results:
            print("✗ No results to save.")
            return
        
        # Sort by size descending
        results.sort(key=lambda x: x['size'], reverse=True)
        
        # Save best result as CSV
        if self.best_result:
            best = self.best_result
            mapping_data = []
            
            for node_id, (n1, n2, n3) in best['mapping'].items():
                mapping_data.append({
                    'node_id': node_id,
                    DATASET_PAIRS[best['dataset_indices'][0]]: n1,
                    DATASET_PAIRS[best['dataset_indices'][1]]: n2,
                    DATASET_PAIRS[best['dataset_indices'][2]]: n3,
                })
            
            df = pd.DataFrame(mapping_data)
            result_file = OUTPUT_DIR / "solution.csv"
            df.to_csv(result_file, index=False)
            print(f"\n✓ Saved solution to: {result_file}")
            print(f"  Format: {', '.join(best['datasets'])}")
            print(f"  Size: {best['size']} neurons\n")
        
        # Save summary
        self._save_summary(results)
    
    def _save_summary(self, results: List[Dict]):
        """Generate and save summary report with detailed statistics."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'best_result': {
                'datasets': None,
                'dataset_indices': None,
                'neuron_count': 0,
                'edge_count': 0,
                'seed_type': None,
            },
            'all_results': []
        }
        
        if self.best_result:
            best = self.best_result
            
            # Count edges in the best result
            edge_count = self._count_edges_in_mapping(
                best['mapping'],
                self.loader.load_graph(best['dataset_indices'][0])
            )
            
            summary['best_result'] = {
                'datasets': best['datasets'],
                'dataset_indices': best['dataset_indices'],
                'neuron_count': best['size'],
                'edge_count': edge_count,
                'seed_type': best['motif_type'],
                'seed_index': best['seed_idx']
            }
        
        for result in results:
            edge_count = self._count_edges_in_mapping(
                result['mapping'],
                self.loader.load_graph(result['dataset_indices'][0])
            )
            
            summary['all_results'].append({
                'datasets': result['datasets'],
                'dataset_indices': result['dataset_indices'],
                'neuron_count': result['size'],
                'edge_count': edge_count,
                'motif_type': result['motif_type'],
                'seed_index': result['seed_idx']
            })
        
        summary_file = OUTPUT_DIR / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Print summary to stdout
        print(f"\n{'='*70}")
        print(f"SOLUTION SUMMARY")
        print(f"{'='*70}\n")
        
        if self.best_result:
            best = summary['best_result']
            print(f"Best Solution Found:")
            print(f"  Datasets: {' → '.join(best['datasets'])}")
            print(f"  Neuron Count: {best['neuron_count']}")
            print(f"  Edge Count: {best['edge_count']}")
            print(f"  Seed Motif Type: {best['seed_type']}")
            print()
        
        if summary['all_results']:
            print(f"All Solutions ({len(summary['all_results'])} found):")
            for i, res in enumerate(summary['all_results'], 1):
                print(f"  {i}. {' → '.join(res['datasets'])}: {res['neuron_count']} neurons, {res['edge_count']} edges")
        
        print(f"\n✓ Summary saved to: {summary_file}\n")
    
    def _count_edges_in_mapping(self, mapping: Dict[int, Tuple[int, int, int]], graph: ig.Graph) -> int:
        """Count the number of edges in the induced subgraph."""
        nodes = {m[0] for m in mapping.values()}
        edge_count = 0
        
        for n1 in nodes:
            for n2 in nodes:
                if n1 != n2 and graph.are_adjacent(n1, n2):
                    edge_count += 1
        
        return edge_count


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        loader = DataLoader()
        finder = IsomorphicCircuitFinder(loader)
        
        results = finder.run()
        finder.save_results(results)
        
        print(f"\n{'='*70}")
        print(f"✓ Completed successfully")
        print(f"{'='*70}\n")
    
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
