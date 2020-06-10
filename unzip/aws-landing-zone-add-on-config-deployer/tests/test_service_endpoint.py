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
from lib.helper import get_service_endpoint


def test_service_endpoint():
    service_name = 's3'
    region_name = 'us-east-1'
    returned_end_point = get_service_endpoint(service_name, region_name)
    expected_end_point = "https://" + service_name + "." + region_name + ".amazonaws.com"
    assert expected_end_point == returned_end_point

