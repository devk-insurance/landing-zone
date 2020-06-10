##############################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
#                                                                            #
#  Licensed under the Apache License, Version 2.0 (the "License").           #
#  You may not use this file except in compliance                            #
#  with the License. A copy of the License is located at                     #
#                                                                            #
#      http://www.apache.org/licenses/LICENSE-2.0                            #
#                                                                            #
#  or in the "license" file accompanying this file. This file is             #
#  distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  #
#  KIND, express or implied. See the License for the specific language       #
#  governing permissions  and limitations under the License.                 #
##############################################################################
import pytest
from lib.logger import Logger
import lib.list_manipulation as list_util
import lib.dict_manipulation as dict_util
from manifest.manifest_parser import BaselineResourceParser

log_level = 'info'
logger = Logger(loglevel=log_level)

ssp = BaselineResourceParser(logger)


def test_list_item_conversion():
    list_of_numbers = [1234, 5678]
    list_of_strings = ssp._convert_list_values_to_string(list_of_numbers)
    for string in list_of_strings:
        assert type(string) is str

def test_remove_empty_strings():
    list_with_empty_string = ['str1', 'str2', '']
    list_without_empty_string = ['str1', 'str2']
    returned_list = list_util.remove_empty_strings(list_with_empty_string)
    assert returned_list == list_without_empty_string

def test_strip_list_items():
    items_with_whitespace = ['str1 ', ' str2']
    items_without_whitespace = ['str1', 'str2']
    returned_list = list_util.strip_list_items(items_with_whitespace)
    assert returned_list == items_without_whitespace

def test_flip_key_value():
    input = {
    'key1': 'value1',
    'key2': 'value1',
    'key3': 'value2'
    }
    output = {
    'value1': ['key1', 'key2'],
    'value2': ['key3']
    }
    response = dict_util.flip_dict_properties(input)
    assert response == output

def test_join_dict_per_key_value_relation():
    dict_a = {
    'key1': ['value1', 'value2']
    }
    dict_b = {
    'value1': ['a', 'b'],
    'value2': ['x', 'y']
    }
    joined_dict = {
    'key1': ['a', 'b', 'x', 'y']
    }
    response = dict_util.join_dict_per_key_value_relation(dict_a, dict_b)
    assert response == joined_dict

def test_get_reduced_merged_list():
    dict_a = {
    'value1': ['a', 'b'],
    'value2': ['x', 'y']
    }
    list_a = ['value1', 'value2']
    reduced_merged_list = ['a', 'b', 'x', 'y']
    response = dict_util.get_reduced_merged_list(dict_a, list_a)
    assert response == reduced_merged_list

def test_get_reduced_merged_list_exception():
    with pytest.raises(TypeError, match=r"Array must be of list type."):
            dict_a = {
            'value1': ['a', 'b'],
            'value2': ['x', 'y']
            }
            list_a = 'value1'
            reduced_merged_list = ['a', 'b', 'x', 'y']
            response = dict_util.get_reduced_merged_list(dict_a, list_a)
