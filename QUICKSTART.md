"""
QUICK START GUIDE - ISOMORPHIC CIRCUIT FINDER
==============================================

What's been created:
---------------------

1. isomorphic_circuit_finder.py (MAIN ALGORITHM)
   - Core algorithm with seed-based expansion
   - Highest-degree node selection strategy
   - Isomorphism verification for 3 datasets
   - Checkpointing for fault tolerance
   - Comprehensive result saving

2. motif_matcher.py (UTILITIES)
   - Motif structure analysis
   - Cross-dataset motif matching
   - Degree pattern matching

3. validate_setup.py (VALIDATION)
   - Check all data files exist
   - Test data loading
   - Verify setup before running

4. ALGORITHM_USAGE.md (DOCUMENTATION)
   - Detailed algorithm explanation
   - Design decisions
   - Troubleshooting guide

Setup Requirements
-------------------

Data files (already present):
✓ /processed/graph/*.pkl              - iGraph graphs
✓ /processed/degrees/*.csv            - Neuron degree info
✓ /data/neuron_properties/motifs_3neuron/*.csv - Seed motifs

Python packages needed:
  - pandas
  - igraph
  - pickle (built-in)

Verify with:
  python validate_setup.py

Running the Algorithm
---------------------

Step 1: Validate data
  cd /Users/arnav/agcode/flywire/qual_challenge
  python validate_setup.py

  Expected output:
    ✓ All required files exist
    ✓ Data loads successfully
    ✓ Seed motifs found
    ✓ VALIDATION PASSED

Step 2: Run full algorithm
  python isomorphic_circuit_finder.py

  Expected output:
    - Progress updates every 10% of seeds
    - Best solutions found so far
    - Statistics at completion
    - Files saved to /results/

Expected Runtime
-----------------

- Data loading: ~30-60 seconds
- Seed matching: ~5-30 seconds per dataset trio
- Expansion: ~5-30 minutes depending on solution size
- Total: 30 minutes to 2 hours

Output Files
-----------

Created in /results/:

1. solution.csv
   Format: node_id, Dataset1_NeuronID, Dataset2_NeuronID, Dataset3_NeuronID
   Example:
     node_id,MANC,MAOL,MCNS
     0,720575940000000001,720575940111111111,720575940222222222
     1,720575940000000002,720575940111111112,720575940222222223
     ...

2. summary.json
   Contains:
   - Best solution statistics
   - Neuron count and edge count
   - Seed motif type used
   - All alternative solutions found

3. checkpoints/
   - Partial results for recovery
   - Can resume from checkpoint if interrupted

Interpreting Results
---------------------

From solution.csv:
- Each row is a neuron in the circuit
- node_id is just an index (0, 1, 2, ...)
- The 3 columns are the matching neuron IDs in each dataset
- All 3 neuron IDs have identical connectivity patterns

From summary.json:
- "neuron_count": N = size of the circuit (goal: maximize this)
- "edge_count": number of connections within the circuit
- "datasets": which 3 datasets were used
- "seed_type": type of initial 3-node motif (SC, BR, FL, etc.)

Example interpretation:
  If N = 47 neurons with 156 edges
  This is a 47-node circuit that exists identically in 3 datasets
  Each neuron in dataset A connects to other circuit neurons
  The exact same connections exist in datasets B and C

Next Steps After Running
------------------------

1. Verify Solution
   - Check that all 3 columns have different neuron IDs
   - Verify neuron IDs are within valid range for each dataset
   - Count rows = neuron_count in summary

2. Analyze Biologically
   - Use FlyWire Codex to look up cell types
   - Visualize circuit in 3D
   - Compare cell types across datasets
   - Write scientific summary (as per challenge)

3. Optimize Further (Optional)
   - Modify PRIORITY_TRIOS to try different dataset combinations
   - Adjust expansion parameters
   - Try different seed motif types

Challenge Deliverables
-----------------------

Your solution.csv file answers the main challenge question:
  ✓ Set of N neurons in 3 datasets
  ✓ Induced directed subgraphs are isomorphic
  ✓ Edge directionality preserved
  ✓ Maximizes N

Additional requirement (from challenge.md):
  - Choose one dataset from your 3
  - Write biological significance summary (max 1 page)
  - Use Codex metadata (cell types, etc.)
  - Include literature references

Common Issues & Solutions
--------------------------

Issue: "No motifs loaded"
  Solution: Check motif CSV files in
    /data/neuron_properties/motifs_3neuron/
  They should be named: manc_motif.csv, maol_motif.csv, etc.

Issue: "Memory error"
  Solution: The algorithm loads one trio at a time
  If still getting errors, check available RAM
  May need to process on high-memory machine

Issue: "Very slow expansion"
  Solution: This usually means finding a large circuit (good!)
  Can reduce max_iterations in expand_from_seed()
  Or set timeout limit

Issue: "Small solution (N < 10)"
  Solution: This is valid but try:
    1. Different dataset combinations
    2. Different seed motif types
    3. Ensure seed motifs were loaded correctly

Running on Different Dataset Combinations
------------------------------------------

To test different combinations, edit isomorphic_circuit_finder.py:

PRIORITY_TRIOS = [
    (3, 4, 5),  # MANC, MAOL, MCNS
    (2, 3, 4),  # FAFB, MANC, MAOL
    (1, 2, 3),  # BANC, FAFB, MANC
    # Add more combinations here
]

Dataset indices:
  1 = BANC
  2 = FAFB
  3 = MANC
  4 = MAOL
  5 = MCNS

Performance Tuning
------------------

To run faster:
  1. Reduce CHECKPOINT_INTERVAL (saves less often)
  2. Reduce max_iterations in expand_from_seed
  3. Process only one dataset trio at a time

To find better solutions:
  1. Increase max_iterations
  2. Try more dataset combinations
  3. Increase attempts per seed
  4. Modify find_highest_degree_candidates() to be less greedy

Contact & Support
-----------------

Algorithm design based on:
  - Maximum Common Induced Subgraph (MCIS) problem
  - Highest-degree heuristic for MCIS approximation
  - FlyWire connectome challenge specifications

For questions about:
  - Algorithm design: see ALGORITHM_USAGE.md
  - Data loading: see validate_setup.py
  - Troubleshooting: see ALGORITHM_USAGE.md -> Troubleshooting

SUCCESS CRITERIA
----------------

Your solution is successful when:
  ✓ solution.csv has 3 columns (one per dataset)
  ✓ N > 3 (found circuit larger than seed)
  ✓ No duplicate neuron IDs in same row
  ✓ Neuron IDs are valid for each dataset
  ✓ All rows have consistent structure
  ✓ summary.json shows valid statistics

GOOD LUCK! 🧠
"""


if __name__ == "__main__":
    print(__doc__)
    print("\nTo start: python validate_setup.py")
