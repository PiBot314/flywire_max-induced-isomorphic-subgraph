import pandas as pd
import igraph as ig
from collections import defaultdict
from typing import Dict, Tuple, Set, List

# ============================================================================
# SYNTHETIC MOCK LOGIC FOR TESTING
# ============================================================================

def create_mock_graphs():
    """
    Creates 3 toy graphs sharing an identical 5-node induced directed circuit.
    Shared isomorphic map (Node IDs as strings):
    G1: ['A', 'B', 'C', 'D', 'E']
    G2: ['X', 'Y', 'Z', 'W', 'V']
    G3: ['M', 'N', 'O', 'P', 'Q']
    """
    # Shared edges within the circuit: 0->1, 1->2, 2->3, 3->4, 4->0 (A directed loop)
    edges_1 = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'E'), ('E', 'A'), ('A', 'Noise1')]
    edges_2 = [('X', 'Y'), ('Y', 'Z'), ('Z', 'W'), ('W', 'V'), ('V', 'X'), ('Noise2', 'Y')]
    edges_3 = [('M', 'N'), ('N', 'O'), ('O', 'P'), ('P', 'Q'), ('Q', 'M'), ('M', 'Noise3')]

    G1 = ig.Graph.DataFrame(pd.DataFrame(edges_1, columns=['source', 'target']), directed=True, use_vids=False)
    G2 = ig.Graph.DataFrame(pd.DataFrame(edges_2, columns=['source', 'target']), directed=True, use_vids=False)
    G3 = ig.Graph.DataFrame(pd.DataFrame(edges_3, columns=['source', 'target']), directed=True, use_vids=False)
    
    # Degrees maps using name strings
    deg1 = {v['name']: (G1.indegree(v.index), G1.outdegree(v.index)) for v in G1.vs}
    deg2 = {v['name']: (G2.indegree(v.index), G2.outdegree(v.index)) for v in G2.vs}
    deg3 = {v['name']: (G3.indegree(v.index), G3.outdegree(v.index)) for v in G3.vs}
    
    # 3-Node Seed motif from the shared directed loop (0 -> 1 -> 2)
    mock_motifs = [('A', 'B', 'C', 'LoopSeed')]
    
    return G1, G2, G3, deg1, deg2, deg3, mock_motifs

# ============================================================================
# FIXED IMPLEMENTATION USING EXPLICIT VERTEX NAME LOOKUPS
# ============================================================================

class TestIsomorphicCircuitFinder:
    def __init__(self):
        self.best_size = 0
        self.best_result = None

    def can_add_to_mapping(self, n1: str, n2: str, n3: str, current_mapping: Dict[int, Tuple[str, str, str]], G1: ig.Graph, G2: ig.Graph, G3: ig.Graph) -> bool:
        for existing_mapping in current_mapping.values():
            m1, m2, m3 = existing_mapping
            
            # Use string names inside are_connected lookup
            if not (G1.are_connected(m1, n1) == G2.are_connected(m2, n2) == G3.are_connected(m3, n3)):
                return False
            if not (G1.are_connected(n1, m1) == G2.are_connected(n2, m2) == G3.are_connected(n3, m3)):
                return False
        return True

    def find_highest_degree_candidates(self, current_nodes_1: Set[str], current_nodes_2: Set[str], current_nodes_3: Set[str], G1: ig.Graph, G2: ig.Graph, G3: ig.Graph, deg_1: Dict[str, Tuple[int, int]], deg_2: Dict[str, Tuple[int, int]], deg_3: Dict[str, Tuple[int, int]]) -> List[Tuple[str, str, str]]:
        neighbors_1, neighbors_2, neighbors_3 = set(), set(), set()
        
        # Translate internal integer indices back to string names
        for node_name in current_nodes_1:
            v_idx = G1.vs.find(name=node_name).index
            neighbors_1.update(G1.vs[G1.predecessors(v_idx)]['name'])
            neighbors_1.update(G1.vs[G1.successors(v_idx)]['name'])
        neighbors_1 -= current_nodes_1
        
        for node_name in current_nodes_2:
            v_idx = G2.vs.find(name=node_name).index
            neighbors_2.update(G2.vs[G2.predecessors(v_idx)]['name'])
            neighbors_2.update(G2.vs[G2.successors(v_idx)]['name'])
        neighbors_2 -= current_nodes_2

        for node_name in current_nodes_3:
            v_idx = G3.vs.find(name=node_name).index
            neighbors_3.update(G3.vs[G3.predecessors(v_idx)]['name'])
            neighbors_3.update(G3.vs[G3.successors(v_idx)]['name'])
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
                for n1 in nodes1[:10]:
                    for n2 in nodes2[:10]:
                        for n3 in nodes3[:10]:
                            candidates.append((n1, n2, n3, total_deg))
                            
        candidates.sort(key=lambda x: x[3], reverse=True)
        return [(n1, n2, n3) for n1, n2, n3, _ in candidates]

    def expand_from_seed(self, seed_mapping: Dict[int, Tuple[str, str, str]], G1: ig.Graph, G2: ig.Graph, G3: ig.Graph, deg_1: Dict[str, Tuple[int, int]], deg_2: Dict[str, Tuple[int, int]], deg_3: Dict[str, Tuple[int, int]]) -> Dict[int, Tuple[str, str, str]]:
        current_mapping = seed_mapping.copy()
        iterations = 0
        
        while iterations < 100:
            iterations += 1
            current_nodes_1 = {m[0] for m in current_mapping.values()}
            current_nodes_2 = {m[1] for m in current_mapping.values()}
            current_nodes_3 = {m[2] for m in current_mapping.values()}
            
            candidates = self.find_highest_degree_candidates(current_nodes_1, current_nodes_2, current_nodes_3, G1, G2, G3, deg_1, deg_2, deg_3)
            if not candidates:
                break
                
            expanded = False
            for n1, n2, n3 in candidates:
                if self.can_add_to_mapping(n1, n2, n3, current_mapping, G1, G2, G3):
                    new_idx = len(current_mapping)
                    current_mapping[new_idx] = (n1, n2, n3)
                    expanded = True
                    break
            if not expanded:
                break
        return current_mapping

    def test_run(self):
        G1, G2, G3, deg1, deg2, deg3, mock_motifs = create_mock_graphs()
        
        # Simulating automated parsing of matching motif blocks across datasets
        motifs_d2 = [('X', 'Y', 'Z', 'LoopSeed')]
        motifs_d3 = [('M', 'N', 'O', 'LoopSeed')]
        
        for a1, b1, c1, m_type in mock_motifs:
            for a2, b2, c2, _ in motifs_d2:
                for a3, b3, c3, _ in motifs_d3:
                    seed_mapping = {0: (a1, a2, a3), 1: (b1, b2, b3), 2: (c1, c2, c3)}
                    
                    result = self.expand_from_seed(seed_mapping, G1, G2, G3, deg1, deg2, deg3)
                    if len(result) > self.best_size:
                        self.best_size = len(result)
                        self.best_result = result

        print("\n" + "="*50)
        print("TEST RUN RESULTS")
        print("="*50)
        print(f"Max Isomorphic Circuit Size Found: {self.best_size} neurons (Expected: 5)")
        print("\nDiscovered Structural Alignments:")
        for idx, (m1, m2, m3) in self.best_result.items():
            print(f"  Row {idx}: Dataset1={m1} | Dataset2={m2} | Dataset3={m3}")

if __name__ == "__main__":
    tester = TestIsomorphicCircuitFinder()
    tester.test_run()