#!/usr/bin/env python

import os,sys
# pykwalify imports
import pykwalify
from pykwalify.core import Core
from pykwalify.errors import SchemaError, CoreError

function_path = os.path.normpath('../../deployment/aws_landing_zone_framework')
if os.path.isfile(os.path.join(function_path, 'manifest.yaml')):
    source_f = os.path.join(function_path, 'manifest.yaml')
if os.path.isfile(os.path.join(function_path, 'manifest.schema.yaml')):
    schema_f = os.path.join(function_path, 'manifest.schema.yaml')

c = Core(source_file=str(source_f), schema_files=[str(schema_f)])
try:
    c.validate(raise_exception=True)
except SchemaError:
    print("Schema Error: ")
except:
    print("Unexpected error:", sys.exc_info()[0])
    raise