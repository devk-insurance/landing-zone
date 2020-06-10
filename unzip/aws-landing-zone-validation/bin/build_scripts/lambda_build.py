###################################################################################################################### 
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    # 
#  Licensed under the Apache License Version 2.0 (the "License"). You may not use this file except in compliance     # 
#  with the License. A copy of the License is located at                                                             # 
#                                                                                                                    # 
#      http://www.apache.org/licenses/                                                                               # 
#                                                                                                                    # 
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES # 
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    # 
#  and limitations under the License.                                                                                # 
######################################################################################################################

#!/usr/bin/env python
import os
import sys
import zipfile


def zip_function(zip_file_name, function_path, output_path, exclude_list=[], include_list=[]):
    """
    create a zip file:
    - Name: zip_file_name
    - source: function_path
    - output: output_path
    - include files: include_list
    - exclude files: exclude_list

    Note that when include_list is specified, files in exclude_list are excluded
    """
    def _write_path(zip_file, path):
        """
        add all files in a directory
        """
        for folder, subs, files in os.walk('./' + path):
            for filename in files:
                fpath = os.path.join(folder, filename)
                if not any(x in fpath for x in exclude_list):
                    print(fpath)
                    zip_file.write(fpath)

    orig_path = os.getcwd()
    os.chdir(output_path)
    function_path = os.path.normpath(function_path)
    zip_name = zip_file_name + '.zip'
    if os.path.exists(zip_name):
        try:
            os.remove(zip_name)
        except OSError:
            pass

    zip_file = zipfile.ZipFile(zip_name, mode='a')
    os.chdir(function_path)
    print('\n Following files will be zipped in {} and saved in the deployment/regional-s3-assets folder. \n--------------'
          '------------------------------------------------------------------------'.format(zip_name))
    if include_list:
        for include_file in include_list:
            print(include_file)
            if include_file[-1:] == '/':
                _write_path(zip_file, include_file)
            else:
                if not include_file in exclude_list:
                    zip_file.write(include_file)

    elif exclude_list:
        for folder, subs, files in os.walk('.'):
            for filename in files:
                fpath = os.path.join(folder, filename)
                if fpath.endswith('.py') or fpath.endswith('.sh') or '.so' in fpath or 'cacert.pem' in fpath or 'schema' in fpath:
                    if not any(x in fpath for x in exclude_list):
                        print(fpath)
                        zip_file.write(fpath)
    

    zip_file.close()
    os.chdir(orig_path)
    return


def make_dir(directory):
    # if exist skip else create dir
    try:
        os.stat(directory)
        print("\n Directory {} already exist... skipping".format(directory))
    except:
        print("\n Directory {} not found, creating now...".format(directory))
        os.makedirs(directory)


def main(argv):
    # if condition changes the path this script runs from command line '$ python source/bin/build_scripts/lambda_build.py'
    if 'bin' not in os.getcwd():
        os.chdir('./source/bin')

    # Create Lambda Zip
    function_path = '../../source'
    output_path = '../../deployment/regional-s3-assets/'
    make_dir(output_path)
    base_exclude = ['power-shell', 'egg', 'requirement', 'setup', 'scratch', 'dist-info']
    print(argv)
    if 'help' in argv:
        print('Help: Please provide either or all the arguments as shown in the example below.')
        print('lambda_build.py avm_cr_lambda state_machine_lambda trigger_lambda deployment_lambda')
        sys.exit(2)
    else:
        for arg in argv:
            include = []
            exclude = []
            print('\n Building {} \n ==========================='.format(arg))
            if arg == 'avm_cr_lambda':
                zip_file_name = 'aws-landing-zone-avm-cr'
                exclude = ['bin', 'update_acct_password_policy', 'config_deployer', 'state_machine_', 'jinja2', 'simplejson', 'markupsafe', 'yaml', 'yorm',
                           'validation', 'manifest_handler', 'handshake_sm', 'add_on_config_deployer', 'launch_avm',
                           'publish', 'launch_baseline_resources']
            elif arg == 'state_machine_lambda':
                zip_file_name = 'aws-landing-zone-state-machine'
                exclude = ['bin', 'update_acct_password_policy', 'config_deployer', 'custom_resource', 'trigger', 'jinja2', 'simplejson', 'markupsafe',
                           'yaml', 'yorm', 'netaddr', 'validation', 'manifest_handler', 'handshake_sm',
                           'launch_baseline_resources', 'add_on_config_deployer', 'launch_avm', 'publish']
            elif arg == 'trigger_lambda':
                zip_file_name = 'aws-landing-zone-state-machine-trigger'
                exclude = ['bin', 'update_acct_password_policy', 'config_deployer', 'custom_resource', 'state_machine_handler', 'state_machine_router',
                           'netaddr', 'validation', 'manifest_handler', 'handshake_sm', 'add_on_config_deployer',
                           'launch_baseline_resources', 'launch_avm', 'publish']
            elif arg == 'deployment_lambda':
                zip_file_name = 'aws-landing-zone-config-deployer'
                exclude = ['bin', 'yorm', 'yaml', 'update_acct_password_policy', 'custom_resource', 'state_machine_', 'netaddr', 'validation',
                           'manifest_handler', 'handshake_sm', 'add_on_config_deployer', 'launch_avm',
                           'launch_baseline_resources', 'publish']
            elif arg == 'add_on_deployment_lambda':
                zip_file_name = 'aws-landing-zone-add-on-config-deployer'
                exclude = ['bin', 'yorm', 'yaml', 'update_acct_password_policy', 'custom_resource', 'state_machine_', 'netaddr', 'validation',
                           'manifest_handler', 'handshake_sm', 'launch_avm', 'launch_baseline_resources', 'publish']
            elif arg == 'build_scripts':
                zip_file_name = 'aws-landing-zone-validation'
                # DO NOT INCLUDE 'yaml' to the exclude list or else it will skip to include manifest.schema.yaml which will cause the build stage to fail
                exclude = ['update_acct_password_policy', 'config_deployer', 'state_machine_', 'simplejson', 'netaddr','yorm', 'jinja2', 'handshake_sm',
                           'markupsafe', 'custom_resource', 'certifi', 'chardet', 'idna', 'launch_baseline_resources', 'requests', 'urllib3', 'add_on_config_deployer',
                           'launch_avm', 'publish']
            elif arg == 'handshake_sm_lambda':
                zip_file_name = 'aws-landing-zone-handshake-state-machine'
                exclude = ['bin', 'update_acct_password_policy', 'config_deployer', 'state_machine_', 'custom_resource', 'trigger', 'jinja2', 'simplejson', 'markupsafe',
                           'yaml', 'yorm', 'netaddr', 'add_on_config_deployer', 'launch_avm', 'publish',
                           'launch_baseline_resources',]
            elif arg == 'launch_avm':
                zip_file_name = 'aws-landing-zone-launch-avm'
                exclude = ['bin', 'update_acct_password_policy', 'config_deployer', 'custom_resource', 'trigger', 'add_on_config_deployer', 'state_machine_router',
                           'netaddr', 'validation', 'manifest_handler', 'handshake_sm', 'publish', 'launch_baseline_resources']
            elif arg == 'baseline_resources':
                zip_file_name = 'aws-landing-zone-baseline-resource'
                exclude = ['bin', 'update_acct_password_policy', 'config_deployer', 'custom_resource', 'trigger', 'add_on_config_deployer',
                           'netaddr', 'validation', 'manifest_handler', 'handshake_sm', 'publish', 'launch_avm',
                           'state_machine_handler', 'state_machine_router']
            elif arg == 'add_on_publisher':
                zip_file_name = 'aws-landing-zone-addon-publisher'
                exclude = ['update_acct_password_policy', 'config_deployer', 'state_machine_',
                           'simplejson', 'netaddr','yorm', 'jinja2', 'handshake_sm', 'yaml',
                           'validation', 'bin', 'markupsafe', 'custom_resource', 'certifi',
                           'chardet', 'idna', 'requests', 'urllib3', 'add_on_config_deployer',
                           'launch_baseline_resources', 'launch_avm']
            elif arg == 'acct_password_policy':
                zip_file_name = 'aws-landing-zone-acct-password-policy'
                include = ['update_acct_password_policy.py', 'lib/logger.py', 'lib/crhelper.py', 
                           'lib/datetime_encoder.py', 'requests/', 'chardet/', 'certifi/', 'idna/']
                exclude = []

            else:
                print('Invalid argument... Please provide either or all the arguments as shown in the example below.')
                print('lambda_build.py avm_cr_lambda state_machine_lambda trigger_lambda deployment_lambda add_on_deployment_lambda')
                sys.exit(2)

            lambda_exclude = base_exclude + exclude

            zip_function(zip_file_name, function_path, output_path, lambda_exclude, include)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1:])
    else:
        print('No arguments provided. Please provide any combination of OR all 4 arguments as shown in the example below.')
        print('lambda_build.py avm_cr_lambda state_machine_lambda trigger_lambda deployment_lambda add_on_deployment_lambda')
        print('Example 2:')
        print('lambda_build.py avm_cr_lambda state_machine_lambda trigger_lambda')
        print('Example 3:')
        print('lambda_build.py avm_cr_lambda state_machine_lambda')
        print('Example 4:')
        print('lambda_build.py avm_cr_lambda')
        sys.exit(2)
