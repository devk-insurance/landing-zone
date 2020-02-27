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


class DirectoryService(object):
    def __init__(self, logger):
        self.logger = logger
        self.ds_client = boto3.client('ds')

    def connect_directory(self, dns_name, netbios_name, user, password, size, vpc_id, subnet_ids, dns_ips):
        try:
            response = self.ds_client.connect_directory(
                Name=dns_name,
                ShortName=netbios_name,
                Password=password,
                Size=size,
                ConnectSettings={
                    'VpcId': vpc_id,
                    'SubnetIds': subnet_ids,
                    'CustomerDnsIps': dns_ips,
                    'CustomerUserName': user
                }
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_directories(self, directory_id=None):
        try:
            if directory_id:
                response = self.ds_client.describe_directories(
                    DirectoryIds=[directory_id]
                )
            else:
                # Think about pagination
                response = self.ds_client.describe_directories()

            return response.get('DirectoryDescriptions')
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_directory(self, directory_id):
        try:
            response = self.ds_client.delete_directory(
                DirectoryId=directory_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

