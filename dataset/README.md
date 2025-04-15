# Datasets

## Overview

1. Reentrancy: [Reentrancy Redux: The Evolution of Real-World Reentrancy Attacks on Blockchains](https://zenodo.org/records/15112729)
    - Total attack: 71
    - Total attack transactions: 73 (Applicable, only Ethereum)
    - Total trace: 29,052

2. POMA: [POMABuster: Detecting Price Oracle Manipulation Attacks in Decentralized Finance](https://blogs.ubc.ca/dependablesystemslab/2024/03/09/pomabuster-detecting-price-oracle-manipulation-attacks-in-decentralized-finance/)
    - Total attack transactions: 4,279 (Applicable, only single-transaction)
    - Total trace: 271,559

3. Uncategorized application-level attacks: [DAppFL: Just-in-Time Fault Localization for Decentralized Applications in Web3](https://2024.issta.org/details/issta-2024-papers/12/DAppFL-Just-in-Time-Fault-Localization-for-Decentralized-Applications-in-Web3)
    - Total attack transactions: 79
    - Total trace: 10,303

4. Top 20 TVL dapp transactions
    - Total dApps: 20
    - Total contracts: 2068
    - Total transaction: 12,386,720

## Generate SQL Query

We scrape/download transaction hash/contract addresses sources from the accordingly paper, reviewers need to generate SQL query based on them.

### POMA

Source: `dataset/poma/single_poma_transaction_hashes.csv`

Run
```
cd dataset/poma
python parse_to_sql.py
```

Output: `dataset/poma/bigquery_traces_query.sql`

### uncategorized

Source: `dataset/uncategorized/dappfl.csv`

Run
```
cd dataset/uncategorized
python parse_to_sql.py
```

Output: `dataset/uncategorized/bigquery_traces_query.sql`

### Top 20 TVL

Source: `dataset/tvl/raw.json`

Run
```
cd dataset/tvl
python parse_to_sql.py
```

Output: 
- `dataset/tvl/bigquery_traces_query.sql` <<< we use this one
- `dataset/tvl/bigquery_transactions_query.sql`

For the difference between `bigquery_traces_query` and `bigquery_traces_query`, please refer to `dataset/tvl/README.md`.

## Download Dataset from Google Bigquery and Split by Transaction

We get raw call traces from Bigquery in batch, and then scatter them by transaction. This will serve as raw call trace input to TxLucent. Please refer to [Google Cloud's official quickstart](https://cloud.google.com/bigquery/docs/quickstarts/query-public-dataset-console) on how to run SQL on a public dataset.

### Reentrancy

Run `dataset/reentrancy/bigquery_traces_query.sql` on Bigquery, 
and download the table as `dataset/reentrancy/reentrancy_raw_input_bigquery.csv`
```
cd dataset/reentrancy
python parse_bigquery_reuslt_to_txn_trace.py
```

Output: `dataset/reentrancy/trace_reentrancy/` folder, containing json files as raw call traces.

### POMA

Run `dataset/poma/bigquery_traces_query.sql` on Bigquery, 
and download the table as `dataset/poma/poma_raw_input_bigquery.jsonl`
```
cd dataset/poma
python parse_bigquery_reuslt_to_txn_trace.py
```

Output: `dataset/poma/trace_poma/` folder, containing json files as raw call traces.


### Uncategorized

Run `dataset/poma/bigquery_traces_query.sql` on Bigquery, 
and download the table as `dataset/poma/poma_raw_input_bigquery.jsonl`
```
cd dataset/poma
python parse_bigquery_reuslt_to_txn_trace.py
```

Output: `trace_poma/` folder, containing json files as raw call traces.

### Top 20 TVL

Run `dataset/poma/bigquery_traces_query.sql` on Bigquery, 
and save the query results to destination table.
Then, dump the table to Google Cloud Storage, and allow split files by remain the file name as `tvl-*`
Use Google Cloud Console to download the files from Google Cloud Storage. For details, refer to
[Download an object from a bucket](https://cloud.google.com/storage/docs/downloading-objects#downloading-an-object).

```
# example:
gsutil -m cp gs://tvl-trace/tvl-* trace_tvl/ 
# format: `gsutil -m cp gs://[BUCKET_NAME]/[FILE_NAME] [DOANLOAD_PATH]`
```

Output: `trace_tvl/` folder, containing jsonl files (chunked) as raw call traces.