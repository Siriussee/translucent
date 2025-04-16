#!/usr/bin/env python3
import json
import os


def decode_selector(data, cache_path='./cache/selector_datsabase.json'):
    """
    Decode function selectors in the provided data list using a local JSON mapping.

    Special decode rules:
      - If the selector equals "0x", it is decoded as "ether_transfer()"
      - If the selector equals "0xff", it is decoded as "create_contract(bytes)"
      - If the selector is None, it is decoded as "suicide_contract()"
      - If the selector is found in the JSON cache at cache_path,
        its corresponding signature is used.
      - Otherwise, the selector is kept as is.

    Args:
        data (list of dict): List of dictionaries that each contain a 'hex' key representing the selector.
        cache_path (str): Path to the JSON file containing the selector mapping.

    Returns:
        list of dict: The input list with an added 'name' field for each entry.
    """
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            selector_mapping = json.load(f)
    else:
        selector_mapping = {}

    for row in data:
        sel = row.get('hex')
        if sel is None:
            row['name'] = 'suicide_contract()'
        elif sel == '0x':
            row['name'] = 'ether_transfer()'
        elif sel == '0xff':
            row['name'] = 'create_contract(bytes)'
        elif sel in selector_mapping:
            row['name'] = selector_mapping[sel]
        else:
            row['name'] = sel  # No match; keep the selector as is.

    return data


# Example usage:
if __name__ == "__main__":
    # Example input data
    example_data = [
        {'hex': '0x'},
        {'hex': '0xff'},
        {'hex': None},
        {'hex': '0xabcdef12'},
        {'hex': '0x12345678'}
    ]

    # Assume ./cache/selector_datsabase.json exists and contains mappings like:
    # {
    #   "0xabcdef12": "transfer(address,uint256)",
    #   "0x12345678": "approve(address,uint256)"
    # }
    decoded = decode_selector(example_data)
    print(json.dumps(decoded, indent=4))
