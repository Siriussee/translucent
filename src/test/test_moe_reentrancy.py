#!/usr/bin/env python3
import os
import glob
import subprocess
import argparse
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(
        description="Run reentrancy detection on each JSON file under output/reentrancy/actiontree/ and report progress."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output showing transaction hash for each detected reentrancy."
    )
    args = parser.parse_args()
    verbose = args.verbose

    # Path to JSON files directory.
    json_dir = "/mnt/bigdata/txnanalyzer/output/reentrancy/actiontree/"
    pattern = os.path.join(json_dir, "*.json")
    json_files = glob.glob(pattern)
    total_files = len(json_files)

    # Counters for statistics.
    reentrancy_detected_count = 0
    no_reentrancy_count = 0
    error_count = 0

    print(f"Processing {total_files} JSON files in '{json_dir}'...")

    # Iterate over JSON files with a progress bar.
    for json_file in tqdm(json_files, desc="Processing files", unit="file"):
        cmd = ["python", "src/moe/reentrancy.py", "--input-file", json_file]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True)
            stdout = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"\nError processing file {json_file}: {e}")
            error_count += 1
            continue

        # Check the output from the detection script.
        if "Reentrancy detected!" in stdout:
            reentrancy_detected_count += 1
            if verbose:
                # Assuming that the transaction hash is the filename without extension.
                tx_hash = os.path.splitext(os.path.basename(json_file))[0]
                print(f"\nReentrancy detected in transaction: {tx_hash}")
        elif "No reentrancy detected." in stdout:
            no_reentrancy_count += 1
        else:
            error_count += 1

    # Print the statistics summary.
    print("\n=== Processing Completed ===")
    print(f"Total JSON files processed: {total_files}")
    print(f"  - Reentrancy detected: {reentrancy_detected_count}")
    print(f"  - No reentrancy found: {no_reentrancy_count}")
    print(f"  - Errors encountered: {error_count}")


if __name__ == "__main__":
    main()
