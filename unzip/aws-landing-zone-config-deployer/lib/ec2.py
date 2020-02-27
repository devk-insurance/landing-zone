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
from botocore.exceptions import ClientError
import boto3
import inspect


class EC2(object):
    def __init__(self, logger, region, **kwargs):
        self.logger = logger
        if kwargs is not None:
            if kwargs.get('credentials') is None:
                logger.debug("Setting up EC2 BOTO3 Client with default credentials")
                self.ec2_client = boto3.client('ec2', region_name=region)
            else:
                logger.debug("Setting up EC2 BOTO3 Client with ASSUMED ROLE credentials")
                cred = kwargs.get('credentials')
                self.ec2_client = boto3.client('ec2', region_name=region,
                                               aws_access_key_id=cred.get('AccessKeyId'),
                                               aws_secret_access_key=cred.get('SecretAccessKey'),
                                               aws_session_token=cred.get('SessionToken')
                                               )
        else:
            logger.info("There were no keyworded variables passed.")
            self.ec2_client = boto3.client('ec2', region_name=region)

    def describe_regions(self):
        try:
            response = self.ec2_client.describe_regions()
            return response.get('Regions')
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_vpcs(self):
        try:
            response = self.ec2_client.describe_vpcs()
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'OptInRequired':
                self.logger.info("Caught exception 'OptInRequired', handling the exception...")
                return {"Error": "OptInRequired"}
            else:
                message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                           'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                self.logger.exception(message)
                raise

    def delete_vpc(self, vpc_id):
        try:
            response = self.ec2_client.delete_vpc(
                VpcId=vpc_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_subnets(self, vpc_id):
        try:
            response = self.ec2_client.describe_subnets(
                Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [
                            vpc_id,
                        ],
                    },
                ]
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_subnet(self,subnet_id):
        try:
            response = self.ec2_client.delete_subnet(
                SubnetId=subnet_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_internet_gateways(self, vpc_id):
        try:
            response = self.ec2_client.describe_internet_gateways(
                Filters=[
                    {
                        'Name': 'attachment.vpc-id',
                        'Values': [
                            vpc_id,
                        ],
                    },
                ]
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def detach_internet_gateway(self, igw_id, vpc_id):
        try:
            response = self.ec2_client.detach_internet_gateway(
                InternetGatewayId=igw_id,
                VpcId=vpc_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_internet_gateway(self, igw_id):
        try:
            response = self.ec2_client.delete_internet_gateway(
                InternetGatewayId=igw_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_key_pair(self, key_name):
        try:
            response = self.ec2_client.create_key_pair(
                KeyName=key_name
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_availability_zones(self):
        try:
            response = self.ec2_client.describe_availability_zones(Filters=[{'Name': 'state', 'Values': ['available']}])
            return [r['ZoneName'] for r in response['AvailabilityZones']]
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_vpc_peering_connection(self, peer_vpc_id, vpc_id, peer_owner_id=None, peer_region=None):
        try:
            kwargs = {
                      'PeerVpcId': peer_vpc_id,
                      'VpcId': vpc_id
                    }
            if peer_region is not None:
                kwargs['PeerRegion'] = peer_region
            if peer_owner_id is not None:
                kwargs['PeerOwnerId'] = peer_owner_id
            response = self.ec2_client.create_vpc_peering_connection(**kwargs)
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def accept_vpc_peering_connection(self, vpc_peering_connection_id):
        try:
            response = self.ec2_client.accept_vpc_peering_connection(
                VpcPeeringConnectionId=vpc_peering_connection_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_vpc_peering_connections(self, vpc_peering_connection_ids):
        try:
            response = self.ec2_client.describe_vpc_peering_connections(
                VpcPeeringConnectionIds=vpc_peering_connection_ids
                )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_vpc_peering_connections_by_filters(self, requester_account_id, requester_vpc_id, accepter_account_id, accepter_vpc_id):
        try:
            response = self.ec2_client.describe_vpc_peering_connections(
                Filters=[
                    {
                        'Name': 'requester-vpc-info.owner-id',
                        'Values': [requester_account_id]
                    },
                    {
                        'Name': 'requester-vpc-info.vpc-id',
                        'Values': [requester_vpc_id]
                    },
                    {
                        'Name': 'accepter-vpc-info.owner-id',
                        'Values': [accepter_account_id]
                    },
                    {
                        'Name': 'accepter-vpc-info.vpc-id',
                        'Values': [accepter_vpc_id]
                    },
                ],
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_vpc_peering_connection(self, vpc_peering_connection_id):
        try:
            response = self.ec2_client.delete_vpc_peering_connection(
                VpcPeeringConnectionId=vpc_peering_connection_id
                )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_route(self, vpc_cidr, route_table_id, peer_connection_id):
        try:
            response = self.ec2_client.create_route(
                DestinationCidrBlock=vpc_cidr,
                RouteTableId=route_table_id,
                VpcPeeringConnectionId=peer_connection_id
                )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_route(self, vpc_cidr, route_table_id):
        try:
            response = self.ec2_client.delete_route(
                DestinationCidrBlock=vpc_cidr,
                RouteTableId=route_table_id
                )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def update_route(self, vpc_cidr, route_table_id, peer_connection_id):
        try:
            response = self.ec2_client.replace_route(
                DestinationCidrBlock=vpc_cidr,
                RouteTableId=route_table_id,
                VpcPeeringConnectionId=peer_connection_id
                )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise
