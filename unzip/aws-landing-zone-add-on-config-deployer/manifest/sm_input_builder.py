from abc import ABC, abstractmethod


class StateMachineInput(ABC):
    """
    The State Machine input class that declares a set of methods that returns
    abstract input.
    """
    @abstractmethod
    def input_map(self):
        pass


class InputBuilder(StateMachineInput):
    """
    This class wraps the specific state machine input with
    common required keys.

    """
    def __init__(self, resource_properties, request_type='Create'):
        self._request_type = request_type
        self._resource_properties = resource_properties

    def input_map(self):
        return {
            "RequestType": self._request_type,
            "ResourceProperties": self._resource_properties
        }


class StackSetResourceProperties:
    """
        This class helps create and return input needed to execute Stack Set
        state machine. This also defines the required keys to execute the state
        machine.

        Example:

        resource_properties = StackSetResourceProperties(stack_set_name,
                                                     template_url,
                                                     parameters,
                                                     capabilities,
                                                     account_list,
                                                     region_list,
                                                     ssm_parameters)
        ss_input = InputBuilder(resource_properties.get_stack_set_input_map())
        sm_input = ss_input.input_map()
        """
    def __init__(self, stack_set_name, template_url, parameters,
                 capabilities, account_list, region_list, ssm_parameters):
        self._stack_set_name = stack_set_name
        self._template_url = template_url
        self._parameters = parameters
        self._capabilities = capabilities
        self._account_list = account_list
        self._region_list = region_list
        self._ssm_parameters = ssm_parameters

    def get_stack_set_input_map(self):
        return {
            "StackSetName": self._stack_set_name,
            "TemplateURL": self._template_url,
            "Capabilities": self._capabilities,
            "Parameters": self._get_cfn_parameters(),
            "AccountList": self._get_account_list(),
            "RegionList": self._get_region_list(),
            "SSMParameters": self._get_ssm_parameters()
        }

    def _get_cfn_parameters(self):
        if isinstance(self._parameters, dict):
            return self._parameters
        else:
            raise TypeError("Parameters must be of dict type")

    def _get_account_list(self):
        if isinstance(self._account_list, list) or self._account_list == "":
            return self._account_list
        else:
            raise TypeError("Account list value must be of list type")

    def _get_ssm_parameters(self):
        if isinstance(self._ssm_parameters, dict):
            return self._ssm_parameters
        else:
            raise TypeError("SSM Parameter value must be of dict type")

    def _get_region_list(self):
        if isinstance(self._region_list, list) or self._region_list == "":
            return self._region_list
        else:
            raise TypeError("Region list value must be of list type")
