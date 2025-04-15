import os
import json
import time

# Configuration for input and output paths
INPUT_FILE = 'poma_raw_input_bigquery.jsonl'
OUTPUT_DIR = 'trace_poma'

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Start timing the processing
start_time = time.time()

# Dictionary to collect call traces per transaction
traces_by_transaction = {}

# Counter for total processed traces
total_traces = 0

# Process the big jsonl file line by line for memory efficiency
with open(INPUT_FILE, 'r') as infile:
    for line in infile:
        # Clean and skip empty lines
        line = line.strip()
        if not line:
            continue

        try:
            # Parse the JSON line
            record = json.loads(line)
        except json.JSONDecodeError:
            # If the record cannot be parsed, skip it
            continue

        # Get the transaction hash; skip the record if missing
        tx_hash = record.get('transaction_hash')
        if not tx_hash:
            continue

        # Initialize list for this transaction if necessary and append record
        if tx_hash not in traces_by_transaction:
            traces_by_transaction[tx_hash] = []
        traces_by_transaction[tx_hash].append(record)
        total_traces += 1

# Total number of unique transactions processed
total_transactions = len(traces_by_transaction)

# Write individual JSON files in pretty print format (indentation = 2 spaces)
for tx_hash, call_traces in traces_by_transaction.items():
    output_filename = os.path.join(OUTPUT_DIR, f'{tx_hash}.json')
    with open(output_filename, 'w') as outfile:
        json.dump(call_traces, outfile, indent=2)

# Calculate processing time and average number of traces per transaction
processing_time = time.time() - start_time
average_traces = total_traces / total_transactions if total_transactions else 0

# Print basic stats
print("----- Processing Statistics -----")
print(f"Total processed traces     : {total_traces}")
print(f"Total processed transactions: {total_transactions}")
print(f"Average traces per transaction: {average_traces:.2f}")
print(f"Total processing time        : {processing_time:.2f} seconds")