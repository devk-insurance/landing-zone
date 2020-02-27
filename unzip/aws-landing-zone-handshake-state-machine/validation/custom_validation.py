import logging
log = logging.getLogger(__name__)

# This is a custom valiator specifically for pyKwlify Schema extensions
# It will validate if the email address exists for all accounts except PRIMARY account
# It will validate if the account exports $[AccountId] as ssm_parameters
def account_validation(value, rule_obj, path):
    log.info("value: %s", value)
    log.info("rule_obj: %s", rule_obj)
    log.info("path: %s", path)

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
