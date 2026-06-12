"""
Isomorphic Circuit Finder
========================
Finds the largest isomorphic directed subgraph across 3 connectome datasets.
Uses maximum-degree individual neurons as starting seeds with a biological variance tolerance.
Employs Beam Search for parallel mapping expansion and Memoized Quick-Adding.
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
    # (3, 4, 5),  # MANC, MAOL, MCNS
    # (2, 3, 4),  # FAFB, MANC, MAOL
    # (1, 2, 3),  # BANC, FAFB, MANC
    (1, 2, 4)   # BANC, FAFB, MAOL
]

CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"

# Search Parameters
START_ID = 500
END_ID = 1000 
DEGREE_TOLERANCE = 0.20  # Allow 20% variance in global degrees to account for biological noise
BEAM_WIDTH = 10           # Number of parallel subgraph branches to track simultaneously

# ============================================================================
# DATA LOADING
# ============================================================================

class DataLoader:
    """Loads graphs and degrees with caching."""
    
    def __init__(self):
        self.graphs = {}
        self.degrees = {}
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

# ============================================================================
# CORE ALGORITHM
# ============================================================================

class IsomorphicCircuitFinder:
    def __init__(self, loader: DataLoader):
        self.loader = loader
        # Global trackers used ONLY by run() and save_results()
        self.best_result = None
        self.best_size = 0
    
    def _has_directed_edge(self, graph: ig.Graph, src_name: str, tgt_name: str) -> bool:
        try:
            graph.get_eid(src_name, tgt_name, directed=True, error=True)
            return True
        except (ValueError, ig.InternalError):
            return False

    def can_add_to_mapping(
        self, n1: str, n2: str, n3: str,
        current_mapping: Dict[int, Tuple[str, str, str]],
        G1: ig.Graph, G2: ig.Graph, G3: ig.Graph
    ) -> bool:
        for m1, m2, m3 in current_mapping.values():
            if not (self._has_directed_edge(G1, m1, n1) == self._has_directed_edge(G2, m2, n2) == self._has_directed_edge(G3, m3, n3)):
                return False
            if not (self._has_directed_edge(G1, n1, m1) == self._has_directed_edge(G2, n2, m2) == self._has_directed_edge(G3, n3, m3)):
                return False
        return True

    def _is_node_conflict(self, n1: str, n2: str, n3: str, mapping: Dict[int, Tuple[str, str, str]]) -> bool:
        """Ensures a new seed doesn't try to map a neuron that is already assigned elsewhere in the circuit."""
        nodes1 = {m[0] for m in mapping.values()}
        nodes2 = {m[1] for m in mapping.values()}
        nodes3 = {m[2] for m in mapping.values()}
        return (n1 in nodes1) or (n2 in nodes2) or (n3 in nodes3)
    
    def find_highest_degree_candidates(
        self, current_nodes_1: Set[str], current_nodes_2: Set[str], current_nodes_3: Set[str],
        G1: ig.Graph, G2: ig.Graph, G3: ig.Graph,
        deg_1: Dict[str, Tuple[int, int]], deg_2: Dict[str, Tuple[int, int]], deg_3: Dict[str, Tuple[int, int]]
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
        
        # Sort individual neighbors by global degree to prioritize structural hubs
        n1_sorted = sorted(list(neighbors_1), key=lambda x: sum(deg_1.get(x, (0,0))), reverse=True)[:15]
        n2_sorted = sorted(list(neighbors_2), key=lambda x: sum(deg_2.get(x, (0,0))), reverse=True)[:15]
        n3_sorted = sorted(list(neighbors_3), key=lambda x: sum(deg_3.get(x, (0,0))), reverse=True)[:15]
        
        candidates = []
        for n1 in n1_sorted:
            for n2 in n2_sorted:
                for n3 in n3_sorted:
                    total_weight = sum(deg_1.get(n1, (0,0))) + sum(deg_2.get(n2, (0,0))) + sum(deg_3.get(n3, (0,0)))
                    candidates.append((n1, n2, n3, total_weight))
        
        candidates.sort(key=lambda x: x[3], reverse=True)
        return [(c[0], c[1], c[2]) for c in candidates]
    
    def expand_with_beam_search(
        self, start_mapping: Dict[int, Tuple[str, str, str]],
        G1: ig.Graph, G2: ig.Graph, G3: ig.Graph,
        deg_1: Dict[str, Tuple[int, int]], deg_2: Dict[str, Tuple[int, int]], deg_3: Dict[str, Tuple[int, int]],
        beam_width: int = BEAM_WIDTH, max_iterations: int = 200
    ) -> Dict[int, Tuple[str, str, str]]:
        """Maintains K parallel mappings to avoid getting stuck in greedy dead-ends."""
        beam = [start_mapping.copy()]
        best_overall = start_mapping.copy()
        stall_count = 0
        
        for iteration in range(max_iterations):
            next_beam = []
            
            for mapping in beam:
                current_nodes_1 = {m[0] for m in mapping.values()}
                current_nodes_2 = {m[1] for m in mapping.values()}
                current_nodes_3 = {m[2] for m in mapping.values()}
                
                candidates = self.find_highest_degree_candidates(
                    current_nodes_1, current_nodes_2, current_nodes_3,
                    G1, G2, G3, deg_1, deg_2, deg_3
                )
                
                expanded_this_mapping = False
                for n1, n2, n3 in candidates[:30]:
                    if self.can_add_to_mapping(n1, n2, n3, mapping, G1, G2, G3):
                        new_map = mapping.copy()
                        new_map[len(new_map)] = (n1, n2, n3)
                        next_beam.append(new_map)
                        expanded_this_mapping = True
                
                if not expanded_this_mapping:
                    next_beam.append(mapping)
            
            # Hash states to remove redundant duplicate paths
            unique_maps = {}
            for m in next_beam:
                sig = frozenset(m.values())
                if sig not in unique_maps or len(m) > len(unique_maps[sig]):
                    unique_maps[sig] = m
                    
            sorted_maps = sorted(unique_maps.values(), key=lambda m: len(m), reverse=True)
            beam = sorted_maps[:beam_width]
            
            # Track overall progress
            if beam and len(beam[0]) > len(best_overall):
                best_overall = beam[0]
                stall_count = 0
            else:
                stall_count += 1
                
            if stall_count >= 3:
                break  # Search has completely stalled across all beam branches
                
        return best_overall

    def _load_checkpoint(self, dataset_triple: Tuple[int, int, int]) -> Optional[Dict[int, Tuple[str, str, str]]]:
        checkpoint_file = CHECKPOINT_DIR / f"checkpoint_{dataset_triple[0]}_{dataset_triple[1]}_{dataset_triple[2]}.json"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                    return {int(k): tuple(v) for k, v in data['mapping'].items()}
            except Exception as e:
                print(f"    ⚠ Failed to load checkpoint: {e}")
        return None

    def _save_checkpoint(self, dataset_triple: Tuple[int, int, int], mapping: Dict[int, Tuple[str, str, str]]):
        checkpoint_file = CHECKPOINT_DIR / f"checkpoint_{dataset_triple[0]}_{dataset_triple[1]}_{dataset_triple[2]}.json"
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'dataset_triple': dataset_triple,
                    'size': len(mapping),
                    'mapping': mapping
                }, f, indent=2)
        except Exception as e:
            pass
    
    def find_circuit(self, dataset_triple: Tuple[int, int, int]) -> Optional[Dict]:
        d1, d2, d3 = dataset_triple
        dataset_names = tuple(DATASET_PAIRS[d] for d in dataset_triple)
        
        print(f"\n{'='*70}\nProcessing: {' - '.join(dataset_names)}\n{'='*70}")
        try:
            graphs = {d1: self.loader.load_graph(d1), d2: self.loader.load_graph(d2), d3: self.loader.load_graph(d3)}
            degrees = {d1: self.loader.load_degrees(d1), d2: self.loader.load_degrees(d2), d3: self.loader.load_degrees(d3)}
            
            G1, G2, G3 = graphs[d1], graphs[d2], graphs[d3]
            deg_1, deg_2, deg_3 = degrees[d1], degrees[d2], degrees[d3]
            
            # LOCAL trackers to prevent overriding global search states
            local_best_size = 0
            local_best_mapping = {}

            # 1. Boot up from checkpoint memory
            existing_mapping = self._load_checkpoint(dataset_triple)
            if existing_mapping:
                local_best_mapping = existing_mapping.copy()
                local_best_size = len(existing_mapping)
                print(f"  Resuming from checkpoint with {local_best_size} nodes...")
                
                # Push the checkpoint through the beam search immediately to see if it can grow
                result = self.expand_with_beam_search(local_best_mapping, G1, G2, G3, deg_1, deg_2, deg_3)
                if len(result) > local_best_size:
                    local_best_mapping = result.copy()
                    local_best_size = len(result)
                    print(f"    ✓ Beam Search extended checkpoint to: {local_best_size} nodes!")
                    self._save_checkpoint(dataset_triple, result)

            # 2. Extract Top 1-node seeds by maximum degree
            print(f"  Sourcing top {START_ID}-{END_ID} max-degree neurons as seeds (Tolerance: ±{DEGREE_TOLERANCE*100}%)...")
            top_x_seeds_d1 = sorted(deg_1.keys(), key=lambda k: deg_1[k][0] + deg_1[k][1], reverse=True)[START_ID:END_ID]

            for seed_idx, n1 in enumerate(top_x_seeds_d1):
                if seed_idx % 15 == 0:
                    print(f"  Progress: {seed_idx}/{END_ID-START_ID} seeds tracked...", flush=True)

                t_in, t_out = deg_1[n1]
                t_tot = t_in + t_out
                
                def get_similar_nodes(deg_dict, top_k=5):
                    cands = []
                    for n, (d_in, d_out) in deg_dict.items():
                        d_tot = d_in + d_out
                        if abs(d_tot - t_tot) <= (t_tot * DEGREE_TOLERANCE):
                            dist = abs(d_in - t_in) + abs(d_out - t_out)
                            cands.append((n, dist))
                    cands.sort(key=lambda x: x[1])
                    return [c[0] for c in cands[:top_k]]

                cand_2 = get_similar_nodes(deg_2)
                if not cand_2: continue
                cand_3 = get_similar_nodes(deg_3)
                if not cand_3: continue

                for n2 in cand_2:
                    for n3 in cand_3:
                        seed_tuple = (n1, n2, n3)
                        
                        # --- MEMOIZATION & QUICK ADD LOGIC ---
                        if seed_tuple in local_best_mapping.values():
                            continue # Seed is already part of the master circuit. Skip.
                            
                        if local_best_mapping and not self._is_node_conflict(n1, n2, n3, local_best_mapping):
                            if self.can_add_to_mapping(n1, n2, n3, local_best_mapping, G1, G2, G3):
                                # SAFELY create a temporary extended map to avoid corrupting the dictionary
                                temp_mapping = local_best_mapping.copy()
                                temp_mapping[len(temp_mapping)] = seed_tuple
                                print(f"    ⚡ Quick Add! Seed fit perfectly into existing master circuit. Size: {len(temp_mapping)}")
                                
                                result = self.expand_with_beam_search(temp_mapping, G1, G2, G3, deg_1, deg_2, deg_3)
                                if len(result) > local_best_size:
                                    local_best_size = len(result)
                                    local_best_mapping = result.copy()
                                    self._save_checkpoint(dataset_triple, result)
                                    print(f"    ✓ Expanded after Quick Add to: {local_best_size} nodes!")
                                continue 
                        
                        # --- STANDARD BEAM SEARCH --- 
                        seed_mapping = {0: seed_tuple}
                        result = self.expand_with_beam_search(seed_mapping, G1, G2, G3, deg_1, deg_2, deg_3)
                        
                        if len(result) > local_best_size:
                            local_best_size = len(result)
                            local_best_mapping = result.copy()
                            self._save_checkpoint(dataset_triple, result)
                            print(f"    ✓ New standard seed breached best: {local_best_size} nodes aligned!")

            if local_best_size > 0:
                return {
                    'mapping': local_best_mapping, 'size': local_best_size,
                    'datasets': dataset_names, 'dataset_indices': dataset_triple
                }
            return None
            
        except Exception as e:
            traceback.print_exc()
            return None

    def run(self):
        all_results = []
        for dataset_triple in PRIORITY_TRIOS:
            result = self.find_circuit(dataset_triple)
            if result:
                all_results.append(result)
                print(f"Completed Trio {result['datasets']} -> Best Size: {result['size']}")
                
                # Global comparison strictly contained to the top-level orchestrator
                if result['size'] > self.best_size:
                    self.best_size = result['size']
                    self.best_result = result
        return all_results

    def save_results(self, results: List[Dict]):
        if not results or not self.best_result: 
            print("✗ No results exceeded seed limits.")
            self._write_summary(results, success=False)
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
        self._write_summary(results, success=True)

    def _write_summary(self, results: List[Dict], success: bool):
        summary_file = OUTPUT_DIR / "summary.txt"
        with open(summary_file, 'w') as f:
            f.write("==================================================\n")
            f.write(" ISOMORPHIC CIRCUIT FINDER SUMMARY\n")
            f.write(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("==================================================\n\n")
            
            if not success:
                f.write("Result: No valid isomorphic circuits discovered.\n")
                return
                
            f.write("--- BEST SOLUTION ---\n")
            best = self.best_result
            f.write(f"Datasets   : {' -> '.join(best['datasets'])}\n")
            f.write(f"Circuit Size: {best['size']} nodes\n\n")
            
            f.write("--- ALL TRIO RESULTS ---\n")
            for r in sorted(results, key=lambda x: x['size'], reverse=True):
                f.write(f"[{' - '.join(r['datasets'])}] Max Size: {r['size']}\n")
        
        print(f"✓ Saved run summary to: {summary_file}")

if __name__ == "__main__":
    loader = DataLoader()
    finder = IsomorphicCircuitFinder(loader)
    finder.save_results(finder.run())