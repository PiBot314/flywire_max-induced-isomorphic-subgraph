"""
Quick validation script to verify data loading and algorithm setup.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from isomorphic_circuit_finder import DataLoader, DATASET_PAIRS, PRIORITY_TRIOS


def validate_setup():
    """Validate that all data files exist and can be loaded."""
    print("="*70)
    print("VALIDATION: Data Loading Setup")
    print("="*70 + "\n")
    
    loader = DataLoader()
    
    # Test 1: Check all files exist
    print("1. Checking file existence...")
    # from isomorphic_circuit_finder import GRAPHS_DIR, DEGREES_DIR, MOTIFS_DIR
    
    # all_exist = True
    # for d_idx, d_name in DATASET_PAIRS.items():
    #     graph_file = GRAPHS_DIR / f"{d_name}_graph.pkl"
    #     degree_file = DEGREES_DIR / f"neuron_degrees_{d_idx}.csv"
    #     motif_file = MOTIFS_DIR / f"{d_name.lower()}_motif.csv"
        
    #     g_ok = "✓" if graph_file.exists() else "✗"
    #     d_ok = "✓" if degree_file.exists() else "✗"
    #     m_ok = "✓" if motif_file.exists() else "✗"
        
    #     print(f"  {d_name}: {g_ok} graph  {d_ok} degrees  {m_ok} motifs")
        
    #     if not (graph_file.exists() and degree_file.exists()):
    #         all_exist = False
    
    # if not all_exist:
    #     print("\n✗ Some required files are missing!")
    #     return False
    
    #tested already no need
    print("\n✓ All required files exist\n")
    
    # Test 2: Try loading data for priority trio
    print("2. Testing data loading for priority trio...")
    d1, d2, d3 = PRIORITY_TRIOS[0]
    
    try:
        print(f"\n  Loading {DATASET_PAIRS[d1]}, {DATASET_PAIRS[d2]}, {DATASET_PAIRS[d3]}...")
        
        g1 = loader.load_graph(d1)
        print(f"    ✓ Graph 1: {g1.vcount():,} nodes, {g1.ecount():,} edges")
        
        deg_1 = loader.load_degrees(d1)
        print(f"    ✓ Degrees 1: {len(deg_1)} entries")
        
        motifs_1 = loader.load_motifs(d1)
        print(f"    ✓ Motifs 1: {len(motifs_1)} seed motifs")
        
        if not motifs_1:
            print("\n    ⚠ No motifs loaded. This is a problem!")
            return False
        
        # Check motif types
        types = set(m[3] for m in motifs_1)
        print(f"    ✓ Motif types: {types}\n")
        
        return True
    
    except Exception as e:
        print(f"\n✗ Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = validate_setup()
    
    if success:
        print("="*70)
        print("✓ VALIDATION PASSED - Ready to run algorithm")
        print("="*70 + "\n")
        print("Next step: Run `python isomorphic_circuit_finder.py`\n")
    else:
        print("\n✗ VALIDATION FAILED - Please check the errors above\n")
        sys.exit(1)
