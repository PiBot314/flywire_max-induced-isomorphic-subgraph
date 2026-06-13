# flywirequal-find-max-isomorphic-subgraph

Find the largest isomorphic neuronal circuit shared across 3 of 5 FlyWire connectome datasets (BANC, FAFB, MANC, MAOL, MCNS).

---

## Technical Stack

| Layer | Tool |
|---|---|
| **Graph engine** | `igraph` (C-backed Python bindings) — directed graph ops, compressed pickle I/O |
| **Data handling** | `pandas` — CSV loading with explicit string dtypes to prevent 64-bit int overflow |
| **Serialization** | Compressed pickle (`.pkl` via `igraph.Read_Picklez`) for graphs; JSON for checkpoints |
| **Language** | Python 3 |
| **Algorithm paradigm** | Heuristic search (Beam Search + greedy expansion) — not exact NP-hard subgraph isomorphism |
| **Storage** | Flat CSV (degrees), JSON (checkpoints), CSV (solution output) |

```mermaid
flowchart LR
    A[Raw Edge Lists\nCSV per dataset] --> B[igraph Directed Graphs\nCompressed .pkl]
    A --> C[Degree CSVs\nin-deg / out-deg per neuron]
    C --> D[Beam Search\nIsomorphic Circuit Finder]
    D --> E[Checkpoint JSONs\nresumable state]
    E --> F[solution.csv\n3 cols x N rows]
    F --> G[verify_solution.py\nindependent validation]
```

---

## High-Level Approach

```mermaid
flowchart TD
    A[5 Connectome Graphs] --> B[Choose 1 Dataset Trio\ne.g. BANC + FAFB + MAOL]
    B --> C[Rank all neurons in G1 by total degree\nPick seeds from rank 1-500]
    C --> D[For each seed n1 in G1:\nFind degree-compatible n2 in G2\nand n3 in G3 with 20pct tolerance]
    D --> E[Form Seed Triplet: n1 n2 n3]
    E --> F[Beam Search width=10]

    subgraph BS[Beam Search Loop]
        F --> G[Expand frontier:\ncollect neighbors of all mapped nodes]
        G --> H[Score neighbor triplets\nby combined global degree]
        H --> I{Edge structure matches\nacross all 3 graphs?}
        I -- Yes --> J[Add triplet to mapping\nKeep top-K beam states]
        I -- No --> K[Discard]
        J --> L{Beam stalled\n3 iterations?}
        L -- No --> G
        L -- Yes --> M[Return best mapping]
    end

    M --> N{Better than\nglobal best?}
    N -- Yes --> O[Save checkpoint JSON]
    N -- No --> P[Try next seed]
    O --> P
    P --> Q{All seeds\nexhausted?}
    Q -- No --> D
    Q -- Yes --> R[Export solution.csv]
    R --> S[verify_solution.py:\nrebuild subgraphs\ncheck isomorphism\ncheck weak connectivity]
```

---

## Approach Flow (Detailed Phases)

```mermaid
flowchart TD
    A[Problem: Find Largest Isomorphic Circuit\nacross 3 of 5 Connectome Datasets] --> B

    subgraph P1[Phase 1 - Data Loading]
        B[Load 5 Graphs: BANC, FAFB, MANC, MAOL, MCNS]
        B --> C[Parse as Unweighted Directed Graphs]
        C --> D[Pre-compute In/Out Degree per Neuron]
    end

    subgraph P2[Phase 2 - Dataset Selection]
        E[Choose a Priority Trio e.g. BANC+FAFB+MAOL]
        E --> F[Load G1, G2, G3 and their Degree Dicts]
    end

    subgraph P3[Phase 3 - Seed Selection]
        G[Rank Neurons by Total Degree - indices 1-500]
        G --> H[Pick Top-Degree Neuron from G1 as Anchor]
        H --> I[Find Degree-Compatible Candidates in G2 and G3\nwith 20 percent tolerance]
        I --> J[Form Seed Triplet: n1, n2, n3]
    end

    subgraph P4[Phase 4 - Beam Search Expansion]
        K[Init Beam with Seed Mapping]
        K --> L[Collect Neighbors of All Mapped Nodes]
        L --> M[Score Candidate Triplets by Combined Degree]
        M --> N{Can Add to Mapping?\nEdge structure matches\nacross all 3 graphs?}
        N -- Yes --> O[Add Triplet, Keep Top-K Beam States]
        N -- No --> P[Discard Triplet]
        O --> Q{Stalled 3 iterations?}
        Q -- No --> L
        Q -- Yes --> R[Return Best Mapping from Beam]
    end

    subgraph P5[Phase 5 - Results]
        S[Compare vs Global Best Size]
        S --> T{New Best?}
        T -- Yes --> U[Save Checkpoint JSON]
        T -- No --> V[Try Next Seed]
        U --> V
        V --> W{All Seeds Done?}
        W -- No --> G
        W -- Yes --> X[Export solution.csv\n3 columns x N rows]
    end

    subgraph P6[Phase 6 - Verification]
        Y[Rebuild Induced Subgraphs\nConfirm Isomorphism\nCheck Weak Connectivity]
    end

    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> P6
```

## Key Design Decisions

| Phase | Key Idea |
|---|---|
| **Seed Selection** | Start from high-degree neurons — structural hubs are more likely to appear across datasets |
| **Degree Tolerance** | ±20% variance allowed to accommodate biological noise in real connectomes |
| **Beam Search** | Tracks K=10 parallel mappings simultaneously to escape greedy dead-ends |
| **Isomorphism Check** | Verifies every pairwise edge direction matches across all 3 graphs before accepting a node |
| **Connectivity** | Final circuit must be weakly connected (beyond pure isomorphism) |

---

## Key Assumptions

1. **Degree as a proxy for structural equivalence** — neurons with similar total degree (±20%) are treated as plausible matches. Assumes hub neurons play equivalent roles across species/datasets.
2. **Hub-adjacent seeds are more productive** — seeds are drawn from rank 1–500, not top-1. The very highest-degree neurons are assumed to be outlier super-hubs unlikely to have exact structural counterparts elsewhere.
3. **Locally connected growth is sufficient** — expansion only considers neighbors of already-mapped nodes. Assumes the target circuit is locally cohesive, not scattered.
4. **Stalling = convergence** — 3 consecutive iterations with no beam improvement is treated as the search having exhausted useful expansions. May terminate early on sparse graphs.
5. **One trio at a time** — only one dataset combination is actively searched per run (currently BANC+FAFB+MAOL). Other combinations are explored in separate runs.
6. **Edge weights carry no structural information** — synapse counts are discarded; only binary edge presence is used, as required by the challenge.

```mermaid
flowchart LR
    subgraph Assumptions
        A1[Degree similarity\nproxies structural role]
        A2[Hub-adjacent seeds\nrank 1-500]
        A3[Circuits are\nlocally cohesive]
        A4[Stall after 3 iters\nmeans convergence]
        A5[One trio\nper run]
        A6[Ignore edge\nweights]
    end
    A1 & A2 --> S[Seed Triplet Formation]
    A3 & A4 --> BS[Beam Search]
    A5 --> R[Run Configuration]
    A6 --> G[Graph Representation]
```

---

## Solution Strengths vs. Challenge Requirements

### Correctness of Formulation
- **Unweighted directed graphs** — edge weights (synapse counts) are explicitly ignored; only edge existence and direction are used, exactly as required.
- **Strict induced subgraph isomorphism** — `can_add_to_mapping()` checks every pairwise directed edge in both directions before accepting a new node.
- **Directionality preserved** — both `A→B` and `B→A` are checked independently for every pair.
- **Weak connectivity enforced** — `verify_solution.py` explicitly builds the circuit graph and checks it is weakly connected.

### Methodological Rigor
- **Independent verifier** — `verify_solution.py` is a fully separate script that reloads graphs from scratch and re-validates end-to-end, guarding against self-confirming bugs.
- **Biological noise tolerance** — the ±20% degree tolerance is a principled, documented design choice reflecting real connectome variance.
- **No same-region assumption** — neuron matching is purely structural, in line with the explicit challenge clarification.
- **Checkpoint/resume system** — progress is persisted to JSON after every improvement, enabling reproducible restarts.

### Search Quality
- **Beam search over greedy** — K=10 parallel mappings avoids permanent entrapment at locally optimal but globally suboptimal nodes.
- **Hub-first seeding** — biases discovery toward structurally rich, well-connected circuits.
- **Degree-sorted candidate expansion** — neighbor triplets ranked by combined global degree before isomorphism checking.

---

## Things to Make It Better

```mermaid
flowchart TD
    subgraph Algorithm
        I1[Replace beam search with\nVF2/VF3 exact isomorphism\nigraph.get_subisomorphisms_vf2]
        I2[Increase stall threshold\nfrom 3 to 10-20 iterations]
        I3[Add local search / hill-climbing\nto swap individual node assignments]
    end

    subgraph Coverage
        I4[Search all 10 dataset trios\nC-5-3 in parallel]
        I5[Extend seed range\nbeyond indices 1-500]
    end

    subgraph Efficiency
        I6[Parallelize seed evaluation\nacross CPU cores via multiprocessing]
        I7[Use in-deg / out-deg tuple fingerprint\nas tighter pre-filter before edge checks]
    end

    subgraph Quality
        I8[Use cell-type annotations\nas soft matching prior]
        I9[Richer beam diversity metric\nbeyond frozenset deduplication]
    end
```

| Area | Improvement |
|---|---|
| **Algorithm** | Replace heuristic beam search with VF2/VF3 exact subgraph isomorphism (`igraph.get_subisomorphisms_vf2()`) for provably optimal results |
| **Seed strategy** | Try all 10 possible dataset trios C(5,3) — the best circuit may be in a combination not yet searched |
| **Candidate filtering** | Use (in-degree, out-degree) tuple fingerprints as a tighter pre-filter, cutting the 15×15×15 triplet space significantly |
| **Stall detection** | Increase stall threshold from 3 to 10–20, or add backtracking to recover from dead-ends |
| **Beam diversity** | Current deduplication by `frozenset(mapping.values())` collapses different paths — use a richer diversity metric |
| **Parallelism** | Seed evaluation is embarrassingly parallel — distribute across CPU cores with `multiprocessing.Pool` |
| **Biological priors** | Incorporate cell-type annotations as a soft filter — same cell class neurons are more likely true correspondences |
| **Post-processing** | After finding best mapping, attempt per-node swaps (local search) to escape the first locally optimal assignment |
