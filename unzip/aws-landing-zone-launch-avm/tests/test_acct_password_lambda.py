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
"""
Simple test to validate that the request format coming from the Cfn template
will turn into a valid API call.
"""
from copy import deepcopy
from botocore.stub import Stubber
import pytest
import update_acct_password_policy as policy
from lib.logger import Logger
import lib.crhelper # needed to mock the library
from pytest_mock import mocker

log_level = 'info'
logger = Logger(loglevel=log_level)
testpath = 'tests/test_data/update_admin_password_policy/'

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

TEST_DATA = {
    'RequestType': 'INVALID',
    'RequestId': 'test_request_id',
    'ResponseURL': 'https://bogus.bogus.fake',
    'ResourceProperties': {
        'HardExpiry': False,
        'AllowUsersToChangePassword': True,
        'MaxPasswordAge': 90,
        'MinimumPasswordLength': 12,
        'PasswordReusePrevention': 6,
        'RequireLowercaseCharacters': True,
        'RequireNumbers': True,
        'RequireSymbols': True,
        'RequireUppercaseCharacters': True,
        'ServiceToken': 'servicetokenplaceholder'
    }
}

class context:
    aws_request_id = 'test_request_id'
    def get_remaining_time_in_millis(self):
        return 900000

test_context = context()

event = {}

stubber = Stubber(policy.iam) # Stub out the iam API

#----------------------------------------------------------------------
# date_handler
#----------------------------------------------------------------------
def date_handler(obj):
    """date_handler: handles dates embedded in the json returned from the api"""
    if not hasattr(obj, 'isoformat'):
        raise TypeError

    return obj.isoformat()

#------------------------------------------------------------------------------
# test_010_create
#------------------------------------------------------------------------------
def test_010_create(mocker):

    event = deepcopy(TEST_DATA)
    event['RequestType'] = 'create'
    mocker.patch('lib.crhelper.send', return_value='0')
    stubber.add_response(
        'update_account_password_policy',
        {}
    )

    stubber.activate()

    policy.lambda_handler(event, test_context)

    # Test is successful if no errors - no data is returned

#------------------------------------------------------------------------------
# test_020_update
#------------------------------------------------------------------------------
def test_020_update(mocker):

    event = deepcopy(TEST_DATA)
    event['RequestType'] = 'update'
    mocker.patch('lib.crhelper.send', return_value='0')
    stubber.add_response(
        'update_account_password_policy',
        {}
    )

    stubber.activate()

    policy.lambda_handler(event, test_context)

    # Test is successful if no errors - no data is returned

#------------------------------------------------------------------------------
# test_030_delete
#------------------------------------------------------------------------------
def test_030_delete(mocker):

    event = deepcopy(TEST_DATA)
    event['RequestType'] = 'delete'
    mocker.patch('lib.crhelper.send', return_value='0')
    stubber.add_response(
        'delete_account_password_policy',
        {}
    )

    stubber.activate()

    policy.lambda_handler(event, test_context)

#------------------------------------------------------------------------------
# test_040_invalid_requesttype
#------------------------------------------------------------------------------
def test_040_invalid_requesttype(mocker):

    event = deepcopy(TEST_DATA)
    event['RequestType'] = 'badrequesttype'
    mocker.patch('lib.crhelper.send', return_value='0')

    with pytest.raises(ValueError):
        policy.lambda_handler(event, test_context)
