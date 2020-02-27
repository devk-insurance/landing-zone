#!/usr/bin/env python
import sys
import uuid
sys.path.insert(0, '../..')
import os
import types
import json
import jinja2
import yaml
from lib.manifest import Manifest

mf_file = "manifest.yaml.j2"
function_path = os.path.normpath('../../../deployment/aws_landing_zone_configuration')

parameters = {
     "region": "us-east-1",
     "core_ou": "core",
     "ou_list": ["application", "tools", "org:prod", "org:dev:users"],
     "master_email": "",
     "security_email": "",
     "logging_email": "",
     "shared_services_email": "",
     "lock_down_stack_sets_role": "No",
     "ad_region": "us-east-1",
     "ad_connector_region": "us-east-1",
     "enable_all_regions": "No",
     "nested_ou_delimiter": "':'"
}

def generate_manifest():
    print("====== Generating Manifest.yaml using Jinja2 ======")
    print("Generating the manifest.yaml from {}".format(os.path.join(function_path, mf_file)))
    j2loader = jinja2.FileSystemLoader(function_path)
    j2env = jinja2.Environment(loader=j2loader)
    j2template = j2env.get_template(mf_file)
    j2result = j2template.render(parameters)
    print("Writing the manifest.yaml to {}".format(os.path.join(function_path, mf_file[0:-3])))
    with open(os.path.join(function_path, mf_file[0:-3]), "w") as fh:
        fh.write(j2result)
    # Now try loading the generated manifest file to see if its valid YAML or not
    try:
        manifest = Manifest(os.path.join(function_path, mf_file[0:-3]))
        print("====== Successfully generated Manifest.yaml, Congratulations ======")
    except Exception as e:
        print("====== INVALID YAML in Manifest.yaml, Please check the YAML formatting ======")
        print(str(e))
        print("***** INVALID YAML in Manifest.yaml, Please check the YAML formatting *****")



if __name__ == '__main__':
    generate_manifest()
