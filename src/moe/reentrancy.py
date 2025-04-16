#!/usr/bin/env python3
import json
import argparse

# Global counter for preorder order
order_counter = 1


def traverse_tree(node, depth, calls):
    """
    Traverse the action tree in preorder and assign order and depth.
    If the node represents a function call (i.e., its "type" is "function" and it contains sender, receiver, and action keys),
    record it as a dictionary with its order, depth, and call details.
    Then traverse its children under the "nodes" key.
    """
    global order_counter
    current_order = order_counter
    order_counter += 1

    # Annotate the node with order and depth attributes
    node["order"] = current_order
    node["depth"] = depth

    # If the node is a function call, record its details.
    # Updated: using "action" as the function name.
    if node.get("type") == "function" and "sender" in node and "receiver" in node and "action" in node:
        call_info = {
            "order": current_order,
            "depth": depth,
            "sender": node["sender"],
            "receiver": node["receiver"],
            "function": node["action"]  # using "action" key as function name
        }
        calls.append(call_info)

    # Traverse children if they exist.
    for child in node.get("nodes", []):
        traverse_tree(child, depth + 1, calls)


def is_inverse(call_a, call_b):
    """
    Returns True if call_b is the inverse of call_a.
    Inverse call is defined by having the sender and receiver swapped.
    The function name does not need to be the same.
    """
    return (call_a["sender"] == call_b["receiver"] and
            call_a["receiver"] == call_b["sender"])


def is_same_call(call_a, call_b):
    """
    Returns True if call_a and call_b are considered the same function call.
    For this detection, they must have identical sender, receiver, and function name.
    """
    return (call_a["function"] == call_b["function"] and
            call_a["sender"] == call_b["sender"] and
            call_a["receiver"] == call_b["receiver"])


def detect_reentrancy(calls):
    """
    Detect the reentrancy pattern based on the following updated conditions:
      - call_A and call_B are "same" calls (i.e., same sender, receiver, and function),
      - call_C is the inverse call of call_A (i.e., sender and receiver swapped; function name may differ),
      - Their depths satisfy: depth_A > depth_C > depth_B,
      - Their orders in the preorder traversal satisfy: order_A < order_B < order_C.
    If such a triple exists, the action tree exhibits reentrancy.
    """
    n = len(calls)
    for i in range(n):
        call_A = calls[i]
        for j in range(n):
            if i == j:
                continue
            call_B = calls[j]
            # Check same function call and that call_A is deeper than call_B and comes earlier in order.
            if not is_same_call(call_A, call_B):
                continue
            if not (call_A["depth"] > call_B["depth"] and call_A["order"] < call_B["order"]):
                continue
            # Now look for call_C that is an inverse call of call_A and satisfies the updated depth and order conditions.
            for k in range(n):
                if k == i or k == j:
                    continue
                call_C = calls[k]
                if not is_inverse(call_A, call_C):
                    continue
                if (call_A["depth"] > call_C["depth"] > call_B["depth"] and
                        call_A["order"] < call_B["order"] < call_C["order"]):
                    return True, (call_A, call_B, call_C)
    return False, None


def main():
    parser = argparse.ArgumentParser(
        description=("Detect if an action tree JSON exhibits reentrancy.\n\n"
                     "Each node in the JSON tree is annotated with:\n"
                     "  - order: the order from a preorder traversal.\n"
                     "  - depth: the level of the node in the tree (root is depth 1).\n\n"
                     "A function call node is defined as having type 'function' and containing the keys: sender, receiver, and action.\n"
                     "The reentrancy pattern is detected if there exists a triple of function calls:\n"
                     "  Let call_A and call_B be two calls with the same (sender, receiver, function), and\n"
                     "  call_C be an inverse call of call_A (i.e., sender and receiver swapped; function name may differ).\n"
                     "  They must satisfy: depth_A > depth_C > depth_B and order_A < order_B < order_C.")
    )
    parser.add_argument(
        "--input-file", help="Path to the input JSON file representing the action tree", required=True)
    args = parser.parse_args()

    # Load the JSON tree.
    with open(args.input_file, "r") as f:
        tree = json.load(f)

    # Reset the global order counter.
    global order_counter
    order_counter = 1

    # Traverse the tree and record all function call nodes.
    calls = []
    traverse_tree(tree, depth=1, calls=calls)

    # Detect the reentrancy pattern.
    detected, triple = detect_reentrancy(calls)
    if detected:
        call_A, call_B, call_C = triple
        print("Reentrancy detected!")
        print("Call_A (deepest): order {}, depth {}, sender '{}', receiver '{}', function '{}'".format(
            call_A["order"], call_A["depth"], call_A["sender"], call_A["receiver"], call_A["function"]))
        print("Call_B (shallowest same call candidate): order {}, depth {}, sender '{}', receiver '{}', function '{}'".format(
            call_B["order"], call_B["depth"], call_B["sender"], call_B["receiver"], call_B["function"]))
        print("Call_C (inverse call in between): order {}, depth {}, sender '{}', receiver '{}', function '{}'".format(
            call_C["order"], call_C["depth"], call_C["sender"], call_C["receiver"], call_C["function"]))
    else:
        print("No reentrancy detected.")


if __name__ == "__main__":
    main()
