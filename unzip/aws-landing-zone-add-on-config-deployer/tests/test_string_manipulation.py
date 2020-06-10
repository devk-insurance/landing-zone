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
from lib.string_manipulation import sanitize, trim_length_from_end, trim_string_from_front


def test_sanitize():
    non_sanitized_string = 'I s@nitize $tring exc*pt_underscore-hypen.'
    sanitized_string_allow_space = 'I s_nitize _tring exc_pt_underscore-hypen.'
    sanitized_string_no_space_replace_hypen = \
        'I-s-nitize--tring-exc-pt_underscore-hypen.'
    assert sanitize(non_sanitized_string,True) == \
           sanitized_string_allow_space
    assert sanitize(non_sanitized_string, False,'-') == \
           sanitized_string_no_space_replace_hypen


def test_trim_length_from_end():
    actual_string = "EighteenCharacters"
    eight_char_string = "Eighteen"
    assert trim_length_from_end(actual_string, 8) == eight_char_string
    assert trim_length_from_end(actual_string, 18) == actual_string
    assert trim_length_from_end(actual_string, 20) == actual_string


def test_trim_string_from_front():
    actual_string = "abcdefgh"
    start_string = "abc"
    expected_result = "defgh"
    assert trim_string_from_front(actual_string, start_string) == expected_result
