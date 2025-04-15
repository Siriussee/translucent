import os
import csv
import json
import time

# Input file and output directory configuration
INPUT_FILE = 'reentrancy_raw_input_bigquery.csv'
OUTPUT_DIR = 'trace_reentrancy'

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Start the processing timer
start_time = time.time()

# Dictionary to hold call traces grouped by transaction hash
traces_by_transaction = {}

# Counter for total processed traces
total_traces = 0

# Open the CSV file and use csv.DictReader to process row by row
with open(INPUT_FILE, 'r', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Extract the transaction hash; skip row if not present
        tx_hash = row.get('transaction_hash')
        if not tx_hash:
            continue

        # Initialize list for this transaction if needed and add the row record
        if tx_hash not in traces_by_transaction:
            traces_by_transaction[tx_hash] = []
        # Append the current row to the list for the corresponding transaction
        traces_by_transaction[tx_hash].append(row)
        total_traces += 1

# Total number of unique transactions processed
total_transactions = len(traces_by_transaction)

# Write each transaction's grouped call traces to an individual JSON file
# The output is pretty printed with indent=2
for tx_hash, call_traces in traces_by_transaction.items():
    output_file = os.path.join(OUTPUT_DIR, f'{tx_hash}.json')
    with open(output_file, 'w') as outfile:
        json.dump(call_traces, outfile, indent=2)

# Calculate total processing time and the average number of traces per transaction
processing_time = time.time() - start_time
average_traces = total_traces / total_transactions if total_transactions else 0

# Print out basic processing statistics
print("----- Processing Statistics -----")
print(f"Total processed traces      : {total_traces}")
print(f"Total processed transactions: {total_transactions}")
print(f"Average traces per transaction: {average_traces:.2f}")
print(f"Total processing time       : {processing_time:.2f} seconds")