from lib.logger import Logger
from lib.pipeline import CodePipeline
from lib.state_machine import StateMachine
from lib.ssm import SSM
from lib.s3 import S3
from lib.ec2 import EC2
from lib.metrics import Metrics
from os import environ
from lib.organizations import Organizations
from lib.manifest import Manifest
from lib.params import ParamsHandler
from lib.helper import sanitize, transform_params, reverse_transform_params, convert_s3_url_to_http_url, convert_http_url_to_s3_url, trim_length, download_remote_file
from lib.cloudformation import StackSet
import inspect
import os
import json
import time
import zipfile
import tempfile
import jinja2
import uuid
import shutil
import errno
import filecmp

log_level = os.environ['log_level']
wait_time = os.environ['wait_time']
logger = Logger(loglevel=log_level)
pipeline = CodePipeline(logger)
TEMPLATE_KEY_PREFIX = '_aws_landing_zone_templates_staging'
MANIFEST_FILE_NAME = 'manifest.yaml'


class StateMachineTriggerLambda(object):
    def __init__(self, logger, sm_arns_map, staging_bucket, manifest_file_path, pipeline_stage, token, execution_mode, primary_account_id):
        self.state_machine = StateMachine(logger)
        self.ssm = SSM(logger)
        self.s3 = S3(logger)
        self.send = Metrics(logger)
        self.param_handler = ParamsHandler(logger)
        self.logger = logger
        self.sm_arns_map = sm_arns_map
        self.manifest = None
        self.nested_ou_delimiter = ""
        self.staging_bucket = staging_bucket
        self.manifest_file_path = manifest_file_path
        self.token = token
        self.pipeline_stage = pipeline_stage
        self.manifest_folder = manifest_file_path[:-len(MANIFEST_FILE_NAME)]
        if execution_mode.lower() == 'sequential':
            self.isSequential = True
        else:
            self.isSequential = False
        self.index = 100
        self.primary_account_id = primary_account_id

    def _save_sm_exec_arn(self, list_sm_exec_arns):
        if list_sm_exec_arns is not None and type(list_sm_exec_arns) is list:
            self.logger.debug("Saving the token:{} with list of sm_exec_arns:{}".format(self.token, list_sm_exec_arns))
            if len(list_sm_exec_arns) > 0:
                sm_exec_arns = ",".join(list_sm_exec_arns) # Create comma seperated string from list e.g. 'a','b','c'
                self.ssm.put_parameter(self.token, sm_exec_arns) # Store the list of SM execution ARNs in SSM
            else:
                self.ssm.put_parameter(self.token, 'PASS')
        else:
            raise Exception("Expecting a list of state machine execution ARNs to store in SSM for token:{}, but found nothing to store.".format(self.token))

    def _stage_template(self, relative_template_path):
        if relative_template_path.lower().startswith('s3'):
            # Convert the S3 URL s3://bucket-name/object
            # to HTTP URL https://s3.amazonaws.com/bucket-name/object
            s3_url = convert_s3_url_to_http_url(relative_template_path)
        else:
            local_file = os.path.join(self.manifest_folder, relative_template_path)
            remote_file = "{}/{}_{}".format(TEMPLATE_KEY_PREFIX, self.token, relative_template_path[relative_template_path.rfind('/')+1:])
            logger.info("Uploading the template file: {} to S3 bucket: {} and key: {}".format(local_file, self.staging_bucket, remote_file))
            self.s3.upload_file(self.staging_bucket, local_file, remote_file)
            s3_url = "{}{}{}{}".format('https://s3.amazonaws.com/', self.staging_bucket, '/', remote_file)
        return s3_url

    def _load_params(self, relative_parameter_path, account = None, region = None):
        if relative_parameter_path.lower().startswith('s3'):
            parameter_file = download_remote_file(self.logger, relative_parameter_path)
        else:
            parameter_file = os.path.join(self.manifest_folder, relative_parameter_path)

        logger.info("Parsing the parameter file: {}".format(parameter_file))

        with open(parameter_file, 'r') as content_file:
            parameter_file_content = content_file.read()

        params = json.loads(parameter_file_content)
        if account is not None:
            #Deploying Core resource Stack Set
            # The last parameter is set to False, because we do not want to replace the SSM parameter values yet.
            sm_params = self.param_handler.update_params(params, account, region, False)
        else:
            # Deploying Baseline resource Stack Set
            sm_params = self.param_handler.update_params(params)

        logger.info("Input Parameters for State Machine: {}".format(sm_params))
        return sm_params

    def _load_template_rules(self, relative_rules_path):
        rules_file = os.path.join(self.manifest_folder, relative_rules_path)
        logger.info("Parsing the template rules file: {}".format(rules_file))

        with open(rules_file, 'r') as content_file:
            rules_file_content = content_file.read()

        rules = json.loads(rules_file_content)

        logger.info("Template Constraint Rules for State Machine: {}".format(rules))

        return rules

    def _populate_ssm_params(self, sm_input):
        # The scenario is if you have one core resource that exports output from CFN stack to SSM parameter
        # and then the next core resource reads the SSM parameter as input, then it has to wait for the first core resource to
        # finish; read the SSM parameters and use its value as input for second core resource's input for SM
        # Get the parameters for CFN template from sm_input
        logger.debug("Populating SSM parameter values for SM input: {}".format(sm_input))
        params = sm_input.get('ResourceProperties').get('Parameters', {})
        # First transform it from {name: value} to [{'ParameterKey': name}, {'ParameterValue': value}]
        # then replace the SSM parameter names with its values
        sm_params = self.param_handler.update_params(transform_params(params))
        # Put it back into the sm_input
        sm_input.get('ResourceProperties').update({'Parameters': sm_params})
        logger.debug("Done populating SSM parameter values for SM input: {}".format(sm_input))
        return sm_input

    def _create_ssm_input_map(self, ssm_parameters):
        ssm_input_map = {}

        for ssm_parameter in ssm_parameters:
            key = ssm_parameter.name
            value = ssm_parameter.value
            ssm_value = self.param_handler.update_params(transform_params({key:value}))
            ssm_input_map.update(ssm_value)

        return ssm_input_map

    def _create_state_machine_input_map(self, input_params, request_type='Create'):
        request = {}
        request.update({'RequestType':request_type})
        request.update({'ResourceProperties':input_params})

        return request

    def _create_account_state_machine_input_map(self, ou_name, account_name='', account_email='', ssm_map=None):
        input_params = {}
        input_params.update({'OUName': ou_name})
        input_params.update({'AccountName': account_name})
        input_params.update({'AccountEmail': account_email})
        input_params.update({'OUNameDelimiter': self.nested_ou_delimiter})
        if ssm_map is not None:
            input_params.update({'SSMParameters':ssm_map})
        return self._create_state_machine_input_map(input_params)

    def _create_stack_set_state_machine_input_map(self, stack_set_name, template_url, parameters, account_list=[], regions_list=[], ssm_map=None, capabilities='CAPABILITY_NAMED_IAM'):
        input_params = {}
        input_params.update({'StackSetName': sanitize(stack_set_name)})
        input_params.update({'TemplateURL': template_url})
        input_params.update({'Parameters': parameters})
        input_params.update({'Capabilities': capabilities})

        if len(account_list) > 0:
            input_params.update({'AccountList': account_list})
            if len(regions_list) > 0:
                input_params.update({'RegionList': regions_list})
            else:
                input_params.update({'RegionList': [self.manifest.region]})
        else:
            input_params.update({'AccountList': ''})
            input_params.update({'RegionList': ''})

        if ssm_map is not None:
            input_params.update({'SSMParameters': ssm_map})

        return self._create_state_machine_input_map(input_params)

    def _create_service_control_policy_state_machine_input_map(self, policy_name, policy_full_path, policy_desc='', ou_list=[]):
        input_params = {}
        policy_doc = {}
        policy_doc.update({'Name': sanitize(policy_name)})
        policy_doc.update({'Description': policy_desc})
        policy_doc.update({'PolicyURL': policy_full_path})
        input_params.update({'PolicyDocument': policy_doc})
        input_params.update({'AccountId': ''})
        input_params.update({'PolicyList': []})
        input_params.update({'Operation': ''})
        input_params.update({'OUList': ou_list})
        input_params.update({'OUNameDelimiter': self.nested_ou_delimiter})
        return self._create_state_machine_input_map(input_params)

    def _create_service_catalog_state_machine_input_map(self, portfolio, product):
        input_params = {}

        sc_portfolio = {}
        sc_portfolio.update({'PortfolioName': sanitize(portfolio.name, True)})
        sc_portfolio.update({'PortfolioDescription': sanitize(portfolio.description, True)})
        sc_portfolio.update({'PortfolioProvider': sanitize(portfolio.owner, True)})
        ssm_value = self.param_handler.update_params(transform_params({'principal_role': portfolio.principal_role}))
        sc_portfolio.update({'PrincipalArn': ssm_value.get('principal_role')})

        sc_product = {}
        sc_product.update({'ProductName': sanitize(product.name, True)})
        sc_product.update({'ProductDescription': product.description})
        sc_product.update({'ProductOwner': sanitize(portfolio.owner, True)})
        if product.hide_old_versions is True:
            sc_product.update({'HideOldVersions': 'Yes'})
        else:
            sc_product.update({'HideOldVersions': 'No'})
        ssm_value = self.param_handler.update_params(transform_params({'launch_constraint_role': product.launch_constraint_role}))
        sc_product.update({'RoleArn':ssm_value.get('launch_constraint_role')})

        ec2 = EC2(self.logger, environ.get('AWS_REGION'))
        region_list = []
        for region in ec2.describe_regions():
            region_list.append(region.get('RegionName'))

        if os.path.isfile(os.path.join(self.manifest_folder, product.skeleton_file)):
            lambda_arn_param = get_env_var('lambda_arn_param_name')
            lambda_arn = self.ssm.get_parameter(lambda_arn_param)
            portfolio_index = self.manifest.portfolios.index(portfolio)
            product_index = self.manifest.portfolios[portfolio_index].products.index(product)
            product_name = self.manifest.portfolios[portfolio_index].products[product_index].name
            logger.info("Generating the product template for {} from {}".format(product_name, os.path.join(self.manifest_folder,product.skeleton_file)))
            j2loader = jinja2.FileSystemLoader(self.manifest_folder)
            j2env = jinja2.Environment(loader=j2loader)
            j2template = j2env.get_template(product.skeleton_file)
            template_url = None
            if product.product_type.lower() == 'baseline':
                # j2result = j2template.render(manifest=self.manifest, portfolio_index=portfolio_index,
                #                              product_index=product_index, lambda_arn=lambda_arn, uuid=uuid.uuid4(),
                #                              regions=region_list)
                template_url = self._stage_template(product.skeleton_file+".template")
            elif product.product_type.lower() == 'optional':
                if len(product.template_file) > 0:
                    template_url = self._stage_template(product.template_file)
                    j2result = j2template.render(manifest=self.manifest, portfolio_index=portfolio_index,
                                                 product_index=product_index, lambda_arn=lambda_arn, uuid=uuid.uuid4(),
                                                 template_url=template_url)
                    generated_avm_template = os.path.join(self.manifest_folder,
                                                          product.skeleton_file + ".generated.template")
                    logger.info("Writing the generated product template to {}".format(generated_avm_template))
                    with open(generated_avm_template, "w") as fh:
                        fh.write(j2result)
                    template_url = self._stage_template(generated_avm_template)
                else:
                    raise Exception("Missing template_file location for portfolio:{} and product:{} in Manifest file".format(portfolio.name,
                                                                                                                             product.name))

        else:
            raise Exception("Missing skeleton_file for portfolio:{} and product:{} in Manifest file".format(portfolio.name,
                                                                                                                     product.name))

        artifact_params = {}
        artifact_params.update({'Info':{'LoadTemplateFromURL':template_url}})
        artifact_params.update({'Type':'CLOUD_FORMATION_TEMPLATE'})
        artifact_params.update({'Description':product.description})
        sc_product.update({'ProvisioningArtifactParameters':artifact_params})

        try:
            if product.rules_file:
                rules = self._load_template_rules(product.rules_file)
                sc_product.update({'Rules': rules})
        except Exception as e:
            logger.error(e)

        input_params.update({'SCPortfolio':sc_portfolio})
        input_params.update({'SCProduct':sc_product})

        return self._create_state_machine_input_map(input_params)

    def _compare_template_and_params(self, sm_input):
        stack_name = sm_input.get('ResourceProperties').get('StackSetName', '')

        if stack_name:
            stack_set = StackSet(self.logger)
            describe_response = stack_set.describe_stack_set(stack_name)
            if describe_response is not None:
                self.logger.info("Found existing stack set.")

                self.logger.info("Checking the status of last stack set operation on {}".format(stack_name))
                response = stack_set.list_stack_set_operations(StackSetName=stack_name,
                                                               MaxResults=1)

                if response:
                    if response.get('Summaries'):
                        for instance in response.get('Summaries'):
                            self.logger.info("Status of last stack set operation : {}".format(instance.get('Status')))
                            if instance.get('Status') != 'SUCCEEDED':
                                self.logger.info("The last stack operation did not succeed. Triggering Update StackSet for {}".format(stack_name))
                                return False

                self.logger.info("Comparing the template of the StackSet: {} with local copy of template".format(stack_name))

                template_http_url = sm_input.get('ResourceProperties').get('TemplateURL', '')
                if template_http_url:
                    template_s3_url = convert_http_url_to_s3_url(template_http_url)
                    local_template_file = download_remote_file(self.logger, template_s3_url)
                else:
                    self.logger.error("TemplateURL in state machine input is empty. Check sm_input:{}".format(sm_input))
                    return False

                cfn_template_file = tempfile.mkstemp()[1]
                with open(cfn_template_file, "w") as f:
                    f.write(describe_response.get('StackSet').get('TemplateBody'))

                template_compare = filecmp.cmp(local_template_file, cfn_template_file, False)
                self.logger.info("Comparing the parameters of the StackSet: {} with local copy of JSON parameters file".format(stack_name))

                params_compare = True
                params = sm_input.get('ResourceProperties').get('Parameters', {})
                if template_compare:
                    cfn_params = reverse_transform_params(describe_response.get('StackSet').get('Parameters'))
                    for key, value in params.items():
                        if cfn_params.get(key, '') == value:
                            pass
                        else:
                            params_compare = False
                            break

                self.logger.info("template_compare={}".format(template_compare))
                self.logger.info("params_compare={}".format(params_compare))
                if template_compare and params_compare:
                    account_list = sm_input.get('ResourceProperties').get("AccountList", [])
                    if account_list:
                        self.logger.info("Comparing the Stack Instances Account & Regions for StackSet: {}".format(stack_name))
                        expected_region_list = set(sm_input.get('ResourceProperties').get("RegionList", []))
                        actual_region_list = set()
                        self.logger.info("Listing the Stack Instances for StackSet: {} and Account: {} ".format(stack_name, account_list[0]))
                        response = stack_set.list_stack_instances(StackSetName=stack_name,
                                                                  StackInstanceAccount=account_list[0],
                                                                  MaxResults=20)
                        self.logger.info(response)

                        if response is not None:
                            for instance in response.get('Summaries'):
                                if instance.get('Status').upper() == 'CURRENT':
                                    actual_region_list.add(instance.get('Region'))
                                else:
                                    self.logger.info("Found at least one of the Stack Instances in {} state. Triggering Update StackSet for {}".format(
                                        instance.get('Status'), stack_name))
                                    return False
                            next_token = response.get('NextToken')
                            while next_token is not None:
                                self.logger.info('Next token found.')
                                response = stack_set.list_stack_instances(StackSetName=stack_name,
                                                                          StackInstanceAccount=account_list[0],
                                                                          MaxResults=20,
                                                                          NextToken=next_token)
                                self.logger.info(response)

                                if response is not None:
                                    for instance in response.get('Summaries'):
                                        if instance.get('Status').upper() == 'CURRENT':
                                            actual_region_list.add(instance.get('Region'))
                                        else:
                                            self.logger.info("Found at least one of the Stack Instances in {} state. Triggering Update StackSet for {}".format(
                                                    instance.get('Status'), stack_name))
                                            return False
                                    next_token = response.get('NextToken')

                        if expected_region_list.issubset(actual_region_list):
                            self.logger.info("Found expected regions : {} in deployed stack instances : {}, so skipping Update StackSet for {}".format(
                                expected_region_list, actual_region_list, stack_name))
                            return True
                    else:
                        self.logger.info("Found no changes in template & parameters, so skipping Update StackSet for {}".format(stack_name))
                        return True
        return False

    def _run_or_queue_state_machine(self, sm_input, sm_arn, list_sm_exec_arns, sm_name):
        logger.info("State machine Input: {}".format(sm_input))
        exec_name = "%s-%s-%s" % (sm_input.get('RequestType'), trim_length(sm_name.replace(" ", ""), 50),
                                  time.strftime("%Y-%m-%dT%H-%M-%S"))
        # If Sequential, kick off the first SM, and save the state machine input JSON
        # for the rest in SSM parameter store under /job_id/0 tree
        if self.isSequential:
            if self.index == 100:
                sm_input = self._populate_ssm_params(sm_input)
                if self._compare_template_and_params(sm_input):
                    return
                else:
                    sm_exec_arn = self.state_machine.trigger_state_machine(sm_arn, sm_input, exec_name)
                list_sm_exec_arns.append(sm_exec_arn)
            else:
                param_name = "/%s/%s" % (self.token, self.index)
                self.ssm.put_parameter(param_name, json.dumps(sm_input))
        # Else if Parallel, execute all SM at regular interval of wait_time
        else:
            sm_input = self._populate_ssm_params(sm_input)
            if self._compare_template_and_params(sm_input):
                return
            else:
                sm_exec_arn = self.state_machine.trigger_state_machine(sm_arn, sm_input, exec_name)
            time.sleep(int(wait_time))  # Sleeping for sometime
            list_sm_exec_arns.append(sm_exec_arn)
        self.index = self.index + 1

    def _deploy_resource(self, resource, sm_arn, list_sm_exec_arns, account_id = None):
        template_full_path = self._stage_template(resource.template_file)
        params = {}
        if resource.parameter_file:
            if len(resource.regions) > 0:
                params = self._load_params(resource.parameter_file, account_id, resource.regions[0])
            else:
                params = self._load_params(resource.parameter_file, account_id, self.manifest.region)

        ssm_map = self._create_ssm_input_map(resource.ssm_parameters)

        if account_id is not None:
            #Deploying Core resource Stack Set
            stack_name = "AWS-Landing-Zone-{}".format(resource.name)
            sm_input = self._create_stack_set_state_machine_input_map(stack_name, template_full_path, params, [str(account_id)], resource.regions, ssm_map)
        else:
            #Deploying Baseline resource Stack Set
            stack_name = "AWS-Landing-Zone-Baseline-{}".format(resource.name)
            sm_input = self._create_stack_set_state_machine_input_map(stack_name, template_full_path, params, [], [], ssm_map)

        self._run_or_queue_state_machine(sm_input, sm_arn, list_sm_exec_arns, stack_name)

    def start_core_account_sm(self, sm_arn_account):
        try:
            logger.info("Setting the lock_down_stack_sets_role={}".format(self.manifest.lock_down_stack_sets_role))

            if self.manifest.lock_down_stack_sets_role is True:
                self.ssm.put_parameter('lock_down_stack_sets_role_flag', 'yes')
            else:
                self.ssm.put_parameter('lock_down_stack_sets_role_flag', 'no')

            # Send metric - pipeline run count
            data = {"PipelineRunCount": "1"}
            self.send.metrics(data)

            logger.info("Processing Core Accounts from {} file".format(self.manifest_file_path))
            list_sm_exec_arns = []
            for ou in self.manifest.organizational_units:
                ou_name = ou.name
                logger.info("Generating the state machine input json for OU: {}".format(ou_name))

                if len(ou.core_accounts) == 0:
                    # Empty OU with no Accounts
                    sm_input = self._create_account_state_machine_input_map(ou_name)
                    self._run_or_queue_state_machine(sm_input, sm_arn_account, list_sm_exec_arns, ou_name)

                for account in ou.core_accounts:
                    account_name = account.name

                    if account_name.lower() == 'primary':
                        org = Organizations(self.logger)
                        response = org.describe_account(self.primary_account_id)
                        account_email = response.get('Account').get('Email', '')
                    else:
                        account_email = account.email

                    if not account_email:
                        raise Exception("Failed to retrieve the email address for the Account: {}".format(account_name))

                    ssm_map = self._create_ssm_input_map(account.ssm_parameters)

                    sm_input = self._create_account_state_machine_input_map(ou_name, account_name, account_email, ssm_map)
                    self._run_or_queue_state_machine(sm_input, sm_arn_account, list_sm_exec_arns, account_name)
            self._save_sm_exec_arn(list_sm_exec_arns)
            return
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def start_core_resource_sm(self, sm_arn_stack_set):
        try:
            logger.info("Parsing Core Resources from {} file".format(self.manifest_file_path))
            list_sm_exec_arns = []
            count = 0
            for ou in self.manifest.organizational_units:
                for account in ou.core_accounts:
                    account_name = account.name
                    account_id = ''
                    for ssm_parameter in account.ssm_parameters:
                        if ssm_parameter.value == '$[AccountId]':
                            account_id = self.ssm.get_parameter(ssm_parameter.name)

                    if account_id == '' :
                        raise Exception("Missing required SSM parameter: {} to retrive the account Id of Account: {} defined in Manifest".format(ssm_parameter.name, account_name))

                    for resource in account.core_resources:
                        # Count number of stacksets
                        count += 1
                        if resource.deploy_method.lower() == 'stack_set':
                            self._deploy_resource(resource, sm_arn_stack_set, list_sm_exec_arns, account_id)
                        else:
                            raise Exception("Unsupported deploy_method: {} found for resource {} and Account: {} in Manifest".format(resource.deploy_method, resource.name, account_name))
            data = {"CoreAccountStackSetCount": str(count)}
            self.send.metrics(data)
            self._save_sm_exec_arn(list_sm_exec_arns)
            return
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def start_service_control_policy_sm(self, sm_arn_scp):
        try:
            logger.info("Processing SCPs from {} file".format(self.manifest_file_path))
            list_sm_exec_arns = []
            count = 0


            # Generate the list of ALL OUs
            all_ous = set()
            for ou in self.manifest.organizational_units:
                all_ous.add(ou.name)

            for policy in self.manifest.organization_policies:
                # Generate the list of OUs to attach this SCP to
                ou_list = []
                attach_ou_list = set(policy.apply_to_accounts_in_ou)

                for ou in attach_ou_list:
                    ou_list.append((ou, 'Attach'))

                # Generate the list of OUs to detach this SCP from
                detach_ou_list = all_ous - attach_ou_list

                for ou in detach_ou_list:
                    ou_list.append((ou, 'Detach'))

                policy_full_path = self._stage_template(policy.policy_file)
                sm_input = self._create_service_control_policy_state_machine_input_map(policy.name, policy_full_path,
                                                                                       policy.description, ou_list)
                self._run_or_queue_state_machine(sm_input, sm_arn_scp, list_sm_exec_arns, policy.name)
                # Count number of stacksets
                count += 1
            self._save_sm_exec_arn(list_sm_exec_arns)
            data = {"SCPPolicyCount": str(count)}
            self.send.metrics(data)
            return
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def start_service_catalog_sm(self, sm_arn_sc):
        try:
            logger.info("Processing Service catalogs section from {} file".format(self.manifest_file_path))
            list_sm_exec_arns = []
            for portfolio in self.manifest.portfolios:
                for product in portfolio.products:
                    sm_input = self._create_service_catalog_state_machine_input_map(portfolio, product)
                    self._run_or_queue_state_machine(sm_input, sm_arn_sc, list_sm_exec_arns, product.name)
            self._save_sm_exec_arn(list_sm_exec_arns)
            return
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def start_baseline_resources_sm(self, sm_arn_stack_set):
        try:
            logger.info("Parsing Basline Resources from {} file".format(self.manifest_file_path))
            list_sm_exec_arns = []
            count = 0
            for resource in self.manifest.baseline_resources:
                if resource.deploy_method.lower() == 'stack_set':
                    self._deploy_resource(resource, sm_arn_stack_set, list_sm_exec_arns)
                    # Count number of stacksets
                    count += 1
                else:
                    raise Exception("Unsupported deploy_method: {} found for resource {} in Manifest".format(resource.deploy_method, resource.name))
            data = {"BaselineStackSetCount": str(count)}
            self.send.metrics(data)
            self._save_sm_exec_arn(list_sm_exec_arns)
            return
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def trigger_state_machines(self):
        try:
            self.manifest = Manifest(self.manifest_file_path)
            if self.manifest.nested_ou_delimiter != "":
                self.nested_ou_delimiter = self.manifest.nested_ou_delimiter

            if self.pipeline_stage == 'core_accounts':
                self.start_core_account_sm(self.sm_arns_map.get('account'))
            elif self.pipeline_stage == 'core_resources':
                self.start_core_resource_sm(self.sm_arns_map.get('stack_set'))
            elif self.pipeline_stage == 'service_control_policy':
                self.start_service_control_policy_sm(self.sm_arns_map.get('service_control_policy'))
            elif self.pipeline_stage == 'service_catalog':
                self.start_service_catalog_sm(self.sm_arns_map.get('service_catalog'))
            elif self.pipeline_stage == 'baseline_resources':
                self.start_baseline_resources_sm(self.sm_arns_map.get('stack_set'))

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def get_state_machines_execution_status(self):
        try:
            sm_exec_arns = self.ssm.get_parameter(self.token)

            if sm_exec_arns == 'PASS':
                self.ssm.delete_parameter(self.token)
                return 'SUCCEEDED', ''
            else:
                list_sm_exec_arns = sm_exec_arns.split(",") # Create a list from comma seperated string e.g. ['a','b','c']

                for sm_exec_arn in list_sm_exec_arns:
                    status = self.state_machine.check_state_machine_status(sm_exec_arn)
                    if status == 'RUNNING':
                        return 'RUNNING', ''
                    elif status == 'SUCCEEDED':
                        continue
                    else:
                        self.ssm.delete_parameter(self.token)
                        self.ssm.delete_parameters_by_path(self.token)
                        err_msg = "State Machine Execution Failed, please check the Step function console for State Machine Execution ARN: {}".format(sm_exec_arn)
                        return 'FAILED', err_msg

                if self.isSequential:
                    # get_parameters_by_path(job_id) => {"Name": "/job_id/101","Value": state_machine_input_json},{"Name": "/job_id/102","Value": state_machine_input_json},...
                    _sm_list = self.ssm.get_parameters_by_path(self.token)
                    if _sm_list:
                        sm_list = sorted(_sm_list, key=lambda i: i['Name'])

                        for next_sm in sm_list:
                            # Get the state machine input json for the next state machine invoke in sequence
                            sm_input = json.loads(next_sm.get('Value'))
                            if self.pipeline_stage == 'core_accounts':
                                sm_arn = self.sm_arns_map.get('account')
                                sm_name = sm_input.get('ResourceProperties').get('OUName') + "-" + sm_input.get('ResourceProperties').get('AccountName')
                            elif self.pipeline_stage == 'core_resources':
                                sm_arn = self.sm_arns_map.get('stack_set')
                                sm_name = sm_input.get('ResourceProperties').get('StackSetName')
                                sm_input = self._populate_ssm_params(sm_input)
                            elif self.pipeline_stage == 'service_control_policy':
                                sm_arn = self.sm_arns_map.get('service_control_policy')
                                sm_name = sm_input.get('ResourceProperties').get('PolicyDocument').get('Name')
                            elif self.pipeline_stage == 'service_catalog':
                                sm_arn = self.sm_arns_map.get('service_catalog')
                                sm_name = sm_input.get('ResourceProperties').get('SCProduct').get('ProductName')
                            elif self.pipeline_stage == 'baseline_resources':
                                sm_arn = self.sm_arns_map.get('stack_set')
                                sm_name = sm_input.get('ResourceProperties').get('StackSetName')
                                sm_input = self._populate_ssm_params(sm_input)

                            if self._compare_template_and_params(sm_input):
                                continue
                            else:
                                exec_name = "%s-%s-%s" % (sm_input.get('RequestType'), trim_length(sm_name.replace(" ", ""), 50),
                                                          time.strftime("%Y-%m-%dT%H-%M-%S"))
                                sm_exec_arn = self.state_machine.trigger_state_machine(sm_arn, sm_input, exec_name)
                                self._save_sm_exec_arn([sm_exec_arn])
                                # Delete the SSM parameter "/job_id/101"
                                self.ssm.delete_parameter(next_sm.get('Name'))
                                return 'RUNNING', ''

                self.ssm.delete_parameter(self.token)
                return 'SUCCEEDED', ''

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise


def get_env_var(env_var):
    if env_var in os.environ.keys():
        return os.environ[env_var]
    else:
        raise Exception("Missing required environment variable: {} in StateMachineTriggerLambda function".format(env_var))


# Load all the State Machine ARNs from the envrionment variables.
# All variables starting with 'sm_arn_' hold ARN of the state machine
def get_state_machine_arns():
    sm_arns = {}
    ENV_SM_PREFIX = 'sm_arn_'
    # Constructing a map of state machine name and ARNs e.g. {'account':'ARN1', 'stack_set':'ARN2'}
    for env_var in os.environ.keys():
        if env_var.startswith(ENV_SM_PREFIX):
            sm_arns[env_var[len(ENV_SM_PREFIX):]] = os.environ[env_var]
    return sm_arns


def get_manifest_file_path(artifact_name, temp_dir):
    try:
        logger.info("Downloading the artifact from Pipeline S3 Artifact bucket: {}".format(artifact_name))
        artifact_bucket_creds =  pipeline.get_credentials()
        artifact_bucket, artifact_key = pipeline.get_artifact_location(artifact_name)

        temp_zip_file = os.path.join(temp_dir,"lz-config.zip")
        s3 = S3(logger, credentials=artifact_bucket_creds)
        s3.download_file(artifact_bucket, artifact_key, temp_zip_file)

        with zipfile.ZipFile(temp_zip_file, 'r') as zip:
            zip.extractall(temp_dir)

        mf_file_path = os.path.join(temp_dir, MANIFEST_FILE_NAME)

        if os.path.isfile(mf_file_path):
            return mf_file_path
        else:
            mf_file_path = os.path.join(temp_dir, "aws-landing-zone-configuration", MANIFEST_FILE_NAME)
            if os.path.isfile(mf_file_path):
                return mf_file_path
            else:
                raise Exception("manifest.yaml does not exist at the root level of aws-landing-zone-configuration.zip or inside aws-landing-zone-configuration folder, please check the ZIP file.")
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise


def lambda_handler(event, context):
    pipeline.parse_event(event)
    temp_dir = tempfile.mkdtemp()

    try:
        logger.info("State Machine Trigger Lambda_handler Event: {}".format(event))

        # Get Account ID from lambda function arn in the context
        account_id = context.invoked_function_arn.split(":")[4]

        pipeline_user_params = pipeline.get_user_params()
        logger.info("Pipeline User Parameters: {}".format(pipeline_user_params))
        artifact_name = pipeline_user_params.get('artifact')
        mf_file_path = get_manifest_file_path(artifact_name, temp_dir)
        exec_mode = pipeline_user_params.get('exec_mode', 'sequential')

        sm_trigger_lambda = StateMachineTriggerLambda(logger, get_state_machine_arns(), get_env_var('staging_bucket'),
            mf_file_path, pipeline_user_params.get('pipeline_stage'), pipeline.continuation_token, exec_mode, account_id)

        if pipeline.is_continuing_pipeline_task():
            status, message = sm_trigger_lambda.get_state_machines_execution_status()

            if status == 'RUNNING':
                pipeline.continue_job_later()
            elif status == 'SUCCEEDED':
                pipeline.put_job_success()
            else:
                pipeline.put_job_failure(message)
        else:
            sm_trigger_lambda.trigger_state_machines()
            pipeline.continue_job_later()

    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        pipeline.put_job_failure(str(message))
    finally:
        try:
            shutil.rmtree(temp_dir)  # delete directory
        except OSError as exc:
            if exc.errno != errno.ENOENT:  # ENOENT - no such file or directory
                raise
