#!/usr/bin/env python3
import json
import argparse

order_counter = 1

def annotate_tree(node, depth=1):
    """
    Annotate the tree with 'depth' and 'order' attributes similar to reentrancy.py.
    Every node gets assigned the current global order number and its depth.
    """
    global order_counter
    node["depth"] = depth
    node["order"] = order_counter
    order_counter += 1
    for child in node.get("nodes", []):
        annotate_tree(child, depth + 1)

def print_tree(node, indent="", exclude=set()):
    """
    Recursively prints a tree structure based on the 'action' field.
    A node is printed only if either:
       - It has no 'call_type' field, or
       - Its 'call_type' value is not in the exclude set.
    If a node is printed, its children are indented further.
    The format is:
       sender_short -> receiver_short: action (depth: <depth>, order: <order>)
    If sender or receiver is absent, only the action is shown.
    """
    call_type = node.get("call_type")
    should_print = (call_type is None) or (call_type not in exclude)

    if should_print:
        action = node.get("action", "N/A")
        depth = node.get("depth", "N/A")
        order = node.get("order", "N/A")
        sender = node.get("sender")
        receiver = node.get("receiver")
        if sender and receiver:
            line = f"{sender[:8]} -> {receiver[:8]}: {action} (depth: {depth}, order: {order})"
        else:
            line = f"{action} (depth: {depth}, order: {order})"
        print(indent + line)
        new_indent = indent + "  "
    else:
        new_indent = indent

    for child in node.get("nodes", []):
        print_tree(child, indent=new_indent, exclude=exclude)

def main():
    parser = argparse.ArgumentParser(
        description=("Visualize a JSON tree based on the 'action' field in each node.\n"
                     "Optionally filter out nodes based on their 'call_type' field. "
                     "Possible call_type values: call, staticcall, create, suicide, delegatecall.\n\n"
                     "This visualization annotates tree nodes with 'depth' and 'order' using a preorder traversal, "
                     "similar to the logic in reentrancy.py."))
    parser.add_argument(
        "--input-file", help="Path to the input JSON file representing the tree", required=True)
    parser.add_argument("--exclude", nargs="*", choices=["call", "staticcall", "create", "suicide", "delegatecall"],
                        default=[], help="List of 'call_type' values to exclude from visualization")
    args = parser.parse_args()

    with open(args.input_file, "r") as f:
        tree = json.load(f)

    global order_counter
    order_counter = 1  # Reset counter before annotating
    annotate_tree(tree, depth=1)

    print("Tree Visualization:\n")
    print_tree(tree, indent="", exclude=set(args.exclude))

if __name__ == '__main__':
    main()