from lib.logger import Logger
import yaml
import sys

log_level = 'info'
logger = Logger(loglevel=log_level)


# Iterate through the first level keys and add them if not found in the existing manifest file
def update_level_one_list(existing, add_on, level_one_dct_key, decision_key):
    if add_on.get(level_one_dct_key):
        for add_on_key_level_one_list in add_on.get(level_one_dct_key):
            if existing.get(level_one_dct_key):
                flag = False
                for existing_key_level_one_list in existing.get(level_one_dct_key):
                    if add_on_key_level_one_list.get(decision_key) == existing_key_level_one_list.get(decision_key):
                        flag = False
                        break  # break the loop if same ou name is found in the OU list
                    else:
                        # Setting the flag to add the value after scanning the full list
                        flag = True
                if flag:
                    # to avoid duplication append check to see if value in the list already exist
                    if add_on_key_level_one_list not in existing.get(level_one_dct_key):
                        logger.info("(Level 1) Adding new {} > {}: {}".format(type(add_on_key_level_one_list).__name__, decision_key, add_on_key_level_one_list.get(decision_key)))
                        existing.get(level_one_dct_key).append(add_on_key_level_one_list)
                        logger.debug(existing.get(level_one_dct_key))
        return existing


# Iterate through the second level keys (value = dictionary) and add them if not found in the existing manifest file
def update_level_two_list_of_dct(existing, add_on, level_one_dct_key, decision_key):
    if add_on.get(level_one_dct_key):
        for add_on_key_level_one_list in add_on.get(level_one_dct_key):
            for key, value in add_on_key_level_one_list.items():
                logger.debug(value)
                if isinstance(value, list):
                    logger.debug(value)
                    for item in value:
                        if isinstance(item, dict):
                            logger.debug(item)
                            # extracted list of account names in the add_on manifest
                            logger.debug(item.get(decision_key))
                            # iterating through existing manifest to add if new core account is added
                            if existing.get(level_one_dct_key):
                                for existing_key_level_one_list in existing.get(level_one_dct_key):
                                    if add_on_key_level_one_list.get(decision_key) == existing_key_level_one_list.get(decision_key):
                                        for k, v in existing_key_level_one_list.items():
                                            logger.debug(v)
                                            flag = False
                                            if isinstance(v, list):
                                                logger.debug(v)
                                                for i in v:
                                                    if isinstance(i, dict):
                                                        logger.debug(v)
                                                        logger.debug(i)
                                                        logger.debug(item.get(decision_key))
                                                        logger.debug(i.get(decision_key))
                                                        if item.get(decision_key) == i.get(decision_key):
                                                            logger.info("Value: {} for Key: '{}' matched, skipping".format(i.get(decision_key), decision_key))
                                                            flag = False
                                                            break
                                                        else:
                                                            flag = True
                                            if flag:
                                                # avoid appending same account in the account list
                                                if item not in v:
                                                    logger.info("(Level 2) Adding new {} > {}: {}".format(type(item).__name__,decision_key, item.get(decision_key)))
                                                    # append new account to core_account list
                                                    v.append(item)
                                                    logger.debug(existing)
    return existing


# Iterate through the second level keys (value = string) and add them if not found in the existing manifest file
def update_level_two_list_of_str(existing, add_on, level_one_dct_key, decision_key):
    if add_on.get(level_one_dct_key):
        for add_on_key_level_one_list in add_on.get(level_one_dct_key):
            for key, value in add_on_key_level_one_list.items():
                logger.debug(value)
                if isinstance(value, list):
                    logger.debug(value)
                    for item in value:
                        if isinstance(item, str):
                            logger.debug(item)
                            if existing.get(level_one_dct_key):
                                for existing_key_level_one_list in existing.get(level_one_dct_key):
                                    if add_on_key_level_one_list.get(decision_key) == existing_key_level_one_list.get(decision_key):
                                        if add_on_key_level_one_list.get(decision_key) == existing_key_level_one_list.get(decision_key):
                                            for k, v in existing_key_level_one_list.items():
                                                logger.debug(v)
                                                if isinstance(v, list):
                                                    logger.debug(v)
                                                    for i in v:
                                                        if isinstance(i, str):
                                                            logger.debug(item)
                                                            logger.debug(i)
                                                            if item != i:
                                                                if item not in v:
                                                                    logger.info(
                                                                    "(Level 2) Adding new {} in {} name: {}".format(type(item).__name__,type(v).__name__, k))
                                                                    v.append(item)
                                                                    logger.debug(existing)
        return existing


# Iterate through the third level keys and add them if not found in the existing manifest file
def update_level_three_list(existing, add_on, level_one_dct_key, decision_key, level_three_dct_key):
    if add_on.get(level_one_dct_key):
        for add_on_key_level_one_list in add_on.get(level_one_dct_key):
            for key, value in add_on_key_level_one_list.items():
                logger.debug(value)
                if isinstance(value, list):
                    logger.debug(value)
                    for item in value:
                        if isinstance(item, dict):
                            logger.debug(item)
                            # extracted list of account names in the add_on manifest
                            if item.get(level_three_dct_key):
                                logger.debug(item.get(level_three_dct_key))
                                for resource in item.get(level_three_dct_key):
                                    logger.debug(resource.get(decision_key))
                                    # iterating through existing manifest to add if new core account is added
                                    if existing.get(level_one_dct_key):
                                        for existing_key_level_one_list in existing.get(level_one_dct_key):
                                            if add_on_key_level_one_list.get(decision_key) == existing_key_level_one_list.get(decision_key):
                                                for k, v in existing_key_level_one_list.items():
                                                    logger.debug(v)
                                                    if isinstance(v, list):
                                                        logger.debug(v)
                                                        for i in v:
                                                            flag = False
                                                            if isinstance(i, dict):
                                                                if item.get(decision_key) == i.get(decision_key):
                                                                    logger.debug(i)
                                                                    logger.debug(type(i))
                                                                    logger.debug(i.get(level_three_dct_key))
                                                                    if i.get(level_three_dct_key):
                                                                        for r in i.get(level_three_dct_key):
                                                                            logger.debug(r.get(decision_key))
                                                                            if resource.get(decision_key) == r.get(decision_key):
                                                                                logger.warning("Duplicate core_resource name {} found in {}, skipping".format(r.get(decision_key), add_on_manifest_file_path))
                                                                                flag = False
                                                                                break
                                                                            else:
                                                                                flag = True
                                                                    else:
                                                                        # Handing the case if core_resources in master manifest is empty list '[ ]'
                                                                        logger.info("Core resources value is an empty list. Setting flag = True to append add_on list.")
                                                                        flag = True
                                                            if flag:
                                                                # avoid appending same account
                                                                # in the account list
                                                                if resource not in i.get(level_three_dct_key):
                                                                    logger.info("(Level 3) Adding new {} > {}: {}".format(type(resource).__name__, decision_key, resource.get(decision_key)))
                                                                    # append new account to core_account list
                                                                    i.get(level_three_dct_key).append(resource)
                                                                    logger.debug(existing)
        return existing


def _reload(add_on, original):
    # return original manifest if updated manifest is None
    update = add_on if add_on is not None else original
    return update


def _json_to_yaml(json, filename):
    # Convert json to yaml
    # logger.info(json)
    yml = yaml.safe_dump(json, default_flow_style=False, indent=2)
    # print(yml)

    # create new manifest file
    file = open(filename, 'w')
    file.write(yml)
    file.close()


def update_organizational_units_accounts(add_on, original):
    level_1_key = 'organizational_units'
    decision_key = 'name'
    level_3_key = 'core_resources'

    # process new org unit addition
    updated_manifest = update_level_one_list(original, add_on, level_1_key, decision_key)
    original = _reload(updated_manifest, original)

    # process new account addition
    updated_manifest = update_level_two_list_of_dct(original, add_on, level_1_key, decision_key)
    original = _reload(updated_manifest, original)

    # process new product addition
    updated_manifest = update_level_two_list_of_str(original, add_on, level_1_key, decision_key)
    original = _reload(updated_manifest, original)

    # process new core resource addition
    updated_manifest = update_level_three_list(original, add_on, level_1_key, decision_key, level_3_key)
    original = _reload(updated_manifest, original)

    return original


def update_scp_policies(add_on, original):
    level_1_key = 'organization_policies'
    decision_key = 'name'

    # process new scp policy addition
    updated_manifest = update_level_one_list(original, add_on, level_1_key, decision_key)
    original = _reload(updated_manifest, original)

    # process adding new OU in existing scp
    updated_manifest = update_level_two_list_of_str(original, add_on, level_1_key, decision_key)
    original = _reload(updated_manifest, original)

    return original


def update_service_catalog_portfolios_products(add_on, original):
    level_1_key = 'portfolios'
    decision_key = 'name'

    # process new portfolio addition
    updated_manifest = update_level_one_list(original, add_on, level_1_key, decision_key)
    original = _reload(updated_manifest, original)

    # process new product addition
    updated_manifest = update_level_two_list_of_dct(original, add_on, level_1_key, decision_key)
    original = _reload(updated_manifest, original)

    return original


def update_baseline_resources(add_on, original):
    level_1_key = 'baseline_resources'
    decision_key = 'name'

    # process new baseline addition
    updated_manifest = update_level_one_list(original, add_on, level_1_key, decision_key)
    original = _reload(updated_manifest, original)

    return original


def main():
    manifest = yaml.safe_load(open(master_manifest_file_path))
    logger.debug(manifest)

    add_on_manifest = yaml.safe_load(open(add_on_manifest_file_path))
    logger.debug(add_on_manifest)

    manifest = update_organizational_units_accounts(add_on_manifest, manifest)

    manifest = update_scp_policies(add_on_manifest, manifest)

    manifest = update_service_catalog_portfolios_products(add_on_manifest, manifest)

    manifest = update_baseline_resources(add_on_manifest, manifest)

    _json_to_yaml(manifest, output_manifest_file_path)

if __name__ == "__main__":
    if len(sys.argv) > 3:
        master_manifest_file_path = sys.argv[1]
        add_on_manifest_file_path = sys.argv[2]
        output_manifest_file_path = sys.argv[3]
        main()
    else:
        print('No arguments provided. Please provide the existing and new manifest files names.')
        print('Example: merge_manifest.py <ORIG-FILE-NAME> <ADD-ON-FILE-NAME> <NEW-FILE-NAME>')
        sys.exit(2)
