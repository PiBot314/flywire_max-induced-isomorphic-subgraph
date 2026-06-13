# FLYWIRE CHALLENGE

> [!WARNING]
> *Work in progress:* The final algorithm did not converge on a large-scale isomorphic circuit within the available runtime. The analysis and results presented here are based on a 5-node circuit obtained during an earlier validation run. Given the limited sample size, definitive biological conclusions are constrained and representative only.

## Find largest induced isomorphic subgraph between 3 of the 5 datasets
Induced Isomorphic Subgraph is the set of vertices and edges that form the same structure between the vertices and edges included, they need not form an exact match to the next set in terms of in degree and out degree.

## FINAL METHODOLOGY

### 1) Recieve and Process Data
Download data, recieved as 5 datasets of csv format source_id, dest_id.

Converted data to useable format -> igraph graphs, csv containing neuron data (in-degree, out-degree and id)

Remove autapses (self loops)

Validated Data structure and formatting for future steps

### 2) Dataset Selection and Load
Select 3 datasets to find maximum size induced subgraph for.
Loading their graphs and in/out degree attributes

### 3) Seed Selection
Identified best candidate to start from priority given to high degree targets and ... [TODO]

### 3) 

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
        G[Rank Neurons by Total Degree - indices 500-1000]
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



[TODO] Technical decisions (why igraph? possibility of parallelisation? checkpoint formation?)
