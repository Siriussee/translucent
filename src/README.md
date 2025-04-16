# Decoder and Detector

Decode call trace from Ethereum (and all other EVM-compatible blockchains) transaction, and compose them into call trace tree, build function selector => function signature database, detect application-level attacks.

## Setting up

Install python environment
```bash
# Use pipenv as my pip package manager
pip install pipenv --user
# install required packages
pipenv install
```

Download function signature database and fastText model. 
See `cache/README.md`.


## Build Call Trace Tree from Raw Traces
- `parsing_tree_eventless.py` batch parse an trace json in a folder to action tree format. You can obtain the call trace tree for each dataset using the following command.
```bash
python src/parsing_tree_eventless.py --trace-path dataset/reentrancy/trace_reentrancy  --output-path dataset/reentrancy/reentrancy
python src/parsing_tree_eventless.py --trace-path dataset/poma/trace_poma  --output-path dataset/poma/poma
python src/parsing_tree_eventless.py --trace-path dataset/uncategorized/trace_uncategorized  --output-path dataset/uncategorized/uncategorized
python src/parsing_tree_eventless.py --trace-path dataset/tvl/trace_tvl  --output-path dataset/tvl/tvl --trace-mode jsonl
```

## Experiment

### Tenderly (RQ1)
Tenderly API can be obtained from [Getting personal account access tokens](https://docs.tenderly.co/account/projects/how-to-generate-api-access-token).

- `src/tenderly/fetch_trace.py` Test tenderly runtime overhead of getting traces
```
python src/tenderly/fetch_trace.py $TENDERLY_API_KEY dataset/reentrancy/trace_reentrancy /mnt/bigdata/txnanalyzer/output/tenderly
```
### MoE (RQ2)
- `test/test_moe_reentrancy.py` `python src/test/test_moe_reentrancy.py -v`
- `test/test_moe_poma.py` `python src/test/test_moe_poma.py -v`
- `test/test_reentrancy.py`
```
python src/test/test_poma.py --input-path  dataset/reentrancy/reentrancy/actiontree/ --ignore-static-delegate
```
- `test/test_poma.py`
```
python src/test/test_poma.py --input-path  dataset/poma/poma/actiontree/ --ignore-static-delegate
```

### Large Scale (RQ3)

```bash
python src/test/test_poma.py --input-path  dataset/uncategorized/uncategorized/actiontree/ --ignore-static-delegate
python src/test/test_reentrancy.py --input-path  dataset/uncategorized/uncategorized/actiontree/ --ignore-static-delegate
python src/test/test_poma.py --input-path  dataset/tvl/tvl/actiontree/ --ignore-static-delegate
python src/test/test_reentrancy.py --input-path  dataset/tvl/tvl/actiontree/ --ignore-static-delegate
```

### Runtime Overhead (RQ4)
Results are from profiling RQ1 and RQ2 (will show after enable verbose mode).

## Utility

- `visualize.py` print one json action tree for visualizing
```
python src/visualize.py --input-file dataset/reentrancy/reentrancy/actiontree/0x1c3464135a0d7b0e770d53afe57b9ff0de70803bbf2e8f7714ea71022447f288.json --exclude staticcall
```

## Dev

### Beautify

```
find . -name "*.py" -exec autopep8 --in-place --aggressive --aggressive {} +   
```