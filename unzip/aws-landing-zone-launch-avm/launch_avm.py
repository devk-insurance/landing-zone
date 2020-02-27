from lib.logger import Logger
from lib.state_machine import StateMachine
from lib.ssm import SSM
from lib.helper import sanitize
from lib.organizations import Organizations
from state_machine_handler import Organizations as Org
from lib.manifest import Manifest
from lib.params import ParamsHandler
import inspect
import sys
import time
import json
import os

MANIFEST_FILE_NAME = 'manifest.yaml'

class LaunchAVM(object):
    def __init__(self, logger, wait_time, manifest_file_path, sm_arn_launch_avm, batch_size):
        self.state_machine = StateMachine(logger)
        self.ssm = SSM(logger)
        self.param_handler = ParamsHandler(logger)
        self.logger = logger
        self.manifest_file_path = manifest_file_path
        self.manifest_folder = manifest_file_path[:-len(MANIFEST_FILE_NAME)]
        self.wait_time = wait_time
        self.sm_arn_launch_avm = sm_arn_launch_avm
        self.manifest = None
        self.list_sm_exec_arns = []
        self.batch_size = batch_size
        self.avm_product_name = None
        self.avm_portfolio_name = None
        self.avm_params = None
        self.root_id = None

    def _load_params(self, relative_parameter_path, account = None, region = None):
        parameter_file = os.path.join(self.manifest_folder, relative_parameter_path)

        self.logger.info("Parsing the parameter file: {}".format(parameter_file))

        with open(parameter_file, 'r') as content_file:
            parameter_file_content = content_file.read()

        params = json.loads(parameter_file_content)
        # The last parameter is set to False, because we do not want to replace the SSM parameter values yet.
        sm_params = self.param_handler.update_params(params, account, region, False)

        self.logger.info("Input Parameters for State Machine: {}".format(sm_params))
        return sm_params

    def _create_state_machine_input_map(self, input_params, request_type='Create'):
        request = {}
        request.update({'RequestType':request_type})
        request.update({'ResourceProperties':input_params})
        return request

    def _create_launch_avm_state_machine_input_map(self, portfolio, product, accounts):
        input_params = {}
        input_params.update({'PortfolioName': sanitize(portfolio, True)})
        input_params.update({'ProductName': sanitize(product, True)})
        input_params.update({'ProvisioningParametersList': accounts})
        return self._create_state_machine_input_map(input_params)

    def _process_accounts_in_batches(self, accounts, organizations, ou_id, ou_name):
        try:
            list_of_accounts = []
            for account in accounts:
                if account.get('Status').upper() == 'SUSPENDED':
                    organizations.move_account(account.get('Id'), ou_id, self.root_id)
                    continue
                else:
                    params = self.avm_params.copy()
                    for key, value in params.items():
                        if value.lower() == 'accountemail':
                            params.update({key: account.get('Email')})
                        elif value.lower() == 'accountname':
                            params.update({key: account.get('Name')})
                        elif value.lower() == 'orgunitname':
                            params.update({key: ou_name})

                    self.logger.info(
                        "Input parameters format for Account: {} are {}".format(account.get('Name'), params))

                    list_of_accounts.append(params)

            if len(list_of_accounts) > 0:
                sm_input = self._create_launch_avm_state_machine_input_map(self.avm_portfolio_name,
                                                                           self.avm_product_name.strip(),
                                                                           list_of_accounts)
                self.logger.info("Launch AVM state machine Input: {}".format(sm_input))
                exec_name = "%s-%s-%s-%s" % (sm_input.get('RequestType'), sanitize(ou_name), "Launch-AVM",
                                             time.strftime("%Y-%m-%dT%H-%M-%S"))
                sm_exec_arn = self.state_machine.trigger_state_machine(self.sm_arn_launch_avm, sm_input, exec_name)
                self.list_sm_exec_arns.append(sm_exec_arn)

                time.sleep(int(wait_time))  # Sleeping for sometime
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def start_launch_avm(self):
        try:
            self.logger.info("Starting the launch AVM trigger")

            org = Org({}, self.logger)
            organizations = Organizations(self.logger)
            delimiter = self.manifest.nested_ou_delimiter

            response = organizations.list_roots()
            self.logger.info("List roots Response")
            self.logger.info(response)
            self.root_id = response['Roots'][0].get('Id')

            for ou in self.manifest.organizational_units:
                self.avm_product_name = ou.include_in_baseline_products[0]

                # Find the AVM for this OU and get the AVM parameters
                for portfolio in self.manifest.portfolios:
                    for product in portfolio.products:
                        if product.name.strip() == self.avm_product_name.strip():
                            self.avm_params = self._load_params(product.parameter_file)
                            self.avm_portfolio_name = portfolio.name.strip()

                if len(self.avm_params) == 0:
                    raise Exception("Baseline product: {} for OU: {} is not found in the" \
                      " portfolios section of Manifest".format(self.avm_product, ou.name))

                ou_id = org._get_ou_id(organizations, self.root_id, ou.name, delimiter)

                self.logger.info("Processing Accounts under: {} in batches of size: {}".format(ou_id, self.batch_size))
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
                    status = self.state_machine.check_state_machine_status(sm_exec_arn)
                    if status == 'RUNNING':
                        final_status = 'RUNNING'
                        time.sleep(int(wait_time))
                        break
                    else:
                        final_status = 'COMPLETED'

            err_flag = False
            failed_sm_execution_list = []
            for sm_exec_arn in self.list_sm_exec_arns:
                status = self.state_machine.check_state_machine_status(sm_exec_arn)
                if status == 'SUCCEEDED':
                    continue
                else:
                    failed_sm_execution_list.append(sm_exec_arn)
                    err_flag = True
                    continue

            if err_flag:
                return 'FAILED', failed_sm_execution_list
            else:
                return 'SUCCEEDED', ''

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
