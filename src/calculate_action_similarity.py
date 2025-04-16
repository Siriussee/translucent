#!/usr/bin/env python3
import json
import argparse
import math
import itertools
import fasttext  # fasttext API for word/sentence embeddings


def print_tree(node, indent="", exclude=set(), collected_actions=None):
    """
    Recursively prints a tree structure based on the 'action' field.
    A node is printed only if either:
       - It has no 'call_type' field, or
       - Its 'call_type' value is not in the exclude set.
    If a node is not printed, its children are processed with the same indentation.
    If a node is printed, its children are indented further.

    Additionally, if the node is printed, the 'action' field is added to collected_actions.
    """
    if collected_actions is None:
        collected_actions = []

    call_type = node.get("call_type")
    should_print = (call_type is None) or (call_type not in exclude)

    if should_print:
        action = node.get("action", "N/A")
        print(indent + action)
        collected_actions.append(action)
        new_indent = indent + "  "
    else:
        new_indent = indent

    for child in node.get("nodes", []):
        print_tree(child, new_indent, exclude, collected_actions)

    return collected_actions


def cosine_similarity(vec1, vec2):
    """
    Calculate cosine similarity between two vectors.
    Cosine similarity = (vec1 . vec2) / (||vec1|| * ||vec2||)
    """
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def main():
    parser = argparse.ArgumentParser(
        description=("Visualize a JSON tree based on the 'action' field in each node.\n"
                     "Optionally filter out nodes based on their 'call_type' field. "
                     "Possible call_type values: call, staticcall, create, suicide."))
    parser.add_argument(
        "--input-file", help="Path to the input JSON file representing the tree", required=True)
    parser.add_argument("--exclude", nargs="*", choices=["call", "staticcall", "create", "suicide"],
                        default=[], help="List of 'call_type' values to exclude from visualization")
    args = parser.parse_args()

    # Read and load the JSON tree from the input file.
    with open(args.input_file, 'r') as f:
        tree = json.load(f)

    print("Tree Visualization:\n")
    # Traverse the tree and collect the printed actions.
    collected_actions = print_tree(tree, indent="", exclude=set(args.exclude))

    # Load the pre-trained fasttext model from the cache folder.
    model_path = "cache/cc.en.300.bin"
    print("\nLoading fasttext model from '{}'...".format(model_path))
    model = fasttext.load_model(model_path)
    print("Fasttext model loaded.\n")

    # Compute the embedding for each action using fasttext's sentence vector method.
    action_embeddings = {}
    for action in collected_actions:
        embedding = model.get_sentence_vector(action)
        action_embeddings[action] = embedding

    # Calculate the average embedding for all actions.
    # zip(*action_embeddings.values()) aggregates each dimension across all embeddings.
    average_embedding = [sum(dim_values) / len(action_embeddings)
                         for dim_values in zip(*action_embeddings.values())]

    # Adjust each action's embedding by subtracting the average embedding.
    corrected_embeddings = {}
    for action, embedding in action_embeddings.items():
        corrected = [value - avg for value,
                     avg in zip(embedding, average_embedding)]
        corrected_embeddings[action] = corrected

    # Compute all unique pairwise combinations, then sort each pair and deduplicate.
    unique_pairs = set()
    for pair in itertools.combinations(collected_actions, 2):
        sorted_pair = tuple(sorted(pair))
        unique_pairs.add(sorted_pair)

    # Optionally, sort the unique pairs for consistent output.
    sorted_unique_pairs = sorted(unique_pairs)

    # Compute cosine similarity values for each unique pair using corrected embeddings,
    # and store the results in a list.
    similarity_results = []
    for action1, action2 in sorted_unique_pairs:
        vec1 = corrected_embeddings[action1]
        vec2 = corrected_embeddings[action2]
        similarity = cosine_similarity(vec1, vec2)
        similarity_results.append((action1, action2, similarity))

    # Sort the results based on the cosine similarity value.
    similarity_results.sort(key=lambda x: x[2])

    # Print the similarities, trimmed to 4 decimal places, in sorted order.
    print("Pairwise Cosine Similarities (using corrected embeddings, sorted by similarity):")
    for action1, action2, similarity in similarity_results:
        print("[{}], [{}]: {:.4f}".format(action1, action2, similarity))


if __name__ == '__main__':
    main()
