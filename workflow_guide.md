# FlyWire Isomorphic Circuit Analysis - Professional Workflow Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [Workflow Phases](#workflow-phases)
3. [Neuron Circuit Patterns](#neuron-circuit-patterns)
4. [Tools & Scripts](#tools--scripts)
5. [Current Status](#current-status)
6. [Next Steps](#next-steps)

---

## Overview

This document provides a comprehensive professional workflow for analyzing isomorphic neuronal circuits across FlyWire connectome datasets. The goal is to identify the largest circuit that exists identically across 3 of 5 datasets (BANC, FAFB, MANC, MAOL, MCNS).

### Challenge Requirements
- **Objective**: Find N neurons forming mutually isomorphic directed induced subgraphs
- **Constraint**: Circuit must be **weakly connected** (all neurons reachable via undirected paths)
- **Deliverable**: CSV file + 1-page scientific summary with visualizations

---

## Workflow Phases

### Phase 1: Data Loading & Preparation
**Duration**: ~30-60 minutes

**Steps**:
1. Load pre-processed graphs from pickle files (`*.pkl`)
2. Load neuron degree information (in-degree, out-degree)
3. Load 3-node seed motifs from CSV files
4. Validate data integrity

**Tools**:
- `validate_setup.py` - Pre-flight data validation
- `DataLoader` class in `isomorphic_circuit_finder.py`

**Outputs**:
- Loaded graph objects (igraph format)
- Degree dictionaries for each dataset
- Seed motif lists

---

### Phase 2: Circuit Discovery
**Duration**: 30 minutes - 2 hours

**Steps**:
1. **Seed Matching**: Find 3-node motifs with identical structure across datasets
2. **Initialize Mapping**: Start with matched triplet
3. **Beam Search Expansion**: 
   - Maintain K=10 parallel expansion paths
   - Find neighbors of current circuit
   - Filter by degree sequence matching
   - Verify isomorphism for each candidate
   - Add valid neurons to mapping
4. **Connectivity Check**: Verify weak connectivity (CRITICAL)
5. **Checkpoint**: Save progress periodically

**Algorithm**:
```python
for each seed_motif in dataset1:
    matched_seeds = find_matching_motifs(dataset2, dataset3)
    for seed_triple in matched_seeds:
        mapping = initialize_mapping(seed_triple)
        mapping = beam_search_expand(mapping, graphs, degrees)
        if is_weakly_connected(mapping) and len(mapping) > best_size:
            best_mapping = mapping
            save_checkpoint(mapping)
```

**Tools**:
- `isomorphic_circuit_finder.py` - Main algorithm
- `motif_matcher.py` - Motif utilities

**Outputs**:
- Best circuit mapping (neuron correspondences)
- Checkpoint files for recovery
- Solution CSV file

---

### Phase 3: Topology Analysis
**Duration**: 10-20 minutes

**Steps**:
1. Extract induced subgraphs for each dataset
2. Calculate network metrics:
   - Node count, edge count, density
   - Degree distributions (in/out/total)
   - Hub neuron identification
   - Motif detection (3-node patterns)
   - Reciprocal connections
   - Clustering coefficients
   - Path lengths and diameter
3. Verify weak connectivity
4. Generate statistical summary

**Tools**:
- `analyze_circuit.py` - Comprehensive topology analyzer

**Outputs**:
- `analysis/circuit_analysis.json` - Full metrics
- `analysis/{DATASET}_degrees.csv` - Degree distributions
- Statistical summary report

**Key Metrics**:
| Metric | Description | Ideal Value |
|--------|-------------|-------------|
| Nodes | Circuit size | Maximize N |
| Edges | Connections | > N (well-connected) |
| Density | Edge ratio | 0.1 - 0.5 |
| Connected | Weak connectivity | TRUE (required) |
| Components | Disconnected parts | 1 (required) |

---

### Phase 4: Visualization
**Duration**: 15-30 minutes

**Steps**:
1. Generate network graph with force-directed layout
2. Color-code nodes by degree:
   - Red: Hub neurons (degree ≥ 4)
   - Blue: Medium degree (2-3)
   - Gray: Low degree (1)
   - Light gray: Isolated (0) - should not exist!
3. Add directional arrows for edges
4. Highlight disconnected components (if any)
5. Create publication-quality figure

**Tools**:
- `visualize_circuit.py` - Network visualization

**Layout Options**:
- `spring` - Force-directed (Fruchterman-Reingold)
- `circular` - Circular arrangement
- `hierarchical` - Layered by in-degree
- `kamada_kawai` - Energy minimization

**Outputs**:
- `visualizations/{DATASET}_circuit_{layout}.png` - Network graph
- High-resolution (300 DPI) publication-ready images

---

### Phase 5: Biological Analysis
**Duration**: 2-4 hours

**Steps**:
1. **Query FlyWire Codex**:
   - Access https://codex.flywire.ai
   - Look up each neuron ID
   - Extract cell type annotations
   - Note neurotransmitter types
   - Identify brain regions
   - Check existing literature references

2. **3D Mesh Visualization**:
   - Use Neuroglancer viewer
   - Highlight circuit neurons
   - Capture multiple viewing angles
   - Save high-quality screenshots

3. **Functional Hypothesis**:
   - Analyze connectivity patterns
   - Identify circuit motifs (feedforward, feedback, reciprocal)
   - Determine sensory/motor/interneuron composition
   - Propose biological function based on:
     - Cell types involved
     - Brain region localization
     - Connectivity structure
     - Known functions of similar circuits

**Tools**:
- FlyWire Codex web interface
- Neuroglancer 3D viewer
- `fetch_metadata.py` (to be created for automation)

**Outputs**:
- `metadata/neuron_metadata.csv` - Cell types and properties
- `visualizations/circuit_3d_mesh.png` - 3D visualization
- Functional hypothesis document

---

### Phase 6: Scientific Summary
**Duration**: 2-3 hours

**Steps**:
1. **Write Summary** (max 1 page):
   - Title and abstract
   - Circuit discovery methodology
   - Network topology description
   - Biological significance
   - Functional hypothesis
   - Discussion and implications
   - References (3-5 key citations)

2. **Include Visualizations**:
   - Network graph (from Phase 4)
   - 3D mesh visualization (from Phase 5)
   - Optional: Degree distribution plots

3. **Literature Citations**:
   - FlyWire/connectome papers
   - Relevant circuit function studies
   - Cell type characterization papers
   - Methodological references

**Template Structure**:
```markdown
# Conserved N-Neuron Circuit Across Drosophila Connectomes

## Abstract
Brief overview of findings (2-3 sentences)

## Circuit Discovery
- Methodology: Beam search with isomorphism verification
- Datasets: [DATASET1], [DATASET2], [DATASET3]
- Circuit size: N neurons, E edges

## Network Topology
[Network graph visualization]
- Connectivity statistics
- Hub neurons identified
- Motif analysis results

## Biological Significance
[3D mesh visualization]
- Cell type composition
- Brain region localization
- Functional hypothesis

## Discussion
- Conservation across datasets
- Potential functional role
- Future directions

## References
1. [Citation 1]
2. [Citation 2]
...
```

**Tools**:
- Markdown editor or LaTeX
- PDF converter for final submission

**Outputs**:
- `scientific_summary.pdf` - Final deliverable

---

## Neuron Circuit Patterns

### 1. Linear Feedforward Chain
```
Sensory → Interneuron1 → Interneuron2 → Motor
```
- **Function**: Sequential information processing
- **Example**: Sensory-motor reflex pathways
- **Characteristics**: Unidirectional flow, no feedback

### 2. Reciprocal (Bidirectional) Connection
```
Neuron A ⇄ Neuron B
```
- **Function**: Mutual feedback, signal amplification
- **Example**: Local processing circuits
- **Characteristics**: Bidirectional edges, potential oscillations

### 3. Feedforward Loop
```
    Input
   ↙     ↘
  ↓       ↓
  Inter → Output
```
- **Function**: Signal integration, coincidence detection
- **Example**: Decision-making circuits
- **Characteristics**: Direct + indirect paths, temporal filtering

### 4. Hub-and-Spoke Pattern
```
      N1
       ↓
N2 → Hub ← N3
       ↑
      N4
```
- **Function**: Information integration/distribution
- **Example**: Central pattern generators
- **Characteristics**: High-degree hub, multiple connections

### 5. Feedback Loop (Recurrent)
```
A → B → C
↑       ↓
←───────
```
- **Function**: Memory, sustained activity, oscillations
- **Example**: Central pattern generators, working memory
- **Characteristics**: Cyclic structure, recurrent connections

### 6. Disconnected Pattern (INVALID)
```
[N1 → N2]    [N3]  [N4]
Connected    Isolated
```
- **Problem**: Not weakly connected
- **Status**: Violates challenge requirement
- **Action**: Must be fixed before submission

---

## Tools & Scripts

### Analysis Tools
| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `validate_setup.py` | Pre-flight checks | Data files | Validation report |
| `isomorphic_circuit_finder.py` | Main algorithm | Graphs, degrees, motifs | Circuit mapping |
| `analyze_circuit.py` | Topology analysis | Checkpoint JSON | Metrics JSON, CSVs |
| `visualize_circuit.py` | Network visualization | Checkpoint JSON | PNG images |
| `verify_solution.py` | Solution validation | Solution CSV | Pass/Fail report |

### Usage Examples

**Validate Setup**:
```bash
python validate_setup.py
```

**Run Circuit Finder**:
```bash
python isomorphic_circuit_finder.py
```

**Analyze Circuit**:
```bash
python analyze_circuit.py
```

**Visualize Network**:
```bash
python visualize_circuit.py --dataset FAFB --layout spring
python visualize_circuit.py --dataset BANC --layout circular --no-labels
```

**Verify Solution**:
```bash
python verify_solution.py results/solution.csv
```

---

## Current Status

### ✅ Completed
1. ✅ Circuit topology analysis script created
2. ✅ Network visualization script created
3. ✅ Analysis performed on checkpoint data
4. ✅ Visualizations generated
5. ✅ Critical issue identified and documented

### ⚠️ Critical Issue Found
**Problem**: Current 33-neuron "solution" is **NOT weakly connected**

**Evidence**:
- 30 disconnected components (should be 1)
- Only 5-6 edges among 33 neurons
- 27-28 isolated neurons with degree = 0
- Violates challenge requirement (challenge.md line 67)

**Impact**: Cannot proceed with scientific summary until fixed

### 🔧 Required Actions
1. **Fix Algorithm** (Recommended):
   - Modify `can_add_to_mapping()` to verify connectivity
   - Add weak connectivity check after each neuron addition
   - Re-run to find valid connected circuit

2. **Alternative**: Extract largest connected component (3-4 neurons)
   - Would be valid but very small
   - Not competitive

### 📊 Analysis Results
| Dataset | Nodes | Edges | Connected | Components |
|---------|-------|-------|-----------|------------|
| BANC    | 33    | 5     | ❌ NO     | 30         |
| FAFB    | 33    | 5     | ❌ NO     | 30         |
| MAOL    | 33    | 6     | ❌ NO     | 30         |

---

## Next Steps

### Immediate (Before Scientific Summary)
1. **Decision Point**: Choose remediation approach
   - Option A: Fix algorithm and re-run
   - Option B: Use smaller valid circuit
   - Option C: Check failed_results/ for better solutions

2. **If Fixing Algorithm**:
   - Modify connectivity checking in `isomorphic_circuit_finder.py`
   - Add `is_weakly_connected()` verification
   - Re-run circuit discovery
   - Verify new solution with `verify_solution.py`

3. **Validate New Solution**:
   - Must have 1 connected component
   - All neurons reachable via undirected paths
   - Passes `verify_solution.py` checks

### After Valid Circuit Found
4. **FlyWire Codex Integration**:
   - Query neuron metadata
   - Extract cell types and neurotransmitters
   - Capture 3D mesh visualizations

5. **Biological Analysis**:
   - Formulate functional hypothesis
   - Search relevant literature
   - Identify biological significance

6. **Scientific Summary**:
   - Write 1-page summary
   - Include visualizations
   - Add literature citations
   - Convert to PDF

7. **Final Submission**:
   - Solution CSV file
   - Scientific summary PDF
   - Submit via FlyWire portal

---

## Visualization Examples

### Network Graph Features
- **Node Size**: Proportional to degree
- **Node Color**:
  - 🔴 Red: Hub neurons (degree ≥ 4)
  - 🔵 Blue: Medium degree (2-3)
  - ⚪ Gray: Low degree (1)
  - ⚫ Light gray: Isolated (0)
- **Edges**: Directed arrows showing synaptic connections
- **Layout**: Force-directed for natural clustering
- **Warning Banner**: Displayed if not weakly connected

### 3D Mesh Visualization
- Use Neuroglancer at https://ngl.flywire.ai
- Highlight circuit neurons in distinct color
- Multiple viewing angles (dorsal, lateral, frontal)
- Include scale bar and orientation markers

---

## Success Criteria

### Valid Solution
- ✅ N > 3 (larger than seed)
- ✅ Weakly connected (1 component)
- ✅ Mutually isomorphic across 3 datasets
- ✅ Edge directionality preserved
- ✅ Passes `verify_solution.py`

### Competitive Solution
- ✅ N > 10 (decent size)
- ✅ N > 50 (good size)
- ✅ N > 100 (excellent size)

### Complete Submission
- ✅ Solution CSV with correct format
- ✅ Scientific summary (max 1 page)
- ✅ Network graph visualization
- ✅ 3D mesh visualization
- ✅ Biological hypothesis
- ✅ Literature citations (3-5)

---

## Resources

### FlyWire Links
- **Codex**: https://codex.flywire.ai
- **Neuroglancer**: https://ngl.flywire.ai
- **Documentation**: https://flywire.ai/docs

### Key Papers
- Dorkenwald et al. (2023) - FlyWire connectome
- Zheng et al. (2018) - FAFB connectome
- Schlegel et al. (2023) - MANC connectome

### Tools Documentation
- **igraph**: https://igraph.org/python/
- **NetworkX**: https://networkx.org/
- **Matplotlib**: https://matplotlib.org/

---

## Contact & Support

For questions about:
- **Algorithm**: See `ALGORITHM_USAGE.md`
- **Data**: See `validate_setup.py`
- **Troubleshooting**: See `CRITICAL_FINDINGS.md`
- **Quick Start**: See `QUICKSTART.md`

---

**Last Updated**: 2026-06-13  
**Status**: Phase 3 Complete - Awaiting Algorithm Fix  
**Next Milestone**: Valid Connected Circuit Discovery