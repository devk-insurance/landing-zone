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

# !/bin/python

from lib.metrics import Metrics
from lib.ssm import SSM
from lib.ec2 import EC2
from lib.sts import STS
from lib.guardduty import GuardDuty as GD
from botocore.vendored import requests
from json import dumps
import inspect
import time
import os

class AssumeRole(object):
    def __call__(self, logger, account):
        try:
            sts = STS(logger)
            role_arn = "arn:aws:iam::" + str(account) + ":role/AWSCloudFormationStackSetExecutionRole"
            session_name = "aws-landing-zone-role"
            # assume role
            credentials = sts.assume_role(role_arn, session_name)
            return credentials
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            logger.exception(message)
            raise

class VPC(object):

    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)
        self.peer_type = event.get('params', {}).get('PeerType')
        self.assume_role = AssumeRole()
        self.wait_time = os.environ['wait_time']

    def _session(self, region, account_id):
        # instantiate EC2 sessions
        return EC2(self.logger, region, credentials=self.assume_role(self.logger, account_id))

    def describe_vpc_peering_connections(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            # Check if VPC Peering Connection Exist
            hub_account_id = self.params.get('HubAccountId')
            hub_vpc_id = self.params.get('HubVPCId')
            hub_region = self.params.get('HubRegion')

            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')
            spoke_vpc_id = self.params.get('SpokeVPCId')

            # peer_connection_id value will be set to none if not found in the event
            peer_connection_id = self.event.get('ConnectionId')

            # instantiate EC2 sessions
            if self.peer_type == 'Hub':
                ec2 = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                ec2 = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            # peering connection id is not None
            if peer_connection_id:
                response = ec2.describe_vpc_peering_connections([peer_connection_id])
            else:
                response = ec2.describe_vpc_peering_connections_by_filters(hub_account_id,
                                                                           hub_vpc_id,
                                                                           spoke_account_id,
                                                                           spoke_vpc_id)
            self.logger.info("Describe VPC Peering Connections Response")
            self.logger.info(response)

            if response.get('Error') == 'VpcPeeringConnectionIdNotFound':
                self.event.update({'DescribeVpcPeeringConnectionErrored': 'Yes'})
            else:
                self.event.update({'DescribeVpcPeeringConnectionErrored': 'No'})

            if response.get('VpcPeeringConnections'):
                for connection in response.get('VpcPeeringConnections'):
                    status = connection.get('Status').get('Code')
                    message = connection.get('Status').get('Message')
                    if status.lower() == 'active':
                        self.logger.info('Found existing ACTIVE connection.')
                        self.logger.info('Peering status is {} with message:{}'.format(status, message))
                        self.event.update({'RelationshipStatus': status})
                        self.event.update({'ConnectionMessage': message})
                        peer_connection_id = connection.get('VpcPeeringConnectionId')
                        self.event.update({'ConnectionId': peer_connection_id})
                        return self.event
                    else:
                        self.event.update({'RelationshipStatus': status})
                        self.event.update({'ConnectionMessage': message})
            else:
                self.event.update({'CheckConnectionResponse': 'EmptyList'})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_vpc_peering_connection(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            hub_account_id = self.params.get('HubAccountId')
            hub_vpc_id = self.params.get('HubVPCId')
            hub_region = self.params.get('HubRegion')

            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')
            spoke_vpc_id = self.params.get('SpokeVPCId')

            # instantiate EC2 sessions
            if self.peer_type == 'Hub':
                ec2 = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                ec2 = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            # Create vpc peering connection
            response = ec2.create_vpc_peering_connection(spoke_account_id,
                                                         spoke_vpc_id,
                                                         hub_vpc_id,
                                                         spoke_region)
            peer_connection_id = response.get('VpcPeeringConnection', {}).get('VpcPeeringConnectionId')
            self.logger.info("Create VPC Peering Connections Response")
            self.logger.info(response)

            self.logger.info("Waiting for Peering connection to be initialized.")
            time.sleep(int(self.wait_time))

            self.event.update({'ConnectionId': peer_connection_id})
            status = response.get('VpcPeeringConnection', {}).get('Status').get('Code')
            message = response.get('VpcPeeringConnection', {}).get('Status').get('Message')
            self.logger.info('Create connection status is {} with message:{}'.format(status, message))
            self.event.update({'RelationshipStatus': status})
            self.event.update({'ConnectionMessage': message})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def accept_vpc_peering_connection(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')

            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')

            # peer_connection_id value will be set to none if not found in the event
            peer_connection_id = self.event.get('ConnectionId')

            # instantiate EC2 sessions
            if self.peer_type == 'Hub':
                ec2 = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                ec2 = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            response = ec2.accept_vpc_peering_connection(peer_connection_id)
            # Status: 'initiating-request'|'pending-acceptance'|'active'|'deleted'|
            # 'rejected'|'failed'|'expired'|'provisioning'|'deleting'
            status = response.get('VpcPeeringConnection', {}).get('Status').get('Code')
            message = response.get('VpcPeeringConnection', {}).get('Status').get('Message')
            hub_vpc_cidr = response.get('VpcPeeringConnection', {}).get('RequesterVpcInfo', {}).get('CidrBlock')
            spoke_vpc_cidr = response.get('VpcPeeringConnection', {}).get('AccepterVpcInfo', {}).get('CidrBlock')
            self.logger.info('Accept connection status is {} with message:{}'.format(status, message))
            self.event.update({'AcceptRelationshipStatus': status})
            self.event.update({'AcceptConnectionMessage': message})
            self.event.update({'HubVPCCIDR': hub_vpc_cidr})
            self.event.update({'SpokeVPCCIDR': spoke_vpc_cidr})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_vpc_peering_connection(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')

            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')

            # peer_connection_id value will be set to none if not found in the event
            peer_connection_id = self.event.get('ConnectionId')

            # instantiate EC2 sessions
            if self.peer_type == 'Hub':
                ec2 = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                ec2 = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            # Create vpc peering connection
            response = ec2.delete_vpc_peering_connection(peer_connection_id)
            self.logger.info("Delete VPC Peering Connections Response")
            self.logger.info(response)
            if response:
                delete_response = 'successful_connection_deletion'
            else:
                delete_response = 'failed_connection_deletion'
            self.event.update({'DeleteConnectionResponse': delete_response})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise


class GuardDuty(object):
    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)
        self.peer_type = event.get('params', {}).get('PeerType')
        self.assume_role = AssumeRole()
        self.wait_time = os.environ['wait_time']

    def _session(self, region, account_id):
        # instantiate GuardDuty sessions
        return GD(self.logger, region, credentials=self.assume_role(self.logger, account_id))

    def _get_master_detector_id(self, guardduty):
        response = guardduty.list_detectors()
        master_detector_id = response.get('DetectorIds')[0]
        self.event.update({'MasterDetectorId': master_detector_id})
        self.logger.info("Master Detector ID: {}".format(master_detector_id))
        # Guardduty only creates one detector per region per account
        return master_detector_id

    def _is_master_equals_member(self):
        if self.params.get('HubAccountId') == self.params.get('SpokeAccountId'):
            self.event.update({'RelationshipStatus': 'MasterAcctIdEqualsMemberAcctId'})
            self.event.update({'Message': 'An AWS account cannot be a GuardDuty master and member account at the '
                                          'same time.'})
            self.logger.info("Hub Account ID is equal to Spoke Account ID. Skipping this step.")
            return True
        else:
            return False

    def get_invitation_status(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')
            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')

            #Check if master account id equals member account id
            if self._is_master_equals_member():
                return self.event

            # instantiate GuardDuty sessions
            if self.peer_type == 'Hub':
                guardduty = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                guardduty = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            detector_id = self.event.get('MemberDetectorId')  # member
            # Obtaining Relationship status with master account.
            response = guardduty.get_master_account(detector_id)
            self.logger.info("Get Master Account (get_master_account) Response")
            self.logger.info(response)
            relationship_status = response.get('Master', {}).get('RelationshipStatus')
            if relationship_status is not None:
             self.event.update({'RelationshipStatus': relationship_status.lower()})
            else:
                raise Exception("LZ Raising Exception: Relationship status not found.")
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_detectors(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')
            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')

            # Check if master account id equals member account id
            if self._is_master_equals_member():
                return self.event

            # instantiate GuardDuty sessions
            if self.peer_type == 'Hub':
                guardduty = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                guardduty = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            response = guardduty.list_detectors()
            self.logger.info("List Detectors Response")
            self.logger.info(response)
            if response.get('DetectorIds'):
                detector_id = response.get('DetectorIds')[0]
                self.event.update({'MemberDetectorId': detector_id})

                # Check for existing relationship and invitation id
                response = guardduty.get_master_account(detector_id)
                self.logger.info("Get Master Account (get_invitation_status) Response")
                self.logger.info(response)
                if response.get('Master') is not None:
                    invitation_id = response.get('Master', {}).get('InvitationId')
                    if invitation_id is not None:
                        self.event.update({'InvitationId': invitation_id})
                    relationship_status = response.get('Master', {}).get('RelationshipStatus')
                    if relationship_status is not None:
                        self.event.update({'RelationshipStatus': relationship_status.lower()})
                else:
                    response = guardduty.list_invitations()
                    self.logger.info("List Invitations Response")
                    self.logger.info(response)
                    if response.get('Invitations'):
                        invitation_id = response.get('Invitations')[0].get('InvitationId')
                        self.event.update({'InvitationId': invitation_id})
                        relationship_status = response.get('Invitations')[0].get('RelationshipStatus')
                        self.event.update({'RelationshipStatus': relationship_status.lower()})
                    else:
                        self.event.update({'InvitationId': 'NotFound'})
            else:
                self.event.update({'MemberDetectorId': 'None'})
            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def list_members(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')
            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')
            next_token = self.event.get('ListMemberNextToken')

            # Check if master account id equals member account id
            if self._is_master_equals_member():
                return self.event

            # instantiate GuardDuty sessions
            if self.peer_type == 'Hub':
                guardduty = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                guardduty = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            detector_id = self._get_master_detector_id(guardduty)

            if next_token:
                args = {'DetectorId': detector_id,
                        'NextToken': next_token}
            else:
                args = {'DetectorId': detector_id}

            response = guardduty.list_members(args)
            self.logger.info("List Members Response")
            self.logger.info(response)
            if response.get('Members'):
                for member in response.get('Members'):
                    if member.get('AccountId') == spoke_account_id:
                        self.logger.info('Account ID: {} is GuardDuty member of Master Account: {}'
                                         .format(spoke_account_id, hub_account_id))
                        self.event.update({'ExistingMember': 'Yes'})
                        self.event.update({'RelationshipStatus': member.get('RelationshipStatus').lower()})
                        # Valid values: CREATED | INVITED | DISABLED | ENABLED | REMOVED | RESIGNED |
                        # EMAILVERIFICATIONINPROGRESS | EMAILVERIFICATIONFAILED
                        return self.event
                else:
                    self.event.update({'ExistingMember': 'No'})
            else:
                self.event.update({'ExistingMember': 'No'})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_detector(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)

            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')
            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')

            # Check if master account id equals member account id
            if self._is_master_equals_member():
                return self.event

            # instantiate GuardDuty sessions
            if self.peer_type == 'Hub':
                guardduty = GD(self.logger, hub_region, credentials=self.assume_role(self.logger, hub_account_id))
            elif self.peer_type == 'Spoke':
                guardduty = GD(self.logger, spoke_region, credentials=self.assume_role(self.logger, spoke_account_id))
            else:
                raise Exception("Peer Type not found in the input")

            detector_id = self.event.get('MemberDetectorId')
            if detector_id == 'None':
                response = guardduty.create_detector()
                self.logger.info("Create Detectors Response")
                self.logger.info(response)
                detector_id = response.get('DetectorId')
                self.event.update({'MemberDetectorId': detector_id})
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def create_members(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')
            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')
            spoke_email_id = self.params.get('SpokeEmailId')

            # Check if master account id equals member account id
            if self._is_master_equals_member():
                return self.event

            # instantiate GuardDuty sessions
            if self.peer_type == 'Hub':
                guardduty = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                guardduty = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            existing_member = self.event.get('ExistingMember')
            if existing_member == 'No':
                detector_id = self._get_master_detector_id(guardduty)
                account_list = [{
                    'AccountId': spoke_account_id,
                    'Email': spoke_email_id
                }]

                response = guardduty.create_members(account_list, detector_id)
                if response.get('UnprocessedAccounts'):
                    self.logger.info("Unable to process member account {}. Reason: {}".
                                    format(response.get('UnprocessedAccounts')[0].get('AccountId'),
                                           response.get('UnprocessedAccounts')[0].get('Result')))
                    self.event.update({'UnprocessedCreateMember': response.get('UnprocessedAccounts')[0].get('Result')})
                else:
                    self.event.update({'NewMemberCreated': 'Yes'})
            else:
                self.logger.info("{} already a member, skipping create_member step.".format(spoke_account_id))
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def invite_members(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')
            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')

            # Check if master account id equals member account id
            if self._is_master_equals_member():
                return self.event

            # instantiate GuardDuty sessions
            if self.peer_type == 'Hub':
                guardduty = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                guardduty = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            existing_member = self.event.get('ExistingMember')
            if existing_member == 'No':
                detector_id = self._get_master_detector_id(guardduty)
                account_list = [spoke_account_id]
                response = guardduty.invite_members(account_list, detector_id)
                if response.get('UnprocessedAccounts'):
                    self.logger.info("Unable to process member account {}. Reason: {}".
                                    format(response.get('UnprocessedAccounts')[0].get('AccountId'),
                                           response.get('UnprocessedAccounts')[0].get('Result')))
                    self.event.update({'UnprocessedInviteMember': response.get('UnprocessedAccounts')[0].get('Result')})
                else:
                    self.event.update({'InviteMember': 'Successful'})

            else:
                self.logger.info("{} already a member, skipping invite_members step.".format(spoke_account_id))
            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def accept_invitation(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')
            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')

            # Check if master account id equals member account id
            if self._is_master_equals_member():
                return self.event

            # instantiate GuardDuty sessions
            if self.peer_type == 'Hub':
                guardduty = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                guardduty = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            existing_member = self.event.get('ExistingMember')
            if existing_member == 'No':
                #get invitation id and status
                #get invitation id and status
                detector_id = self.event.get('MemberDetectorId')  # member

                # Invitation sent - waiting before Invitation ID is generated
                time.sleep(int(self.wait_time))
                response = guardduty.list_invitations()
                self.logger.info("List Invitations in MEMBER - region: {} Response".format(spoke_region))
                self.logger.info(response)

                relationship_status = 'Undetermined'
                if response.get('Invitations'):
                    invitation_id = response.get('Invitations')[0].get('InvitationId')
                    self.event.update({'InvitationId': invitation_id})
                    relationship_status = response.get('Invitations')[0].get('RelationshipStatus')
                    self.event.update({'RelationshipStatus': relationship_status.lower()})
                if relationship_status == 'Invited':
                    guardduty.accept_invitation(detector_id, invitation_id, hub_account_id)
                else:
                    self.logger.info("'RelationshipStatus' != 'Invited', 'RelationshipStatus' = {}, "
                                     "skipping accept_invitation".format(relationship_status))
            else:
                self.logger.info("{} already a member, skipping accept_invitation step.".format(spoke_account_id))

            return self.event
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_detector(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')
            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')

            # Check if master account id equals member account id
            if self._is_master_equals_member():
                return self.event

            # instantiate GuardDuty sessions
            if self.peer_type == 'Hub':
                guardduty = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                guardduty = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            existing_member = self.event.get('ExistingMember')
            if existing_member == 'Yes':
                detector_id = self.event.get('MemberDetectorId')  # member
                # Obtaining Relationship status with master account.
                response = guardduty.disassociate_from_master_account(detector_id)
                self.logger.info("DisassociateFromMasterAccount Response")
                self.logger.info(response)
                response = guardduty.delete_detector(detector_id)
                self.logger.info("Delete Detector Response")
                self.logger.info(response)
            else:
                self.logger.info("{} not a member, skipping delete_detector step.".format(spoke_account_id))


            return self.event

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            gf = GeneralFunctions(self.event, self.logger)
            gf.send_failure_to_cfn()
            raise

    def delete_members(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            self.logger.info(self.params)
            hub_account_id = self.params.get('HubAccountId')
            hub_region = self.params.get('HubRegion')
            spoke_region = self.params.get('SpokeRegion')
            spoke_account_id = self.params.get('SpokeAccountId')

            # Check if master account id equals member account id
            if self._is_master_equals_member():
                return self.event

            # instantiate GuardDuty sessions
            if self.peer_type == 'Hub':
                guardduty = self._session(hub_region, hub_account_id)
            elif self.peer_type == 'Spoke':
                guardduty = self._session(spoke_region, spoke_account_id)
            else:
                raise Exception("Peer Type not found in the input")

            existing_member = self.event.get('ExistingMember')
            if existing_member == 'Yes':
                detector_id = self._get_master_detector_id(guardduty)
                account_list = [spoke_account_id]

                response = guardduty.delete_members(account_list, detector_id)
                if response.get('UnprocessedAccounts'):
                    self.logger.info("Unable to process member account {}. Reason: {}".
                                    format(response.get('UnprocessedAccounts')[0].get('AccountId'),
                                           response.get('UnprocessedAccounts')[0].get('Result')))
                    self.event.update({'UnprocessedCreateMember': response.get('UnprocessedAccounts')[0].get('Result')})
                else:
                    self.event.update({'MemberDeleted': 'Yes'})
            else:
                self.logger.info("{} already a member, skipping delete_members step.".format(spoke_account_id))
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
