#!/usr/bin/python
###############################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.    #
#                                                                             #
#  Licensed under the Apache License Version 2.0 (the "License"). You may not #
#  use this file except in compliance with the License. A copy of the License #
#  is located at                                                              #
#                                                                             #
#      http://www.apache.org/licenses/                                        #
#                                                                             #
#  or in the "license" file accompanying this file. This file is distributed  #
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express #
#  or implied. See the License for the specific language governing permis-    #
#  sions and limitations under the License.                                   #
###############################################################################
import json
from lib.logger import Logger
from botocore.stub import Stubber

# Testing:
from lib.cloudformation import StackSet, Stacks

#@pytest.fixture(autouse=True)
#def cloudformation_stub():
#    with Stubber(Stacks.cfn_client) as stubber:
#        yield stubber
#        stubber.assert_no_pending_responses()

log_level = 'info'
logger = Logger(loglevel=log_level)
testpath = 'tests/lib-tests/'

stackset = StackSet(logger)
stacks = Stacks(logger)

#
# Read a file containing data and return it
#
def load_mock_data(path, filename):
    """
    test/mock data stored in a file
    """
    response = None
    try:
        datafile = open(path + filename,'rb')
    except Exception as e:
        print(e)
        raise e
    else:
        response = datafile.read()
    finally:
        datafile.close()

    return response

#------------------------------------------------------------------------------
# describe_stacks
#------------------------------------------------------------------------------
#def test_describe_stacks_all(cloudformation_stub):
def test_describe_stacks():

    stackname = 'SC-857343878074-pp-e55fxxxxxxxxx'
    mock_stacks = json.loads(load_mock_data(testpath, 'describe-stacks-1.json'))
    expected = mock_stacks

    stubber = Stubber(stacks.cfn_client)

    stubber.add_response(
        'describe_stacks',
        mock_stacks,
        {'StackName': stackname}
    )

    stubber.activate()
    stack_data = stacks.describe_stacks(stackname)
    assert stack_data == expected

# #------------------------------------------------------------------------------
# # describe_stacks_all
# #------------------------------------------------------------------------------
# Can't get this test to work - 'Unexpected API Call: A call was made but no additional calls expected. '
# botocore.exceptions.UnStubbedResponseError: Error getting response stub for operation DescribeStacks: Unexpected API Call: A call was made but no additional calls expected. Either the API Call was not stubbed or it was called multiple times.
# def test_describe_stacks_all():

#     mock_stacks = json.loads(load_mock_data(testpath, 'describe_stacks_all.json'))
#     expected = mock_stacks

#     stubber = Stubber(stacks.cfn_client)
#     stubber.add_response(
#         'describe_stacks',
#         mock_stacks,
#         {}
#     )
#     stubber.activate()

#     stack_data = stacks.describe_stacks_all()
#     assert stack_data == expected
