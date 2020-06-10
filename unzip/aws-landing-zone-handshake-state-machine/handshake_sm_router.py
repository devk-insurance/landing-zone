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

# !/bin/python

from handshake_sm_handler import VPC, GuardDuty, GeneralFunctions
from lib.logger import Logger
import os
import inspect

# initialize logger
log_level = os.environ['log_level']
logger = Logger(loglevel=log_level)

class Handshake(object):
    '''
    VPC Peering:
        Requester = Hub (Master)
        Accepter = Spoke (Members)
    GuardDuty:
        Requester = Hub (Master)
        Accepter = Spoke (Members)

    This class handles different ServiceTypes for Handshake mechanism. Based on ServiceType and Peertype
    each generic state (in State Machine) routes to a specific function mapped the ServiceType.
    '''
    def __init__(self, event, logger):
        self.event = event
        self.params = event.get('ResourceProperties')
        self.logger = logger
        self.logger.info(self.__class__.__name__ + " Class Event")
        self.logger.info(event)
        self.peer_type = event.get('params', {}).get('PeerType')
        self.service_type = self.params.get('ServiceType')
        if self.service_type == 'VPCPeering':
            self.vpc = VPC(event, logger)
        elif self.service_type == 'GuardDuty':
            self.gd = GuardDuty(event, logger)

    def _no_action_response(self, function_name):
        self.logger.info("For {}: No action required in {} account for {} service type".format(function_name,
                                                                                 self.peer_type,
                                                                                 self.service_type))
        return self.event
    def describe_resources(self):
        response = ""
        if self.service_type == 'VPCPeering':
            if self.peer_type == 'Spoke':
                response = self.vpc.describe_vpc_peering_connections()
            if self.peer_type == 'Hub':
                response = self._no_action_response(inspect.stack()[0][3])
        elif self.service_type == 'GuardDuty':
            if self.peer_type == 'Spoke':
                response = self.gd.list_detectors()
            if self.peer_type == 'Hub':
                response = self.gd.list_members()
        else:
            message = "Service Type {} is not supported.".format(self.service_type)
            logger.info(message)
            return {"Message": message}

        self.logger.info(response)
        return response

    def create_resources(self):
        response = ""
        if self.service_type == 'VPCPeering':
            if self.peer_type == 'Spoke':
                response = self._no_action_response(inspect.stack()[0][3])
            if self.peer_type == 'Hub':
                response = self._no_action_response(inspect.stack()[0][3])
        elif self.service_type == 'GuardDuty':
            if self.peer_type == 'Spoke':
                response = self.gd.create_detector()
            if self.peer_type == 'Hub':
                response = self.gd.create_members()
        else:
            message = "Service Type {} is not supported.".format(self.service_type)
            logger.info(message)
            return {"Message": message}

        self.logger.info(response)
        return response

    def send_invitation(self):
        response = ""
        if self.service_type == 'VPCPeering':
            if self.peer_type == 'Spoke':
                response = self._no_action_response(inspect.stack()[0][3])
            if self.peer_type == 'Hub':
                response = self.vpc.create_vpc_peering_connection()
        elif self.service_type == 'GuardDuty':
            if self.peer_type == 'Spoke':
                response = self._no_action_response(inspect.stack()[0][3])
            if self.peer_type == 'Hub':
                response = self.gd.invite_members()
        else:
            message = "Service Type {} is not supported.".format(self.service_type)
            logger.info(message)
            return {"Message": message}

        self.logger.info(response)
        return response

    def check_invitation_status(self):
        response = ""
        if self.service_type == 'VPCPeering':
            if self.peer_type == 'Spoke':
                response = self.vpc.describe_vpc_peering_connections()
            if self.peer_type == 'Hub':
                response = self.vpc.describe_vpc_peering_connections()
        elif self.service_type == 'GuardDuty':
            if self.peer_type == 'Spoke':
                response = self.gd.get_invitation_status()
            if self.peer_type == 'Hub':
                response = self._no_action_response(inspect.stack()[0][3])
        else:
            message = "Function name does not match any function in the handler file."
            logger.info(message)
            return {"Message": message}

        self.logger.info(response)
        return response

    def accept_invitation(self):
        response = ""
        if self.service_type == 'VPCPeering':
            if self.peer_type == 'Spoke':
                response = self.vpc.accept_vpc_peering_connection()
            if self.peer_type == 'Hub':
                response = self._no_action_response(inspect.stack()[0][3])
        elif self.service_type == 'GuardDuty':
            if self.peer_type == 'Spoke':
                response = self.gd.accept_invitation()
            if self.peer_type == 'Hub':
                response = self._no_action_response(inspect.stack()[0][3])
        else:
            message = "Function name does not match any function in the handler file."
            logger.info(message)
            return {"Message": message}

        self.logger.info(response)
        return response

    def delete_resources(self):
        response = ""
        if self.service_type == 'VPCPeering':
            if self.peer_type == 'Spoke':
                response = self._no_action_response(inspect.stack()[0][3])
            if self.peer_type == 'Hub':
                response = self.vpc.delete_vpc_peering_connection()
        elif self.service_type == 'GuardDuty':
            if self.peer_type == 'Spoke':
                response = self.gd.delete_detector()
            if self.peer_type == 'Hub':
                response = self.gd.delete_members()
        else:
            message = "Service Type {} is not supported.".format(self.service_type)
            logger.info(message)
            return {"Message": message}

        self.logger.info(response)
        return response


def general_functions(event, function_name):
    gf = GeneralFunctions(event, logger)
    logger.info("Router FunctionName: {}".format(function_name))

    if function_name == 'ssm_put_parameters':
        response = gf.ssm_put_parameters()
    elif function_name == 'send_success_to_cfn':
        response = gf.send_success_to_cfn()
    elif function_name == 'send_failure_to_cfn':
        response = gf.send_failure_to_cfn()
    elif function_name == 'send_execution_data':
        response = gf.send_execution_data()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response


def lambda_handler(event, context):
    # Lambda handler function
    try:
        logger.debug("Lambda_handler Event")
        logger.debug(event)
        logger.debug(context)
        # Execute custom resource handlers
        class_name = event.get('params', {}).get('ClassName')
        function_name = event.get('params', {}).get('FunctionName')

        if class_name is not None:
            if class_name == "Handshake":
                hand_shake = Handshake(event, logger)
                if function_name is not None:
                    if function_name == 'create_resources':
                        return hand_shake.create_resources()
                    elif function_name == 'describe_resources':
                        return hand_shake.describe_resources()
                    elif function_name == 'send_invitation':
                        return hand_shake.send_invitation()
                    elif function_name == 'delete_resources':
                        return hand_shake.delete_resources()
                    elif function_name == 'check_invitation_status':
                        return hand_shake.check_invitation_status()
                    elif function_name == 'accept_invitation':
                        return hand_shake.accept_invitation()
                    else:
                        message = "Not a valid 'FunctionName'."
                        logger.info(message)
                        return {"Message": message}
                else:
                    message = "FunctionNamePeer Type not found in the input key not found in the input."
                    logger.info(message)
                    return {"Message": message}
            elif class_name == 'GeneralFunctions':
                return general_functions(event, function_name)
            else:
                message = "Class name not found in input."
                logger.info(message)
                return {"Message": message}
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise
