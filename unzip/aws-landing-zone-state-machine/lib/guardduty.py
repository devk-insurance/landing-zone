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
#!/bin/python

from botocore.exceptions import ClientError
import boto3
import inspect
from lib.decorator import try_except_retry


class GuardDuty(object):
    def __init__(self, logger, region, **kwargs):
        self.logger = logger
        if kwargs is not None:
            if kwargs.get('credentials') is None:
                logger.debug("Setting up GuardDuty BOTO3 Client with default credentials")
                self.gd_client = boto3.client('guardduty', region_name=region)
            else:
                logger.debug("Setting up GuardDuty BOTO3 Client with ASSUMED ROLE credentials")
                cred = kwargs.get('credentials')
                self.gd_client = boto3.client('guardduty', region_name=region,
                                               aws_access_key_id=cred.get('AccessKeyId'),
                                               aws_secret_access_key=cred.get('SecretAccessKey'),
                                               aws_session_token=cred.get('SessionToken')
                                               )
        else:
            logger.info("There were no keyworded variables passed.")
            self.gd_client = boto3.client('guardduty', region_name=region)

    def list_invitations(self):
        """
        Response Syntax:
        {
            'Invitations': [
                {
                    'AccountId': 'string',
                    'InvitationId': 'string',
                    'InvitedAt': 'string',
                    'RelationshipStatus': 'string'
                },
            ],
            'NextToken': 'string'
        }
        :returned number of invitations: The default value is 50. The maximum value is 50.
        """
        try:
            response = self.gd_client.list_invitations()
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_detectors(self):
        """
        Response Syntax:
        {
            'DetectorIds': [
                'string',
            ],
            'NextToken': 'string'
        }
        :returned list of detector ID: As of July 25th 2018 - only 1 detector is allowed per AWS Account
        """
        try:
            response = self.gd_client.list_detectors()
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_members(self, kwargs):
        """
        Request Syntax:
        response = client.list_members(
                    DetectorId='string',
                    MaxResults=123,
                    NextToken='string',
                    OnlyAssociated='string' # Default is True
                )
        Response Syntax:
        {
            'Members': [
                {
                    'AccountId': 'string',
                    'DetectorId': 'string',
                    'Email': 'string',
                    'InvitedAt': 'string',
                    'MasterId': 'string',
                    'RelationshipStatus': 'string',
                    'UpdatedAt': 'string'
                },
            ],
            'NextToken': 'string'
        }
        """
        try:
            response = self.gd_client.list_members(**kwargs)
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_detector(self, bool=True):
        """
        Request Syntax:
        response = client.create_detector(
            Enable=True|False
            )
        Response Syntax:
        {
            'DetectorId': 'string'
        }
        """
        try:
            response = self.gd_client.create_detector(
                Enable=bool
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_members(self, account_list, master_detector_id):
        """
        Request Syntax:
            response = client.create_members(
                AccountDetails=[
                    {
                        'AccountId': 'string',
                        'Email': 'string'
                    },
                ],
                DetectorId='string'
            )
        Response Syntax: If the action is successful, the service sends back an HTTP 200 response.
        {
            'UnprocessedAccounts': [
                {
                    'AccountId': 'string',
                    'Result': 'string'
                },
            ]
        }
        """
        try:
            response = self.gd_client.create_members(
                AccountDetails=account_list,
                DetectorId=master_detector_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def invite_members(self, account_list, master_detector_id, disable_email_notification=True, message=None):
        """
        Request Syntax:
            response = client.invite_members(
                AccountIds=[
                    'string',
                ],
                DetectorId='string',
                DisableEmailNotification=True|False,
                Message='string'
            )
        Response Syntax: If the action is successful, the service sends back an HTTP 200 response.
        {
            'UnprocessedAccounts': [
                {
                    'AccountId': 'string',
                    'Result': 'string'
                },
            ]
        }
        """
        try:
            if message is None:
                message = "Inviting GuardDuty member via AWS LZ Handshake SM"
            response = self.gd_client.invite_members(
                AccountIds=account_list,
                DetectorId=master_detector_id,
                DisableEmailNotification=disable_email_notification,
                Message=message
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def accept_invitation(self, member_detector_id, invitation_id, master_id):
        """
        Request Syntax:
        response = client.accept_invitation(
            DetectorId='string',
            InvitationId='string',
            MasterId='string'
        )
        Response Syntax:
        {}
        """
        try:
            response = self.gd_client.accept_invitation(
                DetectorId=member_detector_id,
                InvitationId=invitation_id,
                MasterId=master_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def get_master_account(self, member_detector_id):
        """
        Request Syntax:
        response = client.get_master_account(
            DetectorId='string'
        )
        Response Syntax:
        {
            'Master': {
                'AccountId': 'string',
                'InvitationId': 'string',
                'InvitedAt': 'string',
                'RelationshipStatus': 'string'
            }
        }
        """
        try:
            response = self.gd_client.get_master_account(
                DetectorId=member_detector_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def get_relationship_status(self, member_detector_id):
        try:
            response = self.gd_client.get_master_account(
                DetectorId=member_detector_id
            )
            relationship_status = response.get('Master', {}).get('RelationshipStatus')
            if relationship_status is not None:
                return relationship_status
            else:
                raise Exception("Relationship status not found")
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_members(self, account_list, master_detector_id):
        """
        Request Syntax:
            response = client.delete_members(
                AccountIds=[
                    'string',
                ],
                DetectorId='string'
            )
        Response Syntax: If the action is successful, the service sends back an HTTP 200 response.
        {
            'UnprocessedAccounts': [
                {
                    'AccountId': 'string',
                    'Result': 'string'
                },
            ]
        }
        """
        try:
            response = self.gd_client.delete_members(
                AccountIds=account_list,
                DetectorId=master_detector_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def disassociate_from_master_account(self, member_detector_id):
        """
        Request Syntax:
        response = client.disassociate_from_master_account(
            DetectorId='string'
        )
        Response Syntax:
        { }
        """
        try:
            response = self.gd_client.disassociate_from_master_account(
                DetectorId=member_detector_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_detector(self, member_detector_id):
        """
        Request Syntax:
            response = client.delete_detector(
                    DetectorId='string'
                )
        Response Syntax:
        { }
        """
        try:
            response = self.gd_client.delete_detector(
                DetectorId=member_detector_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise