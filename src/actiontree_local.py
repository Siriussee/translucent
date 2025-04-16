import sys
from hex_decoder import hex_to_function_name
from utils import find_element_by_address, split_signature, build_tree
from parser import extract_function, extract_event, merge_events_functions
from jinja2 import Template
import json
import os
import logging
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)


def read_json_file(file_path):
    try:
        if not os.path.exists(file_path):
            logging.warning(f"File not found: {file_path}")
            return None

        with open(file_path, 'r') as file:
            data = json.load(file)
        return data

    except FileNotFoundError:
        logging.warning(f"File not found: {file_path}")
        return None

    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from the file: {file_path}")
        return None


def convert_to_object(data):
    if data is None:
        return []

    class Row:
        def __init__(self, **entries):
            self.__dict__.update(entries)

    return [Row(**item) for item in data]


def main(
    trace_path, 
    event_path,  
    output_path,
    transaction_hash, 
    event_input_path):

    total_nodes = 0
    name_match = 0
    total_ignored = 0

    call_data_file = f'{trace_path}/{transaction_hash}.json'
    event_data_file = f'{event_path}/{transaction_hash}.json'
    event_input_file = f'{event_input_path}/{transaction_hash}.json'
    
    call_data = convert_to_object(read_json_file(call_data_file))
    event_data = convert_to_object(read_json_file(event_data_file))
    event_input = convert_to_object(read_json_file(event_input_file))
        
    processed_data = extract_function(call_data, transaction_hash)

    hex_to_function_name(
        processed_data,
        "https://www.4byte.directory/api/v1/signatures/?hex_signature=",
        transaction_hash)

    processed_event = extract_event(event_data, event_input)

    hex_to_function_name(
        processed_event,
        "https://www.4byte.directory/api/v1/event-signatures/?hex_signature=",
        transaction_hash)

    merged_tree, unmatched, total_nodes, name_match, total_ignored = merge_events_functions(
        processed_event, total_nodes, name_match, processed_data, total_ignored ,output_path)

    unmatched_node = json.dumps(unmatched, indent=4)

    orphaned_path = f'{output_path}/orphaned/{transaction_hash}_orphaned.json'
    stat_path = f'{output_path}/stats/{transaction_hash}_stat.json'
    
    with open(orphaned_path, 'w') as file:
        file.write(unmatched_node)
    logger.debug(f'Orphaned events write to {orphaned_path}')

    unmatched_num = total_nodes - name_match
    
    missing_rate = round(unmatched_num / total_nodes * 100, 2)
    ignore_rate = round(total_ignored / total_nodes * 100, 2)
    
    logger.debug(
        f"total matched:{name_match}, missing:{unmatched_num}, total:{total_nodes}, missing rate:{missing_rate}%")
    
    stats = {
        "total_nodes": total_nodes,
        "total_name_matches": name_match,
        "total_missing:": unmatched_num,
        "missing_rate": missing_rate,
        "total_ignored": total_ignored,
        "ignore_rate": ignore_rate
        
    }
    with open(stat_path, "w") as json_file:
        json.dump(stats, json_file, indent=4)
        
    #modify the structure here to add in the parameters and process the parameters
    for row in merged_tree:
        if row['id'] == '':
            root_node = {
                'transaction_hash': transaction_hash,
                'type': row['type'],
                'action': row['action'],
                'ignored': row['ignored'],
                'parameters': row['parameters'],
                'values': row['values'],
                'values_raw': row['values_raw'],
                'sender': row['sender'],
                'receiver': row['receiver'],
                'hex': row['hex'],
                'nodes': []
            }

    for row in merged_tree:
        
        root_node['nodes'] = build_tree(merged_tree)['nodes']

        json_tree = json.dumps(root_node, indent=4)

    json_tree_path = f"{output_path}/actiontree/{transaction_hash}.json"
    with open(json_tree_path, 'w') as file:
        file.write(json_tree)
    logger.debug(f'Action tree write to {json_tree_path}')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run script with trace, event and output paths with hashs')
    parser.add_argument('--trace-path', required=True, help='Path to the trace')
    parser.add_argument('--event-path', required=True, help='Path to the event')
    parser.add_argument('--output-path', required=True, help='Path to the output')
    parser.add_argument('--hash', required=True, help='hash')
    parser.add_argument('--event-input-path', required=True, help='Path to the event inputs')

    args = parser.parse_args()
    main(args.trace_path, args.event_path, args.output_path, args.hash, args.event_input_path)
