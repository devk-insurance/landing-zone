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
from pytest_mock import mocker
import launch_avm
from lib.logger import Logger
from botocore.stub import Stubber

log_level = 'info'
logger = Logger(loglevel=log_level)
wait_time = '10'
batch_size = '10'
manifest_file_path = './tests/launch_avm/manifest.yaml'
manifest = None
testpath = 'tests/search_provisioned_products/'

avm = launch_avm.LaunchAVM(
    logger,
    wait_time,
    manifest_file_path,
    'some arn here',
    batch_size
)
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

#----------------------------------------------------------------------
# date_handler
#----------------------------------------------------------------------
def date_handler(obj):
    """date_handler: handles dates embedded in the json returned from the api"""
    if not hasattr(obj, 'isoformat'):
        raise TypeError

    return obj.isoformat()

#------------------------------------------------------------------------------
# test_010_stack_status
#------------------------------------------------------------------------------
def test_010_stack_status(mocker):

    mock_stacks = json.loads(load_mock_data(testpath, 'describe_stacks_all.json'))
    mocker.patch.object(launch_avm.Stacks, 'describe_stacks_all')
    launch_avm.Stacks.describe_stacks_all.return_value = mock_stacks

    expected = {'StackStatus': 'NOTFOUND', 'ExistingParameterKeys': []}
    stackname = 'doesnotexist'
    stack_data = launch_avm.get_stack_data(stackname, logger)
    assert stack_data == expected

    # expected = {'ExistingParameterKeys': ['OUName','MergeAddOn','AVMProduct','ClusterSize','SpokeRegions','Region','DomainAdminEmail','CognitoAdminEmail','DOMAINNAME','AccountName'],'StackStatus': 'UPDATE_COMPLETE'}
    expected = json.loads(load_mock_data(testpath, 'get_stack_data_response.json'))
    stackname = 'SC-123412341234-pp-e55fxxxxxxxxx'
    stack_data = launch_avm.get_stack_data(stackname, logger)
    assert stack_data == expected

#------------------------------------------------------------------------------
# test_020_search
#------------------------------------------------------------------------------
def test_020_search(mocker):

    stackname = 'SC-123412341234-pp-e55fxxxxxxxxx'

    mock_stacks = json.loads(load_mock_data(testpath, 'describe_stacks_all.json'))
    mocker.patch.object(launch_avm.Stacks, 'describe_stacks_all')
    launch_avm.Stacks.describe_stacks_all.return_value = mock_stacks

    mock_products = json.loads(load_mock_data(testpath, 'search_provisioned_products.json'))
    mocker.patch.object(launch_avm.SC, 'search_provisioned_products')
    launch_avm.SC.search_provisioned_products.return_value = mock_products

    expected = json.loads(load_mock_data(testpath, 'expected_pprods.json'))

    for item in expected:
        expected[item]['CreatedTime'] = ''
            
    avm.get_indexed_provisioned_products()

    for item in avm.provisioned_products:
        avm.provisioned_products[item]['CreatedTime'] = ''

    assert avm.provisioned_products == expected
    ppid = 'pp-e55fxxxxxxxxx'
    expected = ['VPCRegion', 'OrgUnitName', 'VPCCidr', 'PeerVPC', 'AccountEmail', 'VPCOptions', 'AccountName']
    assert avm.provisioned_products[ppid].get('ExistingParameterKeys', []) == expected


