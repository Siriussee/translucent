import numpy as np
import pandas as pd
import json

def process_json(input_json_path, transactions, output_json_path):
    
    with open(input_json_path, 'r') as f:
        data = json.load(f)
    
    #i= 0
    for sample, points in data.items():
        for point_type, point in points.items():
            if point:
                matched_transaction = find_exact_match(transactions, point)
                if matched_transaction:
                    points[point_type] = matched_transaction
        """for point in points:
            if point:
                matched_transaction = find_exact_match(transactions, point)
                if matched_transaction:
                    points[i] = matched_transaction
                    i=i+1"""

    with open(output_json_path, 'w') as f:
        json.dump(data, f, indent=4)

def read_transactions(file_path):
    transactions = []
    with open(file_path, mode='r') as file:
        lines = file.readlines()
        
        i = 0
        while i < len(lines):
            transaction_id = lines[i].strip()
            transaction_hash = lines[i+1].strip()
            transaction_methods = lines[i+2].strip()
            embedding_str = lines[i+3].strip()
            embedding = eval(embedding_str)  
            
            transactions.append({
                'id': transaction_id,
                'hash': transaction_hash,
                'methods': transaction_methods,
                'embedding': embedding
            })
            
            i += 5
        
    return transactions

def find_exact_match(transactions, input_embedding):
    for transaction in transactions:
        if transaction['embedding'] == input_embedding:
            return {'hash':transaction['hash'],
                    'methods': transaction['methods'],}
    return None

def main():
    sets = {'knn','kmeans', 'dbscan'}
    transactions_csv_path = './output/10ksample/10ksample.csv'
    transactions = read_transactions(transactions_csv_path)

    for item in sets:
        input_json_path = f'./output/10ksample/{item}/5pt/cluster_points.json'
        
        output_json_path = f'./output/10ksample/{item}/5pt/transactions.json'
        
        """input_json_path = f'./output/10ksample/{item}/5pt/furthest_points_original_from_2d.json'
        
        output_json_path = f'./output/10ksample/{item}/5pt/furthest_points_original_from_2d_txn.json'"""

        process_json(input_json_path, transactions, output_json_path)

if __name__ == "__main__":
    main()