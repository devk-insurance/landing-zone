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

from hashlib import md5
from lib.crhelper import cfn_handler
from custom_resource_handler import StepFunctions, ExpungeDefaultVPC, KeyPair, VPCCalculator, VPCPeering, GetParameters
from lib.logger import Logger
import os
import inspect

# initialise logger
log_level = os.environ.get('log_level')
logger = Logger(loglevel=log_level)
init_failed = False


def execute_state_machine(event):
    try:
        # Executes the state machine with the event from the CFN Custom Resource
        logger.info(event)
        logger.info("Invoking State Machine - Type: {} - CR Router".format(event.get('ResourceType')))
        state_machine = StepFunctions(event, logger)
        logger.info("Creating Organization, Org Unit and Accounts - CR Router")
        state_machine.trigger_state_machine()
        return None
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise


def create(event, context):
    """
    Runs on Stack Creation.
    As there is no real 'resource', and it will never be replaced,
    PhysicalResourceId is set to a hash of StackId and LogicalId.
    """
    s = '%s-%s' % (event.get('StackId'), event.get('LogicalResourceId'))
    physical_resource_id = md5(s.encode('UTF-8')).hexdigest()

    if event.get('ResourceType') == 'Custom::ExpungeVPC':
        ec2 = ExpungeDefaultVPC(event, logger)
        logger.info("Deleting VPCs and dependencies - CR Router")
        response = ec2.expunge_default_vpc()
        logger.info("Response from ExpungeVPC CR Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event.get('ResourceType') == 'Custom::EC2KeyPair':
        ec2 = KeyPair(event, logger)
        logger.info("Creating EC2 Key Pair - CR Router")
        response = ec2.create_key_pair()
        logger.info("Response from KeyPair CR Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event['ResourceType'] == 'Custom::SSMParameters':
        logger.info(event)
        ssm = GetParameters(event, logger)
        logger.info("Running SSM Parameter Values Handler Event - CR Router")
        response = ssm.get_parameter_values()
        logger.info("Response from SSM Parameter Values Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event['ResourceType'] == 'Custom::VPCCalculator':
        logger.info(event)
        vpc = VPCCalculator(event, logger)
        logger.info("Running VPC Calculator - CR Router")
        response = vpc.calculate_vpc_parameters()
        logger.info("Response from Calculate VPC Parameters Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event['ResourceType'] == 'Custom::VPCPeering':
        logger.info(event)
        vpc = VPCPeering(event, logger)
        if event.get('ResourceProperties', {}).get('RouteTableIDs') is not None:
            logger.info("Running VPC Peer Routing - CR Router")
            response = vpc.create_vpc_peering_routing()
        else:
            logger.info("Running VPC Peer Connection - CR Router")
            response = vpc.create_vpc_peering_connection()
        logger.info("Response from VPC Peering Handler")
        logger.info(response)
        return physical_resource_id, response
    else:
        logger.error('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received', exc_info=True)
        raise Exception('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received')


def update(event, context):
    """
    Runs on Stack Update
    """
    physical_resource_id = event['PhysicalResourceId']
    if event.get('ResourceType') == 'Custom::ExpungeVPC':
        ec2 = ExpungeDefaultVPC(event, logger)
        logger.info("Deleting VPCs and dependencies - CR Router")
        response = ec2.expunge_default_vpc()
        logger.info("Response from ExpungeVPC CR Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event['ResourceType'] == 'Custom::VPCCalculator':
        logger.info(event)
        vpc = VPCCalculator(event, logger)
        logger.info("Running VPC Calculator - CR Router")
        response = vpc.calculate_vpc_parameters()
        logger.info("Response from Calculate VPC Parameters Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event['ResourceType'] == 'Custom::SSMParameters':
        logger.info(event)
        ssm = GetParameters(event, logger)
        logger.info("Running SSM Parameter Values Handler Event - CR Router")
        response = ssm.get_parameter_values()
        logger.info("Response from SSM Parameter Values Handler")
        logger.info(response)
        return physical_resource_id, response
    elif event['ResourceType'] == 'Custom::VPCPeering':
        logger.info(event)
        vpc = VPCPeering(event, logger)
        if event.get('ResourceProperties', {}).get('RouteTableIDs') is not None:
            logger.info("Running VPC Peer Routing - CR Router")
            response = vpc.update_vpc_peering_routing()
        else:
            logger.info("Running VPC Peer Connection - CR Router")
            response = vpc.update_vpc_peering_connection()
        logger.info("Response from VPC Peering Handler")
        logger.info(response)
        return physical_resource_id, response
    else:
        logger.error('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received', exc_info=True)
        raise Exception('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received')


def delete(event, context):
    """
    Runs on Stack Delete.
    """
    if event['ResourceType'] == 'Custom::VPCCalculator':
        logger.info(event)
        logger.info("Running VPC Calculator - CR Router")
        response = None
        logger.info("Response from Calculate VPC Parameters Handler")
        logger.info(response)
        return response
    elif event.get('ResourceType') == 'Custom::ExpungeVPC':
        logger.info(event)
        logger.info("No action required, returning 'None'")
        response = None
        return response
    elif event['ResourceType'] == 'Custom::SSMParameters':
        logger.info(event)
        logger.info("Running SSM Parameter Values Handler Event - CR Router")
        response = None
        logger.info("Response from SSM Parameter Values Handler")
        logger.info(response)
        return response
    elif event['ResourceType'] == 'Custom::VPCPeering':
        logger.info(event)
        vpc = VPCPeering(event, logger)
        if event.get('ResourceProperties', {}).get('RouteTableIDs') is not None:
            logger.info("Running VPC Peer Routing - CR Router")
            response = vpc.delete_vpc_peering_routing()
        else:
            logger.info("Running VPC Peer Connection - CR Router")
            response = vpc.delete_vpc_peering_connection()
        logger.info("Response from VPC Peering Handler")
        logger.info(response)
        return response
    else:
        logger.error('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received', exc_info=True)
        raise Exception('No valid ResourceType found! Resource type \"'+event['ResourceType']+'\" received')


def lambda_handler(event, context):
    # Lambda handler function uses crhelper library to handle CloudFormation services
    try:
        logger.info("<<<<<<<<<< Lambda_handler Event >>>>>>>>>>")
        logger.info(event)
        resource_type = event.get('ResourceType')
        if resource_type == 'Custom::Organizations' \
            or resource_type == 'Custom::StackInstance' \
            or resource_type == 'Custom::ServiceControlPolicy' \
            or resource_type == 'Custom::CheckAVMExistsForAccount' \
            or resource_type == 'Custom::ADConnector':
            s = '%s-%s' % (event.get('StackId'), event.get('LogicalResourceId'))
            physical_resource_id = md5(s.encode('UTF-8')).hexdigest()
            event.update({'PhysicalResourceId': physical_resource_id})
            execute_state_machine(event)
        else:
            return cfn_handler(event, context, create, update, delete, logger, init_failed)
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise