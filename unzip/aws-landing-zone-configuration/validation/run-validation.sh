#!/bin/bash
# $1 is the $ARTIFACT_BUCKET from CodePipeline
python3.4 -c 'import yaml,sys;yaml.safe_load(sys.stdin)' < manifest.yaml
if [ $? -ne 0 ]
then
  echo "Manifest file is not valid YAML"
  exit 1
fi

echo "Manifest file is a valid YAML"

# Validate manifest schema
pykwalify -d manifest.yaml -s validation/manifest.schema.yaml
if [ $? -ne 0 ]
then
  echo "Manifest file failed schema validation"
  exit 1
fi

echo "Manifest file validated against the schema successfully"

# check each file in the manifest to make sure it exists
export current=`pwd`
check_files=$(grep '_file:' < manifest.yaml | grep -v '^ *#' | tr -s ' ' | cut -d ' ' -f 3)
  for f in $check_files ; do
  if [ -f $current'/'$f ]; then
    echo "File $f exists"
  else
    echo "File $f does not exist"
    exit 1
  fi
done
# run aws cloudformation validate-template and cfn_nag_scan on all templates
cd templates
export deployment_dir=`pwd`
echo "$deployment_dir/"
for i in $(find . -type f | grep '.template' | grep -v '.j2' | sed 's/^.\///') ; do
    echo "Running aws cloudformation validate-template on $i"
    aws s3 cp $deployment_dir/$i s3://$1/validate/templates/$i
    aws cloudformation validate-template --template-url https://s3.$AWS_REGION.amazonaws.com/$1/validate/templates/$i --region $AWS_REGION
    if [ $? -ne 0 ]
    then
      echo "CloudFormation template failed validation - $i"
      exit 1
    fi
    # delete objects in bucket
    aws s3 rm s3://$1/validate/templates/$i
    echo "Running cfn_nag_scan on $i"
    cfn_nag_scan --input-path $deployment_dir/$i
    if [ $? -ne 0 ]
    then
      echo "CFN Nag failed validation - $i"
      exit 1
    fi
done

# run json validation on all the parameter files

cd ../parameters
export deployment_dir=`pwd`
echo "$deployment_dir/"
for i in $(find . -type f | grep '.json' | grep -v '.j2' | sed 's/^.\///') ; do
    echo "Running json validation on $i"
    python -m json.tool < $i
    if [ $? -ne 0 ]
    then
      echo "CloudFormation parameter file failed validation - $i"
      exit 1
    fi
done
cd ..
