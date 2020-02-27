import logging
log = logging.getLogger(__name__)

# This is a custom valiator specifically for pyKwlify Schema extensions
# It will validate if the email address exists for all accounts except PRIMARY account
# It will validate if the account exports $[AccountId] as ssm_parameters
def account_validation(value, rule_obj, path):
    log.info("Performing Core Account Email validation")

    if (value.get('name').upper() == 'PRIMARY'):
        if value.get('email', '') != '':
            raise AssertionError('No Email is required for the primary account.')
    else:
        if value.get('email', '') == '':
            msg = 'Missing Email address for Account: ' + value.get('name')
            raise AssertionError(msg)

    ssm_parameters = value.get('ssm_parameters', [])

    if ssm_parameters:
        for ssm_param in ssm_parameters:
            val = ssm_param.get('value', '')
            if val == '$[AccountId]':
                return True
        msg = 'Missing $[AccountId] export as ssm_parameters for Account: ' + value.get('name')
        raise AssertionError(msg)
    else:
        msg = 'Missing ssm_parameters for Account: ' + value.get('name')
        raise AssertionError(msg)
    return True

def avm_and_ou_cross_reference_validation(value, rule_obj, path):
    log.info("Performing avm cross reference validation")
    # Enumerate all the Baseline AVM products from Manifest
    portfolios_list = value.get('portfolios')
    valid_avm_list = []
    valid_ou_list = []

    for portfolio in portfolios_list:
        for product in portfolio.get('products'):
            if product.get('product_type').lower() == 'baseline':
                valid_avm_list.append(product.get('name').strip())

    log.info("Valid AVMs defined in manifest: {}".format(valid_avm_list))

    # Enumerate all the OUs to check if its using a valid AVM product
    ou_list = value.get('organizational_units')
    for ou in ou_list:
        ou_name = ou.get('name')

        valid_ou_list.append(ou_name)
        log.info("Validating AVM for OU: {}".format(ou_name))
        avm_list = ou.get('include_in_baseline_products')
        log.info("AVM List for OU: {}".format(avm_list))

        if len(avm_list) == 1:
            if avm_list[0].strip() not in valid_avm_list:
                msg = "Baseline product: {} for OU: {} is not found in the" \
                      " portfolios section of Manifest".format(avm_list[0].strip(), ou_name)
                raise AssertionError(msg)
        else:
            msg = "Only one baseline_product must be associated with the OU: {}".format(ou_name)
            raise AssertionError(msg)


    # Enumerate all the baseline_resources to check if its using valid AVM product(s)
    baseline_resources_list = value.get('baseline_resources')

    for baseline_resource in baseline_resources_list:
        baseline_resource_name = baseline_resource.get('name')
        log.info("Validating AVM for baseline resource: {}".format(baseline_resource_name))
        avm_list = baseline_resource.get('baseline_products')
        log.info("AVM List for baseline resource: {}".format(avm_list))

        for avm_ref in avm_list:
            if avm_ref.strip() not in valid_avm_list:
                msg = "One of the baseline_products: {} for baseline resource: {}" \
                      " is not found in the portfolios section of " \
                      "Manifest: {}".format(avm_ref, baseline_resource_name, valid_avm_list)
                raise AssertionError(msg)

    log.info("Performing OU cross reference validation")
    log.info("Valid OUs defined in manifest: {}".format(valid_ou_list))

    # Enumerate all the scp to check if its using valid OU(s)
    scp_list = value.get('organization_policies')

    for scp in scp_list:
        log.info("Validating OU for SCP: {}".format(scp.get('name')))
        ou_list = scp.get('apply_to_accounts_in_ou')
        log.info("OU List for SCP: {}".format(ou_list))
        for ou in ou_list:
            # Check if the ou belongs to the valid OU list
            # For nested OUs, check if the initial ou structure matches with the ones in valid OU list
            if not any(item.startswith(ou) for item in valid_ou_list):
                msg = "One of the OUs: {} listed under 'apply_to_accounts_in_ou' " \
                      "for Organization policy (SCP): {} is invalid. " \
                      "It is not one of the organizational_units " \
                      "listed in Manifest: {}".format(ou, scp.get('name'), valid_ou_list)
                raise AssertionError(msg)

    return True

def ou_delimiter_validation(value, rule_obj, path):
    log.info("Performing OU delimiter validation")
    valid_delimiter_list = ['.',':','-','_',',',';','#','|']

    if value.strip() != "":
        if value.strip() not in valid_delimiter_list:
            msg = "The nested_ou_delimiter in manifest: {} is invalid, " \
                  "please use one of the valid delimiters " \
                  "from {}".format(value.strip(), valid_delimiter_list)
            raise AssertionError(msg)

    return True

def avm_skeleton_file_validation(value, rule_obj, path):
    log.info("Performing AVM skeleton_file uniqueness validation")

    portfolios_list = value
    avm_skeleton_file_list = []

    # Enumerate all the AVM skeleton_file from Manifest
    for portfolio in portfolios_list:
        for product in portfolio.get('products'):
            if product.get('product_type').lower() == 'baseline':
                avm_skeleton_file_list.append(product.get('skeleton_file').strip())

    # Check for duplicate AVM skeleton_file
    for avm_skeleton_file in avm_skeleton_file_list:
        if avm_skeleton_file_list.count(avm_skeleton_file) > 1:
            msg = "The skeleton_file: {} in manifest is referenced more than one time, " \
                  "for different AVM Baseline products, which is not allowed. Each AVM Baseline product" \
                  "from should reference different skeleton file".format(avm_skeleton_file)
            raise AssertionError(msg)

    return True