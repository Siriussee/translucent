#!/usr/bin/env python3
import json
import argparse
import os
import numpy as np
import fasttext
import fasttext.util
import logging

# Configure logging
logging.basicConfig(
    filename="log.log",
    filemode="w",  # overwrite each time
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Global counter for preorder order and embedding cache.
order_counter = 1
embedding_cache = {}

# Initialize fastText model.
cache_dir = './cache'
os.makedirs(cache_dir, exist_ok=True)

# Download the fastText English model into the cache directory if not exists.
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
    Caches the result so repeated calculations are avoided.
    """
    if func_name in embedding_cache:
        return embedding_cache[func_name]
    # Compute embedding using the fastText model.
    embedding = fasttext_model.get_sentence_vector(func_name)
    embedding_cache[func_name] = embedding
    return embedding

def cosine_similarity(vec1, vec2):
    """
    Compute cosine similarity between two vectors.
    Returns 0 if either vector is zero.
    """
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0
    return np.dot(vec1, vec2) / (norm1 * norm2)

def traverse_tree(node, depth, calls, ignore_static_delegate=False):
    """
    Traverse the action tree in preorder and assign order and depth.
    If the node represents a function call (i.e., its "type" is "function" and it contains sender, receiver, and action keys),
    calculate and store the embedding for its function name on the fly.
    If ignore_static_delegate is True, nodes with call_type "staticcall" or "delegatecall" are ignored (not added as calls).
    Then traverse its children under the "nodes" key.
    """
    global order_counter
    current_order = order_counter
    order_counter += 1

    # Annotate the node with order and depth attributes.
    node["order"] = current_order
    node["depth"] = depth

    # Check if we need to ignore this node based on its call_type.
    call_type = node.get("call_type")
    if ignore_static_delegate and call_type in {"staticcall", "delegatecall"}:
        logging.debug("Node order %d (depth %d) with call_type '%s' ignored during traversal.",
                      current_order, depth, call_type)
        # Traverse children even if node itself is ignored.
        for child in node.get("nodes", []):
            traverse_tree(child, depth + 1, calls, ignore_static_delegate)
        return

    # If the node is a function call, record its details and compute its function name embedding.
    if node.get("type") == "function" and "sender" in node and "receiver" in node and "action" in node:
        func_name = node["action"]
        # Compute and store the embedding.
        original_embedding = get_embedding(func_name)
        node["embedding"] = original_embedding  # temporary embedding, will be updated later.
        call_info = {
            "order": current_order,
            "depth": depth,
            "sender": node["sender"],
            "receiver": node["receiver"],
            "function": func_name,
            "embedding": original_embedding
        }
        calls.append(call_info)
        logging.debug("Added call: order %d, depth %d, sender %s, receiver %s, function %s",
                      current_order, depth, node["sender"], node["receiver"], func_name)

    # Traverse children if they exist.
    for child in node.get("nodes", []):
        traverse_tree(child, depth + 1, calls, ignore_static_delegate)

def adjust_embeddings(calls):
    """
    Calculate the average embedding from all function calls,
    then subtract the average from each call's embedding and update it.
    """
    if not calls:
        return
    all_embeddings = np.array([call["embedding"] for call in calls])
    avg_embedding = np.mean(all_embeddings, axis=0)
    for call in calls:
        call["embedding"] = call["embedding"] - avg_embedding
    logging.debug("Adjusted embeddings by subtracting the average embedding.")

def detect_reentrancy(calls):
    """
    Detect the reentrancy pattern based on the updated conditions:
      (1) There exist two calls call_A and call_B whose function names are similar,
          i.e., cosine similarity between their embeddings > 0,
          and they must have the same sender.
      (2) There exists a call_C whose function name is contradicting call_A's function name,
          i.e., cosine similarity between embedding of call_A and call_C < 0,
          and call_C's receiver must be the same as call_A's receiver.
      (3) Their depths satisfy: depth_A > depth_C > depth_B and order_A < order_B < order_C.
    Instead of stopping at the first found triple, all valid triples are collected.
    Returns a list of tuples (call_A, call_B, call_C, sim_ab, sim_ac) where sim_ab is similarity between call_A and call_B,
    and sim_ac is similarity between call_A and call_C.
    Detailed logging is performed for every candidate triple.
    """
    valid_triples = []
    n = len(calls)
    for i in range(n):
        call_A = calls[i]
        for j in range(n):
            if i == j:
                continue
            call_B = calls[j]
            # Log the pair being compared.
            logging.debug("Evaluating pair: A(order %s, function '%s') and B(order %s, function '%s')",
                          call_A["order"], call_A["function"],
                          call_B["order"], call_B["function"])
            # (1) Check that call_A and call_B's function names are similar and they have the same sender.
            if call_A["sender"] != call_B["sender"]:
                logging.debug("Pair rejected due to different senders: A sender %s, B sender %s",
                              call_A["sender"], call_B["sender"])
                continue
            sim_ab = cosine_similarity(call_A["embedding"], call_B["embedding"])
            if sim_ab <= 0.2:
                logging.debug("Pair rejected due to low similarity (A,B): %.4f", sim_ab)
                continue
            # Ensure depth and order relationship for call_A and call_B.
            if not (call_A["depth"] <= call_B["depth"] and call_A["order"] < call_B["order"]):
                logging.debug("Pair rejected due to depth/order condition: A(depth %d, order %d), B(depth %d, order %d)",
                              call_A["depth"], call_A["order"],
                              call_B["depth"], call_B["order"])
                continue
            # (2) Look for call_C that is contradicting call_A and meets receiver condition.
            for k in range(n):
                if k == i or k == j:
                    continue
                call_C = calls[k]
                sim_ac = cosine_similarity(call_A["embedding"], call_C["embedding"])
                if sim_ac >= -0.1:
                    logging.debug("Pair rejected due to low similarity (A,C): %.4f", sim_ac)
                    continue
                # Check if call_C's receiver is the same as call_A's receiver.
                if call_C["receiver"] != call_A["receiver"]:
                    logging.debug("Candidate C rejected due to receiver mismatch: A receiver %s, C receiver %s",
                                  call_A["receiver"], call_C["receiver"])
                    continue
                # Check the depth and order conditions.
                if call_A["depth"] <= call_C["depth"] <= call_B["depth"] and call_A["order"] < call_B["order"] < call_C["order"]:
                    logging.info("Valid triple found: A(order %d), B(order %d), C(order %d) | sim(A,B)=%.4f, sim(A,C)=%.4f",
                                 call_A["order"], call_B["order"], call_C["order"], sim_ab, sim_ac)
                    valid_triples.append((call_A, call_B, call_C, sim_ab, sim_ac))
                else:
                    logging.debug("Candidate triple rejected due to depth/order condition: A(depth %d, order %d), C(depth %d, order %d), B(depth %d, order %d)",
                                  call_A["depth"], call_A["order"],
                                  call_C["depth"], call_C["order"],
                                  call_B["depth"], call_B["order"])
    return valid_triples

def main():
    parser = argparse.ArgumentParser(
        description=("Detect if an action tree JSON exhibits a reentrancy pattern with updated rules.\n\n"
                     "Each node in the JSON tree is annotated with:\n"
                     "  - order: the order from a preorder traversal.\n"
                     "  - depth: the level of the node in the tree (root is depth 1).\n\n"
                     "A function call node is defined as having type 'function' and containing the keys: sender, receiver, and action.\n"
                     "The updated reentrancy pattern is detected if there exists a triple of function calls:\n"
                     "  (1) Call A and Call B have similar function names (cosine similarity > 0) and the same sender,\n"
                     "  (2) Call C has a contradicting function name compared to Call A (cosine similarity < 0) and its receiver matches A's receiver,\n"
                     "  (3) They satisfy: depth_A > depth_C > depth_B and order_A < order_B < order_C.\n"
                     "Word embeddings for function names are computed using fastText. After obtaining all embeddings, the average is subtracted "
                     "from each to obtain the final embedding used for cosine similarity.\n"
                     "All possible valid (call_A, call_B, call_C) triples are reported with their similarity scores.\n"
                     "Detailed logging is performed to 'log.log' for each candidate triple and the reason for pass/failure.")
    )
    parser.add_argument(
        "--input-file", help="Path to the input JSON file representing the action tree", required=True)
    parser.add_argument(
        "--ignore-static-delegate", action="store_true",
        help="If set, nodes with call_type 'staticcall' or 'delegatecall' will be ignored during traversal.")
    args = parser.parse_args()

    # Load the JSON tree.
    with open(args.input_file, "r") as f:
        tree = json.load(f)

    # Reset the global order counter.
    global order_counter
    order_counter = 1

    # Traverse the tree and record all function call nodes (with their embeddings).
    calls = []
    traverse_tree(tree, depth=1, calls=calls, ignore_static_delegate=args.ignore_static_delegate)

    # Adjust embeddings: subtract average embedding from each function call's embedding.
    adjust_embeddings(calls)

    # Detect the updated reentrancy pattern and collect all valid triples.
    valid_triples = detect_reentrancy(calls)
    if valid_triples:
        print("Reentrancy detected! Found the following valid triples:\n")
        for idx, (call_A, call_B, call_C, sim_ab, sim_ac) in enumerate(valid_triples, 1):
            print(f"Triple {idx}:")
            print("  Call_A: order {}, depth {}, sender '{}', receiver '{}', function '{}'".format(
                call_A["order"], call_A["depth"], call_A["sender"], call_A["receiver"], call_A["function"]))
            print("  Call_B (similar function): order {}, depth {}, sender '{}', receiver '{}', function '{}'".format(
                call_B["order"], call_B["depth"], call_B["sender"], call_B["receiver"], call_B["function"]))
            print("    Similarity (A,B): {:.4f}".format(sim_ab))
            print("  Call_C (contradicting function): order {}, depth {}, sender '{}', receiver '{}', function '{}'".format(
                call_C["order"], call_C["depth"], call_C["sender"], call_C["receiver"], call_C["function"]))
            print("    Similarity (A,C): {:.4f}".format(sim_ac))
            print("")
    else:
        print("No reentrancy detected.")
        logging.info("No valid reentrancy triple was found.")

if __name__ == "__main__":
    main()