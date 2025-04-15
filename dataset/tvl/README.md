Extract contract address from raw.json, build Google Bigquery SQL
```
cd dataset\tvl
python .\parse_to_address.py
```

You get
- contract_address.json: clean contract address by dapp
- bigquery_transactions_query.sql: transactions DIRECTLY interact with target dapp
- bigquery_traces_query.sql: full call trace DIRECTLY and INDIRECTLY interact with target dapp

For example, a attack deploys a malicious contract, Malicious. If
```
Attacker => Malicious => App
```
bigquery_transactions_query.sql won't capture this transaction as it is INDIRECT/internal calls.
However bigquery_traces_query.sql will capture this.