#!/usr/bin/env python3
import os
import json
import argparse
from glob import glob
from tqdm import tqdm
import sys
import logging

# Configure logging to file "log.log"
logging.basicConfig(
    filename="log.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Add the parent directory's "system" folder to the path so we can import poma.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'system'))

from poma import traverse_tree, adjust_embeddings, detect_poma

def reset_poma_globals():
    """
    Reset the globals used in poma.py by modifying the globals() dict of one of its functions.
    This avoids directly importing the global variables.
    """
    globals_map = traverse_tree.__globals__
    globals_map['order_counter'] = 1
    globals_map['embedding_cache'] = {}

def process_file(file_path, ignore_static_delegate=False, verbose=False):
    """
    Process a single JSON file:
      - Loads the JSON file.
      - Retrieves the transaction hash (if present) from the JSON.
      - Resets the globals (order_counter and embedding_cache) used by the poma functions.
      - Traverses the tree, adjusts embeddings, and detects price manipulation (POMA) patterns.
      - If verbose mode is enabled, prints the valid POMA triples.
    Returns a tuple (poma_triples, tx_hash):
      - poma_triples: the valid triples found (or None if none found)
      - tx_hash: transaction hash from the JSON (or "N/A" if not present)
    """
    with open(file_path, "r") as f:
        tree = json.load(f)
    # Assume the transaction hash is stored under "tx_hash" in the JSON.
    tx_hash = tree.get("tx_hash", "N/A")
    
    # Reset globals for this file's processing.
    reset_poma_globals()

    calls = []
    traverse_tree(tree, depth=1, calls=calls, ignore_static_delegate=ignore_static_delegate)
    adjust_embeddings(calls)
    detected, poma_triples = detect_poma(calls)
    
    if verbose:
        if detected and poma_triples:
            print(f"File: {file_path} - Valid POMA triples found:")
            for idx, (a, b, c) in enumerate(poma_triples, start=1):
                print(f"  Triple {idx}:")
                print(f"    Swap-like Call A: order {a['order']}, depth {a['depth']}, sender '{a['sender']}', receiver '{a['receiver']}', function '{a['function']}'")
                print(f"    Swap-like Call B: order {b['order']}, depth {b['depth']}, sender '{b['sender']}', receiver '{b['receiver']}', function '{b['function']}'")
                print(f"    Ether_transfer-like Call C: order {c['order']}, depth {c['depth']}, sender '{c['sender']}', receiver '{c['receiver']}', function '{c['function']}'")
                print("")
        else:
            print(f"File: {file_path} - No valid POMA triples found.")
    return (poma_triples if detected else None), tx_hash

def main():
    parser = argparse.ArgumentParser(
        description="Batch process JSON files to detect Price Manipulation (POMA) patterns using functions from poma.py. "
                    "The FastText model is loaded only once and reused for every file."
    )
    parser.add_argument("--input-path", required=True, help="Folder path containing JSON files to process")
    parser.add_argument("--ignore-static-delegate", action="store_true",
                        help="Ignore nodes with 'staticcall' or 'delegatecall' during traversal.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print valid POMA triples for each file.")
    args = parser.parse_args()

    file_paths = glob(os.path.join(args.input_path, "*.json"))
    total_files = len(file_paths)
    poma_detected_count = 0
    no_poma_count = 0
    error_count = 0
    no_poma_tx_hashes = []  # Collect transaction hashes for which no POMA was found

    for file_path in tqdm(file_paths, desc="Processing JSON files", unit="file"):
        try:
            valid_triples, tx_hash = process_file(file_path, ignore_static_delegate=args.ignore_static_delegate, verbose=args.verbose)
            if valid_triples:
                poma_detected_count += 1
            else:
                no_poma_count += 1
                no_poma_tx_hashes.append(file_path)
        except Exception as e:
            error_count += 1
            logging.error("Error processing file %s: %s", file_path, str(e))

    print("\n=== Processing Completed ===")
    print(f"Total JSON files processed: {total_files}")
    print(f"  - POMA detected: {poma_detected_count}")
    print(f"  - No POMA found: {no_poma_count}")
    print(f"  - Errors encountered: {error_count}")

    # Log all no POMA found transaction hashes to log.log
    if no_poma_tx_hashes:
        logging.info("Transactions with no POMA detected:")
        for tx in no_poma_tx_hashes:
            logging.info("  Transaction hash: %s", tx)

if __name__ == "__main__":
    main()