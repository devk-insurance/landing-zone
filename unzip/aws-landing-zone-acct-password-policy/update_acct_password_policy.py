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
Delete or update password policy on an account

Event:

RequestType: [ Delete | Create | Update ]
ResourceProperties:
    AllowUsersToChangePassword: [ True | False ]
    HardExpiry: [ True | False ]
    MaxPasswordAge: int default: 0
    PasswordReusePrevention: int default: 0
    MinimumPasswordLength: int (no default)
    RequireLowerCaseCharacters: [ True | False ]
    RequireNumbers: [ True | False ]
    RequireSymbols: [ True | False ]
    RequireUppercaseCharacters [ True | False ]


Response:
    cfn_handler is called, passing the create, update, and delete function 
    objects. cfn_handler takes care of sending the response to the Cloud-
    Formation stack.
"""

import os
from ast import literal_eval
import boto3
from botocore.exceptions import ClientError
from botocore.client import Config
from lib.logger import Logger
from lib.crhelper import cfn_handler

# initialize logger
log_level = 'debug' if os.environ.get('log_level', None) is None else os.environ.get('log_level')

logger = Logger(loglevel=log_level)
init_failed = False

config = Config(retries = {'max_attempts':4})

iam = boto3.client('iam', config=config)

def create(event, context):
    """
    Create/Update
    """
    resource_props = event.get('ResourceProperties', {})
    physical_resource_id = "CustomResourcePhysicalID"
    try:
        response = iam.update_account_password_policy(
            AllowUsersToChangePassword=literal_eval(
                resource_props.get('AllowUsersToChangePassword', 'True').title()
                ),
            HardExpiry=literal_eval(
                resource_props.get('HardExpiry', 'True').title()
                ),
            MaxPasswordAge=int(resource_props.get('MaxPasswordAge', 0)),
            MinimumPasswordLength=int(resource_props.get('MinimumPasswordLength', 8)),
            PasswordReusePrevention=int(resource_props.get('PasswordReusePrevention', 0)),
            RequireLowercaseCharacters=literal_eval(
                resource_props.get('RequireLowercaseCharacters', 'True').title()
                ),
            RequireNumbers=literal_eval(
                resource_props.get('RequireNumbers', 'True').title()
                ),
            RequireSymbols=literal_eval(
                resource_props.get('RequireSymbols', 'True').title()
                ),
            RequireUppercaseCharacters=literal_eval(
                resource_props.get('RequireUppercaseCharacters', 'True').title()
                )
        )
    except ClientError as exc:
        logger.warning('update_account_password_policy encountered an exception: {}'.format(exc))
        raise exc

    return physical_resource_id, response

def delete(event, context):
    """
    Delete the account password policy
    """
    try:
        iam.delete_account_password_policy()
    except ClientError as exc:
        # Ignore exception if policy doesn't exist
        if exc.response['Error']['Code'] != 'NoSuchEntity':
            logger.warning('delete_account_password_policy encountered an exception: {}'.format(exc))
            raise exc

update = create # update and create call the same function

def lambda_handler(event, context):
    """
    Pass event and context to cfn_handler
    cfn_handler calls the functions above based on mapping below, then
    uses its "send" function to post the result to CloudFormation
    """
    logger.info("<<<<<<<<<< Lambda_handler Event >>>>>>>>>>")
    logger.info(event)

    request_type = event.get('RequestType', 'invalid').lower()

    if request_type in ['update', 'create', 'delete']:
        return cfn_handler(event, context, create, update, delete, logger, init_failed)
    else:
        logger.error('Invalid or missing request type {}'.format(request_type))
        raise ValueError('No valid RequestType found! Request type "{}" received'.format(event['RequestType']))
