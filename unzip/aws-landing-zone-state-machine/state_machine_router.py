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

# !/bin/python

from state_machine_handler import CloudFormation, Organizations, ServiceCatalog, GeneralFunctions, ServiceControlPolicy, ADConnector
from lib.logger import Logger
import os
import inspect

# initialise logger
log_level = os.environ['log_level']
logger = Logger(loglevel=log_level)


def cloudformation(event, function_name):
    logger.info("Router FunctionName: {}".format(function_name))
    stack_set = CloudFormation(event, logger)
    if function_name == 'describe_stack_set':
        response = stack_set.describe_stack_set()
    elif function_name == 'describe_stack_set_operation':
        response = stack_set.describe_stack_set_operation()
    elif function_name == 'list_stack_instances':
        response = stack_set.list_stack_instances()
    elif function_name == 'list_stack_instances_account_ids':
        response = stack_set.list_stack_instances_account_ids()
    elif function_name == 'create_stack_set':
        response = stack_set.create_stack_set()
    elif function_name == 'create_stack_instances':
        response = stack_set.create_stack_instances()
    elif function_name == 'update_stack_set':
        response = stack_set.update_stack_set()
    elif function_name == 'update_stack_instances':
        response = stack_set.update_stack_instances()
    elif function_name == 'delete_stack_set':
        response = stack_set.delete_stack_set()
    elif function_name == 'delete_stack_instances':
        response = stack_set.delete_stack_instances()
    elif function_name == 'reroute_to_delete_stack_instances':
        response = stack_set.reroute_to_delete_stack_instances()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response


def organizations(event, function_name):
    org = Organizations(event, logger)
    logger.info("Router FunctionName: {}".format(function_name))

    if function_name == 'list_roots':
        response = org.list_roots()
    elif function_name == 'create_organization':
        response = org.create_organization()
    elif function_name == 'check_organization_unit':
        response = org.check_organization_unit()
    elif function_name == 'create_organization_unit':
        response = org.create_organization_unit()
    elif function_name == 'delete_organization_unit':
        response = org.delete_organization_unit()
    elif function_name == 'list_accounts_for_parent':
        response = org.list_accounts_for_parent()
    elif function_name == 'list_parents':
        response = org.list_parents()
    elif function_name == 'list_accounts':
        response = org.list_accounts()
    elif function_name == 'describe_account_status':
        response = org.describe_account_status()
    elif function_name == 'create_account':
        response = org.create_account()
    elif function_name == 'move_account':
        response = org.move_account()
    elif function_name == 'lock_down_stack_sets_role':
        response = org.lock_down_stack_sets_role()
    elif function_name == 'describe_organization':
        response = org.describe_organization()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response


def service_catalog(event, function_name):
    sc = ServiceCatalog(event, logger)
    logger.info("Router FunctionName: {}".format(function_name))
    if function_name == 'list_portfolios':
        response = sc.list_portfolios()
    elif function_name == 'create_portfolio':
        response = sc.create_portfolio()
    elif function_name == 'update_portfolio':
        response = sc.update_portfolio()
    elif function_name == 'associate_principal_with_portfolio':
        response = sc.associate_principal_with_portfolio()
    elif function_name == 'create_product':
        response = sc.create_product()
    elif function_name == 'associate_product_with_portfolio':
        response = sc.associate_product_with_portfolio()
    elif function_name == 'create_constraint':
        response = sc.create_constraint()
    elif function_name == 'check_rules_exist':
        response = sc.check_rules_exist()
    elif function_name == 'create_template_constraint':
        response = sc.create_template_constraint()
    elif function_name == 'describe_constraint':
        response = sc.describe_constraint()
    elif function_name == 'describe_template_constraint':
        response = sc.describe_template_constraint()
    elif function_name == 'delete_constraint':
        response = sc.delete_constraint()
    elif function_name == 'update_product':
        response = sc.update_product()
    elif function_name == 'search_products_as_admin':
        response = sc.search_products_as_admin()
    elif function_name == 'list_portfolios_for_product':
        response = sc.list_portfolios_for_product()
    elif function_name == 'list_constraints_for_portfolio':
        response = sc.list_constraints_for_portfolio()
    elif function_name == 'list_template_constraints_for_portfolio':
        response = sc.list_template_constraints_for_portfolio()
    elif function_name == 'list_principals_for_portfolio':
        response = sc.list_principals_for_portfolio()
    elif function_name == 'disassociate_product_from_portfolio':
        response = sc.disassociate_product_from_portfolio()
    elif function_name == 'disassociate_principal_from_portfolio':
        response = sc.disassociate_principal_from_portfolio()
    elif function_name == 'delete_product':
        response = sc.delete_product()
    elif function_name == 'delete_portfolio':
        response = sc.delete_portfolio()
    elif function_name == 'list_provisioning_artifacts':
        response = sc.list_provisioning_artifacts()
    elif function_name == 'describe_provisioning_artifact':
        response = sc.describe_provisioning_artifact()
    elif function_name == 'create_provisioning_artifact':
        response = sc.create_provisioning_artifact()
    elif function_name == 'update_provisioning_artifact':
        response = sc.update_provisioning_artifact()
    elif function_name == 'delete_provisioning_artifact':
        response = sc.delete_provisioning_artifact()
    elif function_name == 'compare_product_templates':
        response = sc.compare_product_templates()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response


def service_control_policy(event, function_name):
    scp = ServiceControlPolicy(event, logger)
    logger.info("Router FunctionName: {}".format(function_name))
    if function_name == 'list_policies':
        response = scp.list_policies()
    elif function_name == 'list_policies_for_account':
        response = scp.list_policies_for_account()
    elif function_name == 'list_policies_for_ou':
        response = scp.list_policies_for_ou()
    elif function_name == 'create_policy':
        response = scp.create_policy()
    elif function_name == 'update_policy':
        response = scp.update_policy()
    elif function_name == 'delete_policy':
        response = scp.delete_policy()
    elif function_name == 'configure_count':
        policy_list = event.get('ResourceProperties').get('PolicyList', [])
        logger.info("List of policies: {}".format(policy_list))
        event.update({'Index': 0})
        event.update({'Step': 1})
        event.update({'Count': len(policy_list)})
        return event
    elif function_name == 'iterator':
        index = event.get('Index')
        step = event.get('Step')
        count = event.get('Count')
        policy_list = event.get('ResourceProperties').get('PolicyList', [])
        policy_to_apply = policy_list[index] if len(policy_list) > index else None

        if index < count:
            _continue = True
        else:
            _continue = False

        index = index + step

        event.update({'Index': index})
        event.update({'Step': step})
        event.update({'Continue': _continue})
        event.update({'PolicyName': policy_to_apply})
        return event
    elif function_name == 'attach_policy':
        response = scp.attach_policy()
    elif function_name == 'detach_policy':
        response = scp.detach_policy()
    elif function_name == 'detach_policy_from_all_accounts':
        response = scp.detach_policy_from_all_accounts()
    elif function_name == 'enable_policy_type':
        response = scp.enable_policy_type()
    elif function_name == 'configure_count_2':
        ou_list = event.get('ResourceProperties').get('OUList', [])
        logger.info("List of OUs: {}".format(ou_list))
        event.update({'Index': 0})
        event.update({'Step': 1})
        event.update({'Count': len(ou_list)})
        return event
    elif function_name == 'iterator2':
        index = event.get('Index')
        step = event.get('Step')
        count = event.get('Count')
        ou_list = event.get('ResourceProperties').get('OUList', [])
        ou_map = ou_list[index] if len(ou_list) > index else None

        if index < count:
            _continue = True
        else:
            _continue = False

        index = index + step

        event.update({'Index': index})
        event.update({'Step': step})
        event.update({'Continue': _continue})
        if ou_map:
            event.update({'OUName': ou_map[0]})
            event.update({'Operation': ou_map[1]})
        return event

    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response


def launch_avm(event, function_name):
    sc = ServiceCatalog(event, logger)
    logger.info("Router FunctionName: {}".format(function_name))
    if function_name == 'configure_count':
        params_list = event.get('ResourceProperties').get('ProvisioningParametersList', [])
        logger.info("List of Parameters: {}".format(params_list))
        event.update({'Index': 0})
        event.update({'Step': 1})
        event.update({'Count': len(params_list)})
        return event
    elif function_name == 'iterator':
        logger.info("Router FunctionName: {}".format(function_name))
        index = event.get('Index')
        step = event.get('Step')
        count = event.get('Count')
        params_list = event.get('ResourceProperties').get('ProvisioningParametersList', [])
        prod_params = params_list[index] if len(params_list) > index else None

        if index < count:
            _continue = True
        else:
            _continue = False

        index = index + step

        event.update({'Index': index})
        event.update({'Step': step})
        event.update({'Continue': _continue})
        event.update({'NextPageToken': '0'})
        event.update({'ProdParams': prod_params})
        return event
    elif function_name == 'search_provisioned_products':
        response = sc.search_provisioned_products()
    elif function_name == 'provision_product':
        response = sc.provision_product()
    elif function_name == 'describe_record':
        response = sc.describe_record()
    elif function_name == 'update_provisioned_product':
        response = sc.update_provisioned_product()
    elif function_name == 'terminate_provisioned_product':
        response = sc.terminate_provisioned_product()
    elif function_name == 'lookup_product':
        response = sc.lookup_product()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response


def check_avm_exists(event, function_name):
    sc = ServiceCatalog(event, logger)
    logger.info("Router FunctionName: {}".format(function_name))
    if function_name == 'lookup_product':
        response = sc.lookup_product()
    elif function_name == 'search_provisioned_products':
        # Move ProdParams from inside ResourceProperties to outside
        event.update({'ProdParams':event.get('ResourceProperties').get('ProdParams')})
        response = sc.search_provisioned_products()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response


def ad_connector(event, function_name):
    logger.info("Router FunctionName: {}".format(function_name))

    ad = ADConnector(event, logger)
    if function_name == 'connect_directory':
        response = ad.create_ad_connector()
    elif function_name == 'delete_directory':
        response = ad.delete_directory()
    elif function_name == 'check_directory_status':
        response = ad.check_ad_connector_status()
    elif function_name == 'describe_directory':
        response = ad.describe_directory()
    else:
        message = "Function name does not match any function in the handler file."
        logger.info(message)
        return {"Message": message}

    logger.info(response)
    return response


def general_functions(event, function_name):
    gf = GeneralFunctions(event, logger)
    logger.info("Router FunctionName: {}".format(function_name))

    if function_name == 'ssm_put_parameters':
        response = gf.ssm_put_parameters()
    elif function_name == 'export_cfn_output':
        response = gf.export_cfn_output()
    elif function_name == 'send_success_to_cfn':
        response = gf.send_success_to_cfn()
    elif function_name == 'send_failure_to_cfn':
        response = gf.send_failure_to_cfn()
    elif function_name == 'account_initialization_check':
        response = gf.account_initialization_check()
    elif function_name == 'send_execution_data':
        response = gf.send_execution_data()
    elif function_name == 'random_wait':
        response = gf.random_wait()
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
        # Execute custom resource handlers
        class_name = event.get('params', {}).get('ClassName')
        function_name = event.get('params', {}).get('FunctionName')

        if class_name is not None:
            if class_name == "CloudFormation":
                return cloudformation(event, function_name)
            elif class_name == 'Organizations':
                return organizations(event, function_name)
            elif class_name == 'ServiceCatalog':
                return service_catalog(event, function_name)
            elif class_name == 'GeneralFunctions':
                return general_functions(event, function_name)
            elif class_name == 'SCP':
                return service_control_policy(event, function_name)
            elif class_name == 'LaunchAVM':
                return launch_avm(event, function_name)
            elif class_name == 'CheckAVMExists':
                return check_avm_exists(event, function_name)
            elif class_name == 'ADConnector':
                return ad_connector(event, function_name)
            else:
                message = "Class name does not match any class in the handler file."
                logger.info(message)
                return {"Message": message}
        else:
            message = "Class name not found in input."
            logger.info(message)
            return {"Message": message}
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise
