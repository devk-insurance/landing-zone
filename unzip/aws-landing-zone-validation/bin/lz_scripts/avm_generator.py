

from lib.logger import Logger
from lib.ssm import SSM
from lib.manifest import Manifest
from lib.helper import get_available_regions
import sys
import os.path
import jinja2
import uuid
import json


def _generate_template(portfolio, product, lambda_arn, uuid):
    region_list = get_available_regions('ec2')

    if os.path.isfile(os.path.join(manifest_folder, product.skeleton_file)):
        portfolio_index = manifest.portfolios.index(portfolio)
        product_index = manifest.portfolios[portfolio_index].products.index(product)
        product_name = manifest.portfolios[portfolio_index].products[product_index].name
        logger.info("Generating the product template for {} from {}".format(product_name, os.path.join(manifest_folder,product.skeleton_file)))
        j2loader = jinja2.FileSystemLoader(manifest_folder)
        j2env = jinja2.Environment(loader=j2loader)
        j2template = j2env.get_template(product.skeleton_file)
        j2result = j2template.render(manifest=manifest,
                                     portfolio_index=portfolio_index,
                                     product_index=product_index,
                                     lambda_arn=lambda_arn,
                                     uuid=uuid,
                                     regions=region_list)
        generated_avm_template = os.path.join(manifest_folder, product.skeleton_file+".template")
        template_copy = os.path.join(manifest_folder, product.skeleton_file+".template.copy")
        logger.info("Writing the generated product template to {}".format(generated_avm_template))
        with open(generated_avm_template, "w") as fh, open(template_copy, "w") as copy:
            fh.write(j2result)
            copy.write(j2result)
        return generated_avm_template
    else:
        logger.error("Missing skeleton_file for portfolio:{} and product:{} in Manifest file".format(portfolio.name,
                                                                                                     product.name))
        sys.exit(1)


def _read_file(file):
    with open(file) as f:
        return json.load(f)


def _write_file(k, v, file, mode='w'):
    d = {k: v}
    logger.info("Writing to file: {} with key: {} and value: {}".format(file, k, v))
    with open(file, mode) as outfile:
        json.dump(d, outfile, indent=2)
    outfile.close()


def _setup(file, key):
    if os.path.isfile(file):
        logger.info('File - {} exists'.format(file))
    else:
        logger.info('Creating file - {}'.format(file))
        value = list()
        _write_file(key, value, file)


def _is_dict_same(orig_list, add_dict):
    for item in orig_list:
        if item == add_dict:
            return True
    else:
        return False


def _append(file_name, key):
    append_dict = {
        "template": avm_template,
        "parameter": avm_parameter
    }

    _setup(file_name, key)
    # read data
    data = _read_file(file_name)
    # process data
    logger.info("Appending new files into list.")
    json_list = data.get(key)
    logger.info(json_list)
    if not _is_dict_same(json_list, append_dict):
        logger.info('APPENDING DICT')
        logger.info(append_dict)
        json_list.append(append_dict)
        logger.info('NEW LIST')
        logger.info(json_list)
        _write_file(key, json_list, file_name)
    else:
        logger.info('Already exists in the file, skipping...')


def process():
    if master_avm_template.lower() == 'yes':
        _append(master_avm_files, 'master')
    elif master_avm_template.lower() == 'no':
        _append(add_on_avm_files, 'add_on')
    else:
        logger.error("master_avm_template does not have valid value. Allowed values: 'yes' or 'no'")
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) > 4:
        log_level = sys.argv[1]
        lambda_arn_param = sys.argv[2]
        manifest_file_path = sys.argv[3]
        master_avm_template = sys.argv[4]

        logger = Logger(loglevel=log_level)
        TEMPLATE_KEY_PREFIX = '_aws_landing_zone_templates_staging'
        ssm = SSM(logger)
        logger = logger
        uuid = uuid.uuid4()
        manifest = Manifest(manifest_file_path)
        manifest_file_name = 'manifest.yaml' if master_avm_template.lower() == 'yes' else 'add_on_manifest.yaml'
        logger.info("Manifest File Name: {}".format(manifest_file_name))
        manifest_folder = manifest_file_path[:-len(manifest_file_name)]
        lambda_arn = ssm.get_parameter(lambda_arn_param)
        master_avm_files = 'master_avm_files.json'
        add_on_avm_files = 'add_on_avm_files.json'
        file_mode = 'w'

        for portfolio in manifest.portfolios:
            for product in portfolio.products:
                if product.product_type.lower() == 'baseline':
                    avm_template = _generate_template(portfolio, product, lambda_arn, uuid)
                    avm_parameter = os.path.join(manifest_folder, product.parameter_file)
                    process()
    else:
        print('No arguments provided. Please provide the existing and new manifest files names.')
        print('Example: avm_generator.py <LOG-LEVEL> <GET-LAMBDA-ARN-SSM-KEY> <MANIFEST-FILE-PATH> <MASTER-MANIFEST-FILE>')
        sys.exit(2)
