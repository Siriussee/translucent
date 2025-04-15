#!/usr/bin/env python3
import csv

# Path to your CSV file
csv_filename = 'single_poma_transaction_hashes.csv'

# Read the hashes from the CSV file
hashes = []
with open(csv_filename, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        tx_hash = row.get('pom_transaction_hash')
        if tx_hash:
            tx_hash = tx_hash.strip()
            if tx_hash:  # only add non-empty strings
                hashes.append(tx_hash)

# Create string for each hash wrapped in single quotes
hashes_quoted = [f"'{h}'" for h in hashes]

# Join all hashes with commas for easier reading in the SQL query
hashes_joined = ",\n        ".join(hashes_quoted)

# Build the SQL query using a CTE for the transaction hashes.
# A time filter on block_timestamp restricts the data to between Jan. 1, 2021 and May. 31, 2023.
query = f"""
WITH temp_transaction_hashes AS (
  SELECT * FROM UNNEST([
        {hashes_joined}
  ]) AS transaction_hash
)
SELECT
  transaction_hash,
  from_address,
  to_address,
  trace_type,
  call_type,
  trace_id,
  input,
  output
FROM `bigquery-public-data.crypto_ethereum.traces` AS trace
WHERE
  block_timestamp BETWEEN '2021-01-01' AND '2023-05-31'
  AND transaction_hash IN (SELECT transaction_hash FROM temp_transaction_hashes);
"""

# Write the query to a SQL file
with open("bigquery_traces_query.sql", "w") as sql_file:
    sql_file.write(query)