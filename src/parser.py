from utils import find_element_by_address, split_signature
from filelock import FileLock
from hex_decoder import write_json, read_json
import copy


def convert_input_to_values_arrays(parameters_array, value_array_origin, p=0, isevent=False):
    # print(parameters_array)
    parameters_name = []
    value_array = copy.deepcopy(value_array_origin)

    if len(value_array) > 0:
        parameters_name = parameters_array[0]

    # print(parameters_name)
    decoded_array = []

    # add check here as well
    if len(value_array) + p < len(parameters_name):
        if not isevent:
            return [None]
        else:
            while len(value_array) + p < len(parameters_name):
                value_array.append(None)

    for i in range(0, len(parameters_name)):
        parameter_type = parameters_name[i]
        # print(type(values))
        if i + p >= len(value_array):
            decoded_array.append(None)
            continue

        value = value_array[i + p]

        if isinstance(parameter_type, list):
            decoded_array.append(convert_input_to_values_arrays(
                [parameter_type], value_array, p))
            p = p + len(parameter_type) - 1

        else:
            if '[]' in parameter_type:
                # do the array processing
                if value != None:
                    position = int(value, 16) // 32
                    # fix the bug here index out of range, add checks here
                    if position >= len(value_array):
                        decoded_array.append([None])
                        continue

                    array_length = int(value_array[position], 16)

                    if position + array_length >= len(value_array):
                        decoded_array.append([None])
                        continue

                    decoded_values = []
                    for i in range(1, array_length + 1):
                        data = value_array[position + i]
                        decoded_values.append(
                            convert_input_to_values(parameter_type, data))

                    decoded_array.append(decoded_values)

                else:
                    decoded_array.append([None])

            else:
                decoded_array.append(
                    convert_input_to_values(parameter_type, value))

    # print(decoded_array)
    return decoded_array


def convert_input_to_values(parameters_type, value):
    # print(value)
    if value == None:
        return None

    if 'uint' in parameters_type:
        decode_value = int(value, 16)
        return decode_value

    elif 'address' in parameters_type:
        stripped_value = value.lstrip('0')
        return "0x" + stripped_value

    else:
        return value


def parse_parameters_via_split(parameter_string):
    ignored = False

    if ')[]' in parameter_string:
        ignored = True

    stack = [[]]
    buffer = ""

    i = 0

    while i < len(parameter_string):
        char = parameter_string[i]

        if char == "(":
            if buffer.strip():
                stack[-1].append(buffer.strip())
                buffer = ""
            stack.append([])

        elif char == ")":
            if buffer.strip():
                stack[-1].append(buffer.strip())
                buffer = ""

            completed_level = stack.pop()

            if i < len(parameter_string) - 2:
                if parameter_string[i + 1] == '[' and parameter_string[i + 2] == ']':

                    # Wrap the completed level with array notation when popping
                    completed_level = ['[]', *completed_level]
                    i = i + 3

            stack[-1].append(completed_level)

        elif char == ",":
            if buffer.strip():
                stack[-1].append(buffer.strip())
                buffer = ""

        else:
            buffer += char

        i = i + 1

    if buffer.strip():
        stack[-1].append(buffer.strip())

    return stack[0], ignored


def add_elements_in_range(
        from_structure,
        to_structure,
        start_index,
        end_index,
        appended_index,
        current_total,
        current_matched,
        current_igored):

    total_nodes = current_total
    name_match = current_matched
    found_create = False
    found_ether = False
    found_suicide = False
    total_ignored = current_igored

    if appended_index >= start_index and appended_index >= end_index:
        return appended_index, total_nodes, name_match, found_ether, found_create, found_suicide, total_ignored

    elif appended_index >= start_index and appended_index < end_index:
        start_index = appended_index + 1

    for i in range(start_index, end_index + 1):
        total_nodes += 1
        name_match += 1

        row = from_structure[i]
        # print(row)
        name, parameters = split_signature(row['name'])
        ignored = False

        if parameters == '(unknown)':
            name_match -= 1
            parameters = None

        if name == 'ether_transfer':
            found_ether = True
            ignored = True

        elif name == 'create_contract':
            found_create = True
            ignored = True

        elif name == 'suicide_contract':
            found_suicide = True
            ignored = True

        # process the parameters  input for functions here maybe
        processed_para = [None]

        if parameters != '(unknown)' and parameters != '()' and parameters != None:
            processed_para, ignored = parse_parameters_via_split(parameters)

            if ignored != True:
                # print(processed_para)
                converted_values = convert_input_to_values_arrays(
                    processed_para, row['inputs'])
            else:
                converted_values = []
        else:
            converted_values = []

        if ignored:
            total_ignored = total_ignored + 1

        to_structure.append({
            'id': row['trace_id'],
            'type': 'function',
            'call_type': row['call_type'],
            'action': name,
            'ignored': ignored,
            'parameters': processed_para,
            'values': converted_values,
            'values_raw': row['inputs'],
            'sender': row['from_address'],
            'receiver': row['to_address'],
            'hex': row['hex']
        })

    return end_index, total_nodes, name_match, found_ether, found_create, found_suicide, total_ignored


def extract_function(
        results,
        transaction_hash):

    call_prefix = f"call_{transaction_hash}_"
    create_prefix = f"create_{transaction_hash}_"
    suicide_prefix = f"suicide_{transaction_hash}_"
    processed_data = []

    for row in results:
        if row.trace_id.startswith(call_prefix):
            processed_trace_id = row.trace_id[len(call_prefix):]
            # modify here to take the values after first 10
            processed_input = row.input[:10]
            rest_input = row.input[10:]

            chunk_size = 64
            blocks = [rest_input[i:i + chunk_size]
                      for i in range(0, len(rest_input), chunk_size)]

            processed_data.append({
                'trace_id': processed_trace_id,
                'hex': processed_input,
                'name': "",
                'call_type': row.call_type,
                'from_address': row.from_address,
                'to_address': row.to_address,
                'inputs': blocks
            })

        elif row.trace_id.startswith(create_prefix):
            # modify here to take the values after first 10
            processed_trace_id = row.trace_id[len(create_prefix):]
            processed_input = '0xff'
            processed_data.append({
                'trace_id': processed_trace_id,
                'hex': processed_input,
                'name': "",
                'call_type': 'create',  # we define create as create
                'from_address': row.from_address,
                'to_address': row.to_address,
                'inputs': []
            })

        elif row.trace_id.startswith(suicide_prefix):
            # modify here to take the values after first 10
            processed_trace_id = row.trace_id[len(suicide_prefix):]
            processed_input = None
            processed_data.append({
                'trace_id': processed_trace_id,
                'hex': processed_input,
                'name': "",
                'call_type': 'suicide',  # we define suicide as suicide
                'from_address': row.from_address,
                'to_address': row.to_address,
                'inputs': []
            })

        else:
            print(f"unknown traceid: {row.trace_id}")

    def sort_key(trace_id):
        parts = trace_id.split('_')
        return tuple(int(part) if part.isdigit() else float('inf') for part in parts)

    processed_data.sort(key=lambda x: sort_key(x['trace_id']))

    return processed_data


def get_event_input(log_index, event_input):
    for row in event_input:
        if row.log_index == log_index:
            return row.topics_except_first

    return []


def extract_event(event_results, event_input):

    processed_event = []

    for row in event_results:

        processed_event.append({
            'index': row.log_index,
            'hex': row.event,
            'name': "",
            'address': row.address,
            'inputs': get_event_input(row.log_index, event_input)
        })

    return processed_event


def read_count(file_path):

    lock_path = file_path + '.lock'
    lock = FileLock(lock_path)

    with lock:
        data = read_json(file_path)
        return data.get('count', 0)


def update_count(file_path,
                 increment):

    lock_path = file_path + '.lock'
    lock = FileLock(lock_path)

    with lock:
        data = read_json(file_path)
        data['count'] = data.get('count', 0) + increment
        write_json(file_path, data)


def merge_events_functions(
        processed_event,
        current_total,
        current_matched,
        processed_data,
        current_igored,
        output_path):

    merged_tree = []
    unfound_addr = set()
    unmatched = []
    current_index = 0
    appended_index = -1
    total_nodes = current_total
    name_match = current_matched
    total_ignored = current_igored

    ether_count_path = f'{output_path}/ether_count.json'
    create_count_path = f'{output_path}/create_count.json'
    suicide_count_path = f'{output_path}/suicide_count.json'

    have_create = False
    have_ether = False
    have_suicide = False
    check_ether = False
    check_create = False
    check_suicide = False

    for row in processed_event:
        target_addr = row['address']

        if target_addr in unfound_addr:
            unmatched.append(row)
            continue

        else:
            i = find_element_by_address(
                processed_data, current_index, target_addr)

            if i == -1:
                unmatched.append(row)
                unfound_addr.add(target_addr)

            else:
                total_nodes += 1
                name_match += 1
                appended_index, total_nodes, name_match, check_ether, check_create, check_suicide, total_ignored = add_elements_in_range(
                    processed_data, merged_tree, current_index, i, appended_index, total_nodes, name_match, total_ignored)

                have_create = have_create or check_create
                have_ether = have_ether or check_ether
                have_suicide = have_suicide or check_suicide

                name, parameters = split_signature(row['name'])

                if parameters == '(unknown)':
                    name_match -= 1

                processed_para = [None]
                ignored = False

                if parameters != '(unknown)' and parameters != '()' and parameters != None:
                    processed_para, ignored = parse_parameters_via_split(
                        parameters)

                    if ignored != True:
                        converted_values = convert_input_to_values_arrays(
                            processed_para, row['inputs'], isevent=True)
                    else:
                        converted_values = []
                else:
                    converted_values = []

                if ignored:
                    current_igored = current_igored + 1

                # process the parameters input for functions here maybe
                # modify this later for events
                merged_tree.append({
                    'id': row['index'],
                    'type': 'event',
                    'action': name,
                    'ignored': ignored,
                    'parameters': processed_para,
                    'values': converted_values,
                    'values_raw': row['inputs'],
                    'sender': row['address'],
                    'receiver': None,
                    'hex': row['hex']
                })
                current_index = i

    i = len(processed_data) - 1
    appended_index, total_nodes, name_match, check_ether, check_create, check_suicide, total_ignored = add_elements_in_range(
        processed_data, merged_tree, current_index, i, appended_index, total_nodes, name_match, total_ignored)

    have_create = have_create or check_create
    have_ether = have_ether or check_ether
    have_suicide = have_suicide or check_suicide

    if have_create == True:
        update_count(create_count_path, 1)

    if have_ether == True:
        update_count(ether_count_path, 1)

    if have_suicide == True:
        update_count(suicide_count_path, 1)

    return merged_tree, unmatched, total_nodes, name_match, total_ignored
