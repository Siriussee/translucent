import subprocess
import json
import concurrent.futures
import argparse
from hex_decoder import read_json, write_json
import os
from filelock import FileLock


def main(
        trace_path,
        event_path,
        hash_path,
        output_path,
        event_input_path):

    os.makedirs(output_path, exist_ok=True)

    actiontree_path = f'{output_path}/actiontree'
    orphaned_path = f'{output_path}/orphaned'
    stats_path = f'{output_path}/stats'

    os.makedirs(actiontree_path, exist_ok=True)
    os.makedirs(orphaned_path, exist_ok=True)
    os.makedirs(stats_path, exist_ok=True)

    script_path = './src/actiontree_local.py'
    input_path = hash_path
    failed_hashes_path = f'{output_path}/failed_hashes.json'
    failed_hashes_lock_path = failed_hashes_path + '.lock'

    ether_count_path = f'{output_path}/ether_count.json'
    create_count_path = f'{output_path}/create_count.json'
    suicide_count_path = f'{output_path}/suicide_count.json'

    reset_count_in_json(ether_count_path)
    reset_count_in_json(create_count_path)
    reset_count_in_json(suicide_count_path)

    hash_list = read_hashes_from_json(input_path)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_script, script_path, hash, trace_path,
                                   event_path, output_path, event_input_path) for hash in hash_list]

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(
                    f"Script execution for hash {hash} failed with exception: {e}")
                # write_failed_hash(failed_hashes_path, failed_hashes_lock_path, hash)


def read_hashes_from_json(file_path):

    with open(file_path, 'r') as file:
        data = json.load(file)

    hash_list = [item['transaction_hash'] for item in data]

    return hash_list


def reset_count_in_json(file_path):

    data = read_json(file_path)
    data['count'] = 0
    write_json(file_path, data)


def run_script(script_path, hash, trace_path, event_path, output_path, event_input_path):
    subprocess.run(['python', script_path, '--trace-path', trace_path, '--event-path', event_path,
                   '--output-path', output_path, '--hash', hash, '--event-input-path', event_input_path], check=True)


def write_failed_hash(file_path,
                      lock_path,
                      hash):

    lock = FileLock(lock_path)
    with lock:
        if not os.path.exists(file_path):
            failed_hashes = []
        else:
            with open(file_path, 'r') as file:
                failed_hashes = json.load(file)

        failed_hashes.append(hash)

        with open(file_path, 'w') as file:
            json.dump(failed_hashes, file, indent=4)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Run script with trace, event, hash and output paths')
    parser.add_argument('--trace-path', required=True,
                        help='Path to the trace')
    parser.add_argument('--event-path', required=True,
                        help='Path to the event')
    parser.add_argument('--hash-path', required=True,
                        help='Path to the output')
    parser.add_argument('--output-path', required=True,
                        help='Path to the output')
    parser.add_argument('--event-input-path', required=True,
                        help='Path to the event inputs')

    args = parser.parse_args()
    main(args.trace_path, args.event_path, args.hash_path,
         args.output_path, args.event_input_path)
