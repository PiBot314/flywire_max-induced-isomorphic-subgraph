# FlyWire Codex: Maximum Common Induced Subgraph (MCIS) Solution Approach

## Problem Statement

Find the largest neuronal circuit (directed induced subgraph) that is isomorphic across at least 3 of the 5 FlyWire connectome datasets (BANC, FAFB, MANC, MAOL, MCNS).

### Key Constraints
- Circuit = directed induced subgraph
- Must find N neurons present in 3 datasets
- Induced subgraphs must be mutually isomorphic (identical structure)
- Edge weights (synapse counts) ignored - work with unweighted directed graphs
- Edge existence and directionality must be preserved
- Node IDs differ across datasets (requires mapping)

## Solution Strategy

### Phase 1: Data Acquisition & Preprocessing

**1.1 Download Edge Lists**
- Obtain all 5 connectome edge lists (CSV format: source, destination)
- Validate data integrity and format consistency

**1.2 Access FlyWire Metadata**
- Extract cell class/subclass annotations for each dataset
- Obtain neurotransmitter type information
- Build neuron property databases for each dataset

**1.3 Build Graph Representations**
- Parse edge lists into directed graph structures (NetworkX or igraph)
- Create adjacency matrices for efficient lookup
- Compute and store node degree information (in-degree, out-degree)

### Phase 2: Exploratory Analysis

**2.1 Dataset Statistics**
```
For each dataset:
- Total nodes (neurons)
- Total edges (connections)
- Degree distribution (in/out)
- Graph density
- Connected components
- Common motif patterns (3-node, 4-node)
```

**2.2 Cross-Dataset Comparison**
- Compare size and complexity across datasets
- Identify which 3-dataset combinations are most promising
- Analyze overlap in cell types and functional properties

### Phase 3: Search Space Reduction

**3.1 Functional Grouping**
- Group neurons by cell class/subclass across datasets
- Group by neurotransmitter type (excitatory/inhibitory)
- Create candidate correspondence sets based on functional similarity

**3.2 Degree Sequence Filtering**
- For isomorphic subgraphs, degree sequences must match
- Filter candidate neurons by (in-degree, out-degree) pairs
- Build degree-based correspondence tables

**3.3 Local Topology Analysis**
- Compute local clustering coefficients
- Identify common motif participation
- Use graph invariants as additional filters

### Phase 4: Motif-Based Seed Discovery

**4.1 Small Motif Enumeration**
- Start with 3-node directed motifs (13 possible types)
- Use FlyWire's subgraph search to find instances in each dataset
- Identify motifs that appear frequently across all datasets

**4.2 Motif Matching**
```
For each motif type:
1. Find all instances in Dataset A
2. Find all instances in Dataset B  
3. Find all instances in Dataset C
4. Match instances based on:
   - Exact edge structure
   - Compatible node properties (class, neurotransmitter)
   - Degree sequences
```

**4.3 Seed Selection**
- Select top K most promising 3-node seeds
- Prioritize seeds with:
  - High frequency across datasets
  - Strong functional correspondence
  - Potential for expansion (high connectivity)

### Phase 5: Iterative Subgraph Expansion

**5.1 Expansion Algorithm**
```python
def expand_isomorphic_subgraph(seed_mapping, graphs):
    """
    Iteratively grow isomorphic subgraph from seed
    
    Args:
        seed_mapping: Initial node correspondence across 3 datasets
        graphs: List of 3 directed graphs
    
    Returns:
        Maximal isomorphic subgraph mapping
    """
    current_mapping = seed_mapping
    
    while True:
        candidates = find_expansion_candidates(current_mapping, graphs)
        
        if not candidates:
            break
        
        best_candidate = None
        for candidate in candidates:
            if verify_isomorphism_with_addition(current_mapping, candidate, graphs):
                best_candidate = candidate
                break
        
        if best_candidate:
            current_mapping.add(best_candidate)
        else:
            break
    
    return current_mapping
```

**5.2 Candidate Selection Heuristics**
```
Priority order for expansion candidates:
1. Nodes connected to multiple current subgraph nodes
2. Nodes with matching degree sequences across datasets
3. Nodes with compatible functional properties
4. Nodes that preserve motif patterns
```

**5.3 Isomorphism Verification**
- Use VF2 algorithm for subgraph isomorphism checking
- Verify edge preservation across all three datasets
- Verify directionality is preserved
- Use graph canonization (nauty/Traces) for faster comparison

### Phase 6: Optimization & Search

**6.1 Multi-Start Strategy**
- Run expansion from multiple seed motifs
- Explore different 3-dataset combinations (10 total)
- Track best solution found for each combination

**6.2 Pruning Strategies**
- Early termination if current subgraph size exceeds theoretical maximum
- Skip candidates that violate degree constraints
- Use upper bounds from graph theory (e.g., maximum common subgraph size)

**6.3 Parallel Processing**
- Process different seed motifs in parallel
- Process different dataset combinations in parallel
- Aggregate results to find global optimum

### Phase 7: Solution Validation & Output

**7.1 Final Verification**
```
For the largest discovered subgraph:
1. Verify all edges are preserved across datasets
2. Verify directionality matches exactly
3. Confirm induced subgraph property (no missing edges)
4. Validate neuron ID mappings are correct
```

**7.2 Output Generation**
```csv
Dataset_A,Dataset_B,Dataset_C
neuron_id_A1,neuron_id_B1,neuron_id_C1
neuron_id_A2,neuron_id_B2,neuron_id_C2
...
neuron_id_AN,neuron_id_BN,neuron_id_CN
```

**7.3 Documentation**
- Record solution size (N)
- Document which 3 datasets were used
- List runner-up solutions
- Describe computational approach and optimizations

## Algorithm Complexity

### Time Complexity
- Worst case: O(n^k) where n = nodes, k = subgraph size
- With heuristics: Significantly reduced in practice
- Expected: Polynomial time for small-to-medium circuits

### Space Complexity
- O(n + m) for graph storage (n nodes, m edges)
- O(k^2) for subgraph adjacency tracking
- O(k) for node mappings

## Key Optimizations

1. **Functional Filtering**: Use cell type metadata to reduce search space by 10-100x
2. **Degree Sequence Matching**: Filter incompatible nodes early
3. **Motif-Based Seeds**: Start from validated small structures
4. **Incremental Verification**: Check isomorphism at each expansion step
5. **Graph Canonization**: Use canonical forms for fast comparison
6. **Parallel Search**: Explore multiple seeds simultaneously

## Expected Challenges

1. **Scale**: Connectomes may have 10,000+ neurons
2. **Sparsity**: Graphs may be sparse, limiting common structures
3. **Heterogeneity**: Different datasets may have different coverage
4. **Computational Cost**: Subgraph isomorphism is NP-complete
5. **Node Correspondence**: No direct mapping between datasets

## Mitigation Strategies

1. Focus on highly connected regions (hubs, modules)
2. Use biological constraints (cell types, connectivity patterns)
3. Implement efficient pruning and early termination
4. Leverage FlyWire's pre-computed metadata and search tools
5. Start with smaller subgraphs and expand incrementally

## Tools & Libraries

- **NetworkX**: Graph manipulation and analysis
- **igraph**: High-performance graph operations
- **nauty/pynauty**: Graph canonization and isomorphism
- **pandas**: Data manipulation and CSV I/O
- **numpy**: Numerical operations and matrix handling
- **FlyWire API**: Access to metadata and subgraph search

## Success Metrics

- **Primary**: Maximize N (number of matched neurons)
- **Secondary**: Find multiple high-quality solutions
- **Tertiary**: Computational efficiency (runtime < 24 hours)

## Deliverable

Final CSV file with:
- 3 columns (selected dataset names)
- N rows (matched neuron IDs)
- Each row represents corresponding neurons across datasets
- Subgraphs induced by these neurons are mutually isomorphic
