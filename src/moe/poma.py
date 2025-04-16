#!/usr/bin/env python3
import json
import argparse

# Global counter for preorder order
order_counter = 1


def traverse_tree(node, depth, transfer_calls):
    """
    Traverse the action tree in preorder and assign order and depth.
    If the node represents a function call of type "transfer" or "transferFrom" and contains
    the required keys, record it in the transfer_calls list with an added "call_type" field.
    Then traverse its children under the "nodes" key.
    """
    global order_counter
    current_order = order_counter
    order_counter += 1

    # Annotate the node with order and depth attributes.
    node["order"] = current_order
    node["depth"] = depth

    if node.get("type") == "function":
        # Check for a "transfer" call.
        if node.get("action") == "transfer":
            # Ensure keys exist and the "values" field is a list with at least 2 elements.
            if "sender" in node and "receiver" in node and "values" in node:
                vals = node["values"]
                if isinstance(vals, list) and len(vals) >= 2:
                    transfer_info = {
                        "order": current_order,
                        "depth": depth,
                        "call_type": "transfer",
                        "sender": node["sender"],
                        "receiver": node["receiver"],
                        "values": vals  # values[0] and values[1] will be used.
                    }
                    transfer_calls.append(transfer_info)
        # Check for a "transferFrom" call.
        elif node.get("action") == "transferFrom":
            # Ensure keys exist, including a sender, receiver, and the "values" field as a list with at least 3 elements.
            if "sender" in node and "receiver" in node and "values" in node:
                vals = node["values"]
                if isinstance(vals, list) and len(vals) >= 3:
                    transfer_info = {
                        "order": current_order,
                        "depth": depth,
                        "call_type": "transferFrom",
                        "sender": node["sender"],
                        "receiver": node["receiver"],
                        # values[0], values[1], values[2] will be used.
                        "values": vals
                    }
                    transfer_calls.append(transfer_info)

    # Traverse children nodes if present.
    for child in node.get("nodes", []):
        traverse_tree(child, depth + 1, transfer_calls)


def form_transacts(transfer_calls):
    """
    Form valid transacts out of pairs of function calls.
    There are three cases:
    1. Two "transfer" calls form a transact if:
         (a) t1.receiver != t2.receiver,
         (b) t1.sender == t2.values[0],
         (c) t2.sender == t1.values[0].
       The transact is defined as:
         operator = t1.sender,
         pool = t2.sender,
         token_in = t1.receiver,
         token_out = t2.receiver,
         amount_in = t1.values[1],
         amount_out = t2.values[1].
    2. Two "transferFrom" calls form a transact if:
         (a) Their receivers differ,
         (b) The first call's values[0] equals the second call's values[1],
         (c) The first call's values[1] equals the second call's values[2].
       The transact is defined as:
         operator = t1.sender,
         pool = t2.sender,
         token_in = t1.receiver,
         token_out = t2.receiver,
         amount_in = t1.values[2],
         amount_out = t2.values[2].
    3. A "transferFrom" call (t1) and a "transfer" call (t2) form a transact if:
         (a) Their receivers differ,
         (b) t1.values[0] equals t2.values[0],
         (c) t1.values[1] equals t2.sender.
       The transact is defined as:
         operator = t1.sender,
         pool = t2.sender,
         token_in = t1.receiver,
         token_out = t2.receiver,
         amount_in = t1.values[2],
         amount_out = t2.values[1].
    Returns a list of transact dictionaries.
    """
    transacts = []
    n = len(transfer_calls)
    for i in range(n):
        t1 = transfer_calls[i]
        for j in range(i + 1, n):
            t2 = transfer_calls[j]
            # Case 1: Both calls are "transfer"
            if t1["call_type"] == "transfer" and t2["call_type"] == "transfer":
                if t1["receiver"] == t2["receiver"]:
                    continue
                if t1["sender"] != t2["values"][0]:
                    continue
                if t2["sender"] != t1["values"][0]:
                    continue
                transact = {
                    "operator": t1["sender"],
                    "pool": t2["sender"],
                    "token_in": t1["receiver"],
                    "token_out": t2["receiver"],
                    "amount_in": t1["values"][1],
                    "amount_out": t2["values"][1],
                    "t1_order": t1["order"],
                    "t2_order": t2["order"],
                    "t1_depth": t1["depth"],
                    "t2_depth": t2["depth"],
                    "call_types": (t1["call_type"], t2["call_type"])
                }
                transacts.append(transact)
            # Case 2: Both calls are "transferFrom"
            elif t1["call_type"] == "transferFrom" and t2["call_type"] == "transferFrom":
                if t1["receiver"] == t2["receiver"]:
                    continue
                if t1["values"][0] != t2["values"][1]:
                    continue
                if t1["values"][1] != t2["values"][2]:
                    continue
                transact = {
                    "operator": t1["sender"],
                    "pool": t2["sender"],
                    "token_in": t1["receiver"],
                    "token_out": t2["receiver"],
                    "amount_in": t1["values"][2],
                    "amount_out": t2["values"][2],
                    "t1_order": t1["order"],
                    "t2_order": t2["order"],
                    "t1_depth": t1["depth"],
                    "t2_depth": t2["depth"],
                    "call_types": (t1["call_type"], t2["call_type"])
                }
                transacts.append(transact)
            # Case 3: Combination of one "transferFrom" (t1) and one "transfer" (t2)
            elif t1["call_type"] == "transferFrom" and t2["call_type"] == "transfer":
                if t1["receiver"] == t2["receiver"]:
                    continue
                if t1["values"][0] != t2["values"][0]:
                    continue
                if t1["values"][1] != t2["sender"]:
                    continue
                transact = {
                    "operator": t1["sender"],
                    "pool": t2["sender"],
                    "token_in": t1["receiver"],
                    "token_out": t2["receiver"],
                    "amount_in": t1["values"][2],
                    "amount_out": t2["values"][1],
                    "t1_order": t1["order"],
                    "t2_order": t2["order"],
                    "t1_depth": t1["depth"],
                    "t2_depth": t2["depth"],
                    "call_types": (t1["call_type"], t2["call_type"])
                }
                transacts.append(transact)
    return transacts


def detect_price_manipulation(transacts):
    """
    Detect a "price manipulation" pattern in an action tree based on transacts.
    The conditions are:
      1. There exist three transacts, a, b, c, such that:
         - They all have the same pool.
         - a.token_in == c.token_out.
         - a.token_out == c.token_in == b.token_out.
    Returns a tuple (detected: bool, (a, b, c) if detected else None).
    """
    n = len(transacts)
    for i in range(n):
        a = transacts[i]
        for j in range(n):
            if i == j:
                continue
            b = transacts[j]
            for k in range(n):
                if k == i or k == j:
                    continue
                c = transacts[k]
                # Condition 1: All three transacts have the same pool.
                if not (a["pool"] == b["pool"] == c["pool"]):
                    continue
                # Condition 2: token_in of 'a' equals token_out of 'c'
                if a["token_in"] != c["token_out"]:
                    continue
                # Condition 3: token_out of 'a' equals token_in of 'c' and equals token_out of 'b'
                if a["token_out"] != c["token_in"] or a["token_out"] != b["token_out"]:
                    continue
                return True, (a, b, c)
    return False, None


def main():
    parser = argparse.ArgumentParser(
        description=("Detect if an action tree JSON exhibits price manipulation using both 'transfer' and 'transferFrom' calls.\n\n"
                     "Valid transacts are formed as follows:\n\n"
                     "1. Two 'transfer' calls form a transact if:\n"
                     "    (a) Their receivers differ,\n"
                     "    (b) The first call's sender equals the second call's values[0],\n"
                     "    (c) The second call's sender equals the first call's values[0].\n"
                     "   Transact: operator = first call's sender,\n"
                     "            pool = second call's sender,\n"
                     "            token_in = first call's receiver,\n"
                     "            token_out = second call's receiver,\n"
                     "            amount_in = first call's values[1],\n"
                     "            amount_out = second call's values[1].\n\n"
                     "2. Two 'transferFrom' calls form a transact if:\n"
                     "    (a) Their receivers differ,\n"
                     "    (b) The first call's values[0] equals the second call's values[1],\n"
                     "    (c) The first call's values[1] equals the second call's values[2].\n"
                     "   Transact: operator = first call's sender,\n"
                     "            pool = second call's sender,\n"
                     "            token_in = first call's receiver,\n"
                     "            token_out = second call's receiver,\n"
                     "            amount_in = first call's values[2],\n"
                     "            amount_out = second call's values[2].\n\n"
                     "3. A 'transferFrom' call (t1) and a 'transfer' call (t2) form a transact if:\n"
                     "    (a) Their receivers differ,\n"
                     "    (b) t1.values[0] equals t2.values[0],\n"
                     "    (c) t1.values[1] equals t2.sender.\n"
                     "   Transact: operator = t1.sender,\n"
                     "            pool = t2.sender,\n"
                     "            token_in = t1.receiver,\n"
                     "            token_out = t2.receiver,\n"
                     "            amount_in = t1.values[2],\n"
                     "            amount_out = t2.values[1].\n\n"
                     "An action tree is flagged for price manipulation if there exist three transacts, a, b, and c, such that:\n"
                     "    1) All three have the same pool,\n"
                     "    2) a.token_in equals c.token_out,\n"
                     "    3) a.token_out equals c.token_in and equals b.token_out.")
    )
    parser.add_argument(
        "--input-file", help="Path to the input JSON file representing the action tree", required=True)
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose mode to print each transact detected")
    args = parser.parse_args()

    # Load the JSON tree from file.
    with open(args.input_file, "r") as f:
        tree = json.load(f)

    # Reset the global order counter.
    global order_counter
    order_counter = 1

    # Traverse the tree to gather all "transfer" and "transferFrom" function call nodes.
    transfer_calls = []
    traverse_tree(tree, depth=1, transfer_calls=transfer_calls)

    # Form valid transacts from the collected calls.
    transacts = form_transacts(transfer_calls)

    # If verbose mode is enabled, print all transacts detected.
    if args.verbose:
        if transacts:
            print("Transacts detected:")
            for idx, tx in enumerate(transacts, start=1):
                print(f"Transact {idx}: operator='{tx['operator']}', pool='{tx['pool']}', token_in='{tx['token_in']}', token_out='{tx['token_out']}', amount_in='{tx['amount_in']}', amount_out='{tx['amount_out']}' (formed from orders {tx['t1_order']} and {tx['t2_order']})")
        else:
            print("No valid transacts formed from the provided action tree.")

    # Detect the price manipulation pattern using transacts.
    detected, triple = detect_price_manipulation(transacts)
    if detected:
        a, b, c = triple
        print("\nPrice Manipulation detected!")
        print("Transact A: operator '{}', pool '{}', token_in '{}', token_out '{}', amount_in '{}', amount_out '{}' (formed from orders {} and {})".format(
            a["operator"], a["pool"], a["token_in"], a["token_out"],
            a["amount_in"], a["amount_out"], a["t1_order"], a["t2_order"]))
        print("Transact B: operator '{}', pool '{}', token_in '{}', token_out '{}', amount_in '{}', amount_out '{}' (formed from orders {} and {})".format(
            b["operator"], b["pool"], b["token_in"], b["token_out"],
            b["amount_in"], b["amount_out"], b["t1_order"], b["t2_order"]))
        print("Transact C: operator '{}', pool '{}', token_in '{}', token_out '{}', amount_in '{}', amount_out '{}' (formed from orders {} and {})".format(
            c["operator"], c["pool"], c["token_in"], c["token_out"],
            c["amount_in"], c["amount_out"], c["t1_order"], c["t2_order"]))
    else:
        print("\nNo price manipulation detected.")


if __name__ == "__main__":
    main()
