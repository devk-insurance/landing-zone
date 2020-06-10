###############################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.    #
#                                                                             #
#  Licensed under the Apache License, Version 2.0 (the "License").            #
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at                                        #
#                                                                             #
#      http://www.apache.org/licenses/LICENSE-2.0                             #
#                                                                             #
#  or in the "license" file accompanying this file. This file is distributed  #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express #
#  or implied. See the License for the specific language governing permissions#
#  and limitations under the License.                                         #
###############################################################################


def flip_dict_properties(key_value_map: dict) -> dict:
    """This function returns the dictionary with flipped
    keys and values

    :param key_value_map:
    :return: dictionary with flipped key and value

    Example:
    Input: {key1: value1,
            key2: value1,
            key3: value2}
    Output: {value1: [key1, key2],
             value2: [key3]}

    """
    flipped_dict = {}
    for key, value in key_value_map.items():
        if value in flipped_dict:
            flipped_dict[value].append(key)
        else:
            flipped_dict[value] = [key]
    return flipped_dict


def join_dict_per_key_value_relation(dict_1: dict, dict_2: dict) -> dict:
    """ This function joins two dictionaries if the value of dict1 matches
    with the key of the dict 2.
    Condition: the value of the dict 1 must be of list type

    :param dict_1: example: {key1: [value1, value2]}
    :param dict_2: example: {value1: [a, b], value2: [x, y]}
    :return: joined dict example: {key1: [a, b, x, y]}
    """
    joined_dict = {}
    for key, value in dict_1.items():
        reduced_list = get_reduced_merged_list(dict_2, value)
        joined_dict[key] = reduced_list
    return joined_dict


def get_reduced_merged_list(key_value_map: dict, array: list) -> list:
    """ This function returns reduced and merged list of values for a
    given map if the keys match the items in the array


    :param key_value_map: example: {value1: [a, b], value2: [x, y]}
    :param array: example: [value1, value2]
    :return: reduced and merged list example: [a, b, x, y]
    """
    if isinstance(array, list):
        merged_list = [key_value_map.get(item, item) for item in array]
        return [item for sublist in merged_list for item in sublist]
    else:
        raise TypeError("Array must be of list type.")