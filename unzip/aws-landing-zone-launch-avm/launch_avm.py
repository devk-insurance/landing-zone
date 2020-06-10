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
import sys
import time
import json
import os
from uuid import uuid4

from lib.logger import Logger
from lib.state_machine import StateMachine
from lib.ssm import SSM
from lib.string_manipulation import sanitize
from lib.organizations import Organizations
from lib.service_catalog import ServiceCatalog as SC
from state_machine_handler import Organizations as Org
from lib.cloudformation import Stacks
from lib.manifest import Manifest
from manifest.cfn_params_handler import CFNParamsHandler
import inspect

MANIFEST_FILE_NAME = 'manifest.yaml'
stacks_cache = {}

#----------------------------------------------------------------------
# date_handler
#----------------------------------------------------------------------
def date_handler(obj):
    """date_handler: handles dates embedded in the json returned from the api"""
    if not hasattr(obj, 'isoformat'):
        raise TypeError

    return obj.isoformat()

#----------------------------------------------------------------------
def get_stack_data(stack_name, logger):
    """
    Caching mechanism for describe_stacks to reduce API calls.

    Returns the CloudFormation stack data: status and parameters for a given stack
    """
    global stacks_cache
    def get_indexed_stacks():
        """
        Load a dict of all stack info indexed by stackname into stacks_cache
        """
        stack_data = {}
        try:
            cfn = Stacks(logger)

            response = cfn.describe_stacks_all()
            token = 'init'

            while token:

                all_stacks = response.get('Stacks', None)
                token = response.get('NextToken', None)

                if not all_stacks:
                    logger.warning('No stacks found')
                    return

                # index the results by StackName into self.stacks
                for stack in all_stacks:
                    logger.debug(stack)
                    stackname = stack.get('StackName')

                    # This should never happen: stack name duplicated
                    if stackname in stacks_cache:
                        logger.warning('Duplicate stack name found: {}'.format(stackname))
                        continue

                    # add to the stacks dict - saves everything
                    index_stack = {
                        stack.get('StackName'): {
                            'StackStatus': stack.get('StackStatus', ''),
                            'Parameters': stack.get('Parameters', [])
                        }
                    }
                    stacks_cache.update(index_stack)

                if token:
                    response = cfn.describe_stacks_all(token)

            return

        except Exception as e:
            message = {
                'FILE': __file__.split('/')[-1],
                'METHOD': inspect.stack()[0][3],
                'EXCEPTION': str(e)
            }
            logger.exception(message)
            raise


    # Get stacks data if index is empty - only need to do once
    if not stacks_cache:
        get_indexed_stacks()

    stack_data = {}

    stack_data.update({'StackStatus': 'NOTFOUND', 'ExistingParameterKeys': []})

    if stack_name not in stacks_cache:
        return stack_data

    stack_data.update({'StackStatus': stacks_cache.get(stack_name).get('StackStatus')})

    # Copy over the parameter keys to the data to be returned
    parameters = stacks_cache.get(stack_name).get('Parameters')

    for parameter in parameters:
        stack_data['ExistingParameterKeys'].append(parameter.get('ParameterKey'))
        if parameter.get('ParameterKey') == 'AccountEmail':
            stack_data.update({'AccountEmail': parameter.get('ParameterValue')})

    return stack_data

class LaunchAVM(object):
    def __init__(self, logger, wait_time, manifest_file_path, sm_arn_launch_avm, batch_size):
        self.state_machine = StateMachine(logger)
        self.ssm = SSM(logger)
        self.sc = SC(logger)
        self.param_handler = CFNParamsHandler(logger)
        self.logger = logger
        self.manifest_file_path = manifest_file_path
        self.manifest_folder = manifest_file_path[:-len(MANIFEST_FILE_NAME)]
        self.wait_time = wait_time
        self.sm_arn_launch_avm = sm_arn_launch_avm
        self.manifest = None
        self.list_sm_exec_arns = []
        self.batch_size = batch_size
        self.avm_product_name = None
        self.avm_product_id = None
        self.avm_artifact_id = None
        self.avm_params = None
        self.root_id = None
        self.sc_portfolios = {}
        self.sc_products = {}
        self.provisioned_products = {}              # [productid] = []
        self.provisioned_products_by_account = {}   # [account] = [] list of ppids

    def _load_params(self, relative_parameter_path, account=None, region=None):
        parameter_file = os.path.join(self.manifest_folder, relative_parameter_path)

        self.logger.info("Parsing the parameter file: {}".format(parameter_file))

        with open(parameter_file, 'r') as content_file:
            parameter_file_content = content_file.read()

        params = json.loads(parameter_file_content)
        # The last parameter is set to False, because we do not want to replace the SSM parameter values yet.
        sm_params = self.param_handler.update_params(params, account, region, False)

        self.logger.info("Input Parameters for State Machine: {}".format(sm_params))
        return sm_params

    def _create_launch_avm_state_machine_input_map(self, accounts):
        """
        Create the input parameters for the state machine
        """
        portfolio = self.avm_portfolio_name
        product = self.avm_product_name.strip()

        request = {}
        request.update({'RequestType': 'Create'})
        request.update({'PortfolioId': self.sc_portfolios.get(portfolio)})

        portfolio_exist = False
        if any(self.sc_portfolios.get(portfolio)):
            portfolio_exist = True
        request.update({'PortfolioExist': portfolio_exist})

        request.update({'ProductId': self.sc_products.get(portfolio).get(product)})
        request.update({'ProvisioningArtifactId': self._get_provisioning_artifact_id(request.get('ProductId'))})

        product_exist = False
        if any(self.sc_products.get(portfolio).get(product)):
            product_exist = True
        request.update({'ProductExist': product_exist})

        input_params = {}
        input_params.update({'PortfolioName': sanitize(portfolio, True)})
        input_params.update({'ProductName': sanitize(product, True)})
        input_params.update({'ProvisioningParametersList': accounts})

        request.update({'ResourceProperties':input_params})
        # Set up the iteration parameters for the state machine
        request.update({'Index': 0})
        request.update({'Step': 1})
        request.update({'Count': len(input_params['ProvisioningParametersList'])})

        return request

    def _get_provisioning_artifact_id(self, product_id):
        self.logger.info("Listing the provisioning artifact")
        response = self.sc.list_provisioning_artifacts(product_id)
        self.logger.info("List Artifacts Response")
        self.logger.info(response)

        version_list = response.get('ProvisioningArtifactDetails')
        if version_list:
            return version_list[-1].get('Id')
        else:
            raise Exception("Unable to find provisioning artifact id.")

    def _portfolio_in_manifest(self, portname):
        """
        Scan the list of portfolios in the manifest looking for a match
        to portname
        """
        portname = portname.strip()
        self.logger.debug('Looking for portfolio {}'.format(portname))
        exists = False
        for port in self.manifest.portfolios:
            if portname == port.name.strip():
                exists = True
                break
        return exists

    def _product_in_manifest(self, portname, productname):
        """
        Scan the list of products in the portfolio in the manifest looking
        for a match to product name
        """
        portname = portname.strip()
        productname = productname.strip()
        self.logger.debug('Looking for product {} in portfolio {}'.format(productname, portname))
        exists = False
        for port in self.manifest.portfolios:
            if portname == port.name.strip():
                for product in port.products:
                    if productname == product.name.strip():
                        self.logger.debug('MATCH')
                        exists = True
                        break
                break
        return exists

    def sc_lookup(self):
        """
        Using data from input_params gather ServiceCatalog product info.
        The product data is used when creating the json data to hand off
        to LaunchAVM state machine
        """
        try:

            response = self.sc.list_portfolios()
            portfolio_list = response.get('PortfolioDetails')

            for portfolio in portfolio_list:
                portfolio_name = portfolio.get('DisplayName')

                # Is this portfolio in the manifest? If not skip it.
                if not self._portfolio_in_manifest(portfolio_name):
                    continue

                portfolio_id = portfolio.get('Id')
                self.sc_portfolios.update({portfolio_name: portfolio_id})

                # Initialize the portfolio in the products dictionary
                self.sc_products.update({portfolio_name: {}})

                # Get info for the products in this portfolio
                response = self.sc.search_products_as_admin(portfolio_id)

                product_list = response.get('ProductViewDetails')

                # find the product in the portfolio and add it to the dictionary
                for product in product_list:
                    portfolio_product_name = product.get('ProductViewSummary').get('Name')
                    if not self._product_in_manifest(portfolio_name, portfolio_product_name):
                        continue

                    product_id = product['ProductViewSummary'].get('ProductId')

                    # add the product to the sc_products dictionary
                    self.sc_products[portfolio_name].update({ portfolio_product_name: product_id })

            self.logger.debug('DUMP OF SC_PRODUCTS')
            self.logger.debug(json.dumps(self.sc_products, indent=2))

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise


    def get_indexed_provisioned_products(self):
        """
        Get all provisioned products for a Service Catalog product Id.
        Create an index by provisioned_product_id.

        This data is the same for every account for the same product Id.

        Ref: state_machine_handler::search_provisioned_products@2031
        """
        try:
            # 1) Get a complete list of provisioned products for this product Id

            pprods = self.sc.search_provisioned_products(self.avm_product_id)
            token = 'init'

            while token:

                for provisioned_product in pprods.get('ProvisionedProducts'):
                    self.logger.info('PROCESSING ' + str(provisioned_product['Id']))
                    self.logger.debug("ProvisionedProduct:{}".format(provisioned_product))
                    provisioned_product_id = provisioned_product.get('Id')

                    # 2) Remove any with a status of ERROR or UNDER_CHANGE
                    # Ignore products that error out before and
                    # to avoid the case of looking up the same product ignore UNDER_CHANGE
                    if provisioned_product.get('Status') == 'ERROR' or provisioned_product.get('Status') == 'UNDER_CHANGE':
                        continue

                    # This provisioned product passes - add it to the dict
                    # We only reference AccountEmail and ExistingParameterKeys in StackInfo
                    self.provisioned_products[provisioned_product_id] = {}

                    # 3) Extract stack_name from stack_id (see state_machine_handler@2066)
                    stack_id = provisioned_product.get('PhysicalId')
                    self.logger.debug("stack_id={}".format(stack_id))

                    # Extract Stack Name from the Physical Id
                    # e.g. Stack Id: arn:aws:cloudformation:${AWS::Region}:${AWS::AccountId}:stack/SC-${AWS::AccountId}-pp-fb3xte4fc4jmk/5790fb30-547b-11e8-b302-50fae98974c5
                    # Stack name = SC-${AWS::AccountId}-pp-fb3xte4fc4jmk
                    stack_name = stack_id.split('/')[1]
                    self.logger.debug("stack_name={}".format(stack_name))

                    # 4) Query stack state and add AccountEmail, ExistingParameterKeys (see shm@2097)
                    self.provisioned_products[provisioned_product_id] = get_stack_data(stack_name, self.logger)

                    # Add the provisioned product Id to key/value keyed by account
                    # Note: by intentional limitation there is exactly one provisioned product
                    #   per Product Id in ALZ
                    account_email = self.provisioned_products[provisioned_product_id].get('AccountEmail',None)
                    if account_email:
                        self.provisioned_products_by_account[account_email] = provisioned_product_id

                token = pprods.get('NextPageToken', None)
                pprods = None # Reset
                if token:
                    pprods = self.sc.search_provisioned_products(self.avm_product_id, token)

            self.logger.debug('DUMP OF PROVISIONED PRODUCTS')
            self.logger.debug(json.dumps(self.provisioned_products, indent=2, default=date_handler))

            self.logger.debug('DUMP OF PROVISIONED PRODUCTS INDEX')
            self.logger.debug(json.dumps(self.provisioned_products_by_account, indent=2, default=date_handler))

        except Exception as e:
            message = {
                'FILE': __file__.split('/')[-1],
                'METHOD': inspect.stack()[0][3],
                'EXCEPTION': str(e)
            }
            self.logger.exception(message)

    def _process_accounts_in_batches(self, accounts, organizations, ou_id, ou_name):
        """
        Each account in an OU is processed into a batch of one or more accounts.
        This function processes one batch.

        For each account:
            get email, name, ou name
            ignore suspended accounts
            build state machine input
            instantiate state machine

        Note: sm_input must not exceed 32K max
        """
        try:
            list_of_accounts = []
            for account in accounts:
                # Process each account
                if account.get('Status').upper() == 'SUSPENDED':
                    # Account is suspended
                    organizations.move_account(account.get('Id'), ou_id, self.root_id)
                    continue
                else:
                    # Active account
                    params = self.avm_params.copy()
                    for key, value in params.items():
                        if value.lower() == 'accountemail':
                            params.update({key: account.get('Email')})
                        elif value.lower() == 'accountname':
                            params.update({key: account.get('Name')})
                        elif value.lower() == 'orgunitname':
                            params.update({key: ou_name})

                    # Retrieve the provisioned product id
                    ppid = self.provisioned_products_by_account.get(account.get('Email'), None)
                    if ppid:
                        params.update({'ProvisionedProductId': ppid})
                        params.update({'ProvisionedProductExists': True})
                        params.update(
                            {
                                'ExistingParameterKeys':
                                self.provisioned_products.get(ppid).get('ExistingParameterKeys', [])
                            }
                        )
                    else:
                        params.update(
                            {
                                'ProvisionedProductExists': False
                            }
                        )

                    self.logger.info(
                        "Input parameters format for Account: {} are {}".format(
                            account.get('Name'),
                            params)
                    )

                    list_of_accounts.append(params)

            if list_of_accounts:
                # list_of_accounts is passed directly through to the input json data
                # This data should be complete from start_launch_avm
                sm_input = self._create_launch_avm_state_machine_input_map(
                    # self.avm_portfolio_name,
                    # self.avm_product_name.strip(),
                    list_of_accounts
                )
                self.logger.info("Launch AVM state machine Input: {}".format(sm_input))
                exec_name = "%s-%s-%s-%s-%s" % (
                    "AVM",
                    sanitize(ou_name[:40]),
                    time.strftime("%Y-%m-%dT%H-%M-%S"),
                    str(time.time()).split('.')[1],  # append microsecond
                    str(uuid4()).split('-')[1]
                )
                sm_exec_arn = self.state_machine.trigger_state_machine(
                    self.sm_arn_launch_avm,
                    sm_input,
                    exec_name
                )
                self.list_sm_exec_arns.append(sm_exec_arn)

                time.sleep(int(self.wait_time))  # Sleeping for sometime

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def start_launch_avm(self):
        """
        Get a list of accounts
        Find the portfolio id and product id for the AVM product
        Call _process_accounts_in_batches to build and submit input data for
        each batch to a state machine instance
        """
        try:
            self.logger.info("Starting the launch AVM trigger")

            org = Org({}, self.logger)
            organizations = Organizations(self.logger)
            delimiter = ':'
            if self.manifest.nested_ou_delimiter:
                delimiter = self.manifest.nested_ou_delimiter

            response = organizations.list_roots()
            self.logger.debug("List roots Response")
            self.logger.debug(response)
            self.root_id = response['Roots'][0].get('Id')

            for ou in self.manifest.organizational_units:
                self.avm_product_name = ou.include_in_baseline_products[0]

                # Find the AVM for this OU and get the AVM parameters
                for portfolio in self.manifest.portfolios:
                    for product in portfolio.products:
                        if product.name.strip() == self.avm_product_name.strip():
                            self.avm_params = self._load_params(product.parameter_file)
                            self.avm_portfolio_name = portfolio.name.strip()
                            self.avm_product_id = self.sc_products.get(portfolio.name.strip()).get(product.name.strip())

                """
                Get provisioned product data for all accounts
                Note: this reduces the number of API calls, but produces a large
                in-memory dictionary. However, even at 1,000 accounts this should
                not be a concern
                Populates:
                self.provisioned_products = {}              # [productid] = []
                self.provisioned_products_by_account = {}   # [account] = [] list of ppids
                self.stacks = {}                            # [stackname] = stackinfo
                """
                self.get_indexed_provisioned_products()

                if not self.avm_params:
                    raise Exception("Baseline product: {} for OU: {} is not found in the" \
                      " portfolios section of Manifest".format(self.avm_product_name, ou.name))

                ou_id = org._get_ou_id(organizations, self.root_id, ou.name, delimiter)

                self.logger.info(
                    "Processing Accounts under: {} in batches of size: {}".format(ou_id, self.batch_size)
                )
                response = organizations.list_accounts_for_parent(ou_id, self.batch_size)
                self.logger.info("List Accounts for Parent OU {} Response".format(ou_id))
                self.logger.info(response)
                self._process_accounts_in_batches(response.get('Accounts'), organizations, ou_id, ou.name)
                next_token = response.get('NextToken', None)

                while next_token is not None:
                    self.logger.info("Next Token Returned: {}".format(next_token))
                    response = organizations.list_accounts_for_parent(ou_id, self.batch_size, next_token)
                    self.logger.info("List Accounts for Parent OU {} Response".format(ou_id))
                    self.logger.info(response)
                    self._process_accounts_in_batches(response.get('Accounts'), organizations, ou_id, ou.name)
                    next_token = response.get('NextToken', None)

            return
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def trigger_launch_avm_state_machine(self):
        try:
            self.manifest = Manifest(self.manifest_file_path)
            self.sc_lookup() # Get Service Catalog data
            self.start_launch_avm()
            return
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def monitor_state_machines_execution_status(self):
        try:
            final_status = 'RUNNING'

            while final_status == 'RUNNING':
                for sm_exec_arn in self.list_sm_exec_arns:
                    if self.state_machine.check_state_machine_status(sm_exec_arn) == 'RUNNING':
                        final_status = 'RUNNING'
                        time.sleep(int(wait_time))
                        break
                    else:
                        final_status = 'COMPLETED'

            err_flag = False
            failed_sm_execution_list = []
            for sm_exec_arn in self.list_sm_exec_arns:
                if self.state_machine.check_state_machine_status(sm_exec_arn) == 'SUCCEEDED':
                    continue
                else:
                    failed_sm_execution_list.append(sm_exec_arn)
                    err_flag = True
                    continue

            if err_flag:
                result = ['FAILED', failed_sm_execution_list]
            else:
                result = ['SUCCEEDED', '']

            return result

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

if __name__ == '__main__':
    if len(sys.argv) > 5:
        log_level = sys.argv[1]
        wait_time = sys.argv[2]
        manifest_file_path = sys.argv[3]
        sm_arn_launch_avm = sys.argv[4]
        batch_size = int(sys.argv[5])

        logger = Logger(loglevel=log_level)
        avm_run = LaunchAVM(logger, wait_time, manifest_file_path, sm_arn_launch_avm, batch_size)
        avm_run.trigger_launch_avm_state_machine()
        status, failed_execution_list = avm_run.monitor_state_machines_execution_status()
        error = " LaunchAVM State Machine Execution(s) Failed. Navigate to the AWS Step Functions console and" \
                " review the following State Machine Executions. ARN List: {}".format(failed_execution_list)

        if status == 'FAILED':
            logger.error(100 * '*')
            logger.error(error)
            logger.error(100 * '*')
            sys.exit(1)

    else:
        print('No arguments provided. ')
        print('Example: launch_avm.py <LOG-LEVEL> <WAIT-TIME> <MANIFEST-FILE-PATH> <LAUNCH-AVM-SM-ARN> <BATCH_SIZE>')
        sys.exit(2)
