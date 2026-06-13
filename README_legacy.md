# FlyWire Connectome Circuit Discovery - Complete Pipeline

## Overview

This pipeline discovers the largest isomorphic directed induced subgraph (circuit) shared across at least three FlyWire connectomic datasets. 

## Results

### Key Finding
**Only ONE dataset triple has overlapping neurons: (MANC, MAOL, MCNS) with 5,289 shared neurons**

All other 9 possible combinations have zero neuron overlap, dramatically simplifying the search space.

## Pipeline Architecture

### Stage 1: Data Preparation (`prepare_data.py`) ✅ COMPLETED
**Loads and normalizes all five connectome datasets**

- Loads edge lists:
  - BANC: 2,676,592 edges, 112,885 neurons
  - FAFB: 3,732,460 edges, 138,584 neurons
  - MANC: 5,305,638 edges, 23,642 neurons
  - MAOL: 6,484,936 edges, 51,669 neurons
  - MCNS: 6,239,112 edges, 165,820 neurons
  
- Creates igraph structures
- Normalizes neuron identifiers (standard FlyWire 64-bit format)
- Tracks neuron presence/absence per dataset

**Output:**
- `processed/graphs.pkl` - igraph objects (428 MB)
- `processed/presence_dict.pkl` - Neuron → dataset mappings (6.7 MB)
- `processed/datasets.pkl` - Raw edge lists (297 MB)
- `processed/presence_matrix.csv` - Neuron presence/absence matrix (9.6 MB)
- `processed/summary.txt` - Dataset statistics

### Stage 2: Candidate Filtering (`filter_candidates.py`) ✅ COMPLETED
**Prunes unlikely matches using degree signatures**

- Identifies neurons present in all datasets of each triple
- Groups neurons by degree signature (in_degree, out_degree)
- Filters candidates with matching signatures across all 3 datasets

**Key Finding:**
Only (MANC, MAOL, MCNS) has overlapping neurons; other triples eliminated.

**Output:**
- `processed/filtered_candidates.pkl` - Candidate groups per triple

### Stage 3: Circuit Discovery (`optimized_circuit_search.py`) 🔄 IN PROGRESS
**Finds largest isomorphic induced subgraphs**

**Algorithm:**
1. Identify high-degree hub neurons in shared set
2. Extract local neighborhoods with matching structure
3. Generate k-subsets of candidate neurons
4. Check isomorphism using VF2 algorithm (NetworkX)
5. Greedily grow circuits by adding compatible neurons
6. Track maximum size per dataset triple

**Current Progress:**
- ✓ Motifs of size 4: Hundreds found
- ⏳ Motifs of sizes 5-7: Currently searching

**Output:** (when complete)
- `processed/optimized_circuits.pkl` - Best circuits per size

### Stage 4: Export & Reporting (`export_results.py`) ✅ CREATED
**Converts results to required deliverable format**

**Deliverables:**
- `solution.csv` - CSV file with three columns (MANC, MAOL, MCNS) and N rows of matched neurons
- `processed/FINAL_REPORT.txt` - Comprehensive summary with methodology and findings

## File Organization

```
qual_challenge/
├── prepare_data.py                 # Load & normalize datasets
├── filter_candidates.py            # Filter by degree signature
├── optimized_circuit_search.py     # Discover isomorphic circuits
├── export_results.py               # Generate deliverables
├── run_pipeline.py                 # Orchestrate full pipeline
├── basic_thoughts.md               # This planning document
├── challenge.md                    # Original challenge description
├── data/                           # Input edge lists
│   ├── BANC_edgelist.csv
│   ├── FAFB_edgelist.csv
│   ├── MANC_edgelist.csv
│   ├── MAOL_edgelist.csv
│   └── MCNS_edgelist.csv
└── processed/                      # Output data & results
    ├── graphs.pkl                  # NetworkX graphs
    ├── presence_dict.pkl           # Neuron presence
    ├── filtered_candidates.pkl     # Candidate groups
    ├── optimized_circuits.pkl      # Circuit results (when complete)
    ├── presence_matrix.csv         # Presence/absence matrix
    ├── summary.txt                 # Dataset statistics
    └── FINAL_REPORT.txt            # Final summary report
```

## Usage

### Run Full Pipeline
```bash
python3 run_pipeline.py
```

### Run Individual Stages
```bash
# Stage 1: Prepare data
python3 prepare_data.py

# Stage 2: Filter candidates
python3 filter_candidates.py

# Stage 3: Find circuits (currently running)
python3 optimized_circuit_search.py

# Stage 4: Export results
python3 export_results.py
```

### Check Progress
```bash
# Monitor circuit search
tail -f /tmp/circuit_search.log

# Check output files
ls -lh processed/
```

## Technical Details

### Neuron ID Normalization
- FlyWire uses standardized 64-bit unsigned integer IDs
- No transformation needed; consistency checked across datasets

### Isomorphism Checking
- Uses NetworkX `DiGraphMatcher` with VF2 algorithm
- Validates:
  - Identical node count across subgraphs
  - Identical edge count across subgraphs
  - Identical connectivity structure (isomorphic)
  - Edge directionality preserved

### Data Efficiency
- Graphs loaded once and reused (avoid re-parsing)
- Presence dictionary keeps memory footprint low
- Sampling applied to candidate sets for computational efficiency
- Greedy growth limits branching factor

## Computational Requirements

- **Memory:** ~1.5 GB (graphs + caches)
- **Time:** 
  - Data preparation: ~2 minutes
  - Filtering: ~15 minutes
  - Circuit search: Ongoing (depends on motif size)
- **Storage:** ~730 MB processed data

## Expected Deliverable

**File: `solution.csv`**
```
MANC,MAOL,MCNS
720575741350274352,720575841399414563,720575941350274352
...
[N rows of matched neuron IDs]
```

Where:
- Each row contains matching neuron IDs across the three datasets
- All N neurons form isomorphic induced directed subgraphs
- N is maximized subject to isomorphism constraint

## Future Research

Once circuit identified:
- Analyze cell type composition
- Examine neurotransmitter profiles
- Review literature references in Codex
- Investigate functional significance
- Compare across male/female morphology

## Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Data preparation | ✅ Complete | 24.4M edges loaded |
| Filtering | ✅ Complete | Focus on MANC-MAOL-MCNS |
| Circuit search | 🔄 In Progress | 4-node circuits found, exploring larger |
| Export | ✅ Ready | Awaiting circuit results |
| Report | ✅ Complete | FINAL_REPORT.txt generated |

---

**Last Updated:** June 8, 2026
**Pipeline Status:** 75% Complete (circuit search ongoing)
