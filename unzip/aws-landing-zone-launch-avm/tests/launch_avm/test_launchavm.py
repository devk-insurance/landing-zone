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
import mock
import json
import pytest
from pytest_mock import mocker
from botocore.stub import Stubber
import launch_avm
from lib.logger import Logger
from lib.manifest import Manifest
from lib.service_catalog import ServiceCatalog as SC

log_level = 'info'
logger = Logger(loglevel=log_level)
wait_time = '10'
batch_size = '10'
manifest_file_path = './tests/launch_avm/manifest.yaml'
manifest = None
testpath = 'tests/launch_avm/'

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

@pytest.fixture
def load_manifest():
    """Load manifest from the test data"""
    avm.manifest = Manifest(manifest_file_path)

#------------------------------------------------------------------------------
# test_010
#------------------------------------------------------------------------------
def test_010_manifest_parser(load_manifest):
    # basic test that ensures that we can read the manifest. May want to add more srtingent testing
    assert avm.manifest.portfolios[0].get('name') == 'AWS Landing Zone - Baseline'
    assert avm.manifest.organizational_units[0].get('name') == 'core'
    assert avm.manifest.nested_ou_delimiter == ':'

#------------------------------------------------------------------------------
# test_020_sc_lookup
#------------------------------------------------------------------------------
def test_020_sc_lookup(mocker):

    mock_sc_ports = json.loads(load_mock_data(testpath, 'list_portfolios.json'))
    mocker.patch.object(launch_avm.SC, 'list_portfolios')
    launch_avm.SC.list_portfolios.return_value = mock_sc_ports

    mock_sc_prods = json.loads(load_mock_data(testpath, 'search_products_as_admin.json'))
    mocker.patch.object(launch_avm.SC, 'search_products_as_admin')
    launch_avm.SC.search_products_as_admin.return_value = mock_sc_prods

    avm.sc_lookup()

    assert avm.sc_portfolios == {'AWS Landing Zone - Baseline': 'port-3k7oxxxxxxxxx'}
    assert avm.sc_products == {
        'AWS Landing Zone - Baseline': {
            'AWS-Landing-Zone-Account-Vending-Machine': 'prod-jroqxxxxxxxxx'
        }
    }


#------------------------------------------------------------------------------
# test_030
#------------------------------------------------------------------------------
# Build on previous test
def test_030_start_launch_avm(mocker):
    mock_sc_roots = json.loads(load_mock_data(testpath, 'list_roots.json'))
    mocker.patch.object(launch_avm.Organizations, 'list_roots')
    launch_avm.Organizations.list_roots.return_value = mock_sc_roots

    mocker.patch.object(launch_avm.Org, '_get_ou_id')
    launch_avm.Org._get_ou_id.return_value = 'ou-f2xx-fkczxxxx'

    mock_sc_accts = json.loads(load_mock_data(testpath, 'list_accounts_for_parent.json'))
    mocker.patch.object(launch_avm.Organizations, 'list_accounts_for_parent')
    launch_avm.Organizations.list_accounts_for_parent.return_value = mock_sc_accts

    # Mock the function so we don't run batches
    mocker.patch.object(launch_avm.LaunchAVM, '_process_accounts_in_batches')

    avm.start_launch_avm()
    assert avm.avm_params['AccountEmail']
    assert avm.avm_product_name == 'AWS-Landing-Zone-Account-Vending-Machine'
    assert avm.avm_product_id == 'prod-jroqxxxxxxxxx'
    assert avm.provisioned_products == {}

#------------------------------------------------------------------------------
# test_040
#------------------------------------------------------------------------------
def test_040_input_map(mocker):

    # Mock the method to get an id for testing
    mocker.patch.object(launch_avm.LaunchAVM, '_get_provisioning_artifact_id')
    launch_avm.LaunchAVM._get_provisioning_artifact_id.return_value = 'pa-fzz5xxxxxxxxx'

    mock_sc_accts = json.loads(load_mock_data(testpath, 'list_accounts_for_parent.json'))['Accounts']
    input_map = avm._create_launch_avm_state_machine_input_map(
        mock_sc_accts
    )
    expected = json.loads(load_mock_data(testpath, 'batch_input.json'))
    assert expected['PortfolioExist']
    assert expected['ProductExist']

    assert input_map == expected

#------------------------------------------------------------------------------
# Tests that we can process batches without error. Does not call the API and 
# produces no testable output.
#------------------------------------------------------------------------------
# Build on previous test
def test_050_batches(mocker):

    # Mock the method to get an id for testing
    mocker.patch.object(launch_avm.LaunchAVM, '_get_provisioning_artifact_id')
    launch_avm.LaunchAVM._get_provisioning_artifact_id.return_value = 'pa-fzz5xxxxxxxxx'

    mock_sc_accts = json.loads(load_mock_data(testpath, 'list_accounts_for_parent.json'))['Accounts']
    ou_id = 'ou-f2xx-fkczxxxx'
    ou_name = 'core'
    organizations = 'fakefakefake' # Only used if Suspended account

    # mock functions we don't want to call
    mocker.patch.object(launch_avm.StateMachine, 'trigger_state_machine')

    avm._process_accounts_in_batches(mock_sc_accts, organizations, ou_id, ou_name)


