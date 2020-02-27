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

from lib.logger import Logger
import jinja2
import os
import inspect
import yaml
import sys

# initialise logger
log_level = 'info'
logger = Logger(loglevel=log_level)

def find_replace(function_path, file_name, destination_file, parameters):
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


def update_add_on_manifest(event, path):
    extract_path = path
    exclude_j2_files = []

    # Find and replace the variable in Manifest file
    for item in event.get('input_parameters'):
        f = item.get('file_name')
        exclude_j2_files.append(f)
        filename, file_extension = os.path.splitext(f)
        destination_file_path = extract_path + "/" + filename if file_extension == '.j2' else extract_path + "/" + f
        find_replace(extract_path, f, destination_file_path, item.get('parameters'))

def generate_event(user_input_file, path):
    logger.info('Generating Event')
    user_input = yaml.safe_load(open(user_input_file))
    logger.info(user_input)
    update_add_on_manifest(user_input, path)

if __name__ == '__main__':
    if len(sys.argv) > 2:
        path = sys.argv[2]
        file_name = sys.argv[1]
        generate_event(file_name, path)
    else:
        print('Not enough arguments provided. Please provide the path and user input file names.')
        print('Example: merge_manifest.py <PATH-OF-FILES> <USER-INPUT-FILE-NAME>')
        sys.exit(2)
