######################################################################################################################
#  Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://aws.amazon.com/asl/                                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

import re


def sanitize(name, space_allowed=False, replace_with_character='_'):
    # This function will replace any character other than [a-zA-Z0-9._-] with '_'
    if space_allowed:
        sanitized_name = re.sub(r'([^\sa-zA-Z0-9._-])', replace_with_character, name)
    else:
        sanitized_name = re.sub(r'([^a-zA-Z0-9._-])', replace_with_character, name)
    return sanitized_name

def trim_length(string, length):
    if len(string) > length:
        return string[:length]
    else:
        return string
