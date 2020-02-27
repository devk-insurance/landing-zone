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
from lib.decorator import try_except_retry

cfn_client = boto3.client('cloudformation')


class StackSet(object):
    def __init__(self, logger):
        self.logger = logger

    def describe_stack_set(self, stack_set_name):
        try:
            response = cfn_client.describe_stack_set(
                StackSetName=stack_set_name
            )
            return response
        except Exception:
            pass

    def describe_stack_set_operation(self, stack_set_name, operation_id):
        try:
            response = cfn_client.describe_stack_set_operation(
                StackSetName=stack_set_name,
                OperationId=operation_id
            )
            return response
        except Exception as e:
            self.logger.error("'{}' StackSet Operation ID: {} not found.".format(stack_set_name, operation_id))
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_stack_instances(self, **kwargs):
        try:
            response = cfn_client.list_stack_instances(**kwargs)
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_stack_set(self, stack_set_name, template_url, cf_params, capabilities):
        try:
            parameters = []
            d = {}
            for key, value in cf_params.items():
                '''This condition checks if the value is a List and convert it into a Comma-delimited string.
                Note: Remember to change the parameter type from 'List<AWS::EC2::*::*>'
                (Supported AWS-Specific Parameter Types) to 'CommaDelimitedList' in the template.'''

                if type(value) == list:
                    value = ",".join(map(str, value))
                self.logger.debug("CF Parameter Key: {}, CF Parameter Value: {}".format(key, value))
                d['ParameterKey'] = key
                d['ParameterValue'] = value
                parameters.append(d.copy())

            response = cfn_client.create_stack_set(
                StackSetName=stack_set_name,
                TemplateURL=template_url,
                Parameters=parameters,
                Capabilities=[capabilities],
                Tags=[
                    {
                        'Key': 'AWS_Solutions',
                        'Value': 'LandingZoneStackSet'
                    },
                ]
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_stack_instances(self, stack_set_name, account_list, region_list,
                               failed_tolerance_percent=50, max_concurrent_percent=100):
        try:
            response = cfn_client.create_stack_instances(
                StackSetName=stack_set_name,
                Accounts=account_list,
                Regions=region_list,
                OperationPreferences={
                    'FailureTolerancePercentage': failed_tolerance_percent,
                    'MaxConcurrentPercentage': max_concurrent_percent
                }
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'OperationInProgressException':
                self.logger.info("Caught exception 'OperationInProgressException', handling the exception...")
                return {"OperationId": "OperationInProgressException"}
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    def create_stack_instances_with_override_params(self, stack_set_name, account_list, region_list, override_params,
                               failed_tolerance_percent=50, max_concurrent_percent=100):
        try:
            parameters = []
            d = {}
            for key, value in override_params.items():
                '''This condition checks if the value is a List and convert it into a Comma-delimited string.
                Note: Remember to change the parameter type from 'List<AWS::EC2::*::*>'
                (Supported AWS-Specific Parameter Types) to 'CommaDelimitedList' in the template.'''

                if type(value) == list:
                    value = ",".join(map(str, value))
                self.logger.debug("CF Parameter Key: {}, CF Parameter Value: {}".format(key, value))
                d['ParameterKey'] = key
                d['ParameterValue'] = value
                parameters.append(d.copy())

            response = cfn_client.create_stack_instances(
                StackSetName=stack_set_name,
                Accounts=account_list,
                Regions=region_list,
                ParameterOverrides=parameters,
                OperationPreferences={
                    'FailureTolerancePercentage': failed_tolerance_percent,
                    'MaxConcurrentPercentage': max_concurrent_percent
                }
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'OperationInProgressException':
                self.logger.info("Caught exception 'OperationInProgressException', handling the exception...")
                return {"OperationId": "OperationInProgressException"}
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    def update_stack_instances(self, stack_set_name, account_list, region_list, override_params,
                               failed_tolerance_percent=50, max_concurrent_percent=100):
        try:
            parameters = []
            d = {}
            for key, value in override_params.items():
                '''This condition checks if the value is a List and convert it into a Comma-delimited string.
                Note: Remember to change the parameter type from 'List<AWS::EC2::*::*>'
                (Supported AWS-Specific Parameter Types) to 'CommaDelimitedList' in the template.'''

                if type(value) == list:
                    value = ",".join(map(str, value))
                self.logger.debug("CF Parameter Key: {}, CF Parameter Value: {}".format(key, value))
                d['ParameterKey'] = key
                d['ParameterValue'] = value
                parameters.append(d.copy())

            response = cfn_client.update_stack_instances(
                StackSetName=stack_set_name,
                Accounts=account_list,
                Regions=region_list,
                ParameterOverrides=parameters,
                OperationPreferences={
                    'FailureTolerancePercentage': failed_tolerance_percent,
                    'MaxConcurrentPercentage': max_concurrent_percent
                }
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'OperationInProgressException':
                self.logger.info("Caught exception 'OperationInProgressException', handling the exception...")
                return {"OperationId": "OperationInProgressException"}
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    def update_stack_set(self, stack_set_name, parameter, template_url, capabilities, failed_tolerance_percent=50,
                         max_concurrent_percent=100):
        try:
            parameters = []
            d = {}
            for key, value in parameter.items():
                '''This condition checks if the value is a List and convert it into a Comma-delimited string.
                Note: Remember to change the parameter type from 'List<AWS::EC2::*::*>'
                (Supported AWS-Specific Parameter Types) to 'CommaDelimitedList' in the template.'''

                if type(value) == list:
                    value = ",".join(map(str, value))
                self.logger.debug("CF Parameter Key: {}, CF Parameter Value: {}".format(key, value))
                d['ParameterKey'] = key
                d['ParameterValue'] = value
                parameters.append(d.copy())

            response = cfn_client.update_stack_set(
                StackSetName=stack_set_name,
                TemplateURL=template_url,
                Parameters=parameters,
                Capabilities=[capabilities],
                OperationPreferences={
                    'FailureTolerancePercentage': failed_tolerance_percent,
                    'MaxConcurrentPercentage': max_concurrent_percent
                }
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'OperationInProgressException':
                self.logger.info("Caught exception 'OperationInProgressException', handling the exception...")
                return {"OperationId": "OperationInProgressException"}
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    def delete_stack_set(self, stack_set_name):
        try:
            response = cfn_client.delete_stack_set(
                StackSetName=stack_set_name,
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_stack_instances(self, stack_set_name, account_list, region_list, retain_condition=False,
                               failed_tolerance_percent=50, max_concurrent_percent=100):
        try:
            response = cfn_client.delete_stack_instances(
                StackSetName=stack_set_name,
                Accounts=account_list,
                Regions=region_list,
                RetainStacks=retain_condition,
                OperationPreferences={
                    'FailureTolerancePercentage': failed_tolerance_percent,
                    'MaxConcurrentPercentage': max_concurrent_percent
                }
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'OperationInProgressException':
                self.logger.info("Caught exception 'OperationInProgressException', handling the exception...")
                return {"OperationId": "OperationInProgressException"}
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    def describe_stack_instance(self, stack_set_name, account_id, region):
        try:
            response = cfn_client.describe_stack_instance(
                StackSetName=stack_set_name,
                StackInstanceAccount=account_id,
                StackInstanceRegion=region
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_stack_set_operations(self, **kwargs):
        try:
            response = cfn_client.list_stack_set_operations(**kwargs)
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

class Stacks(object):
    def __init__(self, logger, **kwargs):
        self.logger = logger
        if kwargs is not None:
            if kwargs.get('credentials') is None:
                logger.debug("Setting up CFN BOTO3 Client with default credentials")
                self.cfn_client = boto3.client('cloudformation')
            else:
                logger.debug("Setting up CFN BOTO3 Client with ASSUMED ROLE credentials")
                cred = kwargs.get('credentials')
                region = kwargs.get('region', None)

                if region:
                    self.cfn_client = boto3.client('cloudformation', region_name=region,
                                                   aws_access_key_id=cred.get('AccessKeyId'),
                                                   aws_secret_access_key=cred.get('SecretAccessKey'),
                                                   aws_session_token=cred.get('SessionToken')
                                                   )
                else:
                    self.cfn_client = boto3.client('cloudformation',
                                                   aws_access_key_id=cred.get('AccessKeyId'),
                                                   aws_secret_access_key=cred.get('SecretAccessKey'),
                                                   aws_session_token=cred.get('SessionToken')
                                                   )

    @try_except_retry()
    def describe_stacks(self, stack_name):
        try:
            response = self.cfn_client.describe_stacks(
                StackName=stack_name
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise
