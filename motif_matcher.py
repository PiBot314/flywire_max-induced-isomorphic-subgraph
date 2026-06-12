"""
Seed Motif Matcher
==================
Matches corresponding seed motifs across three datasets using igraph native commands.
"""

import pandas as pd
from typing import List, Tuple, Dict
from pathlib import Path
import igraph as ig


class MotifMatcher:
    """Matches seed motifs across datasets based on structure."""
    
    def __init__(self, graphs: Dict[int, ig.Graph], degrees: Dict[int, Dict]):
        self.graphs = graphs
        self.degrees = degrees
    
    def _has_directed_edge(self, graph: ig.Graph, src_name: str, tgt_name: str) -> bool:
        try:
            graph.get_eid(str(src_name), str(tgt_name), directed=True, error=True)
            return True
        except (ValueError, ig.InternalError):
            return False

    def get_motif_structure(self, n1: str, n2: str, n3: str, graph: ig.Graph) -> Tuple:
        """Get degree pattern and exact structural edge pattern using string signatures."""
        try:
            v1 = graph.vs.find(name=str(n1))
            v2 = graph.vs.find(name=str(n2))
            v3 = graph.vs.find(name=str(n3))
            
            deg_pattern = tuple(sorted([
                (graph.indegree(v1.index), graph.outdegree(v1.index)),
                (graph.indegree(v2.index), graph.outdegree(v2.index)),
                (graph.indegree(v3.index), graph.outdegree(v3.index))
            ]))
        except ValueError:
            # Fallback signature if degrees are missing in graph tracking
            deg_pattern = ((0, 0), (0, 0), (0, 0))
        
        edge_pattern = (
            self._has_directed_edge(graph, n1, n2),
            self._has_directed_edge(graph, n1, n3),
            self._has_directed_edge(graph, n2, n1),
            self._has_directed_edge(graph, n2, n3),
            self._has_directed_edge(graph, n3, n1),
            self._has_directed_edge(graph, n3, n2)
        )
        
        return (deg_pattern, edge_pattern)
    
    def find_matching_motifs(
        self,
        motif_1: Tuple[str, str, str, str],
        dataset_indices: Tuple[int, int, int]
    ) -> List[Tuple[Tuple[str, str, str], Tuple[str, str, str]]]:
        d1, d2, d3 = dataset_indices
        a1, b1, c1, motif_type = motif_1
        
        struct_1 = self.get_motif_structure(a1, b1, c1, self.graphs[d1])
        
        motifs_2 = self._load_motifs_by_type(d2, motif_type)
        motifs_3 = self._load_motifs_by_type(d3, motif_type)
        
        matches = []
        
        for a2, b2, c2, _ in motifs_2:
            struct_2 = self.get_motif_structure(a2, b2, c2, self.graphs[d2])
            if struct_2 != struct_1:
                continue
                
            for a3, b3, c3, _ in motifs_3:
                struct_3 = self.get_motif_structure(a3, b3, c3, self.graphs[d3])
                if struct_3 == struct_1:
                    matches.append(((a2, b2, c2), (a3, b3, c3)))
        
        return matches
    
    def _load_motifs_by_type(self, dataset_idx: int, motif_type: str) -> List[Tuple]:
        from isomorphic_circuit_finder import DATASET_PAIRS
        
        MOTIFS_DIR = Path("/Users/arnav/agcode/flywire/qual_challenge/data/neuron_properties/motifs_3neuron")
        dataset_name = DATASET_PAIRS[dataset_idx]
        motif_file = MOTIFS_DIR / f"{dataset_name.lower()}_motif.csv"
        
        if not motif_file.exists():
            return []
        
        df = pd.read_csv(motif_file)
        df.columns = df.columns.str.strip().str.replace('﻿', '')
        motifs = []
        
        for _, row in df.iterrows():
            if str(row['type']).strip() == motif_type:
                motifs.append((
                    str(row['neuron_a_id']).strip(),
                    str(row['neuron_b_id']).strip(),
                    str(row['neuron_c_id']).strip(),
                    motif_type
                ))
        
        return motifs