import json
import re

# Define a regular expression that matches an Ethereum contract address.
eth_address_pattern = re.compile(r'0x[a-fA-F0-9]{40}')

def extract_addresses(text):
    """Extracts all Ethereum contract addresses from the given text,
    ensuring the returned list contains only unique addresses while preserving order.
    """
    addresses = eth_address_pattern.findall(text)
    unique_addresses = list(dict.fromkeys(addresses))
    return unique_addresses

def build_transactions_sql_query(addresses, transactions_table="`bigquery-public-data.crypto_ethereum.transactions`"):
    """
    Build a SQL query that creates a temporary table containing the given contract addresses, then
    returns all transactions from the specified Ethereum transactions table where to_address
    matches any of these addresses and the block_timestamp is between 2023-01-01 and 2024-12-31.
    
    Args:
        addresses (list[str]): List of Ethereum contract addresses.
        transactions_table (str): Fully-qualified BigQuery transactions table name.
        
    Returns:
        str: The SQL query string.
    """
    # Format the list of addresses as a comma-separated string of quoted values.
    addresses_list = ", ".join([f"'{addr}'" for addr in addresses])
    
    query = f"""
-- Temporary table with targeted contract addresses.
WITH contract_addresses AS (
  SELECT address
  FROM UNNEST([{addresses_list}]) AS address
)
SELECT *
FROM {transactions_table}
WHERE to_address IN (SELECT address FROM contract_addresses)
  AND block_timestamp BETWEEN TIMESTAMP('2023-01-01 00:00:00 UTC')
                          AND TIMESTAMP('2024-12-31 23:59:59 UTC')
"""
    return query.strip()

def build_trace_sql_query(addresses, traces_table="`bigquery-public-data.crypto_ethereum.traces`"):
    """
    Build a SQL query that captures the full traces of transactions wherein the traces interact 
    with any of the targeted contract addresses. This is achieved by:
    1. Using a temporary table to hold the targeted contract addresses.
    2. Selecting distinct transaction hashes from the traces table where the to_address matches a targeted address.
    3. Returning all traces for those transaction hashes within the specified timestamp range.
    
    Args:
        addresses (list[str]): List of Ethereum contract addresses.
        traces_table (str): Fully-qualified BigQuery traces table name.
    
    Returns:
        str: The SQL query string.
    """
    # Format the addresses list as a comma-separated string of quoted addresses.
    addresses_list = ", ".join([f"'{addr}'" for addr in addresses])
    
    query = f"""
-- Temporary table with targeted contract addresses.
WITH contract_addresses AS (
  SELECT address
  FROM UNNEST([{addresses_list}]) AS address
),
-- Get all distinct transaction hashes that have at least one trace with a targeted contract address.
selected_hashes AS (
  SELECT DISTINCT transaction_hash
  FROM {traces_table}
  WHERE to_address IN (SELECT address FROM contract_addresses)
    AND block_timestamp BETWEEN TIMESTAMP('2024-01-01 00:00:00 UTC')
                           AND TIMESTAMP('2024-12-31 23:59:59 UTC')
)
-- Return full traces for transactions identified above.
SELECT
  transaction_hash,
  from_address,
  to_address,
  trace_type,
  call_type,
  trace_id,
  input,
  output
FROM {traces_table} t
WHERE t.transaction_hash IN (SELECT transaction_hash FROM selected_hashes)
  AND t.block_timestamp BETWEEN TIMESTAMP('2024-01-01 00:00:00 UTC')
                          AND TIMESTAMP('2024-12-31 23:59:59 UTC')
"""
    return query.strip()

def process_json(input_filename, output_filename, exclude_filename, transactions_sql_filename, traces_sql_filename):
    # Load the source JSON data.
    with open(input_filename, 'r') as infile:
        data = json.load(infile)
    
    # Load the exclusion JSON data.
    with open(exclude_filename, 'r') as exfile:
        exclude_data = json.load(exfile)
    # Expecting the structure {"addresses": [ ... ]}
    if isinstance(exclude_data, dict) and "addresses" in exclude_data:
        exclude_list = exclude_data["addresses"]
    elif isinstance(exclude_data, list):
        exclude_list = exclude_data
    else:
        exclude_list = []
    # Convert all excluded addresses to lower-case for case-insensitive comparison.
    exclude_set = {addr.lower() for addr in exclude_list}

    # Container to hold all unique contract addresses across all records.
    # We'll use both a list for preserving order and a set for case-insensitive uniqueness.
    all_contract_addresses = []
    all_contract_lower = set()
    
    # Process each entry in the "data" list.
    new_data = []
    for entry in data.get("data", []):
        # Extract unique addresses from the "input" field.
        addresses = extract_addresses(entry.get("input", ""))
        # Filter out addresses that are in the exclusion set (case-insensitive).
        filtered_addresses = []
        for addr in addresses:
            lower_addr = addr.lower()
            if lower_addr in exclude_set:
                continue
            if lower_addr not in all_contract_lower:
                all_contract_lower.add(lower_addr)
                all_contract_addresses.append(addr)
            filtered_addresses.append(addr)
        
        # Create a new entry by replacing "input" with "addresses".
        new_entry = {
            "dapp": entry.get("dapp", ""),
            "addresses": filtered_addresses
        }
        new_data.append(new_entry)
    
    # Write the modified JSON data to the output file.
    output_data = {"data": new_data}
    with open(output_filename, 'w') as outfile:
        json.dump(output_data, outfile, indent=4)
    
    # Build the SQL query for the transactions table.
    transactions_sql_query = build_transactions_sql_query(all_contract_addresses)
    with open(transactions_sql_filename, 'w') as sql_file:
        sql_file.write(transactions_sql_query)
    
    # Build the SQL query for the traces table.
    traces_sql_query = build_trace_sql_query(all_contract_addresses)
    with open(traces_sql_filename, 'w') as trace_sql_file:
        trace_sql_file.write(traces_sql_query)
    
    print(f"Processed JSON data has been written to {output_filename}.")
    print(f"Transactions SQL query has been written to {transactions_sql_filename}.")
    print(f"Traces SQL query has been written to {traces_sql_filename}.")

if __name__ == "__main__":
    process_json(
        input_filename="raw.json",
        output_filename="contract_address.json",
        exclude_filename="exclude_contract_address.json",
        transactions_sql_filename="bigquery_transactions_query.sql",
        traces_sql_filename="bigquery_traces_query.sql"
    )