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

from lib.state_machine import StateMachine
from lib.ssm import SSM
from lib.sts import STS
from lib.ec2 import EC2
import netaddr
from os import environ
import time
import inspect
from lib.params import ParamsHandler
from botocore.exceptions import ClientError
from lib.helper import sanitize, trim_length


class StepFunctions(object):
    # Execute State Machines
    def __init__(self, event, logger):
        self.logger = logger
        self.event = event
        self.logger.info("State Machine Event")
        self.logger.info(event)

    def trigger_state_machine(self):
        try:
            self.logger.info("Executing: " + self.__class__.__name__ + "/" + inspect.stack()[0][3])
            sm = StateMachine(self.logger)
            resource_type = self.event.get('ResourceType')
            request_type = self.event.get('RequestType')

            if resource_type == 'Custom::Organizations' and environ.get('sm_arn_account'):
                state_machine_arn = environ.get('sm_arn_account')
            elif resource_type == 'Custom::ServiceControlPolicy' and environ.get('sm_arn_service_control_policy'):
                state_machine_arn = environ.get('sm_arn_service_control_policy')
            elif resource_type == 'Custom::StackInstance' and environ.get('sm_arn_stack_set'):
                state_machine_arn = environ.get('sm_arn_stack_set')
            elif resource_type == 'Custom::CheckAVMExistsForAccount' and environ.get('sm_arn_check_avm_exists'):
                state_machine_arn = environ.get('sm_arn_check_avm_exists')
            elif resource_type == 'Custom::ADConnector' and environ.get('sm_arn_ad_connector'):
                state_machine_arn = environ.get('sm_arn_ad_connector')
            else:
                self.logger.error("ResourceType Not Supported {} or Env. Variable not found".format(resource_type))
                raise Exception("ResourceType Not Supported {} or Env. Variable not found".format(resource_type))

            # Execute State Machine
            if resource_type == 'Custom::StackInstance':
                exec_name = "%s-%s-%s-%s" % ('AVM-CR', request_type,
                                             trim_length(self.event.get('ResourceProperties', {}).get('StackSetName'), 45),
                                             time.strftime("%Y-%m-%dT%H-%M-%S"))
            elif resource_type == 'Custom::Organizations':
                exec_name = "%s-%s-%s-%s" % ('AVM-CR', request_type,
                                             trim_length(self.event.get('ResourceProperties', {}).get('OUName') + '-' +
                                                         self.event.get('ResourceProperties', {}).get('AccountName'), 45),
                                             time.strftime("%Y-%m-%dT%H-%M-%S"))
            elif resource_type == 'Custom::ServiceControlPolicy':
                exec_name = "%s-%s-%s-%s" % ('AVM-CR', request_type,
                                             trim_length(self.event.get('ResourceProperties', {}).get('Operation'), 45),
                                             time.strftime("%Y-%m-%dT%H-%M-%S"))
            elif resource_type == 'Custom::CheckAVMExistsForAccount':
                exec_name = "%s-%s-%s-%s" % ('AVM-CR', request_type,
                                             trim_length(self.event.get('ResourceProperties', {}).get('ProdParams', {}).get('OUName') + '-' +
                                             self.event.get('ResourceProperties', {}).get('ProdParams', {}).get('AccountName'), 45),
                                             time.strftime("%Y-%m-%dT%H-%M-%S"))
            else:
                exec_name = "%s-%s-%s-%s" % ('AVM-CR', request_type, resource_type.replace("Custom::", ""),
                                             time.strftime("%Y-%m-%dT%H-%M-%S-%s"))
            self.event.update({'StateMachineArn': state_machine_arn})
            self.logger.info("Triggering {} State Machine".format(state_machine_arn.split(":", 6)[6]))
            response = sm.trigger_state_machine(state_machine_arn, self.event, sanitize(exec_name))
            self.logger.info("State machine triggered successfully, Execution Arn: {}".format(response))
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise


class ExpungeDefaultVPC(object):
    def __init__(self, event, logger):
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info("Expunge Default VPC Handler Event")
        self.logger.info(event)

    # Delete Subnets and IGW method
    def delete_vpc_dependencies(self, ec2_session, region, vpc_id):
        # using session object
        ec2 = ec2_session

        # describe subnets
        resp_desc_snet = ec2.describe_subnets(vpc_id)
        self.logger.info(resp_desc_snet)

        # delete every subnet
        for item in resp_desc_snet.get('Subnets'):
            self.logger.info("Deleting Subnet ID: {} in {}".format(item.get('SubnetId'), region))
            self.logger.info(ec2.delete_subnet(item.get('SubnetId')))

        # describe internet gateway
        resp_desc_igw = ec2.describe_internet_gateways(vpc_id)
        self.logger.info(resp_desc_igw)
        for item in resp_desc_igw.get('InternetGateways'):
            # Detach the IGW
            self.logger.info("Detaching Internet Gateway ID: {} in {}".format(item.get('InternetGatewayId'), region))
            self.logger.info(ec2.detach_internet_gateway(item.get('InternetGatewayId'), vpc_id))
            # Delete the IGW
            self.logger.info("Deleting Internet Gateway ID: {} in {}".format(item.get('InternetGatewayId'), region))
            self.logger.info(ec2.delete_internet_gateway(item.get('InternetGatewayId')))

    # Using STS to assume role in the member accounts
    def member_expunge_default_vpc(self, accounts, region):
        # instantiate STS class
        sts = STS(self.logger)

        # iterate through all the members in the list
        for account in accounts:
            role_arn = "arn:aws:iam::" + str(account) + ":role/AWSCloudFormationStackSetExecutionRole"
            session_name = "expunge_default_vpc_role"
            # assume role
            credentials = sts.assume_role(role_arn, session_name)
            self.logger.info("Assuming IAM role: {}".format(role_arn))

            # instantiate EC2 class using temporary security credentials
            self.logger.debug("Creating EC2 Session in {} for account: {}".format(region, account))
            ec2 = EC2(self.logger, region, credentials=credentials)

            if type(credentials) == dict:
                response = ec2.describe_vpcs()
                self.logger.info(response)
                if not response.get('Vpcs'):
                    self.logger.info(
                        "There is no default VPC to delete in {} (member account: {}).".format(region, account))
                else:
                    for vpc in response.get('Vpcs'):
                        vpc_id = vpc.get('VpcId')
                        default = True if vpc.get('IsDefault') is True else False
                        if default:
                            self.logger.info("Found the default VPC: {}".format(vpc_id))

                            # Delete dependencies (calling method)
                            self.logger.info(
                                "Deleting dependencies for member account ID: {} in {}".format(account, region))
                            self.delete_vpc_dependencies(ec2, region, vpc_id)

                            # Delete VPC
                            self.logger.info(
                                "Deleting VPC: {} in member account ID: {} in {}".format(vpc_id, account, region))
                            self.logger.info(ec2.delete_vpc(vpc_id))
                        else:
                            self.logger.info("{} is not the default VPC, skipping...".format(vpc_id))
            else:
                self.logger.error("Unable to obtain credentials")

    def expunge_default_vpc(self):
        ec2 = EC2(self.logger, self.params.get('Region'))
        account_list = self.params.get('AccountList')

        # checking if we member account IDs are present in the parameters
        if account_list is not None:
            for region in ec2.describe_regions():
                try:
                    self.logger.info('~' * 75)
                    self.logger.info("Deleting default VPCs from the member account in "
                                     "region: {}".format(region.get('RegionName')))
                    # Calling method to delete VPCs in the member account
                    self.member_expunge_default_vpc(account_list, region.get('RegionName'))
                except Exception as e:
                    message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                               'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                    self.logger.exception(message)
                    raise
        else:
            self.logger.info("'AccountList' key not found in the properties")
            raise Exception("'AccountList' key not found in the properties")


class KeyPair(object):
    def __init__(self, event, logger):
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info("Key Pair Handler Event")
        self.logger.info(event)

    def create_key_pair(self):
        # declare variables
        # check if member account ID is present in the parameters
        account = self.params.get('MemberAccount').strip()
        region = self.params.get('Region').strip()
        key_material = self.params.get('KeyMaterialParameterName').strip()
        key_fingerprint = self.params.get('KeyFingerprintParameterName').strip()

        if account is not None:
            try:
                param_handler = ParamsHandler(self.logger)
                self.logger.info("Generating EC2 key pair")
                key_name = param_handler.create_key_pair(account, region, key_material, key_fingerprint)
                self.logger.info("Successfully generated EC2 key pair: {}".format(key_name))
                return {'KeyName': key_name}
            except Exception as e:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise
        else:
            self.logger.error("No member account ID found in the parameters.")
            raise Exception("No member account ID found in the parameters.")

    def delete_key_pair(self):
        response = {"Status": "SUCCESS"}
        return response


class GetParameters(object):
    def __init__(self, event, logger):
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info("Get SSM Parameter Values Handler Event")
        self.logger.info(event)

    def get_parameter_values(self):
        ssm = SSM(self.logger)

        parameters = {}
        # read values from SSM Parameter Store
        for key_name in self.params.get('SSMParameterKeys'):
            value = ssm.get_parameter(key_name)
            # new_key_name = key_name[key_name.rfind('/')+1:]
            parameters.update({key_name: value})
        self.logger.info(parameters)

        return parameters


class VPCCalculator(object):
    def __init__(self, event, logger):
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info("Calculate VPC Parameters Handler Event")
        self.logger.info(event)

    def calculate_vpc_parameters(self):
        # This function calculates the CIDR ranges based on the number of subnets inputted by the user
        # The subnet name parameters match the subnet parameters provided in the Scalable VPC QuickStart
        # declare variables
        # set the mask based on the number of subnet combinations
        vpc_cidr = self.params.get('VPCCidr')
        number_of_azs = int(self.params.get('AvailabilityZones'))
        public_subnets = self.params.get('PublicSubnets')
        private_subnets = self.params.get('PrivateSubnets')
        region = self.params.get('Region')
        # join the public and private subnet parameter names
        vpc_subnet_parameter_names = public_subnets + private_subnets
        all_subnet_parameter_names = ['PrivateSubnet1ACIDR',
                                      'PrivateSubnet2ACIDR',
                                      'PrivateSubnet3ACIDR',
                                      'PrivateSubnet4ACIDR',
                                      'PublicSubnet1CIDR',
                                      'PublicSubnet2CIDR',
                                      'PublicSubnet3CIDR',
                                      'PublicSubnet4CIDR',
                                      'PrivateSubnet1BCIDR',
                                      'PrivateSubnet2BCIDR',
                                      'PrivateSubnet3BCIDR',
                                      'PrivateSubnet4BCIDR']
        # calculate the difference between all the subnet parameter names so that null cidr values are returned
        # to the template. This makes it easier for the admin looking at the parameters of the stack to discern between
        # used and unused subnets
        excluded_names = list(set(all_subnet_parameter_names) - set(vpc_subnet_parameter_names))

        # calculate the subnet mask based on the number of subnets required
        number_of_subnets = len(vpc_subnet_parameter_names)
        vpc_mask = int(vpc_cidr[vpc_cidr.find('/')+1:])
        layer = 0
        x = float(number_of_subnets)
        while x > 1:
            x = x/2
            layer += 1
        mask = vpc_mask + layer
        if mask > 28:
            raise Exception('The number of subnets requested ({}) does not fit in the VPC CIDR provided ({}).'
                            'Try increasing your CIDR range or decreasing '
                            'the number of subnets required.'.format(number_of_subnets, vpc_cidr))

        # get the available availability_zones and extract the amount needed based on the user input
        ec2 = EC2(self.logger, region)
        availability_zones = ec2.describe_availability_zones()

        # check that there are enough AZs which are available at this time to satisfy the request
        if len(availability_zones) < number_of_azs:
            self.logger.info('Available availability zones: {}'.format(str(availability_zones)))
            self.logger.info('Availability zones requested: {}'.format(str(number_of_azs)))
            raise Exception('Not enough availability zones are available right now to fulfill this request.'
                            'Reduce the number of AZ\'s or try again later')
        else:
            usable_azs = availability_zones[:number_of_azs]

        # calculate the subnet cidrs
        vpc_ip = netaddr.IPNetwork(vpc_cidr)
        vpc_subnets = list(vpc_ip.subnet(mask, count=len(vpc_subnet_parameter_names)))

        # create the parameter set
        parameters = {}
        parameters['AvailabilityZones'] = usable_azs
        parameters['NumberOfAZs'] = str(number_of_azs)
        parameters['VPCCIDR'] = vpc_cidr
        parameters['CreatePrivateSubnets'] = self.params.get('CreatePrivateSubnets')
        parameters['CreatePublicSubnets'] = self.params.get('CreatePublicSubnets')
        parameters['CreateAdditionalPrivateSubnets'] = self.params.get('CreateAdditionalPrivateSubnets')
        for index, subnet in enumerate(vpc_subnet_parameter_names):
            parameters[subnet] = str(vpc_subnets[index])
        # add the null subnet cidr values for the excluded parameter names
        for name in excluded_names:
            parameters[name] = 'None'
        p = {'Parameters': parameters}
        # Adding the parameters in primary dict
        response = {**p, **parameters}
        self.logger.info(response)
        return response


class VPCPeering(object):
    def __init__(self, event, logger):
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info("VPC Peering Handler Event")
        self.logger.info(event)

    def assume_role(self, account):
        try:
            sts = STS(self.logger)
            role_arn = "arn:aws:iam::" + str(account) + ":role/AWSCloudFormationStackSetExecutionRole"
            session_name = "update-vpc_peering_role"
            # assume role
            credentials = sts.assume_role(role_arn, session_name)
            return credentials
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def check_peering_status(self, ec2_session, peer_connection_id, required_statuses, failed_statuses):
        try:
            # using session object
            ec2 = ec2_session
            status = None
            while status not in required_statuses:
                try:
                    response = ec2.describe_vpc_peering_connections([peer_connection_id])
                except ClientError as e:
                    if e.response['Error']['Code'] == 'InvalidVpcPeeringConnectionID.NotFound':
                        self.logger.debug('Peer connection id was not found yet. Retrying...')
                        time.sleep(5)
                        continue
                    else:
                        raise Exception(e)
                status = response.get('VpcPeeringConnections')[0].get('Status').get('Code')
                message = response.get('VpcPeeringConnections')[0].get('Status').get('Message')
                if status in failed_statuses:
                    raise Exception('VPC Peering Connection request {}.{}'.format(status, message))
                self.logger.info('Peering status is {} with message:{}'.format(status, message))
                time.sleep(5)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_vpc_peering_connection(self):
        try:
            ssm = SSM(self.logger)

            requester_account_id = self.params.get('PeeringAccountID')
            requester_vpc_id = self.params.get('PeeringVPCID')
            requester_region = self.params.get('PeeringRegion')
            accepter_region = self.params.get('Region')
            accepter_account_id = self.params.get('AccountID')
            accepter_vpc_id = self.params.get('VPCID')

            # instantiate EC2 sessions
            ec2_peer_requester = EC2(self.logger, requester_region, credentials=self.assume_role(requester_account_id))
            ec2_peer_accepter = EC2(self.logger, accepter_region, credentials=self.assume_role(accepter_account_id))

            # request vpc peering connection
            response = ec2_peer_requester.create_vpc_peering_connection(accepter_vpc_id,
                                                                        requester_vpc_id,
                                                                        accepter_account_id,
                                                                        accepter_region)
            #
            peer_connection_id = response.get('VpcPeeringConnection', {}).get('VpcPeeringConnectionId')
            self.check_peering_status(ec2_peer_requester, peer_connection_id, ['pending-acceptance', 'active'], ['failed', 'rejected'])

            # accept vpc peering
            resp_peer_connection_accept = ec2_peer_accepter.accept_vpc_peering_connection(peer_connection_id)
            accepter_peer_connection_info = resp_peer_connection_accept.get('VpcPeeringConnection')
            if accepter_peer_connection_info.get('Status').get('Code') is not 'active':
                self.check_peering_status(ec2_peer_requester, peer_connection_id, ['active'], ['failed', 'rejected'])

            # get vpc details
            requester_vpc_cidr = response.get('VpcPeeringConnection', {}).get('RequesterVpcInfo').get('CidrBlock')
            accepter_vpc_cidr = accepter_peer_connection_info.get('AccepterVpcInfo').get('CidrBlock')

            # write peering connection id to SSM Parameter store
            accepter_account_name = sanitize(self.params.get('AccountName'))
            prefix = self.params.get('PeeringConnectionKeyPrefix')
            suffix = 'peering_connections'
            peering_connection_id_parameter_key = '{}/{}/{}'.format(prefix, suffix, accepter_account_name)
            ssm.put_parameter(peering_connection_id_parameter_key, peer_connection_id)
            self.logger.info("SSM Parameter key: {} has been written".format(peering_connection_id_parameter_key))

            return {
                    'PeerConnectionID': peer_connection_id,
                    'RequesterAccountID': requester_account_id,
                    'AccepterAccountID': accepter_account_id,
                    'RequesterVPCCIDR': requester_vpc_cidr,
                    'AccepterVPCCIDR': accepter_vpc_cidr
                    }
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def update_vpc_peering_connection(self):
        try:
            requester_account_id = self.params.get('PeeringAccountID')
            requester_vpc_id = self.params.get('PeeringVPCID')
            requester_region = self.params.get('PeeringRegion')
            accepter_account_id = self.params.get('AccountID')
            accepter_vpc_id = self.params.get('VPCID')

            # instantiate EC2 sessions
            ec2_peer_requester = EC2(self.logger, requester_region, credentials=self.assume_role(requester_account_id))
            response = ec2_peer_requester.describe_vpc_peering_connections_by_filters(requester_account_id, requester_vpc_id, accepter_account_id, accepter_vpc_id)

            if response.get('VpcPeeringConnections'):
                peer_conn = response.get('VpcPeeringConnections')[0]
                existing_peering_id = peer_conn.get('VpcPeeringConnectionId')
                requester_vpc_cidr = peer_conn.get('RequesterVpcInfo').get('CidrBlock')
                accepter_vpc_cidr = peer_conn.get('AccepterVpcInfo').get('CidrBlock')
            else:
                return self.create_vpc_peering_connection()

            return {
                'PeerConnectionID': existing_peering_id,
                'RequesterAccountID': requester_account_id,
                'AccepterAccountID': accepter_account_id,
                'RequesterVPCCIDR': requester_vpc_cidr,
                'AccepterVPCCIDR': accepter_vpc_cidr
            }
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_vpc_peering_connection(self):
        try:
            ssm = SSM(self.logger)

            # read values from SSM Parameter Store
            accepter_account_name = sanitize(self.params.get('AccountName'))
            requester_account_id = self.params.get('PeeringAccountID')
            requester_region = self.params.get('Region')
            self.logger.debug(requester_account_id)
            self.logger.info("Peering Account ID: {}".format(requester_account_id))

            prefix = self.params.get('PeeringConnectionKeyPrefix')
            suffix = 'peering_connections'
            peer_connection_id_parameter_key = '{}/{}/{}'.format(prefix, suffix, accepter_account_name)
            peer_connection_id = ssm.get_parameter(peer_connection_id_parameter_key)
            self.logger.debug(peer_connection_id)
            self.logger.info("Peering Connection ID: {}".format(peer_connection_id))

            # instantiate EC2 session
            ec2_peer_requester = EC2(self.logger, requester_region, credentials=self.assume_role(requester_account_id))

            # delete vpc peering connection id
            response = ec2_peer_requester.delete_vpc_peering_connection(peer_connection_id)
            self.logger.info("Peering Connection ID: {} deleted".format(peer_connection_id))
            self.logger.debug(response)
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_vpc_peering_routing(self):
        try:
            # declare variables
            peer_connection_id = self.params.get('PeerConnectionID')
            vpc_cidr = self.params.get('VPCCIDR')
            account_id = self.params.get('AccountID')
            route_table_ids_str = self.params.get('RouteTableIDs')
            route_table_ids = route_table_ids_str.split(",")
            region = self.params.get('Region')

            # instantiate EC2 sessions
            ec2 = EC2(self.logger, region, credentials=self.assume_role(account_id))
            # change routes in all the peer vpc's route tables
            for id in route_table_ids:
                response = ec2.create_route(vpc_cidr, id, peer_connection_id)
                if response.get('Return'):
                    self.logger.info('Route table {} updated successfully'.format(id))
                else:
                    raise Exception("Failed to update the Route table : {} with route to PeerConnectionID : {} "
                                    "for VPC CIDR: {}".format(id, peer_connection_id, vpc_cidr))
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def update_vpc_peering_routing(self):
        try:
            # declare variables
            peer_connection_id = self.params.get('PeerConnectionID')
            vpc_cidr = self.params.get('VPCCIDR')
            account_id = self.params.get('AccountID')
            route_table_ids_str = self.params.get('RouteTableIDs')
            route_table_ids = route_table_ids_str.split(",")
            region = self.params.get('Region')

            # instantiate EC2 sessions
            ec2 = EC2(self.logger, region, credentials=self.assume_role(account_id))
            # change routes in all the peer vpc's route tables
            for id in route_table_ids:
                response = ec2.update_route(vpc_cidr, id, peer_connection_id)
                if response.get('Return'):
                    self.logger.info('Route table {} updated successfully'.format(id))
                else:
                    raise Exception("Failed to update the Route table : {} with route to PeerConnectionID : {} "
                                    "for VPC CIDR: {}".format(id, peer_connection_id, vpc_cidr))
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_vpc_peering_routing(self):
        try:
            # declare variables
            vpc_cidr = self.params.get('VPCCIDR')
            account_id = self.params.get('AccountID')
            route_table_ids_str = self.params.get('RouteTableIDs')
            route_table_ids = route_table_ids_str.split(",")
            region = self.params.get('Region')

            # instantiate EC2 sessions
            ec2 = EC2(self.logger, region, credentials=self.assume_role(account_id))

            # change routes in all the peer vpc's route tables
            for id in route_table_ids:
                response = ec2.delete_route(vpc_cidr, id)
                self.logger.debug(response.get('Return'))
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise
