# Detailed Algorithm Implementation Plan

## Core Algorithm: Maximum Common Induced Subgraph (MCIS)

### Problem Formalization

Given three directed graphs G₁ = (V₁, E₁), G₂ = (V₂, E₂), G₃ = (V₃, E₃):

Find mapping M: V_sub → V₁ × V₂ × V₃ such that:
1. |V_sub| is maximized (N neurons)
2. For all u, v ∈ V_sub: (u,v) ∈ E_sub ⟺ (M₁(u), M₁(v)) ∈ E₁ ∧ (M₂(u), M₂(v)) ∈ E₂ ∧ (M₃(u), M₃(v)) ∈ E₃
3. The induced subgraphs are isomorphic

### Algorithm Pseudocode

```python
def find_maximum_common_induced_subgraph(G1, G2, G3, metadata):
    """
    Find the largest isomorphic induced subgraph across three datasets
    
    Args:
        G1, G2, G3: Directed graphs (NetworkX DiGraph objects)
        metadata: Dictionary containing cell type, class, neurotransmitter info
    
    Returns:
        best_mapping: Dictionary mapping abstract nodes to (id1, id2, id3) tuples
        best_size: Size of the largest subgraph found
    """
    
    # Phase 1: Preprocessing
    degree_groups_1 = group_by_degree_sequence(G1)
    degree_groups_2 = group_by_degree_sequence(G2)
    degree_groups_3 = group_by_degree_sequence(G3)
    
    functional_groups_1 = group_by_function(G1, metadata[1])
    functional_groups_2 = group_by_function(G2, metadata[2])
    functional_groups_3 = group_by_function(G3, metadata[3])
    
    # Phase 2: Find seed motifs
    seeds = find_common_motifs(G1, G2, G3, size=3)
    seeds = filter_by_compatibility(seeds, functional_groups, degree_groups)
    seeds = rank_by_expansion_potential(seeds, G1, G2, G3)
    
    # Phase 3: Expand from seeds
    best_mapping = None
    best_size = 0
    
    for seed in seeds[:TOP_K_SEEDS]:
        mapping = expand_from_seed(seed, G1, G2, G3, metadata)
        
        if len(mapping) > best_size:
            best_size = len(mapping)
            best_mapping = mapping
            
        # Early termination if we find a very large circuit
        if best_size > SATISFACTORY_SIZE:
            break
    
    return best_mapping, best_size


def expand_from_seed(seed_mapping, G1, G2, G3, metadata):
    """
    Greedily expand a seed mapping to maximal size
    """
    current_mapping = seed_mapping.copy()
    current_nodes_1 = set(m[0] for m in current_mapping.values())
    current_nodes_2 = set(m[1] for m in current_mapping.values())
    current_nodes_3 = set(m[2] for m in current_mapping.values())
    
    improved = True
    while improved:
        improved = False
        
        # Find candidate nodes for expansion
        candidates = find_expansion_candidates(
            current_nodes_1, current_nodes_2, current_nodes_3,
            G1, G2, G3, metadata
        )
        
        # Try each candidate
        for (n1, n2, n3) in candidates:
            if can_add_to_mapping(n1, n2, n3, current_mapping, G1, G2, G3):
                # Add to mapping
                new_abstract_node = len(current_mapping)
                current_mapping[new_abstract_node] = (n1, n2, n3)
                current_nodes_1.add(n1)
                current_nodes_2.add(n2)
                current_nodes_3.add(n3)
                improved = True
                break
    
    return current_mapping


def find_expansion_candidates(nodes1, nodes2, nodes3, G1, G2, G3, metadata):
    """
    Find candidate node triples that could extend the current subgraph
    """
    # Get neighbors of current subgraph in each graph
    neighbors1 = get_neighbors(nodes1, G1) - nodes1
    neighbors2 = get_neighbors(nodes2, G2) - nodes2
    neighbors3 = get_neighbors(nodes3, G3) - nodes3
    
    # Filter by degree sequence
    candidates = []
    for n1 in neighbors1:
        deg1 = (G1.in_degree(n1), G1.out_degree(n1))
        
        for n2 in neighbors2:
            deg2 = (G2.in_degree(n2), G2.out_degree(n2))
            if deg1 != deg2:
                continue
            
            for n3 in neighbors3:
                deg3 = (G3.in_degree(n3), G3.out_degree(n3))
                if deg1 != deg3:
                    continue
                
                # Check functional compatibility
                if are_functionally_compatible(n1, n2, n3, metadata):
                    candidates.append((n1, n2, n3))
    
    # Rank candidates by connectivity to current subgraph
    candidates = rank_by_connectivity(candidates, nodes1, nodes2, nodes3, G1, G2, G3)
    
    return candidates


def can_add_to_mapping(n1, n2, n3, current_mapping, G1, G2, G3):
    """
    Check if adding (n1, n2, n3) preserves isomorphism
    """
    # For each existing node in the mapping
    for abstract_node, (m1, m2, m3) in current_mapping.items():
        # Check edge from existing to new
        edge_in_G1_forward = G1.has_edge(m1, n1)
        edge_in_G2_forward = G2.has_edge(m2, n2)
        edge_in_G3_forward = G3.has_edge(m3, n3)
        
        if not (edge_in_G1_forward == edge_in_G2_forward == edge_in_G3_forward):
            return False
        
        # Check edge from new to existing
        edge_in_G1_backward = G1.has_edge(n1, m1)
        edge_in_G2_backward = G2.has_edge(n2, m2)
        edge_in_G3_backward = G3.has_edge(n3, m3)
        
        if not (edge_in_G1_backward == edge_in_G2_backward == edge_in_G3_backward):
            return False
    
    return True


def find_common_motifs(G1, G2, G3, size=3):
    """
    Find small motifs that appear in all three graphs
    Uses FlyWire's subgraph search capability
    """
    motifs = []
    
    # Enumerate all possible directed motifs of given size
    motif_types = enumerate_directed_motifs(size)
    
    for motif_type in motif_types:
        # Find instances in each graph
        instances_1 = find_motif_instances(G1, motif_type)
        instances_2 = find_motif_instances(G2, motif_type)
        instances_3 = find_motif_instances(G3, motif_type)
        
        # Match instances across graphs
        for inst1 in instances_1:
            for inst2 in instances_2:
                for inst3 in instances_3:
                    if are_compatible_instances(inst1, inst2, inst3):
                        motifs.append({
                            0: (inst1[0], inst2[0], inst3[0]),
                            1: (inst1[1], inst2[1], inst3[1]),
                            2: (inst1[2], inst2[2], inst3[2])
                        })
    
    return motifs
```

## Optimization Techniques

### 1. Degree Sequence Filtering

```python
def group_by_degree_sequence(G):
    """Group nodes by (in_degree, out_degree) pairs"""
    degree_groups = defaultdict(list)
    for node in G.nodes():
        deg = (G.in_degree(node), G.out_degree(node))
        degree_groups[deg].append(node)
    return degree_groups
```

**Benefit**: Reduces candidate space by 10-100x since isomorphic nodes must have identical degrees.

### 2. Functional Compatibility

```python
def are_functionally_compatible(n1, n2, n3, metadata):
    """Check if neurons have compatible functional properties"""
    # Check cell class
    class1 = metadata[1][n1]['class']
    class2 = metadata[2][n2]['class']
    class3 = metadata[3][n3]['class']
    
    if not (class1 == class2 == class3):
        return False
    
    # Check neurotransmitter type
    nt1 = metadata[1][n1]['neurotransmitter']
    nt2 = metadata[2][n2]['neurotransmitter']
    nt3 = metadata[3][n3]['neurotransmitter']
    
    if not (nt1 == nt2 == nt3):
        return False
    
    return True
```

**Benefit**: Biological constraints dramatically reduce search space.

### 3. Connectivity-Based Ranking

```python
def rank_by_connectivity(candidates, nodes1, nodes2, nodes3, G1, G2, G3):
    """Rank candidates by number of connections to current subgraph"""
    scores = []
    for (n1, n2, n3) in candidates:
        score = 0
        score += count_edges_to_set(n1, nodes1, G1)
        score += count_edges_to_set(n2, nodes2, G2)
        score += count_edges_to_set(n3, nodes3, G3)
        scores.append((score, (n1, n2, n3)))
    
    scores.sort(reverse=True)
    return [candidate for _, candidate in scores]
```

**Benefit**: Prioritizes candidates most likely to extend the subgraph.

### 4. Early Termination

```python
def compute_upper_bound(current_size, remaining_candidates):
    """Estimate maximum possible final size"""
    # Use graph theory bounds
    # If current best is already larger than theoretical max, stop
    return current_size + len(remaining_candidates)
```

## Handling Large Datasets

### Memory-Efficient Graph Storage

```python
# Use sparse adjacency matrices
from scipy.sparse import csr_matrix

def build_sparse_graph(edge_list):
    """Build memory-efficient graph representation"""
    nodes = set()
    for src, dst in edge_list:
        nodes.add(src)
        nodes.add(dst)
    
    node_to_idx = {node: idx for idx, node in enumerate(sorted(nodes))}
    n = len(nodes)
    
    row, col = [], []
    for src, dst in edge_list:
        row.append(node_to_idx[src])
        col.append(node_to_idx[dst])
    
    data = [1] * len(row)
    adj_matrix = csr_matrix((data, (row, col)), shape=(n, n))
    
    return adj_matrix, node_to_idx
```

### Parallel Processing

```python
from multiprocessing import Pool

def parallel_seed_expansion(seeds, G1, G2, G3, metadata, n_workers=4):
    """Expand multiple seeds in parallel"""
    with Pool(n_workers) as pool:
        results = pool.starmap(
            expand_from_seed,
            [(seed, G1, G2, G3, metadata) for seed in seeds]
        )
    
    # Return best result
    return max(results, key=len)
```

## Validation & Testing

### Isomorphism Verification

```python
def verify_isomorphism(mapping, G1, G2, G3):
    """Verify that the mapping defines isomorphic induced subgraphs"""
    nodes1 = [m[0] for m in mapping.values()]
    nodes2 = [m[1] for m in mapping.values()]
    nodes3 = [m[2] for m in mapping.values()]
    
    # Extract induced subgraphs
    sub1 = G1.subgraph(nodes1)
    sub2 = G2.subgraph(nodes2)
    sub3 = G3.subgraph(nodes3)
    
    # Check sizes match
    assert sub1.number_of_nodes() == sub2.number_of_nodes() == sub3.number_of_nodes()
    assert sub1.number_of_edges() == sub2.number_of_edges() == sub3.number_of_edges()
    
    # Check edge-by-edge correspondence
    for abstract_u, (n1_u, n2_u, n3_u) in mapping.items():
        for abstract_v, (n1_v, n2_v, n3_v) in mapping.items():
            edge_in_1 = sub1.has_edge(n1_u, n1_v)
            edge_in_2 = sub2.has_edge(n2_u, n2_v)
            edge_in_3 = sub3.has_edge(n3_u, n3_v)
            
            assert edge_in_1 == edge_in_2 == edge_in_3, \
                f"Edge mismatch: {abstract_u}->{abstract_v}"
    
    return True
```

## Expected Performance

### Time Complexity
- Preprocessing: O(|V| + |E|) per graph
- Motif finding: O(|V|³) for 3-node motifs
- Expansion: O(N × |V| × degree²) where N is final subgraph size
- Overall: Polynomial in practice with good heuristics

### Space Complexity
- Graph storage: O(|V| + |E|) per graph
- Mapping storage: O(N)
- Candidate tracking: O(|V|)

### Scalability
- Can handle graphs with 10,000-100,000 nodes
- Expansion typically finds circuits of size 10-100 nodes
- Runtime: Minutes to hours depending on dataset size