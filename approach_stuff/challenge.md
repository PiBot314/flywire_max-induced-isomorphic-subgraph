This exercise is designed to evaluate your 
    - technical skills and research ability, 
    - ability to independently approach open-ended scientific problems. 
    
Please note that certain aspects of this assignment are intentionally left unspecified; you will be evaluated on your ability to make reasonable assumptions, and clearly communicate your approach. 

Final selection will be based on both prior qualifications and challenge performance.

# The Qualification Challenge

The FlyWire Codex currently contains five connectomic datasets. Your task is to identify the largest neuronal circuit shared across at least three of these datasets.

For the purposes of this challenge, a circuit is defined as a directed induced subgraph. More formally, your objective is to identify a set of N neurons present in three of the five datasets such that the induced directed subgraphs formed by those neurons are mutually isomorphic (i.e. identical).

The underlying connectomes are weighted by synapse count; however, for simplicity edge weights should be ignored. All analyses should be performed on the corresponding unweighted directed graphs provided below as edge lists:

  • BANC edge list

  • FAFB edge list 

  • MANC edge list 

  • MAOL edge list 

  • MCNS edge list 

# Deliverables
Solution File

Submit a CSV file containing:
    Three columns, corresponding to the selected datasets.
    N rows, corresponding to matched neurons across datasets.

Each row should contain the neuron identifiers that participate in the identified correspondence.

# Optimization Objective

Maximize N, subject to the following constraints:
    The induced directed connectivity structure must be identical across all three datasets.
    If an edge exists between two matched neurons in one dataset, the corresponding edge must exist in the others.
    Edge directionality must be preserved.
    In other words, the correspondence must define mutually isomorphic directed induced subgraphs.

# Research Component

Once you have identified the shared circuit, utilize the metadata available in Codex (cell types, neurotransmitters, annotations, literature references, etc.) to investigate its biological significance in one of the chosen datasets.

Select one of the three datasets and prepare a concise scientific summary (maximum one page) addressing the following:

    Visualization of the identified circuit as a network graph.

    Visualization of the constituent neurons using Codex 3D meshes.

    Observations, interpretation or biological hypothesis regarding the circuit.

    Relevant literature and citations.


The document may be formatted as a short report, research note, or scientific poster.

Submission by June 12, 11:59 PM EST:

# Additional Information
Connectivity Requirement: The discovered isomorphic structures must be weakly connected.

Brain Region Clarification: There is no requirement that matched neurons come from the same brain regions across the 3 datasets, as this information was not provided in the data.

