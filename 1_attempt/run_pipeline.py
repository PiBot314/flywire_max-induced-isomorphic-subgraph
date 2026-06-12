"""
Master orchestration script for circuit discovery pipeline.

Runs all stages:
1. Filter candidates by degree signature
2. Find maximum isomorphic circuits
3. Validate and export results
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def run_stage(script_name, description):
    """
    Run a pipeline stage as a subprocess.
    
    Args:
        script_name: name of the Python script to run
        description: human-readable description
        
    Returns:
        bool: True if successful
    """
    print("\n" + "=" * 70)
    print(description)
    print("=" * 70 + "\n")
    
    script_path = PROJECT_ROOT / script_name
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            capture_output=False,
            timeout=3600  # 1 hour timeout per stage
        )
        
        if result.returncode != 0:
            print(f"\n✗ {description} FAILED (exit code {result.returncode})")
            return False
        
        print(f"\n✓ {description} COMPLETE")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"\n✗ {description} TIMEOUT (exceeded 1 hour)")
        return False
    except Exception as e:
        print(f"\n✗ {description} ERROR: {e}")
        return False


def main():
    """Run complete circuit discovery pipeline."""
    print("\n" + "█" * 70)
    print("FLYWIRE CONNECTOME CIRCUIT DISCOVERY PIPELINE")
    print("█" * 70)
    
    stages = [
        ("filter_candidates.py", "STAGE 1: Filter Candidate Neurons"),
        ("find_circuits.py", "STAGE 2: Find Isomorphic Circuits"),
        ("validate_export.py", "STAGE 3: Validate and Export Results"),
    ]
    
    results = []
    
    for script_name, description in stages:
        success = run_stage(script_name, description)
        results.append((description, success))
        
        if not success:
            print(f"\n⚠ Pipeline halted at {description}")
            break
    
    # Print final summary
    print("\n" + "█" * 70)
    print("PIPELINE EXECUTION SUMMARY")
    print("█" * 70 + "\n")
    
    all_success = True
    for description, success in results:
        status = "✓ COMPLETE" if success else "✗ FAILED"
        print(f"{status}: {description}")
        if not success:
            all_success = False
    
    if all_success:
        print("\n✓ All stages completed successfully!")
        print(f"\nResults location: {PROJECT_ROOT}/processed/circuits/")
    else:
        print("\n✗ Pipeline did not complete successfully.")
        sys.exit(1)


if __name__ == "__main__":
    main()
