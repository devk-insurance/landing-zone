import yorm
from yorm.types import String, Integer, Float, Boolean
from yorm.types import List, Dictionary, AttributeDictionary

@yorm.attr(name=String)
@yorm.attr(value=String)
class SSM(AttributeDictionary):
    def __init__(self, name, value):
        super().__init__()
        self.name = name
        self.value = value

@yorm.attr(all=SSM)
class SSMList(List):
    def __init__(self):
        super().__init__()

@yorm.attr(all=String)
class RegionsList(List):
    def __init__(self):
        super().__init__()

@yorm.attr(all=String)
class dependsOnList(List):
    def __init__(self):
        super().__init__()

@yorm.attr(all=String)
class BaselineProductsList(List):
    def __init__(self):
        super().__init__()

@yorm.attr(all=String)
class ApplyToOUList(List):
    def __init__(self):
        super().__init__()


@yorm.attr(name=String)
@yorm.attr(template_file=String)
@yorm.attr(parameter_file=String)
@yorm.attr(deploy_method=String)
@yorm.attr(ssm_parameters=SSMList)
@yorm.attr(regions=RegionsList)
@yorm.attr(parameter_override=String)
@yorm.attr(baseline_products=BaselineProductsList)
@yorm.attr(depends_on=dependsOnList)
class Resource(AttributeDictionary):
    def __init__(self, name, template_file, parameter_file, deploy_method, parameter_override, baseline_products, regions, ssm_parameters, depends_on):
        super().__init__()
        self.name = name
        self.template_file = template_file
        self.parameter_file = parameter_file
        self.deploy_method = deploy_method
        self.baseline_products = []
        self.regions = []
        self.ssm_parameters = []
        self.depends_on = []
        self.parameter_override = parameter_override


@yorm.attr(all=Resource)
class ResourcesList(List):
    def __init__(self):
        super().__init__()


@yorm.attr(name=String)
@yorm.attr(email=String)
@yorm.attr(ssm_parameters=SSMList)
@yorm.attr(core_resources=ResourcesList)
class Account(AttributeDictionary):
    def __init__(self, name, email, ssm_parameters, core_resources):
        super().__init__()
        self.name = name
        self.email = email
        self.ssm_parameters = []
        self.core_resources = []


@yorm.attr(all=Account)
class AccList(List):
    def __init__(self):
        super().__init__()


@yorm.attr(name=String)
@yorm.attr(core_accounts=AccList)
@yorm.attr(include_in_baseline_products=BaselineProductsList)
class OrganizationalUnit(AttributeDictionary):
    def __init__(self, name, include_in_baseline_products, core_accounts):
        super().__init__()
        self.name = name
        self.include_in_baseline_products = []
        self.core_accounts = []


@yorm.attr(all=OrganizationalUnit)
class OUList(List):
    def __init__(self):
        super().__init__()


@yorm.attr(name=String)
@yorm.attr(description=String)
@yorm.attr(template_file=String)
@yorm.attr(skeleton_file=String)
@yorm.attr(parameter_file=String)
@yorm.attr(ssm_parameters=SSMList)
@yorm.attr(hide_old_versions=Boolean)
@yorm.attr(apply_baseline_to_accounts_in_ou=ApplyToOUList)
@yorm.attr(launch_constraint_role=String)
@yorm.attr(product_type=String)
class Product(AttributeDictionary):
    def __init__(self, name, description, template_file, skeleton_file, parameter_file, hide_old_versions, apply_baseline_to_accounts_in_ou, launch_constraint_role, product_type, ssm_parameters):
        super().__init__()
        self.name = name
        self.description = description
        self.template_file = template_file
        self.skeleton_file = skeleton_file
        self.parameter_file = parameter_file
        self.ssm_parameters = []
        self.hide_old_versions = hide_old_versions
        self.apply_baseline_to_accounts_in_ou = apply_baseline_to_accounts_in_ou
        self.launch_constraint_role = launch_constraint_role
        self.product_type = product_type


@yorm.attr(all=Product)
class ProductsList(List):
    def __init__(self):
        super().__init__()


@yorm.attr(name=String)
@yorm.attr(description=String)
@yorm.attr(owner=String)
@yorm.attr(products=ProductsList)
@yorm.attr(principal_role=String)
class Portfolio(AttributeDictionary):
    def __init__(self, name, description, owner, principal_role, products):
        super().__init__()
        self.name = name
        self.description = description
        self.owner = owner
        self.products = []
        self.principal_role = principal_role


@yorm.attr(all=Portfolio)
class PortfoliosList(List):
    def __init__(self):
        super().__init__()


@yorm.attr(name=String)
@yorm.attr(policy_file=String)
@yorm.attr(description=String)
@yorm.attr(apply_to_accounts_in_ou=ApplyToOUList)
class Policy(AttributeDictionary):
    def __init__(self, name, policy_file, description, apply_to_accounts_in_ou):
        super().__init__()
        self.name = name
        self.description = description
        self.policy_file = policy_file
        self.apply_to_accounts_in_ou = apply_to_accounts_in_ou


@yorm.attr(all=Policy)
class PolicyList(List):
    def __init__(self):
        super().__init__()


@yorm.attr(region=String)
@yorm.attr(version=String)
@yorm.attr(lock_down_stack_sets_role=Boolean)
@yorm.attr(organizational_units=OUList)
@yorm.attr(portfolios=PortfoliosList)
@yorm.attr(baseline_resources=ResourcesList)
@yorm.attr(organization_policies=PolicyList)
@yorm.sync("{self.manifest_file}", auto_create=False)
class Manifest:
    def __init__(self, manifest_file):
        self.manifest_file = manifest_file
        self.organizational_units = []
        self.organization_policies = []
        self.portfolios = []
        self.baseline_resources = []



if __name__ == "__main__":
    manifest = Manifest('../../deployment/aws_landing_zone_framework/manifest.yaml')

    # print(manifest.organizational_units)
    # if manifest.organizational_units:
    #     for ou in manifest.organizational_units:
    #         for account in ou.accounts:
    #             for resource in account.resources:
    #                 print(resource.name)
    #                 print(resource.template_file)
    #                 print(resource.parameter_file)
    #                 print(resource.deploy_method)
    #                 print(resource.regions)
    # else:
    #     print("No OUs to process")
    #
    for port in manifest.portfolios:
        print(port.name)
        print(port.principal_role)
        for prod in port.products:
            print(prod.name)
            print(prod.hide_old_versions)
            if len(prod.skeleton_file) > 0:
                print("template={}".format(prod.skeleton_file))
            if len(prod.template_file) > 0:
                print("template={}".format(prod.template_file))
            print(prod.product_type)
            print(prod.apply_baseline_to_accounts_in_ou)
