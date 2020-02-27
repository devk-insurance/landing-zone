from lib.logger import Logger
from lib.state_machine import StateMachine
from lib.ssm import SSM
from lib.helper import sanitize
from lib.organizations import Organizations
from lib.manifest import Manifest
from lib.params import ParamsHandler
import inspect
import sys
import time
import json
import os

MANIFEST_FILE_NAME = 'manifest.yaml'

class LaunchAVM(object):
    def __init__(self, logger, wait_time, manifest_file_path, sm_arn_launch_avm):
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

    def start_launch_avm(self, sm_arn_launch_avm):
        try:
            self.logger.info("Starting the launch AVM trigger")
            ou_id_map = {}

            org = Organizations(self.logger)
            response = org.list_roots()
            self.logger.info("List roots Response")
            self.logger.info(response)
            root_id = response['Roots'][0].get('Id')

            response = org.list_organizational_units_for_parent(ParentId=root_id)
            next_token = response.get('NextToken', None)

            for ou in response['OrganizationalUnits']:
                ou_id_map.update({ou.get('Name'): ou.get('Id')})

            while next_token is not None:
                response = org.list_organizational_units_for_parent(ParentId=root_id,
                                                                    NextToken=next_token)
                next_token = response.get('NextToken', None)
                for ou in response['OrganizationalUnits']:
                    ou_id_map.update({ou.get('Name'): ou.get('Id')})

            self.logger.info("ou_id_map={}".format(ou_id_map))

            for portfolio in self.manifest.portfolios:
                for product in portfolio.products:
                    if product.product_type.lower() == 'baseline':
                        _params = self._load_params(product.parameter_file)
                        self.logger.info("Input parameters format for AVM: {}".format(_params))
                        list_of_accounts = []
                        for ou in product.apply_baseline_to_accounts_in_ou:
                            self.logger.debug("Looking up ou={} in ou_id_map".format(ou))
                            ou_id = ou_id_map.get(ou)
                            self.logger.debug("ou_id={} for ou={} in ou_id_map".format(ou_id, ou))

                            response = org.list_accounts_for_parent(ou_id)
                            self.logger.debug("List Accounts for Parent Response")
                            self.logger.debug(response)
                            for account in response.get('Accounts'):
                                params = _params.copy()
                                for key, value in params.items():
                                    if value.lower() == 'accountemail':
                                        params.update({key: account.get('Email')})
                                    elif value.lower() == 'accountname':
                                        params.update({key: account.get('Name')})
                                    elif value.lower() == 'orgunitname':
                                        params.update({key: ou})

                                self.logger.info("Input parameters format for Account: {} are {}".format(account.get('Name'), params))

                                list_of_accounts.append(params)

                        if len(list_of_accounts) > 0:
                            sm_input = self._create_launch_avm_state_machine_input_map(portfolio.name, product.name,list_of_accounts)
                            self.logger.info("Launch AVM state machine Input: {}".format(sm_input))
                            exec_name = "%s-%s-%s" % (sm_input.get('RequestType'), "Launch-AVM",
                                                      time.strftime("%Y-%m-%dT%H-%M-%S"))
                            sm_exec_arn = self.state_machine.trigger_state_machine(sm_arn_launch_avm, sm_input, exec_name)
                            self.list_sm_exec_arns.append(sm_exec_arn)

                    time.sleep(int(wait_time))  # Sleeping for sometime

            return
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def trigger_launch_avm_state_machine(self):
        try:
            self.manifest = Manifest(self.manifest_file_path)
            self.start_launch_avm(self.sm_arn_launch_avm)
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
            for sm_exec_arn in self.list_sm_exec_arns:
                status = self.state_machine.check_state_machine_status(sm_exec_arn)
                if status == 'SUCCEEDED':
                    continue
                else:
                    err_msg = "State Machine Execution Failed, please check the Step function console for State Machine Execution ARN: {}".format(
                        sm_exec_arn)
                    self.logger.error(err_msg)
                    err_flag = True
                    continue

            if err_flag:
                return 'FAILED', err_msg
            else:
                return 'SUCCEEDED', ''

        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

if __name__ == '__main__':
    if len(sys.argv) > 4:
        log_level = sys.argv[1]
        wait_time = sys.argv[2]
        manifest_file_path = sys.argv[3]
        sm_arn_launch_avm = sys.argv[4]

        logger = Logger(loglevel=log_level)
        avm_run = LaunchAVM(logger, wait_time, manifest_file_path, sm_arn_launch_avm)
        avm_run.trigger_launch_avm_state_machine()
        status, message = avm_run.monitor_state_machines_execution_status()

        if status == 'FAILED':
            logger.error(message)
            sys.exit(1)

    else:
        print('No arguments provided. ')
        print('Example: launch_avm.py <LOG-LEVEL> <WAIT-TIME> <MANIFEST-FILE-PATH> <LAUNCH-AVM-SM-ARN>')
        sys.exit(2)
