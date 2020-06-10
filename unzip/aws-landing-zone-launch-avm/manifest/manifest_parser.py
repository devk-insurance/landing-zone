import os
import sys
import json
from lib.manifest import Manifest
from manifest.stage_to_s3 import StageFile
from manifest.sm_input_builder import InputBuilder, StackSetResourceProperties
from lib.parameter_manipulation import transform_params
from lib.organizations import Organizations
from lib.s3 import S3
from lib.list_manipulation import list_sanitizer
from lib.dict_manipulation import get_reduced_merged_list, flip_dict_properties, join_dict_per_key_value_relation
from manifest.cfn_params_handler import CFNParamsHandler


class BaselineResourceParser:
    def __init__(self, logger):
        self.logger = logger
        self.org = Organizations(logger)
        self.s3 = S3(logger)
        self.param_handler = CFNParamsHandler(logger)
        self.manifest = Manifest(os.environ.get('MANIFEST_FILE_PATH'))
        self.manifest_folder = os.environ.get('MANIFEST_FOLDER')

    def parse_baseline_resource_manifest(self):

        self.logger.info("Parsing Core Resources from {} file"
                         .format(os.environ.get('MANIFEST_FILE_PATH')))

        state_machine_inputs = []

        avm_to_account_ids_map = self.get_avm_to_accounts_map()

        for resource in self.manifest.baseline_resources:
            self.logger.info(">>>> START : {} >>>>".format(resource.name))
            avm_list = resource.baseline_products
            account_list = get_reduced_merged_list(avm_to_account_ids_map, avm_list)

            if resource.deploy_method.lower() == 'stack_set':
                sm_input = self._get_state_machine_input(resource,
                                                         account_list)
                state_machine_inputs.append(sm_input)
            else:
                raise Exception("Unsupported deploy_method: {} found for "
                                "resource {} and Account: {} in Manifest"
                                .format(resource.deploy_method,
                                        resource.name,
                                        account_list))
            self.logger.info("<<<< FINISH : {} <<<<".format(resource.name))

        # Exit if there are no CloudFormation resources
        if len(state_machine_inputs) == 0:
            self.logger.info("CloudFormation resources not found in the "
                             "manifest")
            sys.exit(0)
        else:
            return state_machine_inputs

    def get_avm_to_accounts_map(self):
        # get root ID
        root_id = self._get_root_id()
        ou_id_list = []
        ou_name_to_id_map = {}
        ou_id_to_avm_name_map = {}
        # get OUs from the manifest
        for org_unit in self.manifest.organizational_units:
            self.logger.info("Processing OU Name: {}".format(org_unit.name))
            self.logger.info(org_unit.include_in_baseline_products)
            ou_id = self.get_ou_id(root_id, org_unit.name, self.manifest.nested_ou_delimiter)
            ou_id_list.append(ou_id)
            ou_name_to_id_map.update({org_unit.name: ou_id})
            ou_id_to_avm_name_map.update({ou_id: org_unit.include_in_baseline_products[0]})
        accounts_in_all_ous, ou_id_to_account_map = self._get_accounts_in_ou(ou_id_list)

        self.logger.info("Printing list of OU Ids in the Manifest: {}".format(ou_id_list))
        self.logger.info(ou_name_to_id_map)
        self.logger.info("Printing all accounts in OUs managed by ALZ: {}".format(accounts_in_all_ous))
        self.logger.info("Printing OU Id to Accounts Map")
        self.logger.info(ou_id_to_account_map)
        self.logger.info("Printing OU Id to AVM Product Map")
        self.logger.info(ou_id_to_avm_name_map)
        avm_to_ou_ids_map = flip_dict_properties(ou_id_to_avm_name_map)
        avm_to_accounts_map = join_dict_per_key_value_relation(avm_to_ou_ids_map, ou_id_to_account_map)
        self.logger.info("Printing AVM Product to Accounts Map")
        self.logger.info(avm_to_accounts_map)
        return avm_to_accounts_map

    def get_ou_id(self, parent_id, nested_ou_name, delimiter):
        self.logger.info("Looking up the OU Id for OUName: '{}' with nested ou delimiter: '{}'"
                         .format(nested_ou_name, delimiter))
        nested_ou_name_list = self._empty_separator_handler(delimiter, nested_ou_name)
        response = self._list_ou_for_parent(parent_id, list_sanitizer(nested_ou_name_list))
        self.logger.info(response)
        return response

    @staticmethod
    def _empty_separator_handler(delimiter, nested_ou_name):
        if delimiter == "":
            nested_ou_name_list = [nested_ou_name]
        else:
            nested_ou_name_list = nested_ou_name.split(delimiter)
        return nested_ou_name_list

    def get_accounts_in_ou(self, ou_id_to_account_map, ou_name_to_id_map,
                           resource):
        accounts_in_ou = []
        ou_ids_manifest = []
        # convert OU Name to OU IDs
        for ou_name in resource.deploy_to_ou:
            ou_id = [value for key, value in ou_name_to_id_map.items()
                     if ou_name in key]
            ou_ids_manifest.extend(ou_id)
        # convert OU IDs to accounts
        for ou_id, accounts in ou_id_to_account_map.items():
            if ou_id in ou_ids_manifest:
                accounts_in_ou.extend(accounts)
        self.logger.info(">>> Accounts: {} in OUs: {}"
                         .format(accounts_in_ou, resource.deploy_to_ou))
        return accounts_in_ou

    def _get_root_id(self):
        response = self.org.list_roots()
        self.logger.info("Response: List Roots")
        self.logger.info(response)
        return response['Roots'][0].get('Id')

    def _list_ou_for_parent(self, parent_id, nested_ou_name_list):
        ou_list = self.org.list_organizational_units_for_parent(parent_id)
        index = 0  # always process the first item
        self.logger.info("Looking for existing OU: '{}' under parent id: '{}'".format(nested_ou_name_list[index],
                                                                                      parent_id))
        for dictionary in ou_list:
            if dictionary.get('Name') == nested_ou_name_list[index]:
                self.logger.info("OU Name: '{}' exists under parent id: '{}'".format(dictionary.get('Name'), parent_id))
                nested_ou_name_list.pop(index)  # pop the first item in the list
                if len(nested_ou_name_list) == 0:
                    self.logger.info("Returning last level OU ID: {}".format(dictionary.get('Id')))
                    return dictionary.get('Id')
                else:
                    return self._list_ou_for_parent(dictionary.get('Id'), nested_ou_name_list)

    def _get_accounts_in_ou(self, ou_id_list):
        _accounts_in_ou = []
        accounts_in_all_ous = []
        ou_id_to_account_map = {}

        for _ou_id in ou_id_list:
            self.logger.info("Getting accounts under OU ID: {}".format(_ou_id))
            _account_list = self.org.list_all_accounts_for_parent(_ou_id)
            self.logger.info(_account_list)
            for _account in _account_list:
                self.logger.info(_account)
                # filter ACTIVE and CREATED accounts
                if _account.get('Status') == "ACTIVE":
                    # create a list of accounts in OU
                    accounts_in_all_ous.append(_account.get('Id'))
                    _accounts_in_ou.append(_account.get('Id'))

            # create a map of accounts for each ou
            self.logger.info("Creating Key:Value Mapping - "
                             "OU ID: {} ; Account List: {}"
                             .format(_ou_id, _accounts_in_ou))
            ou_id_to_account_map.update({_ou_id: _accounts_in_ou})
            self.logger.info(ou_id_to_account_map)

            # reset list of accounts in the OU
            _accounts_in_ou = []

        self.logger.info("All accounts in OU List: {}"
                         .format(accounts_in_all_ous))
        self.logger.info("OU to Account ID mapping")
        self.logger.info(ou_id_to_account_map)
        return accounts_in_all_ous, ou_id_to_account_map

    # return list of strings
    @staticmethod
    def _convert_list_values_to_string(_list):
        return list(map(str, _list))

    def _get_state_machine_input(self, resource, account_list) -> dict:
        local_file = StageFile(self.logger, resource.template_file)
        template_url = local_file.get_staged_file()

        parameters = {}

        # set region variables
        if len(resource.regions) > 0:
            region = resource.regions[0]
            region_list = resource.regions
        else:
            region = self.manifest.region
            region_list = [region]

        # if parameter file link is provided for the CFN resource
        if resource.parameter_file:
            parameters = self._load_params(resource.parameter_file,
                                           account_list,
                                           region)

        ssm_parameters = self._create_ssm_input_map(resource.ssm_parameters)

        accounts = "" if resource.parameter_override == 'true' or account_list == [] else account_list
        regions = "" if resource.parameter_override == 'true' or account_list == [] else region_list

        # generate state machine input list
        stack_set_name = "AWS-Landing-Zone-Baseline-{}".format(resource.name)
        resource_properties = StackSetResourceProperties(stack_set_name,
                                                         template_url,
                                                         parameters,
                                                         os.environ
                                                         .get('CAPABILITIES'),
                                                         accounts,
                                                         regions,
                                                         ssm_parameters)
        ss_input = InputBuilder(resource_properties.get_stack_set_input_map())
        return ss_input.input_map()

    def _load_params(self, relative_parameter_path, account=None, region=None):
        if relative_parameter_path.lower().startswith('s3'):
            parameter_file = self.s3.get_s3_object(relative_parameter_path)
        else:
            parameter_file = os.path.join(self.manifest_folder,
                                          relative_parameter_path)

        self.logger.info("Parsing the parameter file: {}".format(
            parameter_file))

        with open(parameter_file, 'r') as content_file:
            parameter_file_content = content_file.read()

        params = json.loads(parameter_file_content)

        sm_params = self.param_handler.update_params(params, account,
                                                     region, False)

        self.logger.info("Input Parameters for State Machine: {}".format(
            sm_params))
        return sm_params

    def _create_ssm_input_map(self, ssm_parameters):
        ssm_input_map = {}

        for ssm_parameter in ssm_parameters:
            key = ssm_parameter.name
            value = ssm_parameter.value
            ssm_value = self.param_handler.update_params(
                transform_params({key: value})
            )
            ssm_input_map.update(ssm_value)
        return ssm_input_map
