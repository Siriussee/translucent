#!/usr/bin/env python3
import os
import json
import shutil
import subprocess
import argparse
import concurrent.futures
from filelock import FileLock
from tqdm import tqdm
from hex_decoder import read_json, write_json

def main(trace_path, event_path, output_path, event_input_path, trace_mode):
    # Prepare output directories
    prepare_directories(output_path)
    initialize_counts(output_path)

    script_path = os.path.join('.', 'src', 'actiontree_local_eventless.py')

    if trace_mode == "default":
        process_default_mode(trace_path, script_path, event_path, output_path, event_input_path)
    elif trace_mode == "jsonl":
        process_jsonl_mode(trace_path, script_path, event_path, output_path, event_input_path)

def prepare_directories(output_path):
    """Create necessary directories under output_path."""
    for subdir in ['actiontree', 'orphaned', 'stats']:
        os.makedirs(os.path.join(output_path, subdir), exist_ok=True)

def initialize_counts(output_path):
    """Reset counts in specific JSON files."""
    count_files = ['ether_count.json', 'create_count.json', 'suicide_count.json']
    for fname in count_files:
        file_path = os.path.join(output_path, fname)
        reset_count_in_json(file_path)

def process_default_mode(trace_path, script_path, event_path, output_path, event_input_path):
    """Process trace files in default mode (each .json file treated individually)."""
    hash_list = read_hashes_from_trace_dir(trace_path)
    run_batch(script_path, hash_list, trace_path, event_path, output_path, event_input_path)

def process_jsonl_mode(trace_path, script_path, event_path, output_path, event_input_path):
    """
    Process trace files in JSONL mode.
    For each large JSONL file in trace_path, convert its lines into proper JSON files,
    run the processing batch, then clean up the temporary files.
    """
    temp_trace_path = os.path.join(output_path, "trace_temp")
    os.makedirs(temp_trace_path, exist_ok=True)

    # Identify jsonl files (files not ending with .json)
    jsonl_files = [f for f in os.listdir(trace_path) if not f.endswith('.json')]
    for jsonl_filename in tqdm(jsonl_files, desc="Processing jsonl files", unit="file"):
        src_file = os.path.join(trace_path, jsonl_filename)
        process_single_jsonl_file(src_file, temp_trace_path)
        hash_list = read_hashes_from_trace_dir(temp_trace_path)
        run_batch(script_path, hash_list, temp_trace_path, event_path, output_path, event_input_path)
        clean_temp_folder(temp_trace_path)

def run_batch(script_path, hash_list, trace_path, event_path, output_path, event_input_path):
    """
    Execute the given script concurrently on a batch of hash values (transactions).
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(run_script, script_path, hash_val, trace_path, event_path, output_path, event_input_path)
            for hash_val in hash_list
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Script execution failed with exception: {e}")
                # Optionally log the failed hash using write_failed_hash function.

def read_hashes_from_trace_dir(trace_dir):
    """
    Return a list of transaction hashes extracted from filenames ending with '.json'
    in the given directory.
    """
    return [os.path.splitext(filename)[0] for filename in os.listdir(trace_dir) if filename.endswith('.json')]

def process_single_jsonl_file(src_file, temp_trace_path):
    """
    Process a single JSONL file:
      - For each line, parse the JSON.
      - Convert from the original format:
          { "transaction_hash": ..., "traces": [ { "from_address": ..., ... }, ... ] }
        to the proper format where every trace gets the transaction_hash field:
          [ { "transaction_hash": ..., "from_address": ..., ... }, ... ]
      - Save the result as {transaction_hash}.json in temp_trace_path.
    A progress bar shows progress across the lines.
    """
    # Count total lines for progress bar if possible.
    total_lines = sum(1 for _ in open(src_file, 'r'))
    with open(src_file, 'r') as infile, tqdm(total=total_lines, desc=f"Processing {os.path.basename(src_file)}", unit="line") as pbar:
        for line in infile:
            line = line.strip()
            if not line:
                pbar.update(1)
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                pbar.update(1)
                continue  # skip invalid JSON

            transaction_hash = record.get("transaction_hash")
            traces = record.get("traces", [])
            if transaction_hash and traces and isinstance(traces, list):
                modified_traces = []
                for trace in traces:
                    new_trace = trace.copy()
                    new_trace["transaction_hash"] = transaction_hash
                    modified_traces.append(new_trace)
                out_file = os.path.join(temp_trace_path, f"{transaction_hash}.json")
                with open(out_file, 'w') as outfile:
                    json.dump(modified_traces, outfile, indent=4)
            pbar.update(1)

def clean_temp_folder(folder):
    """Remove all .json files in the specified folder."""
    for filename in os.listdir(folder):
        if filename.endswith('.json'):
            os.remove(os.path.join(folder, filename))

def reset_count_in_json(file_path):
    """
    Reset the 'count' field in the given JSON file to 0.
    Assumes the file exists and has a 'count' key.
    """
    data = read_json(file_path)
    data['count'] = 0
    write_json(file_path, data)

def run_script(script_path, hash_val, trace_path, event_path, output_path, event_input_path):
    """
    Build and execute the command to run the actiontree script for a given hash.
    """
    cmd = [
        'python', script_path,
        '--trace-path', trace_path,
        '--output-path', output_path,
        '--hash', hash_val
    ]
    if event_path:
        cmd.extend(['--event-path', event_path])
    if event_input_path:
        cmd.extend(['--event-input-path', event_input_path])
    subprocess.run(cmd, check=True)

def write_failed_hash(file_path, lock_path, hash_val):
    """Append a failed hash to the file in a thread-safe manner."""
    lock = FileLock(lock_path)
    with lock:
        if not os.path.exists(file_path):
            failed_hashes = []
        else:
            with open(file_path, 'r') as file:
                failed_hashes = json.load(file)
        failed_hashes.append(hash_val)
        with open(file_path, 'w') as file:
            json.dump(failed_hashes, file, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Run the actiontree script with provided trace, event, and output paths. '
                    'Use default mode for individual JSON files or jsonl mode for large JSON Lines files.'
    )
    parser.add_argument('--trace-path', required=True,
                        help='Directory containing trace JSON files or JSONL files (without extension)')
    parser.add_argument('--event-path', required=False, default='',
                        help='Path to the event (optional)')
    parser.add_argument('--output-path', required=True,
                        help='Path to the output directory')
    parser.add_argument('--event-input-path', required=False, default='',
                        help='Path to the event input files (optional)')
    parser.add_argument('--trace-mode', choices=['default', 'jsonl'], default='default',
                        help="Trace file mode: 'default' for individual .json files, 'jsonl' for large JSON Lines files.")
    args = parser.parse_args()
    main(args.trace_path, args.event_path, args.output_path, args.event_input_path, args.trace_mode)