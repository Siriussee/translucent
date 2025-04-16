# TxLucent

## Artifact Structure

- `dataset/`: Contain scripts on downloading and preprocessing (group by transaction_hash, etc.) raw transaction call traces from BigQuery.
- `src/`: Contain script on decoding raw transaction call traces, extracting semantics, and detecting attacks.
- `cache/`: Contain fasttext model, function signature database.

## Easy Start

We prepare the processed reentrancy dataset for getting hands on TxLucent's detection results w/o the burden of downloading and processing dataset. To start, simply run.

```
python src/test/test_reentrancy.py --input-path  dataset/reentrancy/reentrancy/actiontree/ --ignore-static-delegate
```

## To Start

For reproduce experiment results on all 4 datasets, please

1. Go to [`dataset/README.md`](dataset/README.md), finish all steps.
2. Go to [`src/README.md`](src/README.md), finish all steps.

