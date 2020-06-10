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
from botocore.stub import Stubber, ANY

# Testing:
from lib.service_catalog import ServiceCatalog

log_level = 'info'
logger = Logger(loglevel=log_level)
testpath = 'tests/lib-tests/'

SC = ServiceCatalog(logger)

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
# 
#------------------------------------------------------------------------------
def test_search_provisioned_products():

    productid = 'prod-jroqxxxxxxxxx'
    mock_api = json.loads(load_mock_data(testpath, 'search_provisioned_products.json'))
    expected = json.loads(load_mock_data(testpath, 'search_provisioned_products.json'))

    stubber = Stubber(SC.sc_client)

    stubber.add_response(
        'search_provisioned_products',
        mock_api,
        {
            "AccessLevelFilter": {
                "Key": "Account",
                "Value": "self"
            },
            "Filters": {
                "SearchQuery": ANY
            },
            "PageToken": ANY,
            "SortBy": "createdTime"
        }
    )
    #cloudformation_stub.activate()
    stubber.activate()
    
    pprods = SC.search_provisioned_products(productid)
    assert pprods == expected
