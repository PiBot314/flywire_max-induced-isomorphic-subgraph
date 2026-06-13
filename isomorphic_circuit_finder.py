"""
Isomorphic Circuit Finder
========================
Finds the largest isomorphic directed subgraph across 3 connectome datasets.
Uses maximum-degree individual neurons as starting seeds with a biological variance tolerance.
Employs Beam Search for parallel mapping expansion and Memoized Quick-Adding.
Features 100% Native Integer C-Speed processing and Checkpoint Auto-Healing.
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
START_ID = 0
END_ID = 5
DEGREE_TOLERANCE = 0.20  
BEAM_WIDTH = 10          

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
        self.best_result = None
        self.best_size = 0
        self.vid_cache = {}

    def _get_vid(self, graph: ig.Graph, name: str) -> int:
        g_id = id(graph)
        if g_id not in self.vid_cache:
            self.vid_cache[g_id] = {}
        if name not in self.vid_cache[g_id]:
            try:
                self.vid_cache[g_id][name] = graph.vs.find(name=name).index
            except ValueError:
                self.vid_cache[g_id][name] = -1
        return self.vid_cache[g_id][name]

    def can_add_to_mapping(
        self, n1: str, n2: str, n3: str,
        current_mapping: Dict[int, Tuple[str, str, str]],
        G1: ig.Graph, G2: ig.Graph, G3: ig.Graph
    ) -> bool:
        if not current_mapping:
            return True
            
        is_connected = False
        
        v1_new = self._get_vid(G1, n1)
        v2_new = self._get_vid(G2, n2)
        v3_new = self._get_vid(G3, n3)
        
        if -1 in (v1_new, v2_new, v3_new):
            return False

        for m1, m2, m3 in current_mapping.values():
            m1_v = self._get_vid(G1, m1)
            m2_v = self._get_vid(G2, m2)
            m3_v = self._get_vid(G3, m3)
            
            # Using are_adjacent guarantees strict directed edge checking
            # Check Forward Edges
            fwd_1 = G1.are_adjacent(m1_v, v1_new)
            fwd_2 = G2.are_adjacent(m2_v, v2_new)
            fwd_3 = G3.are_adjacent(m3_v, v3_new)
            if not (fwd_1 == fwd_2 == fwd_3):
                return False
                
            # Check Backward Edges
            bwd_1 = G1.are_adjacent(v1_new, m1_v)
            bwd_2 = G2.are_adjacent(v2_new, m2_v)
            bwd_3 = G3.are_adjacent(v3_new, m3_v)
            if not (bwd_1 == bwd_2 == bwd_3):
                return False
                
            # Weak connectivity: must have at least one valid edge to the circuit
            if fwd_1 or bwd_1:
                is_connected = True
                
        return is_connected

    def _is_node_conflict(self, n1: str, n2: str, n3: str, mapping: Dict[int, Tuple[str, str, str]]) -> bool:
        nodes1 = {m[0] for m in mapping.values()}
        nodes2 = {m[1] for m in mapping.values()}
        nodes3 = {m[2] for m in mapping.values()}
        return (n1 in nodes1) or (n2 in nodes2) or (n3 in nodes3)
    
    def find_highest_degree_candidates(
        self, current_mapping: Dict[int, Tuple[str, str, str]],
        G1: ig.Graph, G2: ig.Graph, G3: ig.Graph,
        deg_1: Dict[str, Tuple[int, int]], deg_2: Dict[str, Tuple[int, int]], deg_3: Dict[str, Tuple[int, int]]
    ) -> List[Tuple[str, str, str]]:
        
        num_nodes = len(current_mapping)
        mapped_1 = [current_mapping[i][0] for i in range(num_nodes)]
        mapped_2 = [current_mapping[i][1] for i in range(num_nodes)]
        mapped_3 = [current_mapping[i][2] for i in range(num_nodes)]

        m1_vids = [self._get_vid(G1, n) for n in mapped_1]
        m2_vids = [self._get_vid(G2, n) for n in mapped_2]
        m3_vids = [self._get_vid(G3, n) for n in mapped_3]

        def get_pool_vids(graph, m_vids):
            pool = set()
            for v in m_vids:
                if v != -1:
                    pool.update(graph.predecessors(v))
                    pool.update(graph.successors(v))
            return pool - set(m_vids)
        
        p1_vids = get_pool_vids(G1, m1_vids)
        p2_vids = get_pool_vids(G2, m2_vids)
        p3_vids = get_pool_vids(G3, m3_vids)

        def get_sig_vid(v_idx, m_vids, graph):
            sig = []
            for m in m_vids:
                sig.append((graph.are_adjacent(m, v_idx), graph.are_adjacent(v_idx, m)))
            return tuple(sig)

        # 1. Build grouped signatures natively
        sig1_dict = defaultdict(list)
        for v1 in p1_vids:
            sig1_dict[get_sig_vid(v1, m1_vids, G1)].append(v1)

        sig2_dict = defaultdict(list)
        for v2 in p2_vids:
            sig2_dict[get_sig_vid(v2, m2_vids, G2)].append(v2)

        sig3_dict = defaultdict(list)
        for v3 in p3_vids:
            sig3_dict[get_sig_vid(v3, m3_vids, G3)].append(v3)

        # 2. Intersect valid topologies shared across datasets
        common_sigs = set(sig1_dict.keys()) & set(sig2_dict.keys()) & set(sig3_dict.keys())

        candidates = []
        for sig in common_sigs:
            # Enforce weak connectivity: mathematically blocks disjointed node signatures
            if not any(fwd or bwd for fwd, bwd in sig):
                continue
                
            # 3. Translate perfectly matched signatures back to string IDs for candidate generation
            n1_names = [G1.vs[v]['name'] for v in sig1_dict[sig]]
            n2_names = [G2.vs[v]['name'] for v in sig2_dict[sig]]
            n3_names = [G3.vs[v]['name'] for v in sig3_dict[sig]]
            
            n1_sorted = sorted(n1_names, key=lambda x: sum(deg_1.get(x, (0,0))), reverse=True)[:5]
            n2_sorted = sorted(n2_names, key=lambda x: sum(deg_2.get(x, (0,0))), reverse=True)[:5]
            n3_sorted = sorted(n3_names, key=lambda x: sum(deg_3.get(x, (0,0))), reverse=True)[:5]

            for n1 in n1_sorted:
                for n2 in n2_sorted:
                    for n3 in n3_sorted:
                        w = sum(deg_1.get(n1, (0,0))) + sum(deg_2.get(n2, (0,0))) + sum(deg_3.get(n3, (0,0)))
                        candidates.append((n1, n2, n3, w))

        candidates.sort(key=lambda x: x[3], reverse=True)
        return [(c[0], c[1], c[2]) for c in candidates[:30]]
    
    def expand_with_beam_search(
        self, start_mapping: Dict[int, Tuple[str, str, str]],
        G1: ig.Graph, G2: ig.Graph, G3: ig.Graph,
        deg_1: Dict[str, Tuple[int, int]], deg_2: Dict[str, Tuple[int, int]], deg_3: Dict[str, Tuple[int, int]],
        beam_width: int = BEAM_WIDTH, max_iterations: int = 200
    ) -> Dict[int, Tuple[str, str, str]]:
        beam = [start_mapping.copy()]
        best_overall = start_mapping.copy()
        stall_count = 0
        
        for iteration in range(max_iterations):
            next_beam = []
            
            for mapping in beam:
                candidates = self.find_highest_degree_candidates(
                    mapping, G1, G2, G3, deg_1, deg_2, deg_3
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
            
            unique_maps = {}
            for m in next_beam:
                sig = frozenset(m.values())
                if sig not in unique_maps or len(m) > len(unique_maps[sig]):
                    unique_maps[sig] = m
                    
            sorted_maps = sorted(unique_maps.values(), key=lambda m: len(m), reverse=True)
            beam = sorted_maps[:beam_width]
            
            if beam and len(beam[0]) > len(best_overall):
                best_overall = beam[0]
                stall_count = 0
            else:
                stall_count += 1
                
            if stall_count >= 3:
                break 
                
        return best_overall

    def _load_checkpoint(self, dataset_triple: Tuple[int, int, int], G1: ig.Graph) -> Optional[Dict[int, Tuple[str, str, str]]]:
        checkpoint_file = CHECKPOINT_DIR / f"checkpoint_{dataset_triple[0]}_{dataset_triple[1]}_{dataset_triple[2]}.json"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                    mapping = {int(k): tuple(v) for k, v in data['mapping'].items()}
                    
                    if len(mapping) > 1:
                        nodes1 = [m[0] for m in mapping.values()]
                        vids1 = [self._get_vid(G1, n) for n in nodes1]
                        edges = []
                        for i in range(len(vids1)):
                            for j in range(len(vids1)):
                                if i != j and vids1[i] != -1 and vids1[j] != -1 and G1.are_adjacent(vids1[i], vids1[j]):
                                    edges.append((i, j))
                                    
                        test_graph = ig.Graph(n=len(vids1), edges=edges, directed=True)
                        if not test_graph.is_connected(mode="weak"):
                            print(f"    ⚠ Corrupted disjointed checkpoint detected ({len(mapping)} nodes). Purging and starting fresh...")
                            checkpoint_file.unlink()
                            return None
                            
                    return mapping
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
            
            local_best_size = 0
            local_best_mapping = {}

            existing_mapping = self._load_checkpoint(dataset_triple, G1)
            if existing_mapping:
                local_best_mapping = existing_mapping.copy()
                local_best_size = len(existing_mapping)
                print(f"  Resuming from perfectly connected checkpoint with {local_best_size} nodes...")
                
                result = self.expand_with_beam_search(local_best_mapping, G1, G2, G3, deg_1, deg_2, deg_3)
                if len(result) > local_best_size:
                    local_best_mapping = result.copy()
                    local_best_size = len(result)
                    print(f"    ✓ Beam Search extended checkpoint to: {local_best_size} nodes!")
                    self._save_checkpoint(dataset_triple, result)

            print(f"  Sourcing top {START_ID}-{END_ID} max-degree neurons as seeds (Tolerance: ±{DEGREE_TOLERANCE*100}%)...")
            top_x_seeds_d1 = sorted(deg_1.keys(), key=lambda k: deg_1[k][0] + deg_1[k][1], reverse=True)[START_ID:END_ID]

            for seed_idx, n1 in enumerate(top_x_seeds_d1):
                if seed_idx % 10 == 0:
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
                        
                        if seed_tuple in local_best_mapping.values():
                            continue 
                            
                        if local_best_mapping and not self._is_node_conflict(n1, n2, n3, local_best_mapping):
                            if self.can_add_to_mapping(n1, n2, n3, local_best_mapping, G1, G2, G3):
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