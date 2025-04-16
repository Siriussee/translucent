#!/usr/bin/env python3
import os
import argparse
import json
import requests
from tqdm import tqdm

def trace_transaction(tenderly_node_access_key, transaction_hash):
    url = f"https://mainnet.gateway.tenderly.co/{tenderly_node_access_key}" 
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "tenderly_traceTransaction",
        "params": [transaction_hash]
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error tracing transaction {transaction_hash}: {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred for transaction {transaction_hash}: {e}")
        return None

def main(tenderly_node_access_key, input_folder_path, output_folder_path):
    # Ensure output folder exists
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)
    
    # List files with .json extension in the input folder
    transaction_files = [f for f in os.listdir(input_folder_path)
                         if os.path.isfile(os.path.join(input_folder_path, f)) and f.endswith('.json')]
    
    if not transaction_files:
        print("No transaction files found in the input folder.")
        return

    # Process each file with a progress bar
    for filename in tqdm(transaction_files, desc="Processing Transactions"):
        # The transaction hash is extracted from filename "[hash].json"
        transaction_hash = os.path.splitext(filename)[0]
        
        # Read the file (if needed, e.g., validation) or simply use the file name as the hash.
        input_file_path = os.path.join(input_folder_path, filename)
        try:
            with open(input_file_path, 'r') as f:
                # Optionally, validate the JSON content if needed.
                _ = json.load(f)
        except Exception as e:
            print(f"Could not read or validate file {input_file_path}: {e}")
        
        # Trace the transaction
        trace_result = trace_transaction(tenderly_node_access_key, transaction_hash)
        if trace_result is not None:
            # Save the trace_result to the output folder as "{transaction_hash}.json"
            output_file_path = os.path.join(output_folder_path, f"{transaction_hash}.json")
            try:
                with open(output_file_path, 'w') as out_file:
                    json.dump(trace_result, out_file, indent=2)
            except Exception as e:
                print(f"Error writing file {output_file_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trace Ethereum transactions using the Tenderly API.')
    parser.add_argument('tenderly_node_access_key', type=str, help='Tenderly Node Access Key')
    parser.add_argument('input_folder_path', type=str, help='Path to the folder containing JSON files named "{transaction_hash}.json"')
    parser.add_argument('output_folder_path', type=str, help='Path to the folder where trace results will be stored')
    
    args = parser.parse_args()
    
    main(args.tenderly_node_access_key, args.input_folder_path, args.output_folder_path)