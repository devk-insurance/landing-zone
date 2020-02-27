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

#!/bin/python

import boto3
import inspect
from botocore.exceptions import ClientError

org_client = boto3.client('organizations')


class Organizations(object):
    def __init__(self, logger):
        self.logger = logger

    def list_roots(self):
        try:
            response = org_client.list_roots()
            return response
        except Exception as e:
            return None

    # describe organization
    def describe_org(self):
        try:
            response = org_client.describe_organization()
            return response
        except Exception:
            pass

    # create a new organization
    def create_organization(self, feature_set='ALL'):
        try:
            response = org_client.create_organization(
                FeatureSet=feature_set
            )
            return response
        except Exception as e:
            self.logger.info("The organization already exist in this account. This should not impact the workflow.")
            pass

    def list_organizational_units_for_parent(self, **kwargs):
        try:
            response = org_client.list_organizational_units_for_parent(**kwargs)
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_organizational_unit(self, root_id, name):
        try:
            response = org_client.create_organizational_unit(
                ParentId=root_id,
                Name=name
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_organization_unit(self, ou_id):
        try:
            org_client.delete_organizational_unit(
                OrganizationalUnitId=ou_id
            )
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_parents(self,account_id):
        try:
            response = org_client.list_parents(
                ChildId=account_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_accounts_for_parent(self,ou_id):
        try:
            response = org_client.list_accounts_for_parent(
                ParentId=ou_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_account(self, acct_name, email, role_name='AWSCloudFormationStackSetExecutionRole',
                       billing_access='ALLOW'):
        try:
            response = org_client.create_account(
                Email=email,
                AccountName=acct_name,
                RoleName=role_name,
                IamUserAccessToBilling=billing_access
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'FinalizingOrganizationException':
                self.logger.info("Caught exception 'FinalizingOrganizationException', handling the exception...")
                return {"Error": "FinalizingOrganizationException"}
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    def describe_account_status(self, req_id):
        try:
            response = org_client.describe_create_account_status(
                CreateAccountRequestId=req_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def move_account(self, acct_id, src_id, dst_id):
        try:
            response = org_client.move_account(
                AccountId=acct_id,
                SourceParentId=src_id,
                DestinationParentId=dst_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_accounts(self, **kwargs):
        try:
            response = org_client.list_accounts(**kwargs)
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_account(self, acct_id):
        try:
            response = org_client.describe_account(
                AccountId=acct_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise
