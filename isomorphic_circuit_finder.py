"""
Isomorphic Circuit Finder
========================
Finds the largest isomorphic directed subgraph across 3 connectome datasets.
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
import itertools

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

PRIORITY_TRIOS = [
    (3, 4, 5),  # MANC, MAOL, MCNS
    (2, 3, 4),  # FAFB, MANC, MAOL
    (1, 2, 3),  # BANC, FAFB, MANC
    (2, 1, 4)
]

CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
CHECKPOINT_INTERVAL = 10 

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
        OUTPUT_DIR.mkdir(exist_ok=True)
        CHECKPOINT_DIR.mkdir(exist_ok=True)
    
    def load_graph(self, dataset_idx: int) -> ig.Graph:
        if dataset_idx in self.graphs:
            return self.graphs[dataset_idx]
        
        dataset_name = DATASET_PAIRS[dataset_idx]
        graph_file = GRAPHS_DIR / f"{dataset_name}_graph.pkl"
        
        if not graph_file.exists():
            raise FileNotFoundError(f"Graph not found: {graph_file}")
        
        print(f"  Loading {dataset_name} graph...", flush=True)
        try:
            graph = ig.Graph.Read_Picklez(str(graph_file)) 
        except Exception as e:
            raise RuntimeError(f"Failed to load compressed pickle for {dataset_name}: {e}")
            
        self.graphs[dataset_idx] = graph
        return graph
    
    def load_degrees(self, dataset_idx: int) -> Dict[str, Tuple[int, int]]:
        if dataset_idx in self.degrees:
            return self.degrees[dataset_idx]
        
        dataset_name = DATASET_PAIRS[dataset_idx]
        degree_file = DEGREES_DIR / f"neuron_degrees_{dataset_idx}.csv"
        
        if not degree_file.exists():
            raise FileNotFoundError(f"Degrees not found: {degree_file}")
        
        print(f"  Loading {dataset_name} degrees...", flush=True)
        df = pd.read_csv(degree_file, dtype={'neuron_id': str})
        
        degree_dict = {}
        for _, row in df.iterrows():
            neuron_id = str(row['neuron_id']).strip()
            degree_dict[neuron_id] = (int(row['in_degree']), int(row['out_degree']))
        
        self.degrees[dataset_idx] = degree_dict
        return degree_dict
    
    def load_motifs(self, dataset_idx: int) -> List[Tuple[str, str, str, str]]:
        if dataset_idx in self.motifs:
            return self.motifs[dataset_idx]
        
        dataset_name = DATASET_PAIRS[dataset_idx]
        motif_file = MOTIFS_DIR / f"{dataset_name.lower()}_motif.csv"
        
        if not motif_file.exists():
            print(f"    ⚠ Motifs not found: {motif_file}")
            return []
        
        print(f"  Loading {dataset_name} motifs...", flush=True)
        df = pd.read_csv(motif_file)
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
                continue
        
        self.motifs[dataset_idx] = motifs
        print(f"    ✓ {len(motifs)} seed motifs")
        return motifs

# ============================================================================
# CORE ALGORITHM
# ============================================================================

class IsomorphicCircuitFinder:
    """Main algorithm for finding isomorphic subgraphs using string name lookups."""
    
    def __init__(self, loader: DataLoader):
        self.loader = loader
        self.best_result = None
        self.best_size = 0
    
    def _has_directed_edge(self, graph: ig.Graph, src_name: str, tgt_name: str) -> bool:
        try:
            graph.get_eid(src_name, tgt_name, directed=True, error=True)
            return True
        except (ValueError, ig.InternalError):
            return False

    def can_add_to_mapping(
        self,
        n1: str, n2: str, n3: str,
        current_mapping: Dict[int, Tuple[str, str, str]],
        G1: ig.Graph, G2: ig.Graph, G3: ig.Graph
    ) -> bool:
        for existing_mapping in current_mapping.values():
            m1, m2, m3 = existing_mapping
            
            if not (self._has_directed_edge(G1, m1, n1) == self._has_directed_edge(G2, m2, n2) == self._has_directed_edge(G3, m3, n3)):
                return False
            if not (self._has_directed_edge(G1, n1, m1) == self._has_directed_edge(G2, n2, m2) == self._has_directed_edge(G3, n3, m3)):
                return False
        return True
    
    def find_highest_degree_candidates(
        self,
        current_nodes_1: Set[str],
        current_nodes_2: Set[str],
        current_nodes_3: Set[str],
        G1: ig.Graph, G2: ig.Graph, G3: ig.Graph,
        deg_1: Dict[str, Tuple[int, int]],
        deg_2: Dict[str, Tuple[int, int]],
        deg_3: Dict[str, Tuple[int, int]]
    ) -> List[Tuple[str, str, str]]:
        neighbors_1, neighbors_2, neighbors_3 = set(), set(), set()
        
        for node in current_nodes_1:
            try:
                v_idx = G1.vs.find(name=node).index
                neighbors_1.update(G1.vs[G1.predecessors(v_idx)]['name'])
                neighbors_1.update(G1.vs[G1.successors(v_idx)]['name'])
            except ValueError: pass
        neighbors_1 -= current_nodes_1
        
        for node in current_nodes_2:
            try:
                v_idx = G2.vs.find(name=node).index
                neighbors_2.update(G2.vs[G2.predecessors(v_idx)]['name'])
                neighbors_2.update(G2.vs[G2.successors(v_idx)]['name'])
            except ValueError: pass
        neighbors_2 -= current_nodes_2
        
        for node in current_nodes_3:
            try:
                v_idx = G3.vs.find(name=node).index
                neighbors_3.update(G3.vs[G3.predecessors(v_idx)]['name'])
                neighbors_3.update(G3.vs[G3.successors(v_idx)]['name'])
            except ValueError: pass
        neighbors_3 -= current_nodes_3
        
        degree_to_nodes = defaultdict(lambda: [[], [], []])
        for n1 in neighbors_1:
            if n1 in deg_1: degree_to_nodes[deg_1[n1]][0].append(n1)
        for n2 in neighbors_2:
            if n2 in deg_2: degree_to_nodes[deg_2[n2]][1].append(n2)
        for n3 in neighbors_3:
            if n3 in deg_3: degree_to_nodes[deg_3[n3]][2].append(n3)
        
        candidates = []
        for deg_seq, (nodes1, nodes2, nodes3) in degree_to_nodes.items():
            if nodes1 and nodes2 and nodes3:
                total_deg = deg_seq[0] + deg_seq[1]
                for n1 in nodes1[:5]:
                    for n2 in nodes2[:5]:
                        for n3 in nodes3[:5]:
                            candidates.append((n1, n2, n3, total_deg))
        
        candidates.sort(key=lambda x: x[3], reverse=True)
        return [(n1, n2, n3) for n1, n2, n3, _ in candidates]
    
    def expand_from_seed(
        self,
        seed_mapping: Dict[int, Tuple[str, str, str]],
        G1: ig.Graph, G2: ig.Graph, G3: ig.Graph,
        deg_1: Dict[str, Tuple[int, int]],
        deg_2: Dict[str, Tuple[int, int]],
        deg_3: Dict[str, Tuple[int, int]],
        max_iterations: int = 500
    ) -> Dict[int, Tuple[str, str, str]]:
        current_mapping = seed_mapping.copy()
        iterations = 0
        no_progress_count = 0
        
        while iterations < max_iterations and no_progress_count < 3:
            iterations += 1
            current_nodes_1 = {m[0] for m in current_mapping.values()}
            current_nodes_2 = {m[1] for m in current_mapping.values()}
            current_nodes_3 = {m[2] for m in current_mapping.values()}
            
            candidates = self.find_highest_degree_candidates(
                current_nodes_1, current_nodes_2, current_nodes_3,
                G1, G2, G3, deg_1, deg_2, deg_3
            )
            
            if not candidates:
                break
            
            expanded = False
            for n1, n2, n3 in candidates[:50]:
                if self.can_add_to_mapping(n1, n2, n3, current_mapping, G1, G2, G3):
                    new_idx = len(current_mapping)
                    current_mapping[new_idx] = (n1, n2, n3)
                    expanded = True
                    no_progress_count = 0
                    break
            
            if not expanded:
                no_progress_count += 1
        
        return current_mapping
    
    def find_circuit(self, dataset_triple: Tuple[int, int, int]) -> Optional[Dict]:
        d1, d2, d3 = dataset_triple
        dataset_names = tuple(DATASET_PAIRS[d] for d in dataset_triple)
        
        print(f"\n{'='*70}\nProcessing: {' - '.join(dataset_names)}\n{'='*70}")
        try:
            graphs = {d1: self.loader.load_graph(d1), d2: self.loader.load_graph(d2), d3: self.loader.load_graph(d3)}
            degrees = {d1: self.loader.load_degrees(d1), d2: self.loader.load_degrees(d2), d3: self.loader.load_degrees(d3)}
            
            G1, G2, G3 = graphs[d1], graphs[d2], graphs[d3]
            deg_1, deg_2, deg_3 = degrees[d1], degrees[d2], degrees[d3]
            
            motifs_1 = self.loader.load_motifs(d1)
            if not motifs_1: return None
            
            best_result = None
            best_size = 0
            
            # Slice the seed search to a manageable number of diverse starting points to optimize speed
            for seed_idx, (a1, b1, c1, motif_type) in enumerate(motifs_1[:30]):
                if seed_idx % 3 == 0:
                    print(f"  Progress: {seed_idx}/{min(30, len(motifs_1))} seeds tracked...", flush=True)
                
                motifs_d2 = self._load_motifs_by_type(d2, motif_type)[:20]
                motifs_d3 = self._load_motifs_by_type(d3, motif_type)[:20]
                
                struct_1 = self._get_motif_structure(a1, b1, c1, G1)
                
                for a2, b2, c2, _ in motifs_d2:
                    for a3, b3, c3, _ in motifs_d3:
                        
                        # Loop through internal structural mapping combinations explicitly 
                        # to remove ordering dependency false negatives
                        for p2 in itertools.permutations([a2, b2, c2]):
                            for p3 in itertools.permutations([a3, b3, c3]):
                                
                                seed_mapping = {
                                    0: (a1, p2[0], p3[0]),
                                    1: (b1, p2[1], p3[1]),
                                    2: (c1, p2[2], p3[2])
                                }
                                
                                # Quick validation that seed permutation is legal before expanding
                                if not self.can_add_to_mapping_initial(seed_mapping, G1, G2, G3):
                                    continue
                                    
                                result = self.expand_from_seed(seed_mapping, G1, G2, G3, deg_1, deg_2, deg_3)
                                
                                if len(result) > best_size:
                                    best_size = len(result)
                                    best_result = {
                                        'mapping': result, 'size': len(result), 'seed_idx': seed_idx,
                                        'motif_type': motif_type, 'datasets': dataset_names, 'dataset_indices': dataset_triple
                                    }
                                    print(f"    ✓ New best: {best_size} nodes aligned!")
            return best_result
        except Exception as e:
            traceback.print_exc()
            return None

    def can_add_to_mapping_initial(self, seed_mapping: Dict[int, Tuple[str, str, str]], G1: ig.Graph, G2: ig.Graph, G3: ig.Graph) -> bool:
        # Mini isomorphism sanity check on the 3 seed nodes themselves
        for i in range(3):
            for j in range(3):
                if i == j: continue
                m1, m2, m3 = seed_mapping[i]
                n1, n2, n3 = seed_mapping[j]
                if not (self._has_directed_edge(G1, m1, n1) == self._has_directed_edge(G2, m2, n2) == self._has_directed_edge(G3, m3, n3)):
                    return False
        return True

    def _get_motif_structure(self, n1: str, n2: str, n3: str, graph: ig.Graph) -> Tuple:
        return (
            self._has_directed_edge(graph, n1, n2),
            self._has_directed_edge(graph, n1, n3),
            self._has_directed_edge(graph, n2, n1),
            self._has_directed_edge(graph, n2, n3),
            self._has_directed_edge(graph, n3, n1),
            self._has_directed_edge(graph, n3, n2)
        )

    def _load_motifs_by_type(self, dataset_idx: int, motif_type: str) -> List[Tuple]:
        dataset_name = DATASET_PAIRS[dataset_idx]
        motif_file = MOTIFS_DIR / f"{dataset_name.lower()}_motif.csv"
        if not motif_file.exists(): return []
        try:
            df = pd.read_csv(motif_file)
            df.columns = df.columns.str.strip().str.replace('﻿', '')
            motifs = []
            for _, row in df.iterrows():
                if str(row['type']).strip() == motif_type:
                    motifs.append((str(row['neuron_a_id']).strip(), str(row['neuron_b_id']).strip(), str(row['neuron_c_id']).strip(), motif_type))
            return motifs
        except Exception: return []

    def run(self):
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
        if not results or not self.best_result: 
            print("✗ No results exceeded seed limits.")
            return
        best = self.best_result
        mapping_data = []
        for node_id, (n1, n2, n3) in best['mapping'].items():
            mapping_data.append({
                'node_id': node_id,
                DATASET_PAIRS[best['dataset_indices'][0]]: n1,
                DATASET_PAIRS[best['dataset_indices'][1]]: n2,
                DATASET_PAIRS[best['dataset_indices'][2]]: n3,
            })
        pd.DataFrame(mapping_data).to_csv(OUTPUT_DIR / "solution.csv", index=False)
        print(f"\n✓ Saved solution file detailing {best['size']} neurons.")

if __name__ == "__main__":
    loader = DataLoader()
    finder = IsomorphicCircuitFinder(loader)
    finder.save_results(finder.run())