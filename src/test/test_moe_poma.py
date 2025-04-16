#!/usr/bin/env python3
import os
import glob
import subprocess
import argparse
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(
        description="Run price manipulation detection on each JSON file under output/poma/actiontree/ and report progress."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose output showing transaction hash for each detected price manipulation."
    )
    args = parser.parse_args()
    verbose = args.verbose

    # Folder containing JSON action tree files.
    json_dir = "/mnt/bigdata/txnanalyzer/output/poma/actiontree/"
    pattern = os.path.join(json_dir, "*.json")
    json_files = glob.glob(pattern)
    total_files = len(json_files)

    # Counters for statistics.
    detected_count = 0
    nondetected_count = 0
    error_count = 0

    print(f"Processing {total_files} JSON files in '{json_dir}'...")

    # Process each file with a progress bar.
    for json_file in tqdm(json_files, desc="Processing files", unit="file"):
        cmd = ["python", "src/moe/poma.py", "--input-file", json_file]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True)
            stdout = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"\nError processing file {json_file}: {e}")
            error_count += 1
            continue

        if "Price Manipulation detected!" in stdout:
            detected_count += 1
            if verbose:
                # Assuming the transaction hash is the filename without its extension.
                tx_hash = os.path.splitext(os.path.basename(json_file))[0]
                print(
                    f"\nPrice manipulation detected in transaction: {tx_hash}")
        elif "No price manipulation detected." in stdout:
            nondetected_count += 1
        else:
            error_count += 1

    # Print summary statistics.
    print("\n=== Processing Completed ===")
    print(f"Total JSON files processed: {total_files}")
    print(f"  - Price manipulation detected: {detected_count}")
    print(f"  - No price manipulation detected: {nondetected_count}")
    print(f"  - Errors encountered: {error_count}")


if __name__ == "__main__":
    main()
