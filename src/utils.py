
def find_element_by_address(
        data, 
        startindex, 
        target):
        
    for i in range(startindex, len(data)):
        if data[i]['from_address'] == target:
            return i
    return -1


def split_signature(signature):
    split_position = signature.find('(')
    first_part = signature[:split_position]
    rest_part = signature[split_position:]
    return first_part, rest_part


def build_tree(data):
    nodes = {}
    tree = {}
    prev_parent_id = None

    for entry in data:
        entry['nodes'] = []
        nodes[entry['id']] = entry

    for entry in data:
        if entry['id'] == '':
            tree = entry
        else:
            if entry['type'] != 'event':
                parent_id = '_'.join(entry['id'].split('_')[:-1])
                prev_parent_id = entry['id']
                if parent_id in nodes:
                    nodes[parent_id]['nodes'].append(entry)

            else:
                if prev_parent_id in nodes:
                    nodes[prev_parent_id]['nodes'].append(entry)

    return tree
