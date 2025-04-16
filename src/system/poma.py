#!/usr/bin/env python3
import json
import argparse
import os
import numpy as np
import fasttext
import fasttext.util
import logging

# Configure logging to file "log.log"
logging.basicConfig(
    filename="log.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Global counter for preorder order and embedding cache.
order_counter = 1
embedding_cache = {}

# Initialize fastText model.
cache_dir = './cache'
os.makedirs(cache_dir, exist_ok=True)
original_dir = os.getcwd()
os.chdir(cache_dir)
fasttext.util.download_model('en', if_exists='ignore')
os.chdir(original_dir)
fasttext_model_path = os.path.join(cache_dir, 'cc.en.300.bin')
fasttext_model = fasttext.load_model(fasttext_model_path)

def get_embedding(func_name: str) -> np.ndarray:
    """
    Get the embedding vector for a function name using fastText.
    Uses get_sentence_vector to handle multi-word names.
    Caches the result to avoid repeated calculations.
    """
    if func_name in embedding_cache:
        return embedding_cache[func_name]
    embedding = fasttext_model.get_sentence_vector(func_name)
    embedding_cache[func_name] = embedding
    return embedding

def cosine_similarity(vec1, vec2):
    """
    Compute the cosine similarity between two vectors.
    Returns 0 if either vector has zero norm.
    """
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0
    return np.dot(vec1, vec2) / (norm1 * norm2)

def traverse_tree(node, depth, calls, ignore_static_delegate=False):
    """
    Traverse the action tree in preorder, assign order and depth,
    and record all function call nodes (with keys: sender, receiver, action).
    Calculate and attach the word embedding for the function name.
    If ignore_static_delegate is True, ignore nodes with call_type 'staticcall' or 'delegatecall'.
    """
    global order_counter
    current_order = order_counter
    order_counter += 1

    # Annotate the node.
    node["order"] = current_order
    node["depth"] = depth

    # Check if we should ignore staticcall/delegatecall nodes.
    call_type = node.get("call_type")
    if ignore_static_delegate and call_type in {"staticcall", "delegatecall"}:
        logging.debug("Ignoring node order %d, depth %d with call_type '%s'", current_order, depth, call_type)
        # Still traverse its children even if this node is ignored.
        for child in node.get("nodes", []):
            traverse_tree(child, depth + 1, calls, ignore_static_delegate)
        return

    # If the node is a function call and has necessary info, record it.
    if node.get("type") == "function" and "sender" in node and "receiver" in node and "action" in node:
        func_name = node["action"]
        emb = get_embedding(func_name)
        node["embedding"] = emb
        call_info = {
            "order": current_order,
            "depth": depth,
            "sender": node["sender"],
            "receiver": node["receiver"],
            "function": func_name,
            "embedding": emb
        }
        calls.append(call_info)
        logging.debug("Recorded call: order %d, depth %d, sender %s, receiver %s, function '%s'",
                      current_order, depth, node["sender"], node["receiver"], func_name)

    # Recurse into children.
    for child in node.get("nodes", []):
        traverse_tree(child, depth + 1, calls, ignore_static_delegate)

def adjust_embeddings(calls):
    """
    Compute the average embedding of all calls and subtract it from each call's embedding.
    """
    if not calls:
        return
    all_embeddings = np.array([call["embedding"] for call in calls])
    avg_embedding = np.mean(all_embeddings, axis=0)
    for call in calls:
        call["embedding"] = call["embedding"] - avg_embedding
    logging.debug("Adjusted all embeddings by subtracting the average embedding.")

def detect_poma(calls, threshold_swap=0.5, threshold_ether=0):
    """
    Detect Price Manipulation (POMA) pattern based on the following rules:
      1. There exist two calls, a and b, whose function names are similar to one of
         the candidate keywords ["swap", "fillOrder", "exchange"] (cosine similarity > threshold_swap),
         and their depths must be either equal or differ by at most 1.
      2. They must have the same sender but different receivers.
      3. There exists a third call, c, with a function name similar to "ether_transfer" (cosine similarity > threshold_ether),
         and the orders satisfy: a.order < b.order < c.order.
    Returns a tuple (detected: bool, list_of_triples: list).
    All found triples are logged.
    """
    candidate_keywords = ["swap", "fillOrder", "exchange"]
    # Pre-compute embeddings for candidate keywords.
    candidate_embeddings = {kw: get_embedding(kw) for kw in candidate_keywords}
    ether_transfer_emb = get_embedding("ether_transfer")
    swap_candidates = []
    valid_triples = []

    # Identify candidates for swap-like calls.
    for call in calls:
        max_sim = 0
        matched_kw = None
        # Check similarity against each candidate keyword.
        for kw, emb in candidate_embeddings.items():
            sim = cosine_similarity(call["embedding"], emb)
            if sim > max_sim:
                max_sim = sim
                matched_kw = kw
        if max_sim > threshold_swap:
            swap_candidates.append(call)
            logging.debug("Call order %d considered candidate for %s (sim=%.4f): function=%s",
                          call["order"], matched_kw, max_sim, call["function"])
        else:
            logging.debug("Call order %d rejected as candidate (max sim=%.4f): function=%s",
                          call["order"], max_sim, call["function"])

    n = len(swap_candidates)
    for i in range(n):
        a = swap_candidates[i]
        for j in range(i + 1, n):
            b = swap_candidates[j]
            # Check depth condition: difference must be ≤ 1.
            if abs(a["depth"] - b["depth"]) > 1:
                logging.debug("Candidate pair rejected due to depth diff: orders %d and %d (depths: %d and %d)",
                              a["order"], b["order"], a["depth"], b["depth"])
                continue
            # Check that both calls have the same sender and different receivers.
            if a["sender"] != b["sender"]:
                logging.debug("Candidate pair rejected due to sender mismatch: orders %d and %d (senders: %s vs %s)",
                              a["order"], b["order"], a["sender"], b["sender"])
                continue
            if a["receiver"] == b["receiver"]:
                logging.debug("Candidate pair rejected due to identical receivers: orders %d and %d (receiver: %s)",
                              a["order"], b["order"], a["receiver"])
                continue

            # For each valid a & b pair, look for a third call c for ether_transfer.
            for c in calls:
                if not (a["order"] < b["order"] < c["order"]):
                    logging.debug("Candidate triple rejected due to order condition: orders a=%d, b=%d, c=%d",
                                  a["order"], b["order"], c["order"])
                    continue
                sim_ether = cosine_similarity(c["embedding"], ether_transfer_emb)
                if sim_ether > threshold_ether:
                    valid_triples.append((a, b, c))
                    logging.info("Valid triple found: a(order %d), b(order %d), c(order %d) | sim_ether=%.4f",
                                 a["order"], b["order"], c["order"], sim_ether)
                else:
                    logging.debug("Candidate triple (a.order %d, b.order %d, c.order %d) rejected due to ether sim: %.4f",
                                  a["order"], b["order"], c["order"], sim_ether)

    if valid_triples:
        logging.info("Total valid POMA triples detected: %d", len(valid_triples))
        return True, valid_triples
    else:
        logging.info("No POMA triple detected.")
        return False, None

def main():
    parser = argparse.ArgumentParser(
        description=("Detect Price Manipulation (POMA) in an action tree JSON using function calls.\n\n"
                     "The script traverses the tree (annotating each node with order and depth), calculates word embeddings for function names, "
                     "adjusts these embeddings, and then detects all valid POMA triples based on the following rules:\n"
                     "  1. There exist two calls whose function names are similar to one of ['swap', 'fillOrder', 'exchange'] with depth difference ≤ 1, "
                     "     with same sender and different receivers.\n"
                     "  2. There exists a later call with function name similar to 'ether_transfer' such that a.order < b.order < c.order.\n")
    )
    parser.add_argument("--input-file", help="Path to the input JSON file representing the action tree", required=True)
    parser.add_argument("--ignore-static-delegate", action="store_true",
                        help="If set, nodes with call_type 'staticcall' or 'delegatecall' will be ignored during traversal.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode to print detected candidate triples")
    args = parser.parse_args()

    # Load the action tree from JSON.
    with open(args.input_file, "r") as f:
        tree = json.load(f)

    global order_counter
    order_counter = 1  # Reset the order counter.
    calls = []
    traverse_tree(tree, depth=1, calls=calls, ignore_static_delegate=args.ignore_static_delegate)
    adjust_embeddings(calls)

    detected, triples = detect_poma(calls)
    if detected:
        if args.verbose:
            print("Price Manipulation detected! Valid triples:")
            for idx, (a, b, c) in enumerate(triples, start=1):
                print(f"Triple {idx}:")
                print(f"  Swap/Filled/Exchange-like Call A: order {a['order']}, depth {a['depth']}, sender '{a['sender']}', receiver '{a['receiver']}', function '{a['function']}'")
                print(f"  Swap/Filled/Exchange-like Call B: order {b['order']}, depth {b['depth']}, sender '{b['sender']}', receiver '{b['receiver']}', function '{b['function']}'")
                print(f"  Ether_transfer-like Call C: order {c['order']}, depth {c['depth']}, sender '{c['sender']}', receiver '{c['receiver']}', function '{c['function']}'")
                print("")
        else:
            print("Price Manipulation detected!")
    else:
        print("No price manipulation detected.")

if __name__ == "__main__":
    main()