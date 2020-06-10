###################################################################################################################### 
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
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

#!/bin/python

import boto3
import inspect
import tempfile
from os import environ
from lib.helper import get_service_endpoint


class S3(object):
    def __init__(self, logger, **kwargs):
        self.logger = logger
        self.service_name = 's3'
        self.s3_resource = boto3.resource(self.service_name,
                                          region_name=environ.get('AWS_REGION'),
                                          endpoint_url=get_service_endpoint(self.service_name,
                                                                            environ.get('AWS_REGION')))
        if kwargs is not None:
            if kwargs.get('credentials') is None:
                logger.debug("Setting up S3 BOTO3 Client with default credentials")
                self.s3_client = boto3.client(self.service_name,
                                              region_name=environ.get('AWS_REGION'),
                                              endpoint_url=get_service_endpoint(self.service_name,
                                                                                environ.get('AWS_REGION')))
            else:
                logger.debug("Setting up S3 BOTO3 Client with ASSUMED ROLE credentials")
                cred = kwargs.get('credentials')
                self.s3_client = boto3.client(self.service_name,
                                              aws_access_key_id=cred.get('AccessKeyId'),
                                              aws_secret_access_key=cred.get('SecretAccessKey'),
                                              aws_session_token=cred.get('SessionToken'))
        else:
            logger.info("There were no keyworded variables passed.")
            self.s3_client = boto3.client(self.service_name,
                                          region_name=environ.get('AWS_REGION'),
                                          endpoint_url=get_service_endpoint(self.service_name,
                                                                            environ.get('AWS_REGION')))

    def upload_file(self, bucket_name, local_file_location, key_name):
        try:
            self.s3_resource.Bucket(bucket_name).upload_file(local_file_location, key_name)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def get_s3_object(self, remote_s3_url):
        """ This function downloads the file from the S3 bucket for a given
        S3 path in the method attribute.

        :param remote_s3_url: s3://bucket-name/key-name
        :return: remote S3 file

        Use Cases:
        - manifest file contains template and parameter file as s3://bucket-name/key in SM trigger lambda
        """
        try:
            _file = tempfile.mkstemp()[1]
            parsed_s3_path = remote_s3_url.split("/", 3)  # s3://bucket-name/key
            remote_bucket = parsed_s3_path[2]  # Bucket name
            remote_key = parsed_s3_path[3]  # Key
            self.download_file(remote_bucket, remote_key, _file)
            return _file
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1],
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def download_file(self, bucket_name, key_name, local_file_location):
        """ This function downloads the file from the S3 bucket for a given
        S3 path in the method attribute.

        Use Cases:
        - download the S3 object on a given local file path

        :param bucket_name:
        :param key_name:
        :param local_file_location:
        :return None:
        """
        try:
            self.logger.info("Downloading {}/{} from S3 to {}".format(bucket_name, key_name, local_file_location))
            self.s3_resource.Bucket(bucket_name).download_file(key_name, local_file_location)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def put_bucket_encryption(self, bucket_name, key_id):
        try:
            self.s3_client.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'aws:kms',
                                'KMSMasterKeyID': key_id
                            }
                        },
                    ]
                }
            )

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise
