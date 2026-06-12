# Implementation Plan & Project Structure

## Project Directory Structure

```
isomorphic/
├── data/
│   ├── raw/                    # Downloaded edge lists
│   │   ├── BANC_edges.csv
│   │   ├── FAFB_edges.csv
│   │   ├── MANC_edges.csv
│   │   ├── MAOL_edges.csv
│   │   └── MCNS_edges.csv
│   ├── metadata/               # FlyWire metadata
│   │   ├── BANC_metadata.json
│   │   ├── FAFB_metadata.json
│   │   ├── MANC_metadata.json
│   │   ├── MAOL_metadata.json
│   │   └── MCNS_metadata.json
│   └── processed/              # Intermediate results
│       ├── graphs/             # Serialized graph objects
│       ├── motifs/             # Discovered motifs
│       └── candidates/         # Candidate circuits
├── src/
│   ├── __init__.py
│   ├── data_loader.py          # Load and parse edge lists
│   ├── graph_builder.py        # Build graph representations
│   ├── metadata_handler.py     # Handle FlyWire metadata
│   ├── preprocessing.py        # Degree grouping, filtering
│   ├── motif_finder.py         # Find common motifs
│   ├── subgraph_expander.py    # Expand from seeds
│   ├── isomorphism_checker.py  # Verify isomorphism
│   ├── optimizer.py            # Main optimization loop
│   └── output_generator.py     # Generate CSV output
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_motif_analysis.ipynb
│   └── 03_results_visualization.ipynb
├── tests/
│   ├── test_graph_builder.py
│   ├── test_motif_finder.py
│   └── test_isomorphism.py
├── results/
│   ├── solution.csv            # Final output
│   ├── runner_ups.csv          # Alternative solutions
│   └── analysis_report.md      # Detailed analysis
├── requirements.txt
├── README.md
├── APPROACH.md                 # This document
└── run_optimization.py         # Main entry point
```

## Implementation Phases

### Phase 1: Setup & Data Acquisition (Day 1)

**Tasks:**
1. Set up Python environment with required libraries
2. Download all five edge list files
3. Access FlyWire Codex API for metadata
4. Validate data integrity and format

**Deliverables:**
- All data files in `data/raw/`
- Metadata files in `data/metadata/`
- Data validation report

**Code Modules:**
- `data_loader.py`: Functions to download and load edge lists
- `metadata_handler.py`: Functions to fetch and parse metadata

### Phase 2: Graph Construction & Analysis (Day 1-2)

**Tasks:**
1. Parse edge lists into NetworkX DiGraph objects
2. Compute basic statistics for each dataset
3. Build degree sequence indices
4. Create functional groupings from metadata
5. Identify dataset characteristics

**Deliverables:**
- Graph objects serialized to disk
- Statistical analysis report
- Degree and functional group indices

**Code Modules:**
- `graph_builder.py`: Build and serialize graphs
- `preprocessing.py`: Create indices and groupings

### Phase 3: Motif Discovery (Day 2-3)

**Tasks:**
1. Enumerate 3-node directed motif types
2. Find motif instances in each dataset
3. Match motifs across datasets using FlyWire search
4. Filter by functional compatibility
5. Rank seeds by expansion potential

**Deliverables:**
- List of common motifs across datasets
- Ranked seed candidates
- Motif frequency analysis

**Code Modules:**
- `motif_finder.py`: Motif enumeration and matching

### Phase 4: Subgraph Expansion (Day 3-5)

**Tasks:**
1. Implement greedy expansion algorithm
2. Add candidate filtering heuristics
3. Implement isomorphism verification
4. Run expansion from top seeds
5. Track best solutions for each dataset combination

**Deliverables:**
- Expanded subgraphs for each seed
- Best solution per dataset combination
- Expansion statistics and logs

**Code Modules:**
- `subgraph_expander.py`: Core expansion logic
- `isomorphism_checker.py`: Verification functions

### Phase 5: Optimization & Refinement (Day 5-6)

**Tasks:**
1. Implement parallel processing
2. Add early termination conditions
3. Refine heuristics based on results
4. Explore all 10 dataset combinations
5. Identify global optimum

**Deliverables:**
- Optimized algorithm implementation
- Complete search results
- Performance benchmarks

**Code Modules:**
- `optimizer.py`: Main optimization loop with parallelization

### Phase 6: Validation & Output (Day 6-7)

**Tasks:**
1. Verify final solution isomorphism
2. Generate output CSV
3. Document runner-up solutions
4. Create visualizations
5. Write analysis report

**Deliverables:**
- `solution.csv`: Final answer
- `runner_ups.csv`: Alternative solutions
- `analysis_report.md`: Methodology and results
- Visualization notebooks

**Code Modules:**
- `output_generator.py`: CSV generation and formatting

## Key Implementation Details

### 1. Data Loading

```python
# data_loader.py
import pandas as pd
import networkx as nx

def load_edge_list(filepath):
    """Load edge list from CSV file"""
    df = pd.read_csv(filepath, names=['source', 'target'])
    return df

def build_graph_from_edges(edge_df):
    """Build NetworkX DiGraph from edge list"""
    G = nx.DiGraph()
    G.add_edges_from(edge_df.values)
    return G
```

### 2. Metadata Integration

```python
# metadata_handler.py
import requests
import json

def fetch_neuron_metadata(dataset_name, neuron_ids):
    """Fetch metadata from FlyWire Codex API"""
    # API endpoint (to be determined)
    url = f"https://codex.flywire.ai/api/{dataset_name}/neurons"
    
    metadata = {}
    for neuron_id in neuron_ids:
        response = requests.get(f"{url}/{neuron_id}")
        if response.status_code == 200:
            data = response.json()
            metadata[neuron_id] = {
                'class': data.get('cell_class'),
                'subclass': data.get('cell_subclass'),
                'neurotransmitter': data.get('neurotransmitter')
            }
    
    return metadata
```

### 3. Degree-Based Filtering

```python
# preprocessing.py
from collections import defaultdict

def create_degree_index(G):
    """Create index of nodes by degree sequence"""
    degree_index = defaultdict(list)
    
    for node in G.nodes():
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        degree_index[(in_deg, out_deg)].append(node)
    
    return degree_index

def find_compatible_nodes(deg_seq, index1, index2, index3):
    """Find nodes with matching degree sequence across datasets"""
    nodes1 = set(index1.get(deg_seq, []))
    nodes2 = set(index2.get(deg_seq, []))
    nodes3 = set(index3.get(deg_seq, []))
    
    return nodes1, nodes2, nodes3
```

### 4. Main Optimization Loop

```python
# run_optimization.py
import argparse
from src.optimizer import find_maximum_common_subgraph
from src.output_generator import generate_solution_csv

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', default='data/raw')
    parser.add_argument('--output', default='results/solution.csv')
    parser.add_argument('--n-workers', type=int, default=4)
    args = parser.parse_args()
    
    # Load all datasets
    datasets = ['BANC', 'FAFB', 'MANC', 'MAOL', 'MCNS']
    graphs = {}
    metadata = {}
    
    for dataset in datasets:
        print(f"Loading {dataset}...")
        graphs[dataset] = load_and_build_graph(dataset, args.data_dir)
        metadata[dataset] = load_metadata(dataset, args.data_dir)
    
    # Find optimal solution
    print("Starting optimization...")
    best_solution = find_maximum_common_subgraph(
        graphs, 
        metadata,
        n_workers=args.n_workers
    )
    
    # Generate output
    print(f"Found solution with {len(best_solution['mapping'])} neurons")
    generate_solution_csv(best_solution, args.output)
    print(f"Solution saved to {args.output}")

if __name__ == '__main__':
    main()
```

## Required Libraries

```txt
# requirements.txt
networkx>=3.0
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0
matplotlib>=3.7.0
seaborn>=0.12.0
requests>=2.31.0
tqdm>=4.65.0
joblib>=1.3.0
pynauty>=2.8.6  # For graph canonization
python-igraph>=0.10.0  # Alternative graph library
jupyter>=1.0.0
pytest>=7.4.0
```

## Testing Strategy

### Unit Tests

```python
# tests/test_isomorphism.py
import pytest
from src.isomorphism_checker import verify_isomorphism

def test_simple_isomorphism():
    """Test isomorphism verification on simple graphs"""
    # Create two isomorphic triangles
    G1 = nx.DiGraph([(1, 2), (2, 3), (3, 1)])
    G2 = nx.DiGraph([(10, 20), (20, 30), (30, 10)])
    G3 = nx.DiGraph([(100, 200), (200, 300), (300, 100)])
    
    mapping = {
        0: (1, 10, 100),
        1: (2, 20, 200),
        2: (3, 30, 300)
    }
    
    assert verify_isomorphism(mapping, G1, G2, G3) == True

def test_non_isomorphism():
    """Test that non-isomorphic graphs are rejected"""
    G1 = nx.DiGraph([(1, 2), (2, 3)])
    G2 = nx.DiGraph([(10, 20), (20, 30), (30, 10)])  # Has extra edge
    G3 = nx.DiGraph([(100, 200), (200, 300)])
    
    mapping = {
        0: (1, 10, 100),
        1: (2, 20, 200),
        2: (3, 30, 300)
    }
    
    assert verify_isomorphism(mapping, G1, G2, G3) == False
```

## Performance Monitoring

```python
# Add to optimizer.py
import time
from tqdm import tqdm

class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.checkpoints = {}
    
    def checkpoint(self, name):
        self.checkpoints[name] = time.time() - self.start_time
    
    def report(self):
        print("\n=== Performance Report ===")
        for name, elapsed in self.checkpoints.items():
            print(f"{name}: {elapsed:.2f}s")
```

## Visualization

```python
# notebooks/03_results_visualization.ipynb
import matplotlib.pyplot as plt
import networkx as nx

def visualize_solution(mapping, G1, G2, G3):
    """Visualize the discovered isomorphic subgraph"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    for idx, (G, dataset) in enumerate([(G1, 'Dataset 1'), 
                                         (G2, 'Dataset 2'), 
                                         (G3, 'Dataset 3')]):
        nodes = [mapping[i][idx] for i in range(len(mapping))]
        subgraph = G.subgraph(nodes)
        
        pos = nx.spring_layout(subgraph)
        nx.draw(subgraph, pos, ax=axes[idx], 
                with_labels=True, node_color='lightblue',
                node_size=500, font_size=8, arrows=True)
        axes[idx].set_title(dataset)
    
    plt.tight_layout()
    plt.savefig('results/solution_visualization.png', dpi=300)
    plt.show()
```

## Timeline

| Phase | Duration | Key Milestones |
|-------|----------|----------------|
| Setup & Data | 1 day | All data downloaded and validated |
| Graph Construction | 1 day | Graphs built, statistics computed |
| Motif Discovery | 2 days | Common motifs identified and ranked |
| Expansion | 3 days | Subgraphs expanded, solutions found |
| Optimization | 1 day | All combinations explored |
| Validation & Output | 1 day | Final solution verified and documented |
| **Total** | **7-9 days** | Complete solution delivered |

## Success Criteria

1. ✅ All five datasets successfully loaded and processed
2. ✅ At least 10 common motifs identified across datasets
3. ✅ Expansion algorithm successfully grows subgraphs
4. ✅ Solution found with N ≥ 10 neurons (minimum viable)
5. ✅ Solution verified to be mutually isomorphic
6. ✅ Output CSV correctly formatted
7. ✅ Runner-up solutions documented
8. ✅ Complete methodology documented

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| Datasets too large | Use sparse matrices, parallel processing |
| No common motifs found | Relax functional constraints, try smaller motifs |
| Expansion too slow | Implement better heuristics, early termination |
| Solution too small | Try more seed motifs, different dataset combinations |
| API rate limits | Cache metadata, batch requests |
| Memory constraints | Process datasets sequentially, use disk caching |

## Next Steps

Once you've downloaded the data files and are ready to proceed:

1. Run `python run_optimization.py` to start the optimization
2. Monitor progress in the console output
3. Check intermediate results in `data/processed/`
4. Review final solution in `results/solution.csv`
5. Analyze results using Jupyter notebooks

The implementation is designed to be modular, testable, and scalable to handle large connectome datasets efficiently.