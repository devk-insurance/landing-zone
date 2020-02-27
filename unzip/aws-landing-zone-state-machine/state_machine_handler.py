###################################################################################################################### 
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           # 
#                                                                                                                    # 
#  Licensed under the Apache License Version 2.0 (the "License"). You may not use this file except in compliance     # 
#  with the License. A copy of the License is located at                                                             # 
#                                                                                                                    # 
#      http://www.apache.org/licenses/                                                                               # 
#                                                                                                                    # 
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES # 
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    # 
#  and limitations under the License.                                                                                # 
######################################################################################################################

# !/bin/python

from lib.organizations import Organizations as Org
from lib.service_catalog import ServiceCatalog as SC
from lib.scp import ServiceControlPolicy as SCP
from lib.directory_service import DirectoryService
from lib.cloudformation import StackSet, Stacks
from lib.assume_role_helper import AssumeRole
from lib.s3 import S3
from lib.metrics import Metrics
from lib.ssm import SSM
from lib.ec2 import EC2
from lib.sts import STS
from lib.iam import IAM
from os import environ
import requests
from botocore.exceptions import ClientError
from json import dumps, loads
import inspect
import time
import os
import json
from lib.helper import sanitize, convert_http_url_to_s3_url, download_remote_file
import tempfile
import filecmp
import time
from random import randint


class CloudFormation(object):
    """
    This class handles requests from Cloudformation (StackSet) State Machine.
    """

    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)

    def describe_stack_set(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            # To prevent CFN from throwing 'Response object is too long.' when the event payload gets overloaded
            # Deleting the 'OldResourceProperties' from event, since it not being used in the SM

            if self.event.get('OldResourceProperties'):
                self.event.pop('OldResourceProperties', '')

            # Check if stack set already exist
            stack_set = StackSet(self.logger)
            response = stack_set.describe_stack_set(self.params.get('StackSetName'))
            self.logger.info("Describe Response")
            self.logger.info(response)
            # If stack_set already exist, skip to create the stack_set_instance
            if response is not None:
                value = "yes"
                self.logger.info("Found existing stack set.")
            else:
                value = "no"
                self.logger.info("Existing stack set not found.")
            self.event.update({'StackSetExist': value})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def describe_stack_set_operation(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            self.event.update({'RetryDeleteFlag': False})

            stack_set = StackSet(self.logger)
            response = stack_set.describe_stack_set_operation(self.params.get('StackSetName'),
                                                              self.event.get('OperationId'))
            self.logger.info(response)
            operation_status = response.get('StackSetOperation', {}).get('Status')
            self.logger.info("Operation Status: {}".format(operation_status))
            if operation_status == 'FAILED':
                account_id = self.params.get('AccountList')[0] if type(self.params.get('AccountList')) is list else None
                if account_id:
                    for region in self.params.get('RegionList'):
                        self.logger.info("Account: {} - describing stack instance in {} region".format(account_id, region))
                        try:
                            resp = stack_set.describe_stack_instance(self.params.get('StackSetName'), account_id, region)
                            self.event.update({region: resp.get('StackInstance', {}).get('StatusReason')})
                        except ClientError as e:
                            # When CFN has triggered StackInstance delete and the SCP is still attached (due to race condition), then it fails to delete the stack
                            # and StackSet throws the StackInstanceNotFoundException exception back, the CFN stack in target account ends up with 'DELETE_FAILED' state
                            # so it should try again
                            if e.response['Error']['Code'] == 'StackInstanceNotFoundException' and self.event.get('RequestType') == 'Delete':
                                self.logger.exception("Caught exception 'StackInstanceNotFoundException', sending the flag to go back to Delete Stack Instances stage...")
                                self.event.update({'RetryDeleteFlag': True})
                            else:
                                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                                self.logger.exception(message)
                                raise


            operation_status = response.get('StackSetOperation', {}).get('Status')
            self.event.update({'OperationStatus': operation_status})

            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_stack_instances_account_ids(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            accounts = self.event.get('StackInstanceAccountList', [])

            # Check if stack instances exist
            stack_set = StackSet(self.logger)
            if self.event.get('NextToken') is not None and self.event.get('NextToken') != 'Complete':
                response = stack_set.list_stack_instances(StackSetName=self.params.get('StackSetName'), MaxResults=20,
                                                          NextToken=self.event.get('NextToken'))
            else:
                response = stack_set.list_stack_instances(StackSetName=self.params.get('StackSetName'), MaxResults=20)

            self.logger.info("List SI Accounts Response")
            self.logger.info(response)

            if response:
                if not response.get('Summaries'):  # 'True' if list is empty
                    self.event.update({'NextToken': 'Complete'})
                    self.logger.info("No existing stack instances found. (Summaries List: Empty)")
                else:
                    for instance in response.get('Summaries'):
                        account_id = instance.get('Account')
                        accounts.append(account_id)

                    self.event.update({'StackInstanceAccountList': list(set(accounts))})
                    self.logger.info("Next Token Returned: {}".format(response.get('NextToken')))

                    if response.get('NextToken') is None:
                        self.event.update({'NextToken': 'Complete'})
                    else:
                        self.event.update({'NextToken': response.get('NextToken')})

            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_stack_instances(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            if 'ParameterOverrides' in self.params.keys():
                self.logger.info("Override parameters found in the event")
                self.event.update({'OverrideParametersExist': 'yes'})
            else:
                self.logger.info("Override parameters NOT found in the event")
                self.event.update({'OverrideParametersExist': 'no'})

            # Check if stack instances exist
            stack_set = StackSet(self.logger)
            # if account list is not present then only create StackSet and skip stack instance creation
            if type(self.params.get('AccountList')) is not list:
                self.event.update({'InstanceExist': 'no'})
                self.event.update({'NextToken': 'Complete'})
                self.event.update({'CreateInstance': 'no'})
                self.event.update({'DeleteInstance': 'no'})
                return self.event
            else:
                if self.event.get('NextToken') is not None and self.event.get('NextToken') != 'Complete':
                    self.logger.info('Found next token')
                    response = stack_set.list_stack_instances(StackSetName=self.params.get('StackSetName'),
                                                              StackInstanceAccount=self.params.get('AccountList')[0],
                                                              MaxResults=20,
                                                              NextToken=self.event.get('NextToken')
                                                              )
                else:
                    self.logger.info('Next token not found.')
                    response = stack_set.list_stack_instances(StackSetName=self.params.get('StackSetName'),
                                                              StackInstanceAccount=self.params.get('AccountList')[0],
                                                              MaxResults = 20)
                self.logger.info("List SI Response")
                self.logger.info(response)

                if response is not None:
                    if not response.get('Summaries'):  # 'True' if list is empty
                        self.event.update({'InstanceExist': 'no'})
                        self.event.update({'NextToken': 'Complete'}) # exit loop
                        self.event.update({'CreateInstance': 'yes'}) # create stack instance set to yes
                        self.event.update({'DeleteInstance': 'no'})  # delete stack instance set to no
                        self.logger.info("No existing stack instances found. (Summaries List: Empty)")
                        return self.event
                    else:
                        self.logger.info("Found existing stack instance.")
                        # Delete path in SM, will skip StackSet deletion if InstanceExist is 'yes'
                        self.event.update({'InstanceExist': 'yes'})
                        # Iterate through response to check if stack instance exists in
                        # account and region in the given self.event.
                        account_id = ""
                        existing_region_list = [] if self.event.get('ExistingRegionList') is None else self.event.get(
                            'ExistingRegionList')
                        for instance in response.get('Summaries'):
                            if instance.get('Region') not in existing_region_list:
                                self.logger.info("Region {} not in the region list. Adding it..."
                                                 .format(instance.get('Region')))
                                # appending to the list
                                existing_region_list.append(instance.get('Region'))
                            else:
                                self.logger.info("Already in the region list. Skipping...")
                            account_id = instance.get('Account')
                        self.logger.info("Region List: {} for Account: {}".format(existing_region_list, account_id))

                        self.logger.info("Next Token Returned: {}".format(response.get('NextToken')))

                        if response.get('NextToken') is None:
                            # replace the region list in the self.event
                            add_region_list = self._add_region_list(existing_region_list)
                            self.logger.info("Add region list: {}".format(add_region_list))

                            # Build a region list if the event is from AVM
                            if self.params.get('TemplateURL') == "":  # Event from AVM (CFN) - limit this functionality to baseline resources
                                delete_region_list = self._delete_region_list(existing_region_list)
                                self.logger.info("Delete region list: {}".format(delete_region_list))
                            else: # this condition blocks the core resource stage to delete stack instances
                                delete_region_list = []

                            self._update_event_for_add(add_region_list)
                            self._update_event_for_delete(delete_region_list)

                        else:
                            self.event.update({'NextToken': response.get('NextToken')})
                            # Update the self.event with existing_region_list
                            self.event.update({'ExistingRegionList': existing_region_list})
                        return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def _update_event_for_delete(self, delete_region_list):
        if delete_region_list:
            self.event.update({'DeleteRegionList': delete_region_list})
            self.event.update({'DeleteInstance': 'yes'})
            self.event.update({'NextToken': 'Complete'})
        else:
            self.event.update({'DeleteInstance': 'no'})
            self.event.update({'NextToken': 'Complete'})

    def _update_event_for_add(self, add_region_list):
        if add_region_list:
            self.event.update({'AddRegionList': add_region_list})
            self.params.update({'RegionList': add_region_list})
            self.event.update({'ResourceProperties': self.params})
            self.event.update({'CreateInstance': 'yes'})
            self.event.update({'NextToken': 'Complete'})
        else:
            self.event.update({'CreateInstance': 'no'})
            self.event.update({'NextToken': 'Complete'})

    def _add_region_list(self, existing_region_list):
        event_set = set(self.params.get('RegionList'))
        existing_set = set(existing_region_list)
        add_region_list = list(event_set - event_set.intersection(existing_set))
        return add_region_list

    def _delete_region_list(self, existing_region_list):
        event_set = set(self.params.get('RegionList'))
        existing_set = set(existing_region_list)
        delete_region_list = list(event_set.union(existing_set) - event_set)
        return delete_region_list

    def _get_ssm_secure_string(self, parameters):
        if parameters.get('ALZRegion'):
            ssm = SSM(self.logger, parameters.get('ALZRegion'))
        else:
            ssm = SSM(self.logger)

        self.logger.info("Updating Parameters")
        self.logger.info(parameters)
        copy = parameters.copy()
        for key, value in copy.items():
            if type(value) is str and value.startswith('_get_ssm_secure_string_'):
                ssm_param_key = value[len('_get_ssm_secure_string_'):]
                decrypted_value = ssm.get_parameter(ssm_param_key)
                copy.update({key: decrypted_value})
            elif type(value) is str and value.startswith('_alfred_decapsulation_'):
                decapsulated_value = value[(len('_alfred_decapsulation_')+1):]
                self.logger.info("Removing decapsulation header. Printing decapsulated value below:")
                self.logger.info(decapsulated_value)
                copy.update({key: decapsulated_value})
        return copy

    def reroute_to_delete_stack_instances(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            # Update RegionList with DeleteRegionList
            self.params.update({'RegionList': self.event.get('DeleteRegionList')})
            self.event.update({'ResourceProperties': self.params})

            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_stack_set(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            # Create a new stack set
            stack_set = StackSet(self.logger)
            self.logger.info("Creating StackSet")
            parameters = self._get_ssm_secure_string(self.params.get('Parameters'))
            response = stack_set.create_stack_set(self.params.get('StackSetName'),
                                                  self.params.get('TemplateURL'),
                                                  parameters,
                                                  self.params.get('Capabilities'))
            if response.get('StackSetId') is not None:
                value = "success"
            else:
                value = "failure"
            self.event.update({'StackSetStatus': value})
            # set create stack instance flag to yes (Handle SM Condition: Create or Delete Stack Instance?)
            self.event.update({'CreateInstance': 'yes'})
            # set delete stack instance flag to no (Handle SM Condition: Delete Stack Instance or Finish?)
            self.event.update({'DeleteInstance': 'no'})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_stack_instances(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            # generate region list if 'all' keyword is found
            if 'all' in (value.lower() for value in self.params.get('RegionList')):
                ec2 = EC2(self.logger, environ.get('AWS_REGION'))
                region_list = []
                for region in ec2.describe_regions():
                    region_list.append(region.get('RegionName'))
                self.logger.info("Converting ['all'] to complete AWS region list: {}".format(region_list))
            else:
                region_list = self.params.get('RegionList')

            # Create stack instances
            stack_set = StackSet(self.logger)

            self.logger.info("Creating StackSet Instance: {}".format(self.params.get('StackSetName')))
            if 'ParameterOverrides' in self.params:
                self.logger.info("Found 'ParameterOverrides' key in the event.")
                parameters = self._get_ssm_secure_string(self.params.get('ParameterOverrides'))
                response = stack_set.create_stack_instances_with_override_params(self.params.get('StackSetName'),
                                                                                 self.params.get('AccountList'),
                                                                                 region_list, parameters)
            else:
                response = stack_set.create_stack_instances(self.params.get('StackSetName'),
                                                            self.params.get('AccountList'),
                                                            region_list)
            self.logger.info(response)
            self.logger.info("Operation ID: {}".format(response.get('OperationId')))
            self.event.update({'OperationId': response.get('OperationId')})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def update_stack_set(self):
        # Updates the stack set and all associated stack instances.
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            stack_set = StackSet(self.logger)

            # Update existing StackSet
            self.logger.info("Updating Stack Set: {}".format(self.params.get('StackSetName')))

            parameters = self._get_ssm_secure_string(self.params.get('Parameters'))
            response = stack_set.update_stack_set(self.params.get('StackSetName'),
                                                  parameters,
                                                  self.params.get('TemplateURL'),
                                                  self.params.get('Capabilities'))

            self.logger.info("Response Update Stack Set")
            self.logger.info(response)
            self.logger.info("Operation ID: {}".format(response.get('OperationId')))
            self.event.update({'OperationId': response.get('OperationId')})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def update_stack_instances(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            stack_set = StackSet(self.logger)
            override_parameters = self.params.get('ParameterOverrides') # this should come from the event
            self.logger.info("override_params_list={}".format(override_parameters))

            response = stack_set.update_stack_instances(self.params.get('StackSetName'),
                                                        self.params.get('AccountList'),
                                                        self.params.get('RegionList'),
                                                        override_parameters)
            self.logger.info("Update Stack Instance Response")
            self.logger.info(response)
            self.logger.info("Operation ID: {}".format(response.get('OperationId')))
            self.event.update({'OperationId': response.get('OperationId')})
            # need for Delete Stack Instance or Finish? choice in the state machine. No will route to Finish path.
            self.event.update({'DeleteInstance': 'no'})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_stack_set(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            # Delete StackSet
            stack_set = StackSet(self.logger)
            self.logger.info("Deleting StackSet: {}".format(self.params.get('StackSetName')))
            self.logger.info(stack_set.delete_stack_set(self.params.get('StackSetName')))
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_stack_instances(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            # generate region list if 'all' keyword is found
            if 'all' in (value.lower() for value in self.params.get('RegionList')):
                ec2 = EC2(self.logger, environ.get('AWS_REGION'))
                region_list = []
                for region in ec2.describe_regions():
                    region_list.append(region.get('RegionName'))
                self.logger.info("Converting 'all' to full region list: {}".format(region_list))
            else:
                region_list = self.params.get('RegionList')

            # Delete stack_set_instance(s)
            stack_set = StackSet(self.logger)
            self.logger.info("Deleting Stack Instance: {}".format(self.params.get('StackSetName')))

            response = stack_set.delete_stack_instances(self.params.get('StackSetName'),
                                                        self.params.get('AccountList'),
                                                        region_list)
            self.logger.info(response)
            self.logger.info("Operation ID: {}".format(response.get('OperationId')))
            self.event.update({'OperationId': response.get('OperationId')})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

class Organizations(object):
    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties', {})
        self.logger = logger
        self.logger.info("Organization Event")
        self.logger.info(event)

    def list_roots(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            response = org.list_roots()
            self.logger.info("Response: List Roots")
            self.logger.info(response)
            if response is None:
                self.event.update({'RootId': 'None'})
            else:
                root_id = response['Roots'][0].get('Id')
                self.event.update({'RootId': root_id})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_organization(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            response = org.create_organization()
            self.logger.info("Response: Create Org")
            self.logger.info(response)
            response = org.list_roots()
            root_id = response['Roots'][0].get('Id')
            self.event.update({'RootId': root_id})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def _strip_list_items(self, array):
        return [item.strip() for item in array]

    def _remove_empty_strings(self, array):
        return [x for x in array if x != '']

    def _list_sanitizer(self, array):
        stripped_array = self._strip_list_items(array)
        return self._remove_empty_strings(stripped_array)

    def _empty_seperator_handler(self, delimiter, nested_ou_name):
        if delimiter == "":
            nested_ou_name_list = [nested_ou_name]
        else:
            nested_ou_name_list = nested_ou_name.split(delimiter)
        return nested_ou_name_list

    def get_ou_id(self, nested_ou_name, delimiter):
        try:
            org = Org(self.logger)
            response = org.list_roots()
            root_id = response['Roots'][0].get('Id')
            self.logger.info("Organizations Root Id: {}".format(root_id))
            self.logger.info("Looking up the OU Id for OUName: {} with nested ou delimiter: {}".format(nested_ou_name, delimiter))
            return self._get_ou_id(org, root_id, nested_ou_name, delimiter)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def _get_ou_id(self, org, parent_id, nested_ou_name, delimiter):
        try:
            nested_ou_name_list = self._empty_seperator_handler(delimiter, nested_ou_name)
            response = self._list_ou_for_parent(org, parent_id, self._list_sanitizer(nested_ou_name_list))
            self.logger.info(response)
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def _list_ou_for_parent(self, org, parent_id, nested_ou_name_list):
        try:
            ou_list = org.list_organizational_units_for_parent(parent_id)
            index = 0  # always process the first item
            self.logger.info("Looking for existing OU: {} under parent id: {}".format(nested_ou_name_list[index], parent_id))
            for dictionary in ou_list:
                if dictionary.get('Name') == nested_ou_name_list[index]:
                    self.logger.info("OU Name: {} exists under parent id: {}".format(dictionary.get('Name'), parent_id))
                    nested_ou_name_list.pop(index) # pop the first item in the list
                    if len(nested_ou_name_list) == 0:
                        self.logger.info("Returning last level OU ID: {}".format(dictionary.get('Id')))
                        return dictionary.get('Id')
                    else:
                        return self._list_ou_for_parent(org, dictionary.get('Id'), nested_ou_name_list)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def check_organization_unit(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            if self.event.get('RootId') == 'None':
                self.logger.info("Root ID is 'None', skip API call, return OUId = 'None'")
                self.event.update({'OUNextToken': 'Complete'})
            else:
                self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
                self.logger.info(self.params)
                parent_id = self.event.get('RootId')
                nested_ou_name = self.params.get('OUName')
                self.logger.info(nested_ou_name)
                delimiter = self.params.get('OUNameDelimiter')
                ou_id = self._get_ou_id(org, parent_id, nested_ou_name, delimiter)
                if isinstance(ou_id, str):
                    self.logger.info("Last Level OU ID: {}".format(ou_id))
                    self.event.update({'OUId': ou_id})
                    return self.event
                else:
                    self.logger.info("OU ID for the last OU not found")
            self.event.update({'OUId': 'None'})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def _create_nested_ou(self, org, parent_id, nested_ou_name, delimiter):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            nested_ou_name_list = self._empty_seperator_handler(delimiter, nested_ou_name)
            response = self._create_child_ou(org, parent_id, self._list_sanitizer(nested_ou_name_list))
            self.logger.info("Destination OU ID: {}".format(response))
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def _create_child_ou(self, org, parent_id, nested_ou_name_list):
        try:
            self.logger.info("Parent ID: {}".format(parent_id))
            self.logger.info("Nested OU List: {}".format(nested_ou_name_list))
            last_level_ou_id = self._list_ou_for_parent(org, parent_id, nested_ou_name_list.copy())
            self.logger.info("Existing OU ID: {}".format(last_level_ou_id))
            index = 0
            if last_level_ou_id is not None:
                parent_id = last_level_ou_id
                self.logger.info("Last Level OU ID: {}".format(last_level_ou_id))
                return parent_id
            else:
                self.logger.info("Nested OU List: {}".format(nested_ou_name_list))
                self.logger.info("OU: {} does not exist under parent id: {}, creating now..."
                                 .format(nested_ou_name_list[index], parent_id))
                response_create_ou = org.create_organizational_unit(parent_id, nested_ou_name_list[index])
                # handle exception: duplicate child OU name under same parent OU
                if response_create_ou.get('Error') == 'DuplicateOrganizationalUnitException':
                    self.logger.info('OU already exist, updating parent id')
                    self.logger.info("Parent ID: {}".format(parent_id))
                    # if exists then list to obtain the OU id
                    parent_id = self._list_ou_for_parent(org, parent_id, [nested_ou_name_list[index]])
                    self.logger.info("Updated Parent ID: {}".format(parent_id))
                # update parent OU id
                else:
                    self.logger.info("New OU Created successfully")
                    parent_id = response_create_ou.get('OrganizationalUnit').get('Id')
                    self.logger.info("Updated Parent ID: {}".format(parent_id))
                # remove first OU name in the list, to process next OU in the list
                nested_ou_name_list.pop(index)
                self.logger.info("Updated Nested OU List: {}".format(nested_ou_name_list))
                # if this is the last level nested OU then return the OU ID else callback
                if len(nested_ou_name_list) == 0:
                    self.logger.info("All nested OUs created, returning: {}".format(parent_id))
                    return parent_id
                self.logger.info("Callback Create Function")
                return self._create_child_ou(org, parent_id, nested_ou_name_list)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_organization_unit(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            parent_id = self.event.get('RootId')
            nested_ou_name = self.params.get('OUName')
            self.logger.info("Creating Nested OUs: {}".format(nested_ou_name))
            delimiter = self.params.get('OUNameDelimiter')
            ou_id = self._create_nested_ou(org, parent_id, nested_ou_name, delimiter)
            self.logger.info("Nested OU structure created, returning destination OU ID: {} (last level).".format(ou_id))
            self.event.update({'OUId': ou_id})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_organization_unit(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            self.logger.info("Deleting Org Unit: {}".format(self.event.get('OUId')))
            org.delete_organization_unit(self.event.get('OUId'))
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_accounts_for_parent(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            response = org.list_accounts_for_parent(self.event.get('OUId'))
            self.logger.info("List Accounts for Parent Response")
            self.logger.info(response)
            accounts = len(response.get('Accounts'))
            self.event.update({'OrgUnitAccounts': accounts})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_accounts(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            if self.event.get('RootId') == 'None':
                self.logger.info("Root ID is 'None', skipping list_accounts API call.")
                self.event.update({'AccountId': 'None'})
                self.event.update({'NextToken': 'Complete'})
                return self.event
            else:
                if self.params.get('AccountName') == "":
                    self.event.update({'AccountId': 'None'})
                    self.event.update({'NextToken': 'Complete'})
                    return self.event
                if self.event.get('NextToken') is not None:
                    self.logger.info('NEXT TOKEN')
                    response = org.list_accounts(
                        MaxResults=20,
                        NextToken=self.event.get('NextToken')
                    )
                else:
                    self.logger.info('NO NEXT TOKEN')
                    response = org.list_accounts(
                        MaxResults=20
                    )
                self.logger.info("List Account Response")
                self.logger.info(response)
                self.logger.info("Next Token Returned: {}".format(response.get('NextToken')))
                for account in response.get('Accounts'):
                    if account.get('Email').lower() == self.params.get('AccountEmail').lower():
                        self.logger.info(account.get('Email'))
                        self.event.update({'AccountId': account.get('Id')})
                        self.event.update({'NextToken': 'Complete'})
                        return self.event
                if response.get('NextToken') is None:
                    self.event.update({'NextToken': 'Complete'})
                    self.event.update({'AccountId': 'None'})
                else:
                    self.event.update({'NextToken': response.get('NextToken')})
                return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_parents(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            if self.event.get('AccountId') is not None:
                response = org.list_parents(self.event.get('AccountId'))
                self.logger.info("List Parents Response")
                self.logger.info(response)
                self.event.update({'ParentId': response.get('Parents')[0].get('Id')})
            else:
                self.logger.info("No AccountId Listed in event")
                self.event.update({'ParentId': 'None'})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_account(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            response = org.create_account(self.params.get('AccountName'), self.params.get('AccountEmail'))
            self.logger.info("Create Account Response")
            self.logger.info(response)
            # Catching FinalizingOrganizationException error and handling in state machine.
            if response.get('Error') == 'FinalizingOrganizationException':
                self.event.update({'OrganizationInitializing': 'yes'})
            else:
                self.event.update({'OrganizationInitializing': 'no'})
            # Returning account status for 'describe_account_status' api
            create_account_request_id = response.get('CreateAccountStatus', {}).get('Id')
            self.event.update({'CreateAccountRequestId': create_account_request_id})
            # setting rootId as parentId for 'move' step
            self.event.update({'ParentId': self.event.get('RootId')})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def describe_account_status(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            response = org.describe_account_status(self.event.get('CreateAccountRequestId'))
            self.logger.info("Describe Account Response")
            self.logger.info(response)
            account_status = response.get('CreateAccountStatus', {}).get('State')
            self.event.update({'CreateAccountStatus': account_status})
            if account_status == 'FAILED':
                # 'FailureReason': 'ACCOUNT_LIMIT_EXCEEDED'|'EMAIL_ALREADY_EXISTS'|'INVALID_ADDRESS'|'INVALID_EMAIL'|'
                # CONCURRENT_ACCOUNT_MODIFICATION'|'INTERNAL_FAILURE'
                self.event.update({'FailureReason': response.get('CreateAccountStatus', {}).get('FailureReason')})
                return self.event
            elif account_status == 'SUCCEEDED':
                self.event.update({'AccountId': response.get('CreateAccountStatus', {}).get('AccountId')})
                return self.event
            else:
                return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def move_account(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            org = Org(self.logger)
            if self.event.get('RequestType') == 'Delete':
                self.logger.info("Received Account Delete request, skipping...")
            else:
                if self.event.get('ParentId') == self.event.get('OUId'):
                    self.logger.info("Account already in OU, no move required")
                else:
                    response = org.move_account(self.event.get('AccountId'), self.event.get('ParentId'),
                                                self.event.get('OUId'))
                    self.logger.info("Move Account Response")
                    self.logger.info(response)
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def _update_child_account_trust_relationship(self, account, principal_arns):
        try:
            region = os.environ.get('AWS_REGION')

            _assume_role = AssumeRole()
            iam = IAM(self.logger, region, credentials=_assume_role(self.logger, account))

            principals = principal_arns.split(",")
            principals = [p.strip() for p in principals]

            policy_doc = {}
            policy_stmt = {}
            policy_doc.update({'Version': '2012-10-17'})
            policy_stmt.update({'Effect': 'Allow'})
            policy_stmt.update({"Action": "sts:AssumeRole"})
            policy_stmt.update({"Principal": {'AWS': principals}})
            policy_doc.update({"Statement": [policy_stmt]})
            self.logger.info("Applying policy: {} for account ID: {}".format(json.dumps(policy_doc), account))

            iam.update_assume_role_policy('AWSCloudFormationStackSetExecutionRole', json.dumps(policy_doc))
            time.sleep(5)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def lock_down_stack_sets_role(self):
        try:
            account = self.event.get('AccountId')
            # To handle Organization Unit (OU) creation, in which case no action to take
            if account.lower() == 'none':
                return self.event

            response_url = self.event.get('ResponseURL', '')

            # Check if invoked from AVM or Codepipeline
            # Lock the account only if invoked from AVM
            # Unlock the account if invoked from Codepipeline
            if response_url:
                ssm = SSM(self.logger)
                ssm_flag_key = 'lock_down_stack_sets_role_flag'
                self.logger.info("Looking up values in SSM parameter:{}".format(ssm_flag_key))
                existing_param = ssm.describe_parameters(ssm_flag_key)

                principal_arns = environ.get('unlock_role_arns')
                if existing_param:
                    flag = ssm.get_parameter(ssm_flag_key)
                    self.logger.info("Found SSM parameter: {} with value:{}".format(ssm_flag_key, flag))
                    if flag.lower() == 'yes':
                        ssm_roles_key = environ.get('ssm_key_for_lock_down_role_arns')
                        existing_param = ssm.describe_parameters(ssm_roles_key, begins_with=True)
                        if existing_param:
                            role_arns_list = ssm.get_parameters_by_path(ssm_roles_key)
                            self.logger.info("role_arns_list = {}".format(role_arns_list))
                            principal_arns = ''
                            for role_arn in role_arns_list:
                                principal_arns = role_arn.get('Value') + ',' + principal_arns
                            principal_arns = principal_arns[:-1]

                self._update_child_account_trust_relationship(account, principal_arns)
                self.event.update({'AssumeRolePolicyUpdated': "yes"})
            else:
                principal_arns = environ.get('unlock_role_arns')
                self._update_child_account_trust_relationship(account, principal_arns)
                self.event.update({'AssumeRolePolicyUpdated': "yes"})

            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def describe_organization(self):
        try:
            org = Org(self.logger)
            response = org.describe_org()

            self.event.update({'OrganizationId': response.get('Organization').get('Id')})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise


class ServiceCatalog(object):
    """
    This class handles requests from Cloudformation (StackSet) State Machine.
    """

    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)

    def list_portfolios(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            portfolio_event = self.params.get('SCPortfolio')

            # Check if stack set already exist
            sc = SC(self.logger)
            response = sc.list_portfolios()
            portfolio_list = response.get('PortfolioDetails')
            value = None
            self.logger.info("List Portfolio Response")
            self.logger.info(response)
            # If portfolio already exist, skip to create the portfolio
            if portfolio_list:
                for portfolio in portfolio_list:
                    if portfolio.get('DisplayName') == portfolio_event.get('PortfolioName'):
                        value = "yes"
                        self.logger.info("Portfolio Found")
                        self.event.update({'PortfolioId': portfolio.get('Id')})
                        self.event.update({'PortfolioExist': value})
                        return self.event
                    else:
                        value = "no"
                        continue
            else:
                self.logger.info("Portfolio List is empty.")
                value = "no"
            self.event.update({'PortfolioExist': value})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_portfolio(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            portfolio_event = self.params.get('SCPortfolio')

            # Check if stack set already exist
            sc = SC(self.logger)
            self.logger.info("Creating Service Catalog Portfolio")
            response = sc.create_portfolio(portfolio_event.get('PortfolioName'),
                                           portfolio_event.get('PortfolioDescription'),
                                           portfolio_event.get('PortfolioProvider'))
            self.logger.info("Create Portfolio Response")
            self.logger.info(response)
            portfolio_id = response.get('PortfolioDetail', {}).get('Id')
            self.event.update({'PortfolioId': portfolio_id})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def update_portfolio(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            portfolio_event = self.params.get('SCPortfolio')
            sc = SC(self.logger)
            self.logger.info("Update Service Catalog Portfolio")
            response = sc.update_portfolio(self.event.get('PortfolioId'),
                                           portfolio_event.get('PortfolioName'),
                                           portfolio_event.get('PortfolioDescription'),
                                           portfolio_event.get('PortfolioProvider'))
            self.logger.info("Update Portfolio Response")
            self.logger.info(response)
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_principals_for_portfolio(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            portfolio_id = self.event.get('PortfolioId')
            portfolio_event = self.params.get('SCPortfolio')

            # checking if there are no portfolio ID in the event
            if portfolio_id is None:
                self.logger.info("Product not associated - empty list")
                value = 'no'
                self.event.update({'PrincipalExist': value})
                return self.event

            # List principals associated with the given portfolio
            response = sc.list_principals_for_portfolio(portfolio_id)
            self.logger.info("List Principal Response")
            self.logger.info(response)
            principal_list = response.get('Principals')
            self.event.update({'TotalPrincipals': len(principal_list)})
            value = None
            for principal in principal_list:
                if principal.get('PrincipalARN') == portfolio_event.get('PrincipalArn'):
                    value = 'yes'
                    self.event.update({'PrincipalExist': value})
                    return self.event
                else:
                    self.logger.info("Principal not found in list")
                    value = 'no'
            self.event.update({'PrincipalExist': value})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def associate_principal_with_portfolio(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            portfolio_event = self.params.get('SCPortfolio')
            portfolio_id = self.event.get('PortfolioId')
            sc = SC(self.logger)

            self.logger.info("Associating the principal {} with the portfolio"
                             .format(portfolio_event.get('PrincipalArn')))

            # Associating product with principal
            sc.associate_principal_with_portfolio(portfolio_id, portfolio_event.get('PrincipalArn'))
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_product(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            product_event = self.params.get('SCProduct')
            sc = SC(self.logger)

            # Add name of the artifact
            artifact_parameters = product_event.get('ProvisioningArtifactParameters')
            artifact_parameters.update({'Name': 'v1'})

            # Create SC product
            self.logger.info("Creating Service Catalog Product")
            response = sc.create_product(product_event.get('ProductName'), product_event.get('ProductOwner'),
                                         product_event.get('ProductDescription'),
                                         artifact_parameters)
            self.logger.info("Create Product Response")
            self.logger.info(response)
            product_id = response.get('ProductViewDetail', {}).get('ProductViewSummary', {}).get('ProductId')
            self.event.update({'ProductId': product_id})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def update_product(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            product_event = self.params.get('SCProduct')
            sc = SC(self.logger)
            product_id = self.event.get('ProductId')
            # Update SC product
            self.logger.info("Updating Service Catalog Product")
            response = sc.update_product(product_id,
                                         product_event.get('ProductName'),
                                         product_event.get('ProductOwner'),
                                         product_event.get('ProductDescription'))
            self.logger.info("Update Product Response")
            self.logger.info(response)
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def search_products_as_admin(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            portfolio_id = self.event.get('PortfolioId')
            product_event = self.params.get('SCProduct')
            # Search SC product
            self.logger.info("Searching Service Catalog Product")
            response = sc.search_products_as_admin(portfolio_id)
            product_list = response.get('ProductViewDetails')
            self.logger.info("Search Products Response")
            self.logger.info(response)
            value = None
            if product_list:
                for product in product_list:
                    self.logger.info(product)
                    if product.get('ProductViewSummary', {}).get('Name') == product_event.get('ProductName'):
                        value = 'yes'
                        self.event.update({'ProductId': product.get('ProductViewSummary', {}).get('ProductId')})
                        self.event.update({'ProductExist': value})
                        return self.event
                    else:
                        self.logger.info("Product not found in list")
                        value = 'no'
            else:
                self.logger.info("Product not found - empty list")
                value = 'no'
            self.event.update({'ProductExist': value})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_portfolios_for_product(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            product_id = self.event.get('ProductId')
            portfolio_event = self.params.get('SCPortfolio')
            sc = SC(self.logger)

            # checking if there are no product ID in the event
            if product_id is None:
                self.logger.info("Product not associated - empty list")
                value = 'no'
                self.event.update({'AlreadyAssociated': value})
                return self.event

            # Listing portfolio for the product
            self.logger.info("List portfolios for the product")
            response = sc.list_portfolios_for_product(product_id)
            self.logger.info("List Portfolio Response")
            self.logger.info(response)
            value = None
            portfolios = response.get('PortfolioDetails')
            if portfolios:
                for portfolio in portfolios:
                    self.logger.info(portfolio)
                    if portfolio.get('DisplayName') == portfolio_event.get('PortfolioName'):
                        value = 'yes'
                        self.event.update({'AlreadyAssociated': value})
                        return self.event
                    else:
                        self.logger.info("Product not associated with any portfolio in the list.")
                        value = 'no'
            else:
                self.logger.info("Product not associated - empty list")
                value = 'no'
            self.event.update({'AlreadyAssociated': value})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def associate_product_with_portfolio(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            portfolio_id = self.event.get('PortfolioId')
            product_id = self.event.get('ProductId')
            sc = SC(self.logger)

            # Associating product with portfolio
            self.logger.info("Associating the product with the portfolio")
            sc.associate_product_with_portfolio(product_id, portfolio_id)

            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_constraints_for_portfolio(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            product_id = self.event.get('ProductId')
            portfolio_id = self.event.get('PortfolioId')
            sc = SC(self.logger)

            self.logger.info("Product ID: {} ; Portfolio ID: {}".format(product_id, portfolio_id))
            # checking if there are no product ID in the event
            if product_id is None:
                self.logger.info("Product not associated - empty list")
                value = 'no'
                self.event.update({'LaunchConstraintExist': value})
                return self.event

            # Listing portfolio for the product
            self.logger.info("List constraint for the portfolio")
            response = sc.list_constraints_for_portfolio(product_id, portfolio_id)
            self.logger.info("List Constraint Response")
            self.logger.info(response)
            value = None
            constraints = response.get('ConstraintDetails')
            if constraints:
                for constraint in constraints:
                    self.logger.info(constraint)
                    if constraint.get('Type') == 'LAUNCH':
                        value = 'yes'
                        self.event.update({'LaunchConstraintExist': value})
                        self.event.update({'ConstraintId': constraint.get('ConstraintId')})
                        return self.event
                    else:
                        self.logger.info("Launch Type Constraint not found in the list.")
                        value = 'no'
            else:
                self.logger.info("Launch Type Constraint not found - empty list")
                value = 'no'
            self.event.update({'LaunchConstraintExist': value})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_template_constraints_for_portfolio(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            product_id = self.event.get('ProductId')
            portfolio_id = self.event.get('PortfolioId')
            sc = SC(self.logger)

            self.logger.info("Product ID: {} ; Portfolio ID: {}".format(product_id, portfolio_id))
            # checking if there are no product ID in the event
            if product_id is None:
                self.logger.info("Product not associated - empty list")
                value = 'no'
                self.event.update({'TemplateConstraintExist': value})
                return self.event

            # Listing portfolio for the product
            self.logger.info("List constraint for the portfolio")
            response = sc.list_constraints_for_portfolio(product_id, portfolio_id)
            self.logger.info("List Constraint Response")
            self.logger.info(response)
            value = None
            constraints = response.get('ConstraintDetails')
            if constraints:
                for constraint in constraints:
                    self.logger.info(constraint)
                    if constraint.get('Type') == 'TEMPLATE':
                        value = 'yes'
                        self.event.update({'TemplateConstraintExist': value})
                        self.event.update({'ConstraintId': constraint.get('ConstraintId')})
                        return self.event
                    else:
                        self.logger.info("Template Type Constraint not found in the list.")
                        value = 'no'
            else:
                self.logger.info("Template Type Constraint not found - empty list")
                value = 'no'
            self.event.update({'TemplateConstraintExist': value})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_constraint(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            product_event = self.params.get('SCProduct')
            product_id = self.event.get('ProductId')
            portfolio_id = self.event.get('PortfolioId')
            sc = SC(self.logger)
            # Create constraint for this product
            parameter = {"RoleArn": product_event.get('RoleArn')}
            description = "Constraint for Product ID: {}".format(product_id)
            self.logger.info("Creating constraint for product id: {}".format(product_id))
            response = sc.create_constraint(product_id, portfolio_id, dumps(parameter), description)
            self.logger.info("Response from create_constraint")
            self.logger.info(response)
            constraint_id = response.get('ConstraintDetail', {}).get('ConstraintId')
            self.event.update({'ConstraintId': constraint_id})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def check_rules_exist(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            product_event = self.params.get('SCProduct')
            if product_event.get('Rules'):
                self.event.update({'RulesExist': 'yes'})
            else:
                self.event.update({'RulesExist': 'no'})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_template_constraint(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            product_event = self.params.get('SCProduct')
            product_id = self.event.get('ProductId')
            portfolio_id = self.event.get('PortfolioId')
            sc = SC(self.logger)
            # Create constraint for this product
            parameter = {"Rules": product_event.get('Rules')}
            description = "Constraint for Product ID: {}".format(product_id)
            self.logger.info("Creating constraint for product id: {}".format(product_id))
            response = sc.create_constraint(product_id, portfolio_id, dumps(parameter), description, 'TEMPLATE')
            self.logger.info("Response from create_constraint")
            self.logger.info(response)
            constraint_id = response.get('ConstraintDetail', {}).get('ConstraintId')
            self.event.update({'ConstraintId': constraint_id})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def describe_constraint(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            constraint_id = self.event.get('ConstraintId')
            sc = SC(self.logger)
            product_event = self.params.get('SCProduct')
            self.logger.info("Describe constraint for the portfolio")
            response = sc.describe_constraint(constraint_id)
            self.logger.info("Describe Constraint Response")
            self.logger.info(response)
            role_arn = loads(response.get("ConstraintParameters")).get('RoleArn')
            if product_event.get('RoleArn') == role_arn:
                self.logger.info("Role ARN matched: skip to next state")
                value = 'yes'
            else:
                self.logger.info("Role ARN did not match: updated required.")
                value = 'no'
            self.event.update({'RoleArnMatched': value})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def describe_template_constraint(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            constraint_id = self.event.get('ConstraintId')
            sc = SC(self.logger)
            product_event = self.params.get('SCProduct')
            self.logger.info("Describe constraint for the portfolio")
            response = sc.describe_constraint(constraint_id)
            self.logger.info("Describe Constraint Response")
            self.logger.info(response)
            rules = loads(response.get("ConstraintParameters")).get('Rules')
            if product_event.get('Rules') == rules:
                self.logger.info("Template Rules matched: skip to next state")
                value = 'yes'
            else:
                self.logger.info("Template Rules did not match: updated required.")
                value = 'no'
            self.event.update({'RulesMatched': value})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_constraint(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            constraint_id = self.event.get('ConstraintId')
            sc = SC(self.logger)
            self.logger.info("Deleting constraint from the portfolio")
            sc.delete_constraint(constraint_id)
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def disassociate_principal_from_portfolio(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            portfolio_id = self.event.get('PortfolioId')
            portfolio_event = self.params.get('SCPortfolio')
            sc = SC(self.logger)
            self.logger.info("Disassociating principal ARN from the portfolio")
            sc.disassociate_principal_from_portfolio(portfolio_id, portfolio_event.get('PrincipalArn'))
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def disassociate_product_from_portfolio(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            portfolio_id = self.event.get('PortfolioId')
            product_id = self.event.get('ProductId')
            sc = SC(self.logger)
            self.logger.info("Disassociating product from the portfolio")
            sc.disassociate_product_from_portfolio(product_id, portfolio_id)
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_product(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            product_id = self.event.get('ProductId')
            self.logger.info("Deleting the product from the portfolio")
            sc.delete_product(product_id)
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_portfolio(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            portfolio_id = self.event.get('PortfolioId')
            self.logger.info("Deleting the portfolio")
            sc.delete_portfolio(portfolio_id)
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_provisioning_artifacts(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            product_id = self.event.get('ProductId')
            product_event = self.params.get('SCProduct')
            self.logger.info("Listing the provisioning artifact")
            response = sc.list_provisioning_artifacts(product_id)
            self.logger.info("List Artifacts Response")
            self.logger.info(response)
            # Returns the artifact id to be deleted or else empty string
            # Returns the min and max version numbers and total versions (if 49 then send artifact id of min version)
            version_list = []
            for number in response.get('ProvisioningArtifactDetails', {}):
                version_list.append(int(number.get('Name')[1:]))
            existing_latest_version = 'v' + str(max(version_list))
            existing_oldest_version = 'v' + str(min(version_list))
            self.logger.info("List: {}, Min: {}, Max: {}, Hide: {}, Length: {}".format(version_list,
                                                                                       existing_oldest_version,
                                                                                       existing_latest_version,
                                                                                       existing_latest_version,
                                                                                       len(version_list)))
            if len(version_list) > 49:
                value = 'yes'
                self.logger.info("To avoid LimitExceededException we must delete the oldest version")
                for item in response.get('ProvisioningArtifactDetails', {}):
                    if item.get('Name') == existing_oldest_version:
                        self.event.update({'DeleteArtifactId': item.get('Id')})
                        self.event.update({'ExistingOldestVersion': existing_oldest_version})
            else:
                value = 'no'

            self.event.update({'DeleteOldestArtifact': value})
            self.event.update({'ExistingLatestVersion': existing_latest_version})

            # get the artifact ID of existing latest version
            if len(version_list) >= 1:
                for item in response.get('ProvisioningArtifactDetails', {}):
                    if item.get('Name') == existing_latest_version:
                        self.event.update({'ExistingLatestArtifactId': item.get('Id')})
            else:
                self.event.update({'ExistingLatestArtifactId': "None"})

            # get the artifact ID of 'latest - 1' version
            if product_event.get('HideOldVersions').lower() == 'yes' and len(version_list) >= 1:
                for item in response.get('ProvisioningArtifactDetails', {}):
                    if item.get('Name') == existing_latest_version:
                        self.event.update({'HideArtifactId': item.get('Id')})

            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def _rewrite_file_with_invert_match(self, local_old_template_file, old_template_file, exclude_key):
        try:
            with open(old_template_file, 'w') as new_file:
                for line in open(local_old_template_file):
                    if exclude_key not in line:
                        new_file.write(line)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def compare_product_templates(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            product_id = self.event.get('ProductId')
            artifact_id = self.event.get('ExistingLatestArtifactId')

            # download new template file
            new_template_http_url = self.params.get('SCProduct', {}).get('ProvisioningArtifactParameters').get('Info').get('LoadTemplateFromURL')
            new_template_s3_url = convert_http_url_to_s3_url(new_template_http_url)
            local_new_template_file = download_remote_file(self.logger, new_template_s3_url)

            # download existing template file
            response_describe_artifact = sc.describe_provisioning_artifact(product_id, artifact_id)
            old_template_http_url = response_describe_artifact.get('Info').get('TemplateUrl')
            old_template_s3_url = convert_http_url_to_s3_url(old_template_http_url)
            local_old_template_file = download_remote_file(self.logger, old_template_s3_url)

            old_template_file = tempfile.mkstemp()[1] # [1] == os.path.abspath(file)
            new_template_file = tempfile.mkstemp()[1]

            # before file comparision remove lines that begins with 'key:'
            # why? to avoid false negative because this line contains UUID that will always show up in file diff
            exclude = 'key:'
            self._rewrite_file_with_invert_match(local_old_template_file, old_template_file, exclude)
            self._rewrite_file_with_invert_match(local_new_template_file, new_template_file, exclude)

            # set boolean value - if matches set to True else False
            templates_matching = filecmp.cmp(new_template_file, old_template_file, False)

            self.logger.info("templates_matching={}".format(templates_matching))

            # update event to skip artifact creation workflow
            if templates_matching:
                self.logger.info("No changes made in the AVM template, skipping new artifact (version) creation")
                self.event.update({'CreateNewArtifact': "no"})
            else:
                self.event.update({'CreateNewArtifact': "yes"})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise


    def describe_provisioning_artifact(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            product_id = self.event.get('ProductId')
            artifact_id = self.event.get('ProvisioningArtifactId')
            self.logger.info("Describe the provisioning artifact")
            response = sc.describe_provisioning_artifact(product_id, artifact_id)
            self.event.update({'ProvisioningArtifactStatus': response.get('Status')})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_provisioning_artifact(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            product_id = self.event.get('ProductId')
            artifact_parameters = self.params.get('SCProduct', {}).get('ProvisioningArtifactParameters')
            # read the version number and +1 as name of new version
            existing_latest_version = self.event.get('ExistingLatestVersion')
            new_version_number = 'v' + str(int(existing_latest_version[1:]) + 1)
            artifact_parameters.update({'Name': new_version_number})
            self.logger.info("Creating the provisioning artifact")
            response = sc.create_provisioning_artifact(product_id, artifact_parameters)
            self.event.update({'ProvisioningArtifactId': response.get('ProvisioningArtifactDetail', {}).get('Id')})
            self.event.update({'ProvisioningArtifactStatus': response.get('Status')})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def update_provisioning_artifact(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            product_id = self.event.get('ProductId')
            artifact_id = self.event.get('HideArtifactId')
            self.logger.info("Hiding the previous (new version - 1) artifact")
            # Send 'False' to hide the artifact (version)
            sc.update_provisioning_artifact(product_id, artifact_id, False)
            self.event.update({'ProvisioningArtifactId': artifact_id})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_provisioning_artifact(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            product_id = self.event.get('ProductId')
            artifact_id = self.event.get('DeleteArtifactId')
            self.logger.info("Deleting the provisioning artifact")
            sc.delete_provisioning_artifact(product_id, artifact_id)
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def lookup_product(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            portfolio_name = self.params.get('PortfolioName')
            product_name = self.params.get('ProductName')

            sc = SC(self.logger)
            response = sc.list_portfolios()
            portfolio_list = response.get('PortfolioDetails')
            self.logger.info("List Portfolio Response")
            self.logger.info(response)
            # If portfolio already exist, skip to create the portfolio
            if portfolio_list:
                for portfolio in portfolio_list:
                    if portfolio.get('DisplayName') == portfolio_name:
                        self.logger.info("Portfolio Found")
                        portfolio_id = portfolio.get('Id')
                        self.event.update({'PortfolioId': portfolio_id})
                        self.event.update({'PortfolioExist': 'yes'})

                        response = sc.search_products_as_admin(portfolio_id)
                        product_list = response.get('ProductViewDetails')
                        self.logger.info("Search Products Response")
                        self.logger.info(response)
                        if product_list:
                            for product in product_list:
                                self.logger.info(product)
                                if product.get('ProductViewSummary', {}).get('Name') == product_name:
                                    product_id = product.get('ProductViewSummary', {}).get('ProductId')
                                    self.event.update({'ProductId': product_id})
                                    self.event.update({'ProductExist': 'yes'})

                                    self.logger.info("Listing the provisioning artifact")
                                    response = sc.list_provisioning_artifacts(product_id)
                                    self.logger.info("List Artifacts Response")
                                    self.logger.info(response)

                                    version_list = response.get('ProvisioningArtifactDetails')
                                    if version_list:
                                        artifact_id = version_list[-1].get('Id')
                                        self.event.update({'ProvisioningArtifactId': artifact_id})
                                        return self.event

            self.event.update({'PortfolioExist': 'no'})
            self.event.update({'ProductExist': 'no'})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def provision_product(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            product_id = self.event.get('ProductId')
            artifact_id = self.event.get('ProvisioningArtifactId')
            product_params = self.event.get('ProdParams')
            account_name = product_params.get('AccountName')
            ou_name = product_params.get('OrgUnitName')

            params_list = []
            for key, value in product_params.items():
                param = {}
                # In some weird cases, AccountName comes back as '' for the AWS Organizations Master account
                value = "Primary" if key == 'AccountName' and value == "" else value
                param.update({"Key": key})
                param.update({"Value": value})

                # Set the parameters only if it has non blank value; else let SC/CFN use the DefaultValue from the template
                if param.get('Value').strip() != "":
                    params_list.append(param)

            self.logger.info("params_list={}".format(params_list))

            # Provision SC product
            self.logger.info("Provisioning Service Catalog Product")
            # Sanitize the account name and OU name
            provisioned_product_name = sanitize("%s_%s_%s_%s" % ('lz', ou_name, account_name,
                                                                 time.strftime("%Y-%m-%dT%H-%M-%S")))

            response = sc.provision_product(product_id, artifact_id, provisioned_product_name, params_list)
            self.logger.info("Provision Product Response")
            self.logger.info(response)
            record_id = response.get('RecordDetail', {}).get('RecordId')
            self.event.update({'RecordId': record_id})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def _provisioned_products_status(self, sc, pp_id):
        try:
            # Descrive Provisioned Product - send status & message to SM output
            pp_desc_resp = sc.describe_provisioned_product(pp_id)
            self.logger.info('Descrive Provisioned Product Response')
            self.logger.info(pp_desc_resp)
            provisioned_product_detail = pp_desc_resp.get('ProvisionedProductDetail', {})
            details = {'ProvisionedProductName': provisioned_product_detail.get('Name'),
                      'ProvisionedProductID': provisioned_product_detail.get('Id'),
                      'ProvisionedProductStatus': provisioned_product_detail.get('Status'),
                      'ProvisionedProductStatusMessage': provisioned_product_detail.get('StatusMessage')
                      }
            return details
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def describe_record(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            record_id = self.event.get('RecordId')

            # Describe Record
            self.logger.info("Describe Record of Service Catalog Provisioning Product")
            response = sc.describe_record(record_id)
            self.logger.info("Describe Record Response")
            self.logger.info(response)
            status = response.get('RecordDetail', {}).get('Status')
            self.event.update({'ProvisioningStatus': status})
            provisioned_product_id = response.get('RecordDetail', {}).get('ProvisionedProductId')
            key = 'ProvisionedProductStatus-' + provisioned_product_id
            if status != 'SUCCEEDED':
                product_details = self._provisioned_products_status(sc, provisioned_product_id)
                self.event.update({key: product_details})
                # ONLY if service catalog provision product FAILS due to
                # "Error calling API cloudformation:UpdateStack. ErrorCode: Throttling, Message: Rate exceeded"
                # then Retry after random wait time
                if status == 'FAILED':
                    status_message = product_details.get('ProvisionedProductStatusMessage','')
                    self.logger.info(status_message)
                    if ("updatestack" in status_message.lower()) and ("throttling" in status_message.lower()):
                        self.event.update({'ProvisioningStatus': "RETRY"})
            else:
                detail_value = self.event.get(key)
                if self.event.get('RequestType') == 'Delete':
                    status = 'DELETED'
                    detail_value.update({'ProvisionedProductStatus': status})
                    self.event.update({key: detail_value})
                else:
                    product_details = self._provisioned_products_status(sc, provisioned_product_id)
                    self.event.update({key: product_details})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def search_provisioned_products(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            product_id = self.event.get('ProductId')
            next_token = self.event.get('NextPageToken')
            product_params = self.event.get('ProdParams')
            account_email = product_params.get('AccountEmail')
            self.logger.info("Searching for provisioned product with AccountEmail={} and ProductId={}"
                             .format(account_email, product_id))

            if next_token is None:
                next_token = '0'

            response = sc.search_provisioned_products(product_id, next_token)

            self.logger.info("Search Provisioned Products Response")
            self.logger.info(response)
            self.logger.info("Next Page Token Returned: {}".format(response.get('NextPageToken')))

            for provisioned_product in response.get('ProvisionedProducts'):
                self.logger.info("ProvisionedProduct:{}".format(provisioned_product))

                provisioned_product_id = provisioned_product.get('Id')
                status = provisioned_product.get('Status')

                # Ignore products that error out before and
                # to avoid the case of looking up the same product ignore UNDER_CHANGE
                if status == 'ERROR' or status == 'UNDER_CHANGE':
                    continue

                stack_id = provisioned_product.get('PhysicalId')
                self.logger.info("stack_id={}".format(stack_id))
                # Extract Stack Name from the Physical Id
                # e.g. Stack Id: arn:aws:cloudformation:${AWS::Region}:${AWS::AccountId}:stack/SC-${AWS::AccountId}-pp-fb3xte4fc4jmk/5790fb30-547b-11e8-b302-50fae98974c5
                # Stack name = SC-${AWS::AccountId}-pp-fb3xte4fc4jmk
                stack_name = stack_id.split('/')[1]
                self.logger.info("stack_name={}".format(stack_name))

                cfn = Stacks(self.logger)
                resp = {}
                try:
                    resp = cfn.describe_stacks(stack_name)
                except ClientError as e:
                    self.logger.error(e.response)
                    error_info = e.response.get('Error')
                    error_message = error_info.get('Message')
                    self.logger.error(error_info)
                    self.logger.error(error_message)
                    # This is not very resilient way to do this but boto API doesn't provide a better way.
                    if error_message == 'Stack with id {name} does not exist'.format(name=stack_name):
                        self.logger.info('Underlying CFN Stack:{} for the SC provisioned product for Account: {} does not exist.'.format(stack_name, product_params.get('AccountName')))
                        self.logger.info('Skip this provisioned product, move on to the next one or should we terminate this provisioned product?')
                        continue

                stacks = resp.get('Stacks')

                if stacks is not None and type(stacks) is list:
                    for stack in stacks:
                        parameters = stack.get('Parameters')
                        found_provisioned_product = False

                        if parameters is not None and type(parameters) is list:
                            for parameter in parameters:
                                if parameter.get('ParameterKey') == 'AccountEmail' and parameter.get('ParameterValue') == account_email:
                                    self.logger.info("Found the provisioned product with AccountEmail={}".format(account_email))
                                    self.event.update({'ProvisionedProductId': provisioned_product_id})
                                    self.event.update({'ProvisionedProductExists': True})
                                    self.event.update({'NextPageToken': 'Complete'})
                                    found_provisioned_product = True

                            if found_provisioned_product:
                                existing_parameter_keys = []
                                for parameter in parameters:
                                    existing_parameter_keys.append(parameter.get('ParameterKey'))
                                self.event.update({'ExistingParameterKeys': existing_parameter_keys})
                                return self.event

            if response.get('NextPageToken') is None:
                self.event.update({'NextPageToken': 'Complete'})
                self.event.update({'ProvisionedProductId': 'None'})
                self.event.update({'ProvisionedProductExists': False})
            else:
                self.event.update({'NextPageToken': response.get('NextPageToken')})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def update_provisioned_product(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            provisioned_product_id = self.event.get('ProvisionedProductId')
            product_id = self.event.get('ProductId')
            artifact_id = self.event.get('ProvisioningArtifactId')
            product_params = self.event.get('ProdParams')
            existing_parameter_keys = self.event.get('ExistingParameterKeys')

            params_list = []
            for key, value in product_params.items():
                param = {}
                value = "Primary" if key == 'AccountName' and value == "" else value
                param.update({"Key": key})
                # Use previous value for all parameters except OrgUnitName
                # Use the current OU that account belongs to in Organizations
                if key in existing_parameter_keys and key != 'OrgUnitName':
                    param.update({"UsePreviousValue": True})
                else:
                    param.update({"Value": value})

                params_list.append(param)

            self.logger.info("params_list={}".format(params_list))
            response = sc.update_provisioned_product(product_id, artifact_id, provisioned_product_id, params_list)
            self.logger.info("Update Provisioned Product Response")
            self.logger.info(response)
            record_id = response.get('RecordDetail', {}).get('RecordId')
            self.event.update({'RecordId': record_id})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def terminate_provisioned_product(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            sc = SC(self.logger)
            provisioned_product_id = self.event.get('ProvisionedProductId')

            response = sc.terminate_provisioned_product(provisioned_product_id)
            self.logger.info("Terminate Provisioned Product Response")
            self.logger.info(response)
            record_id = response.get('RecordDetail', {}).get('RecordId')
            self.event.update({'RecordId': record_id})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise


class ServiceControlPolicy(object):
    """
    This class handles requests from Service Control Policy State Machine.
    """

    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)

    def _load_policy(self, relative_policy_path):
        policy_file = download_remote_file(self.logger, relative_policy_path)

        self.logger.info("Parsing the policy file: {}".format(policy_file))

        with open(policy_file, 'r') as content_file:
            policy_file_content = content_file.read()

        #Check if valid json
        json.loads(policy_file_content)
        #Return the Escaped JSON text
        return policy_file_content.replace('"', '\"').replace('\n', '\r\n').replace(" ", "")


    def list_policies(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            # Check if PolicyName attribute exists in event, if so, it is called for attach or detach policy
            if 'PolicyName' in self.event:
                policy_name = self.event.get('PolicyName')
            else:
                policy_name = self.params.get('PolicyDocument').get('Name')

            # Check if SCP already exist
            scp = SCP(self.logger)
            pages = scp.list_policies()

            for page in pages:
                policies_list = page.get('Policies')

                # iterate through the policies list
                for policy in policies_list:
                    if policy.get('Name') == policy_name:
                        self.logger.info("Policy Found")
                        self.event.update({'PolicyId': policy.get('Id')})
                        self.event.update({'PolicyArn': policy.get('Arn')})
                        self.event.update({'PolicyExist': "yes"})
                        return self.event
                    else:
                        continue

            self.event.update({'PolicyExist': "no"})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_policy(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            policy_doc = self.params.get('PolicyDocument')

            scp = SCP(self.logger)
            self.logger.info("Creating Service Control Policy")
            policy_s3_url = convert_http_url_to_s3_url(policy_doc.get('PolicyURL'))
            policy_content = self._load_policy(policy_s3_url)

            response = scp.create_policy(policy_doc.get('Name'),
                                         policy_doc.get('Description'),
                                         policy_content)
            self.logger.info("Create SCP Response")
            self.logger.info(response)
            policy_id = response.get('Policy').get('PolicySummary').get('Id')
            self.event.update({'PolicyId': policy_id})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def update_policy(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            policy_doc = self.params.get('PolicyDocument')
            policy_id = self.event.get('PolicyId')
            policy_s3_url = convert_http_url_to_s3_url(policy_doc.get('PolicyURL'))
            policy_content = self._load_policy(policy_s3_url)

            scp = SCP(self.logger)
            self.logger.info("Updating Service Control Policy")
            response = scp.update_policy(policy_id, policy_doc.get('Name'),
                                         policy_doc.get('Description'),
                                         policy_content)
            self.logger.info("Update SCP Response")
            self.logger.info(response)
            policy_id = response.get('Policy').get('PolicySummary').get('Id')
            self.event.update({'PolicyId': policy_id})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_policy(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            policy_id = self.event.get('PolicyId')

            scp = SCP(self.logger)
            self.logger.info("Deleting Service Control Policy")
            response = scp.delete_policy(policy_id)
            self.logger.info("Delete SCP Response")
            self.logger.info(response)
            status = 'Policy: {} deleted successfully'.format(policy_id)
            self.event.update({'Status': status})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def attach_policy(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            if self.params.get('AccountId') == "":
                target_id = self.event.get('OUId')
            else:
                target_id = self.params.get('AccountId')
            policy_id = self.event.get('PolicyId')
            scp = SCP(self.logger)
            response = scp.attach_policy(policy_id, target_id)
            self.logger.info("Attach Policy Response")
            self.logger.info(response)
            status = 'Policy: {} attached successfully to Target: {}'.format(policy_id, target_id)
            self.event.update({'Status': status})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def detach_policy(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            if self.params.get('AccountId') == "":
                target_id = self.event.get('OUId')
            else:
                target_id = self.params.get('AccountId')
            policy_id = self.event.get('PolicyId')
            scp = SCP(self.logger)
            response = scp.detach_policy(policy_id, target_id)
            self.logger.info("Detach Policy Response")
            self.logger.info(response)
            status = 'Policy: {} detached successfully from Target: {}'.format(policy_id, target_id)
            self.event.update({'Status': status})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_policies_for_ou(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            ou_name = self.event.get('OUName')
            delimiter = self.params.get('OUNameDelimiter')
            policy_name = self.params.get('PolicyDocument').get('Name')

            # Check if SCP already exist
            scp = SCP(self.logger)
            organizations = Organizations(self.event, self.logger)

            ou_id = organizations.get_ou_id(ou_name, delimiter)
            self.event.update({'OUId': ou_id})
            pages = scp.list_policies_for_target(ou_id)

            for page in pages:
                policies_list = page.get('Policies')

                # iterate through the policies list
                for policy in policies_list:
                    if policy.get('Name') == policy_name:
                        self.logger.info("Policy Found")
                        self.event.update({'PolicyId': policy.get('Id')})
                        self.event.update({'PolicyArn': policy.get('Arn')})
                        self.event.update({'PolicyAttached': "yes"})
                        return self.event
                    else:
                        continue

            self.event.update({'PolicyAttached': "no"})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_policies_for_account(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            account_id = self.params.get('AccountId')
            policy_name = self.event.get('PolicyName')

            # Check if SCP already exist
            scp = SCP(self.logger)
            pages = scp.list_policies_for_target(account_id)

            for page in pages:
                policies_list = page.get('Policies')

                # iterate through the policies list
                for policy in policies_list:
                    if policy.get('Name') == policy_name:
                        self.logger.info("Policy Found")
                        self.event.update({'PolicyId': policy.get('Id')})
                        self.event.update({'PolicyArn': policy.get('Arn')})
                        self.event.update({'PolicyAttached': "yes"})
                        return self.event
                    else:
                        continue

            self.event.update({'PolicyAttached': "no"})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def detach_policy_from_all_accounts(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            policy_id = self.event.get('PolicyId')
            scp = SCP(self.logger)

            pages = scp.list_targets_for_policy(policy_id)
            accounts = []

            for page in pages:
                target_list = page.get('Targets')

                # iterate through the policies list
                for target in target_list:
                    account_id = target.get('TargetId')
                    scp.detach_policy(policy_id, account_id)
                    accounts.append(account_id)

            status = 'Policy: {} detached successfully from Accounts: {}'.format(policy_id, accounts)
            self.event.update({'Status': status})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def enable_policy_type(self):
        try:
            org = Org(self.logger)
            response = org.list_roots()
            self.logger.info("List roots Response")
            self.logger.info(response)
            root_id = response['Roots'][0].get('Id')

            scp = SCP(self.logger)
            scp.enable_policy_type(root_id)
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise


class ADConnector(object):
    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info("AD Connector Event")
        self.logger.info(event)

    def _get_password(self, region, encapsulated_ssm_key):
        # instantiate SSM class using temporary security credentials
        ssm = SSM(self.logger, region)
        ssm_key = encapsulated_ssm_key[len('_get_ssm_secure_string_'):]
        decrypted_value = ssm.get_parameter(ssm_key)
        return decrypted_value

    def create_ad_connector(self):
        try:
            ds = DirectoryService(self.logger)
            dns_name = self.params.get('DomainDNSName')
            netbios_name = self.params.get('DomainNetBIOSName')
            user = self.params.get('ConnectorUserName')
            # get secure_string from ssm in home region
            encap_ssm_key = self.params.get('ConnectorPassword')
            home_region = self.params.get('ALZRegion')
            password = self._get_password(home_region, encap_ssm_key)
            size = self.params.get('ADConnectorSize')
            vpc_id = self.params.get('VPCId')
            subnet_ids = [self.params.get('Subnet1Id'), self.params.get('Subnet2Id')]
            dns_ips = [self.params.get('DNSIp1'), self.params.get('DNSIp2')]

            response = ds.connect_directory(dns_name, netbios_name, user, password,
                                            size, vpc_id, subnet_ids, dns_ips)
            directory_id = response.get('DirectoryId')
            self.event.update({'DirectoryId': directory_id})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def check_ad_connector_status(self):
        try:
            ds = DirectoryService(self.logger)

            directory_id = self.event.get('DirectoryId', '')

            if directory_id:
                directories = ds.describe_directories(directory_id)
                self.logger.info("ds.describe_directories={}".format(directories))
                if self.event.get('RequestType') == 'Create' or self.event.get('RequestType') == 'Update':
                    self.event.update({'DeleteStatus': ''})
                    stage = directories[0].get('Stage')
                    if stage == 'Active':
                        self.event.update({'CreateStatus': 'Complete'})
                    elif stage == 'Requested' or stage == 'Creating' or stage == 'Created':
                        self.event.update({'CreateStatus': 'Continue'})
                    else:
                        self.event.update({'CreateStatus': 'Fail'})
                elif self.event.get('RequestType') == 'Delete':
                    self.event.update({'CreateStatus': ''})

                    if directories:
                        stage = directories[0].get('Stage')
                    else:
                        stage = 'Deleted'

                    if stage == 'Deleted':
                        self.event.update({'DeleteStatus': 'Complete'})
                    elif stage == 'Deleting':
                        self.event.update({'DeleteStatus': 'Continue'})
                    else:
                        self.event.update({'DeleteStatus': 'Fail'})
                return self.event
            else:
                raise Exception("Unable to find the key: {'DirectoryId'} in the State Machine Output")
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_directory(self):
        try:
            ds = DirectoryService(self.logger)
            directory_id = self.event.get('DirectoryId')
            self.logger.info("Deleting the directory : {}".format(directory_id))
            ds.delete_directory(directory_id)
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def describe_directory(self):
        try:
            ds = DirectoryService(self.logger)
            directories = ds.describe_directories()
            self.logger.info("ds.describe_directories={}".format(directories))
            self.event.update({'DirectoryExists': 'no'})

            for directory in directories:
                # Check Directory name
                if directory.get('Name') == self.params.get('DomainDNSName'):
                    dns_ip1 = self.params.get('DNSIp1')
                    dns_ip2 = self.params.get('DNSIp2')
                    # Check AD DNS IP addresses
                    if dns_ip1 in directory.get('DnsIpAddrs') and dns_ip2 in directory.get('DnsIpAddrs'):
                        directory_id = directory.get('DirectoryId')
                        status = directory.get('Stage')
                        if status == 'Requested' or status == 'Creating' or status == 'Created' or status == 'Active':
                            self.event.update({'DirectoryExists': 'yes'})
                            self.event.update({'DirectoryId': directory_id})

            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise


class GeneralFunctions(object):
    """
    This class handles requests from Cloudformation (StackSet) State Machine.
    """

    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)

    def export_cfn_output(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            regions = self.params.get('RegionList')
            accounts = self.params.get('AccountList')
            stack_set_name = self.params.get('StackSetName')
            stack_set = StackSet(self.logger)

            if len(accounts) == 0 or len(regions) == 0:
                self.logger.info("Either AccountList or RegionList empty; so skipping the export_cfn_output ")
                return self.event

            self.logger.info("Picking the first account from AccountList")
            account = accounts[0]

            self.logger.info("Picking the first region from RegionList")
            region = regions[0]
            if region.lower() == 'all':
                region = environ.get('AWS_REGION')

            # First retrieve the Stack ID from the target account, region deployed via the StackSet
            response = stack_set.describe_stack_instance(stack_set_name, account, region)

            stack_id = response.get('StackInstance').get('StackId')
            self.logger.info("stack_id={}".format(stack_id))
            if stack_id:
                stack_name = stack_id.split('/')[1]
            else:
                raise Exception("Describe Stack Instance failed to retrieve the StackId for StackSet: {} in account: {} and region: {}".format(stack_set_name, account, region))
            self.logger.info("stack_name={}".format(stack_name))

            # instantiate STS class
            _assume_role = AssumeRole()
            cfn = Stacks(self.logger, credentials=_assume_role(self.logger, account), region=region)

            response = cfn.describe_stacks(stack_name)
            stacks = response.get('Stacks')

            if stacks is not None and type(stacks) is list:
                for stack in stacks:
                    if stack.get('StackId') == stack_id:
                        self.logger.info("Found Stack: {}".format(stack.get('StackName')))
                        self.logger.info("Exporting Output of Stack: {} from Account: {} and region: {}"
                                         .format(stack.get('StackName'), str(account), region))
                        outputs = stack.get('Outputs')
                        if outputs is not None and type(outputs) is list:
                            for output in outputs:
                                key = 'output_' + output.get('OutputKey').lower()
                                value = output.get('OutputValue')
                                self.event.update({key: value})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def account_initialization_check(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            sts = STS(self.logger)
            account = self.event.get('AccountId')
            region = os.environ.get('AWS_REGION')

            role_arn = "arn:aws:iam::" + str(account) + ":role/AWSCloudFormationStackSetExecutionRole"
            session_name = "check_account_creation_role"

            # assume role
            credentials = sts.assume_role_new_account(role_arn, session_name)
            self.logger.info("Assuming IAM role: {}".format(role_arn))

            if credentials.get('Error') is not None:
                self.event.update({'AccountInitialized': "no"})
                self.event.update({'Error': credentials.get('Error')})
                return self.event
            else:
                # instantiate EC2 class using temporary security credentials
                self.logger.info("Validating account initialization, ID: {}".format(account))
                ec2 = EC2(self.logger, region, credentials=credentials)

                try:
                    # Checking if EC2 Service Initialized
                    response = ec2.describe_regions()
                    self.logger.info('EC2 DescribeRegion Response')
                    self.logger.info(response)

                    # If API call succeeds
                    self.logger.info('Account Initialized')
                    self.event.update({'AccountInitialized': "yes"})
                    return self.event
                except Exception as e:
                    # If API call fails
                    self.logger.error('Error: {}'.format(e))
                    self.logger.error('Account still initializing, waiting for the Organization State Machine to retry...')
                    self.event.update({'AccountInitialized': "no"})
                    self.event.update({'Error': 'An error occurred when calling the DescribeRegions operation.'})
                    return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def nested_dictionary_iteration(self, dictionary):
        for key, value in dictionary.items():
            if type(value) is dict:
                yield (key, value)
                yield from self.nested_dictionary_iteration(value)
            else:
                yield (key, value)

    def ssm_put_parameters(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            ssm = SSM(self.logger)
            ssm_params = self.params.get('SSMParameters')
            self.logger.info(ssm_params)
            ssm_value = 'NotFound'
            if ssm_params is not None and type(ssm_params) is dict:
                # iterate through the keys to save them in SSM Parameter Store
                for key, value in ssm_params.items():
                    if value.startswith('$[') and value.endswith(']'):
                        value = value[2:-1]
                    # Iterate through all the keys in the event (includes the nested keys)
                    for k, v in self.nested_dictionary_iteration(self.event):
                        if value.lower() == k.lower():
                            ssm_value = v
                            break
                        else:
                            ssm_value = 'NotFound'
                    if ssm_value == 'NotFound':
                        # Raise Exception if the key is not found in the State Machine output
                        raise Exception("Unable to find the key: {} in the State Machine Output".format(value))
                    else:
                        self.logger.info("Adding {}: {} into SSM PS.".format(key, ssm_value))
                        ssm.put_parameter(key, ssm_value)
            else:
                self.logger.info("Nothing to add in SSM Parameter Store")
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def send_status(self, response_status):
        try:
            response_url = self.event.get('ResponseURL')
            reason = 'See details in State Machine Execution: ' + self.event.get('StateMachineArn')
            response_body = {}
            response_body.update({'Status': response_status})
            response_body.update({'Reason': reason})
            response_body.update({'PhysicalResourceId': self.event.get('PhysicalResourceId')})
            response_body.update({'StackId': self.event.get('StackId')})
            response_body.update({'RequestId': self.event.get('RequestId')})
            response_body.update({'LogicalResourceId': self.event.get('LogicalResourceId')})
            response_body.update({'Data': self.event})

            json_response_body = dumps(response_body)

            self.logger.info("Response Body")
            self.logger.info(json_response_body)

            headers = {
                'content-type': '',
                'content-length': str(len(json_response_body))
            }
            response = requests.put(response_url, data=json_response_body, headers=headers)
            self.logger.info("CloudFormation returned status code: " + response.reason)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def send_success_to_cfn(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.event)
            response_url = self.event.get('ResponseURL')
            if response_url is not None and len(response_url) > 0:
                self.send_status('SUCCESS')
            else:
                self.logger.info("ResponseURL not found")
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def send_failure_to_cfn(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            response_url = self.event.get('ResponseURL')
            if response_url is not None and len(response_url) > 0:
                self.send_status('FAILED')
            else:
                self.logger.info("ResponseURL not found")
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def send_execution_data(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            send = Metrics(self.logger)
            data = {"StateMachineExecutionCount": "1"}
            send.metrics(data)
            return self.event
        except:
            return self.event

    def random_wait(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            # Random wait between 1 to 14 minutes
            _seconds = randint(60, 840)
            time.sleep(_seconds)
            return self.event
        except:
            return self.event
