import sys
import os
import json
import logging
import argparse
from hex_decoder import hex_to_function_name
from selector_decoder import decode_selector
from utils import find_element_by_address, split_signature, build_tree
from parser import extract_function, extract_event, merge_events_functions
from jinja2 import Template

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


def main(trace_path, event_path, output_path, transaction_hash, event_input_path):
    total_nodes = 0
    name_match = 0
    total_ignored = 0

    # Read call (trace) data
    call_data_file = os.path.join(trace_path, f'{transaction_hash}.json')
    call_data = convert_to_object(read_json_file(call_data_file))

    # Process call data for function extraction
    processed_data = extract_function(call_data, transaction_hash)

    decode_selector(processed_data)

    # hex_to_function_name(
    #     processed_data,
    #     "https://www.4byte.directory/api/v1/signatures/?hex_signature=",
    #     transaction_hash)

    # Initialize processed_event as empty list in case event support is not provided.
    processed_event = []

    # Check if event paths are provided (non-empty) and file exists.
    if event_path and event_input_path:
        event_data_file = os.path.join(event_path, f'{transaction_hash}.json')
        event_input_file = os.path.join(
            event_input_path, f'{transaction_hash}.json')

        event_data = convert_to_object(read_json_file(event_data_file))
        event_input = convert_to_object(read_json_file(event_input_file))

        # Process event data only if both event files are available
        processed_event = extract_event(event_data, event_input)

        hex_to_function_name(
            processed_event,
            "https://www.4byte.directory/api/v1/event-signatures/?hex_signature=",
            transaction_hash)
    else:
        logger.debug(
            "Event path or event input path not provided, skipping event extraction.")

    # Merge the processed event and function (call) data into a single merged_tree.
    merged_tree, unmatched, total_nodes, name_match, total_ignored = merge_events_functions(
        processed_event, total_nodes, name_match, processed_data, total_ignored, output_path)

    unmatched_node = json.dumps(unmatched, indent=4)
    orphaned_path = os.path.join(
        output_path, 'orphaned', f'{transaction_hash}_orphaned.json')
    stat_path = os.path.join(output_path, 'stats',
                             f'{transaction_hash}_stat.json')

    os.makedirs(os.path.dirname(orphaned_path), exist_ok=True)
    os.makedirs(os.path.dirname(stat_path), exist_ok=True)

    with open(orphaned_path, 'w') as file:
        file.write(unmatched_node)
    logger.debug(f'Orphaned events written to {orphaned_path}')

    unmatched_num = total_nodes - name_match if total_nodes > 0 else 0
    missing_rate = round(unmatched_num / total_nodes *
                         100, 2) if total_nodes > 0 else 0
    ignore_rate = round(total_ignored / total_nodes *
                        100, 2) if total_nodes > 0 else 0

    logger.debug(
        f"Total matched: {name_match}, missing: {unmatched_num}, total: {total_nodes}, missing rate: {missing_rate}%")

    stats = {
        "total_nodes": total_nodes,
        "total_name_matches": name_match,
        "total_missing": unmatched_num,
        "missing_rate": missing_rate,
        "total_ignored": total_ignored,
        "ignore_rate": ignore_rate
    }
    with open(stat_path, "w") as json_file:
        json.dump(stats, json_file, indent=4)

    # Building the final action tree.
    root_node = None
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
            break

    # If root_node is found, assign its children from the built tree.
    if root_node is not None:
        tree_structure = build_tree(merged_tree)
        root_node['nodes'] = tree_structure.get('nodes', [])
        json_tree = json.dumps(root_node, indent=4)

        json_tree_path = os.path.join(
            output_path, 'actiontree', f'{transaction_hash}.json')
        os.makedirs(os.path.dirname(json_tree_path), exist_ok=True)
        with open(json_tree_path, 'w') as file:
            file.write(json_tree)
        logger.debug(f'Action tree written to {json_tree_path}')
    else:
        logger.error(
            "No root node found in the merged tree. Action tree cannot be built.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Process trace and optionally event files to build an action tree.')
    parser.add_argument('--trace-path', required=True,
                        help='Path to the trace files')
    parser.add_argument('--output-path', required=True,
                        help='Path to the output')
    parser.add_argument('--hash', required=True, help='Transaction hash')
    # Make event-path and event-input-path optional by providing defaults.
    parser.add_argument('--event-path', required=False,
                        default='', help='Path to the event files (optional)')
    parser.add_argument('--event-input-path', required=False,
                        default='', help='Path to the event input files (optional)')

    args = parser.parse_args()
    main(args.trace_path, args.event_path,
         args.output_path, args.hash, args.event_input_path)
