"""
Seed Motif Matcher
==================
Matches corresponding seed motifs across three datasets.
"""

import pandas as pd
from typing import List, Tuple, Dict
from pathlib import Path
import networkx as nx


class MotifMatcher:
    """Matches seed motifs across datasets based on structure."""
    
    def __init__(self, graphs: Dict[int, nx.DiGraph], degrees: Dict[int, Dict]):
        self.graphs = graphs
        self.degrees = degrees
    
    def get_motif_structure(self, n1: int, n2: int, n3: int, graph: nx.DiGraph) -> Tuple:
        """
        Get the structure signature of a 3-node motif.
        Returns: (deg_pattern, edge_pattern)
        
        edge_pattern: Tuple of 6 bools for edges:
          (n1->n2, n1->n3, n2->n1, n2->n3, n3->n1, n3->n2)
        """
        nodes = [n1, n2, n3]
        
        # Get degree patterns
        deg_pattern = tuple(sorted([
            (graph.in_degree(n1), graph.out_degree(n1)),
            (graph.in_degree(n2), graph.out_degree(n2)),
            (graph.in_degree(n3), graph.out_degree(n3))
        ]))
        
        # Get edge pattern
        edge_pattern = (
            graph.has_edge(n1, n2),
            graph.has_edge(n1, n3),
            graph.has_edge(n2, n1),
            graph.has_edge(n2, n3),
            graph.has_edge(n3, n1),
            graph.has_edge(n3, n2)
        )
        
        return (deg_pattern, edge_pattern)
    
    def find_matching_motifs(
        self,
        motif_1: Tuple[int, int, int, str],
        dataset_indices: Tuple[int, int, int]
    ) -> List[Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]]:
        """
        For a seed motif in dataset 1, find matching motifs in datasets 2 and 3.
        Returns list of (motif_2, motif_3) tuples that match structurally.
        """
        d1, d2, d3 = dataset_indices
        a1, b1, c1, motif_type = motif_1
        
        # Get structure of seed motif
        struct_1 = self.get_motif_structure(a1, b1, c1, self.graphs[d1])
        
        # Load motifs from other datasets
        motifs_2 = self._load_motifs_by_type(d2, motif_type)
        motifs_3 = self._load_motifs_by_type(d3, motif_type)
        
        matches = []
        
        # Find all matching structures
        for a2, b2, c2, _ in motifs_2:
            struct_2 = self.get_motif_structure(a2, b2, c2, self.graphs[d2])
            
            if struct_2 != struct_1:
                continue
            
            # This one matches! Find one in dataset 3
            for a3, b3, c3, _ in motifs_3:
                struct_3 = self.get_motif_structure(a3, b3, c3, self.graphs[d3])
                
                if struct_3 == struct_1:
                    matches.append(((a2, b2, c2), (a3, b3, c3)))
        
        return matches
    
    def _load_motifs_by_type(self, dataset_idx: int, motif_type: str) -> List[Tuple]:
        """Load all motifs of a specific type from a dataset."""
        from isomorphic_circuit_finder import DATASET_PAIRS
        from pathlib import Path
        
        MOTIFS_DIR = Path("/Users/arnav/agcode/flywire/qual_challenge/data/neuron_properties/motifs_3neuron")
        dataset_name = DATASET_PAIRS[dataset_idx]
        motif_file = MOTIFS_DIR / f"{dataset_name.lower()}_motif.csv"
        
        if not motif_file.exists():
            return []
        
        df = pd.read_csv(motif_file)
        motifs = []
        
        for _, row in df.iterrows():
            if row['type'].strip() == motif_type:
                motifs.append((
                    int(row['neuron_a_id']),
                    int(row['neuron_b_id']),
                    int(row['neuron_c_id']),
                    row['type'].strip()
                ))
        
        return motifs
