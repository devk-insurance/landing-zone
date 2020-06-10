from manifest.sm_input_builder import InputBuilder, StackSetResourceProperties
from lib.logger import Logger
logger = Logger('info')


# declare Stack Set state machine input variables
stack_set_name = "StackSetName1"
template_url = "https://s3.amazonaws.com/bucket/prefix"
parameters = {"Key1": "Value1",
              "Key2": "Value2"}
capabilities = "CAPABILITY_NAMED_IAM"
account_list = ["account_id_1",
                "account_id_2"]
region_list = ["us-east-1",
               "us-east-2"]
ssm_parameters = {
    "/ssm/parameter/store/key": "value"
}


def build_stack_set_input():
    # get stack set output
    resource_properties = StackSetResourceProperties(
        stack_set_name, template_url, parameters,
        capabilities, account_list, region_list,
        ssm_parameters)
    ss_input = InputBuilder(resource_properties.get_stack_set_input_map())
    return ss_input.input_map()


def test_stack_set_input_type():
    # check if returned input is of type dict
    stack_set_input = build_stack_set_input()
    assert isinstance(stack_set_input, dict)


def test_ss_resource_property_type():
    # check if resource property is not None
    stack_set_input = build_stack_set_input()
    assert isinstance(stack_set_input.get("ResourceProperties"), dict)


def test_ss_request_type_value():
    # check the default request type is create
    stack_set_input = build_stack_set_input()
    assert stack_set_input.get("RequestType") == "Create"
