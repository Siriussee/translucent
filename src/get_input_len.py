import json
import os
import argparse


def extract_values_raw_lengths(data, lengths):
    if "values_raw" in data:
        lengths.append(len(data["values_raw"]))

    if "nodes" in data:
        for node in data["nodes"]:
            extract_values_raw_lengths(node, lengths)

       

def read_hashes_from_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        
    hash_list = [item['transaction_hash'] for item in data]
    
    return hash_list

def main(actiontree_path, hash_path, output_path):
    result_path = f'{output_path}/length'
    os.makedirs(result_path, exist_ok=True)
    
    hash_list = read_hashes_from_json(hash_path)
    
    for hash in hash_list:
        file_path = f'{actiontree_path}/{hash}.json'
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        lengths = []
        extract_values_raw_lengths(data, lengths)
        
        average_length = sum(lengths) / len(lengths) if lengths else 0
    
        result = {
            "length_array": lengths,
            "total_nodes": len(lengths),
            "average_length": average_length
        }
        
        output_file = f'{result_path}/{hash}.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=4)

    
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get the avg length of function inputs')
    parser.add_argument('--actiontree-path', required=True, help='Path to the action tree')
    parser.add_argument('--hash-path', required=True, help='Path to the hash script')
    parser.add_argument('--output-path', required=True, help='Path to the output')
    
    args = parser.parse_args()
    main(args.actiontree_path, args.hash_path, args.output_path)
