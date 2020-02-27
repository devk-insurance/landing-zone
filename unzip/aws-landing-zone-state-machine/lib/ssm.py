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
ssm_client = boto3.client('ssm')

class SSM(object):
    def __init__(self, logger):
        self.logger = logger

    def put_parameter(self, name, value, description="This value was stored by Landing Zone Solution.",
                      type='String', overwrite=True):
        try:
            response = ssm_client.put_parameter(
                Name=name,
                Value=value,
                Description=description,
                Type=type,
                Overwrite=overwrite
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def put_parameter_use_cmk(self, name, value, key_id, description="This value was stored by Landing Zone Solution.",
                      type='SecureString', overwrite=True):
        try:
            response = ssm_client.put_parameter(
                Name=name,
                Value=value,
                Description=description,
                KeyId=key_id,
                Type=type,
                Overwrite=overwrite
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def get_parameter(self, name):
        try:
            response = ssm_client.get_parameter(
                Name=name,
                WithDecryption=True
            )
            return response.get('Parameter', {}).get('Value')
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_parameter(self, name):
        try:
            response = ssm_client.delete_parameter(
                # Name (string)
                Name=name
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def get_parameters_by_path(self, path):
        try:
            response = ssm_client.get_parameters_by_path(
                Path=path if path.startswith('/') else '/'+path,
                Recursive=False,
                WithDecryption=True
            )
            return response.get('Parameters', [])
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_parameters_by_path(self, name):
        try:
            params_list = self.get_parameters_by_path(name)
            if params_list:
                for param in params_list:
                    self.delete_parameter(param.get('Name'))
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_parameters(self, parameter_name):
        try:
            response = ssm_client.describe_parameters(
                ParameterFilters=[
                    {
                        'Key': 'Name',
                        'Option': 'Equals',
                        'Values': [parameter_name]
                    }
                ]
            )
            parameters = response.get('Parameters', [])
            if parameters:
                return parameters[0]
            else:
                return None
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise