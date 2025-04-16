# TxLucent

## Artifact Structure

- `dataset/`: Contain scripts on downloading and preprocessing (group by transaction_hash, etc.) raw transaction call traces from BigQuery.
- `src/`: Contain script on decoding raw transaction call traces, extracting semantics, and detecting attacks.
- `cache/`: Contain fasttext model, function signature database.

## To Start

1. Go to `dataset/README.md`, finish all steps.
2. Go to `src/README.md`, finish all steps.