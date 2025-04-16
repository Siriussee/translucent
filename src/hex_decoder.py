import requests
import json
import os
from filelock import FileLock
from datetime import datetime
import time
import logging

RATE_LIMIT = 10
TIME_PERIOD = 45  # in seconds
RATE_LIMIT_FILE = './input/rate_limit.json'
RATE_LIMIT_LOCK = RATE_LIMIT_FILE + '.lock'


def get_timestamp():
    return datetime.now().isoformat()


def read_json(file_path):

    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}


def write_json(file_path,
               data):

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def update_hex_mapping(hex_data,
                       file_path='./cache/hexmapping.json'):

    lock_path = file_path + '.lock'
    lock = FileLock(lock_path)

    with lock:
        data = read_json(file_path)
        data.update(hex_data)
        write_json(file_path, data)


def merge_cache_files(existing_cache_path,
                      new_cache_path):

    existing_lock_path = existing_cache_path + '.lock'
    existing_lock = FileLock(existing_lock_path)

    with existing_lock:
        existing_cache = read_json(existing_cache_path)
        new_cache = read_json(new_cache_path)
        for key, value in new_cache.items():
            if key not in existing_cache:
                existing_cache[key] = value
        write_json(existing_cache_path, existing_cache)
        os.remove(new_cache_path)


def call_api_with_rate_limit(url):
    while True:
        with FileLock(RATE_LIMIT_LOCK):
            rate_limit_data = read_json(RATE_LIMIT_FILE)
            current_time = time.time()

            if not rate_limit_data or (current_time - rate_limit_data.get('start_time', 0) > TIME_PERIOD):
                rate_limit_data = {'start_time': current_time, 'count': 0}
            if rate_limit_data['count'] < RATE_LIMIT:
                rate_limit_data['count'] += 1
                write_json(RATE_LIMIT_FILE, rate_limit_data)
                break
            else:
                sleep_time = TIME_PERIOD - \
                    (current_time - rate_limit_data['start_time'])
                logging.warning(
                    f"Rate limit exceeded. Sleeping for {sleep_time} seconds.")
                time.sleep(sleep_time)
                continue

    response = requests.get(url)
    if response.status_code == 429:
        logging.error("Rate limit exceeded. Retrying...")
        raise Exception("Rate limit exceeded")
    return response


def hex_to_function_name(
        data,
        fixedurl,
        transaction_hash):

    main_cache_path = './cache/hexmapping.json'
    temp_cache_path = f'./cache/temp_hexmapping_{transaction_hash}.json'

    main_cache_lock_path = main_cache_path + '.lock'
    main_cache_lock = FileLock(main_cache_lock_path)

    with main_cache_lock:
        main_cache = read_json(main_cache_path)

    temp_cache = read_json(temp_cache_path)

    for row in data:
        if row['hex'] in main_cache:
            row['name'] = main_cache[row['hex']]
        elif row['hex'] in temp_cache:
            row['name'] = temp_cache[row['hex']]

        else:

            if row['hex'] == '0x':
                row['name'] = 'ether_transfer()'
                temp_cache[row['hex']] = row['name']

            elif row['hex'] == '0xff':
                row['name'] = 'create_contract(bytes)'
                temp_cache[row['hex']] = row['name']

            elif row['hex'] == None:
                row['name'] = 'suicide_contract()'
                temp_cache[row['hex']] = row['name']

            else:
                url = fixedurl + row['hex']
                logging.debug(f"4byte DB Lookup: {row['hex']}")
                retry = 0
                while retry < 5:
                    try:
                        response = call_api_with_rate_limit(url)
                        if response.status_code == 200:

                            data = response.json()

                            if data['count'] == 0:
                                row['name'] = row['hex'] + "(unknown)"

                            elif data['count'] == 1:
                                row['name'] = data['results'][0]['text_signature']

                            else:
                                sorted_data = sorted(
                                    data['results'], key=lambda x: x['id'])
                                row['name'] = sorted_data[0]['text_signature']

                            temp_cache[row['hex']] = row['name']

                        else:
                            logging.error(
                                f"Request failed with status code {response.status_code} for {row['hex']} and {transaction_hash}")
                        break

                    except Exception as e:
                        logging.error(
                            f"Error fetching data for {row['hex']}: {e}")
                        time.sleep(2 ** retry)
                        retry += 1

    write_json(temp_cache_path, temp_cache)
    merge_cache_files(main_cache_path, temp_cache_path)
