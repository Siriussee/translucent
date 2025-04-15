import os
import json
import time

# Input and output configuration
INPUT_FILE = 'uncategorized_attack_raw_input_bigquery.json'
OUTPUT_DIR = 'trace_uncategorized'

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Start timer for the processing
start_time = time.time()

# Dictionary to collect call traces per transaction
traces_by_transaction = {}

# Load the entire JSON list from the input file.
# Note: This assumes the file can fit into memory. For extremely large files,
# consider using a streaming parser like ijson.
with open(INPUT_FILE, 'r') as infile:
    data = json.load(infile)

# Total trace counter
total_traces = 0

# Process each record in the list
for record in data:
    # Get the transaction hash; skip the record if missing
    tx_hash = record.get('transaction_hash')
    if not tx_hash:
        continue

    # If the transaction hash doesn't exist in our dictionary, initialize it.
    if tx_hash not in traces_by_transaction:
        traces_by_transaction[tx_hash] = []

    # Append the current call trace to the corresponding transaction.
    traces_by_transaction[tx_hash].append(record)
    total_traces += 1

# Total number of unique transactions processed
total_transactions = len(traces_by_transaction)

# For each transaction, write the list of call traces to a separate JSON file
for tx_hash, call_traces in traces_by_transaction.items():
    output_filename = os.path.join(OUTPUT_DIR, f'{tx_hash}.json')
    with open(output_filename, 'w') as outfile:
        # Write the JSON data with pretty-print formatting (indentation = 2 spaces)
        json.dump(call_traces, outfile, indent=2)

# Calculate processing time and average number of traces per transaction
processing_time = time.time() - start_time
average_traces = total_traces / total_transactions if total_transactions else 0

# Print basic statistics about the processing
print("----- Processing Statistics -----")
print(f"Total processed traces      : {total_traces}")
print(f"Total processed transactions: {total_transactions}")
print(f"Average traces per transaction: {average_traces:.2f}")
print(f"Total processing time       : {processing_time:.2f} seconds")