#!/usr/bin/env python3
import os
import json
import argparse
from glob import glob
from tqdm import tqdm

import sys
# Add the parent directory's "system" folder to the path so we can import reentrancy.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'system'))

from reentrancy import traverse_tree, adjust_embeddings, detect_reentrancy

def reset_reentrancy_globals():
    """
    Reset the globals used in reentrancy.py by modifying the globals() dict of one of its functions.
    This avoids directly importing the global variables.
    """
    globals_map = traverse_tree.__globals__
    globals_map['order_counter'] = 1
    globals_map['embedding_cache'] = {}

def process_file(file_path, ignore_static_delegate=False, verbose=False):
    """
    Process a single JSON file:
      - Loads the JSON file.
      - Resets the globals (order_counter and embedding_cache) used by the reentrancy functions.
      - Traverses the tree, adjusts embeddings, and detects reentrancy.
      - If verbose mode is enabled, prints the valid reentrancy triples.
    Returns the valid triples found.
    """
    with open(file_path, "r") as f:
        tree = json.load(f)
    
    # Reset globals for this file's processing.
    reset_reentrancy_globals()

    calls = []
    traverse_tree(tree, depth=1, calls=calls, ignore_static_delegate=ignore_static_delegate)
    adjust_embeddings(calls)
    valid_triples = detect_reentrancy(calls)

    if verbose:
        if valid_triples:
            print(f"File: {file_path} - Valid reentrancy triples found:")
            for idx, (call_A, call_B, call_C, sim_ab, sim_ac) in enumerate(valid_triples, 1):
                print(f"  Triple {idx}:")
                print(f"    Call_A: order {call_A['order']}, depth {call_A['depth']}, "
                      f"sender '{call_A['sender']}', receiver '{call_A['receiver']}', function '{call_A['function']}'")
                print(f"    Call_B: order {call_B['order']}, depth {call_B['depth']}, "
                      f"sender '{call_B['sender']}', receiver '{call_B['receiver']}', function '{call_B['function']}'")
                print(f"      Similarity (A,B): {sim_ab:.4f}")
                print(f"    Call_C: order {call_C['order']}, depth {call_C['depth']}, "
                      f"sender '{call_C['sender']}', receiver '{call_C['receiver']}', function '{call_C['function']}'")
                print(f"      Similarity (A,C): {sim_ac:.4f}")
                print("")
        else:
            print(f"File: {file_path} - No valid reentrancy triples found.")
    return valid_triples

def main():
    import argparse
    from glob import glob
    from tqdm import tqdm
    import os

    parser = argparse.ArgumentParser(
        description="Batch process JSON files to detect reentrancy patterns using functions from reentrancy.py. "
                    "The FastText model is loaded only once and reused for every file."
    )
    parser.add_argument("--input-path", required=True, help="Folder path containing JSON files to process")
    parser.add_argument("--ignore-static-delegate", action="store_true",
                        help="Ignore nodes with 'staticcall' or 'delegatecall' during traversal.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print valid reentrancy triples for each file.")
    args = parser.parse_args()

    file_paths = glob(os.path.join(args.input_path, "*.json"))
    total_files = len(file_paths)
    reentrancy_detected_count = 0
    no_reentrancy_count = 0
    error_count = 0

    for file_path in tqdm(file_paths, desc="Processing JSON files", unit="file"):
        try:
            valid_triples = process_file(file_path, ignore_static_delegate=args.ignore_static_delegate, verbose=args.verbose)
            if valid_triples:
                reentrancy_detected_count += 1
            else:
                no_reentrancy_count += 1
        except Exception as e:
            error_count += 1

    print("\n=== Processing Completed ===")
    print(f"Total JSON files processed: {total_files}")
    print(f"  - Reentrancy detected: {reentrancy_detected_count}")
    print(f"  - No reentrancy found: {no_reentrancy_count}")
    print(f"  - Errors encountered: {error_count}")

if __name__ == "__main__":
    main()