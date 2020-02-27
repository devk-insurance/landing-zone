######################################################################################################################
#  Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://aws.amazon.com/asl/                                                                                    #
#                                                                                                                    #
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

# !/bin/python

from lib.s3 import S3
from lib.logger import Logger
import jinja2
import os
from pathlib import Path
import json
import inspect
import zipfile
from hashlib import md5
from lib.crhelper import cfn_handler
import shutil
import errno

# initialise logger
log_level = 'info' if os.environ.get('log_level') is None else os.environ.get('log_level')
logger = Logger(loglevel=log_level)
init_failed = False

def unzip_function(zip_file_name, function_path, output_path):
    try:
        orig_path = os.getcwd()
        os.chdir(function_path)
        zip_file = zipfile.ZipFile(zip_file_name, 'r')
        zip_file.extractall(output_path)
        zip_file.close()
        os.chdir(orig_path)
        return
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise


def find_replace(function_path, file_name, destination_file, parameters):  # , find_replace):
    try:

        j2loader = jinja2.FileSystemLoader(function_path)
        j2env = jinja2.Environment(loader=j2loader)
        j2template = j2env.get_template(file_name)
        dictionary = {}
        for key, value in parameters.items():
            value = "\"%s\"" % value if "json" in file_name else value
            dictionary.update({key: value})
        logger.debug(dictionary)
        output = j2template.render(dictionary)
        with open(destination_file, "w") as fh:
            fh.write(output)
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise


def zip_function(zip_file_name, function_path, output_path, exclude_list = []):
    try:
        orig_path = os.getcwd()
        os.chdir(output_path)
        function_path = os.path.normpath(function_path)
        if os.path.exists(zip_file_name):
            try:
                os.remove(zip_file_name)
            except OSError:
                pass
        zip_file = zipfile.ZipFile(zip_file_name, mode='a')
        os.chdir(function_path)
        for folder, subs, files in os.walk('.'):
            for filename in files:
                file_path = os.path.join(folder, filename)
                if not any(x in file_path for x in exclude_list):
                    logger.debug(file_path)
                    zip_file.write(file_path)
        zip_file.close()
        os.chdir(orig_path)
        return
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise


def make_dir(directory):
    # if exist skip else create dir
    try:
        os.stat(directory)
        logger.info("Directory {} already exist... skipping".format(directory))
    except:
        logger.info("Directory {} not found, creating now...".format(directory))
        os.makedirs(directory)


def config_deployer(event, previous_event, RequestType = 'Create'):
    try:
        s3 = S3(logger)
        base_path = '/tmp/lz'

        # set variables
        source_bucket_name = event.get('bucket_config', {}).get('source_bucket_name')
        source_key_name = event.get('bucket_config', {}).get('source_s3_key')
        destination_bucket_name = event.get('bucket_config', {}).get('destination_bucket_name')
        destination_key_name = event.get('bucket_config', {}).get('destination_s3_key')
        add_on_zip_file_name = source_key_name.split("/")[-1] if "/" in source_key_name else source_key_name
        add_on_file_path = base_path + "/" + add_on_zip_file_name
        lzconfig_file_path = base_path + "/" + destination_key_name
        add_on_extract_path = base_path + "/" + 'add_on_extract'
        lzconfig_extract_path = base_path + "/" + 'lzconfig_extract'
        output_path = base_path + "/" + 'out'
        merge_add_on_flag = event.get('bucket_config', {}).get('merge_add_on')

        logger.info("add_on_zip_file_name: {}".format(add_on_zip_file_name))
        logger.info("destination_key_name: {}".format(destination_key_name))
        logger.info("merge_add_on_flag: {}".format(merge_add_on_flag))

        if RequestType == 'Create':
            # Download the Add-On ZIP from Solutions S3 bucket
            make_dir(base_path)
            s3.download_file(source_bucket_name, source_key_name, add_on_file_path)

            # Unzip the Add-On ZIP file
            unzip_function(add_on_zip_file_name, base_path, add_on_extract_path)

            # Find and replace the variable in user-input.yaml
            for item in event.get('find_replace'):
                f = item.get('file_name')
                filename, file_extension = os.path.splitext(f)
                destination_file_path = add_on_extract_path + "/" + filename if file_extension == '.j2' else add_on_extract_path + "/" + f
                find_replace(add_on_extract_path, f, destination_file_path, item.get('parameters'))

            # Zip the contents
            make_dir(output_path)
            zip_function(add_on_zip_file_name, add_on_extract_path, output_path)

            if (merge_add_on_flag.upper() == 'YES'):
                try:
                    # Download the LZ Configuration ZIP from Customer's S3 bucket
                    s3.download_file(destination_bucket_name, destination_key_name, lzconfig_file_path)
                except Exception as e:
                    message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                    error_message = "Check the S3 Bucket name: {} and Bucket Permissions. " \
                                    "Check if the file: {} exists inside the bucket.".format(destination_bucket_name,
                                                                                             destination_key_name)
                    logger.exception(message)
                    raise Exception(error_message)

                # Unzip the LZ Configuration ZIP file
                unzip_function(destination_key_name, base_path, lzconfig_extract_path)

                #Check if manifest.yaml exists at the root level
                if os.path.isfile(os.path.join(lzconfig_extract_path, 'manifest.yaml')):
                    lzconfig_add_on_path = lzconfig_extract_path + "/" + "add-on"
                #OR inside aws-landing-zone-configuration/manifest.yaml
                elif os.path.isfile(os.path.join(lzconfig_extract_path, 'aws-landing-zone-configuration', 'manifest.yaml')):
                    lzconfig_add_on_path = lzconfig_extract_path + "/" + "aws-landing-zone-configuration/add-on"

                make_dir(lzconfig_add_on_path)
                shutil.copyfile(output_path + "/" + add_on_zip_file_name, lzconfig_add_on_path + "/" + add_on_zip_file_name)

                # if previous_event exists - delete the old zip file from the landing zone config zip
                if previous_event is not None:
                    # old event variables - for update path
                    previous_source_key_name = previous_event.get('bucket_config', {}).get('source_s3_key')
                    previous_add_on_zip_file_name = previous_source_key_name.split("/")[
                        -1] if "/" in previous_source_key_name else previous_source_key_name
                    logger.info("Found old resource properties in the CFN event. Printing old resource properties.")
                    logger.info(previous_event)
                    my_file = Path(lzconfig_add_on_path + "/" + previous_add_on_zip_file_name)
                    logger.info("Searching for {} in the ALZ config zip contents".format(my_file))
                    if my_file.is_file():
                        logger.info("Found the old add-on zip file in the ALZ config zip, deleting the file")
                        os.remove(lzconfig_add_on_path + "/" + previous_add_on_zip_file_name)

                zip_function(destination_key_name, lzconfig_extract_path, output_path)
                # Upload the file in the customer S3 bucket
                local_file = output_path + "/" + destination_key_name
                remote_file = destination_key_name
                s3.upload_file(destination_bucket_name, local_file, remote_file)
            else:
                # Upload the file in the customer S3 bucket
                local_file = output_path + "/" + add_on_zip_file_name
                remote_file = add_on_zip_file_name
                s3.upload_file(destination_bucket_name, local_file, remote_file)
        elif RequestType == 'Delete':
            if (merge_add_on_flag.upper() == 'YES'):
                try:
                    make_dir(base_path)
                    # Download the LZ Configuration ZIP from Customer's S3 bucket
                    s3.download_file(destination_bucket_name, destination_key_name, lzconfig_file_path)
                except Exception as e:
                    message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
                    error_message = "Check the S3 Bucket name: {} and Bucket Permissions. " \
                                    "Check if the file: {} exists inside the bucket.".format(destination_bucket_name,
                                                                                             destination_key_name)
                    logger.exception(message)
                    raise Exception(error_message)

                # Unzip the LZ Configuration ZIP file
                unzip_function(destination_key_name, base_path, lzconfig_extract_path)

                #Check if manifest.yaml exists at the root level
                if os.path.isfile(os.path.join(lzconfig_extract_path, 'manifest.yaml')):
                    lzconfig_add_on_path = lzconfig_extract_path + "/" + "add-on"
                #OR inside aws-landing-zone-configuration/manifest.yaml
                elif os.path.isfile(os.path.join(lzconfig_extract_path, 'aws-landing-zone-configuration', 'manifest.yaml')):
                    lzconfig_add_on_path = lzconfig_extract_path + "/" + "aws-landing-zone-configuration/add-on"

                my_file = Path(lzconfig_add_on_path + "/" + add_on_zip_file_name)
                if my_file.is_file():
                    os.remove(lzconfig_add_on_path + "/" + add_on_zip_file_name)

                make_dir(output_path)
                zip_function(destination_key_name, lzconfig_extract_path, output_path)

                # Upload the file in the customer S3 bucket
                local_file = output_path + "/" + destination_key_name
                s3.upload_file(destination_bucket_name, local_file, destination_key_name)

        return None
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        raise
    finally:
        try:
            shutil.rmtree('/tmp/lz')  # delete directory
        except OSError as exc:
            if exc.errno != errno.ENOENT:  # ENOENT - no such file or directory
                raise


def create(event, context):
    """
    Runs on Stack Creation.
    As there is no real 'resource', and it will never be replaced,
    PhysicalResourceId is set to a hash of StackId and LogicalId.
    """
    s = '%s-%s' % (event.get('StackId'), event.get('LogicalResourceId'))
    physical_resource_id = md5(s.encode('UTF-8')).hexdigest()
    logger.info("physical_resource_id: {}".format(physical_resource_id))

    if event.get('ResourceType') == 'Custom::AddOnConfigDeployer':
        response = config_deployer(event.get('ResourceProperties'), event.get('OldResourceProperties'), 'Create')
        return physical_resource_id, response
    else:
        logger.error('No valid ResourceType found!')


def update(event, context):
    """
    Update is identical to Create
    """
    physical_resource_id = event.get('PhysicalResourceId')

    if event.get('ResourceType') == 'Custom::AddOnConfigDeployer':
        response = config_deployer(event.get('ResourceProperties'), event.get('OldResourceProperties'), 'Create')
        return physical_resource_id, response
    else:
        logger.error('No valid ResourceType found!')


def delete(event, context):
    """
    Delete capability is not required for this function.
    """
    physical_resource_id = event.get('PhysicalResourceId')
    if event.get('ResourceType') == 'Custom::AddOnConfigDeployer':
        response = config_deployer(event.get('ResourceProperties'), event.get('OldResourceProperties'), 'Delete')
        return physical_resource_id, response
    else:
        logger.error('No valid ResourceType found!')
    return


def lambda_handler(event, context):
    logger.info("<<<<<<<<<< AddOnConfigDeployer Event >>>>>>>>>>")
    logger.info(event)
    logger.debug(context)
    return cfn_handler(event, context, create, update, delete, logger, init_failed)
