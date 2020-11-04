#!/bin/bash
# strict mode
set -euo pipefail
IFS=$'\t\n'

# safe relative calls
BASE="$(cd $(dirname "$0") && pwd)"

DIR_ZIP="${BASE}/zip"
mkdir -p "${DIR_ZIP}"
pushd "${DIR_ZIP}"

BUCKET_PREFIX="https://s3.amazonaws.com/solutions-reference/aws-landing-zone"
DIR_ADD_ON="add-on"

ZONE_VERSION="v1.0.2"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
popd

ZONE_VERSION="v2.0"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-add-on-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm-cr.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-handshake-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-launch-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-v2-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-validation.zip"

mkdir -p "${DIR_ADD_ON}"
pushd "${DIR_ADD_ON}"
# typo is expected for so[l]ution
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-soution.template"
popd
popd

ZONE_VERSION="v2.0.1"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-add-on-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm-cr.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-handshake-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-launch-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-v201-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-validation.zip"

mkdir -p "${DIR_ADD_ON}"
pushd "${DIR_ADD_ON}"
# typo is expected for so[l]ution
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-soution.template"
popd
popd

ZONE_VERSION="v2.0.2"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-add-on-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm-cr.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-handshake-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-launch-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-validation.zip"

mkdir -p "${DIR_ADD_ON}"
pushd "${DIR_ADD_ON}"
# typo is expected for so[l]ution
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-soution.template"
popd
popd

ZONE_VERSION="v2.0.3"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-add-on-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm-cr.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-handshake-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-launch-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-validation.zip"

mkdir -p "${DIR_ADD_ON}"
pushd "${DIR_ADD_ON}"
# typo is expected for so[l]ution
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-soution.template"
popd
popd

ZONE_VERSION="v2.1.0"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-add-on-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm-cr.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-handshake-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-launch-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-validation.zip"

mkdir -p "${DIR_ADD_ON}"
pushd "${DIR_ADD_ON}"
# typo is expected for so[l]ution
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-soution.template"
popd
popd

ZONE_VERSION="v2.2.0"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-add-on-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm-cr.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-handshake-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-launch-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-v22-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-validation.zip"

mkdir -p "${DIR_ADD_ON}"
pushd "${DIR_ADD_ON}"
# typo is expected for so[l]ution
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-soution.template"
popd
popd

ZONE_VERSION="v2.3.0"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-addon-publisher.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-add-on-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm-cr.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-handshake-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-launch-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-validation.zip"

mkdir -p "${DIR_ADD_ON}"
pushd "${DIR_ADD_ON}"
# typo is fixed for so[l]ution
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.template"
popd
popd

ZONE_VERSION="v2.3.1"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-addon-publisher.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-add-on-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm-cr.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-handshake-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-launch-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-validation.zip"

mkdir -p "${DIR_ADD_ON}"
pushd "${DIR_ADD_ON}"
# typo is fixed for so[l]ution
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.template"
popd
popd

ZONE_VERSION="v2.4.0"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-addon-publisher.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-add-on-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-acct-password-policy.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm-cr.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-baseline-resource.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-handshake-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-launch-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-validation.zip"

mkdir -p "${DIR_ADD_ON}"
pushd "${DIR_ADD_ON}"
# typo is fixed for so[l]ution
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.template"
popd
popd

ZONE_VERSION="v2.4.1"
mkdir -p "${ZONE_VERSION}"
pushd "${ZONE_VERSION}"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-initiation.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-addon-publisher.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-add-on-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-acct-password-policy.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-avm-cr.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-baseline-resource.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-config-deployer.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-handshake-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-launch-avm.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine-trigger.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-state-machine.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-configuration.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/aws-landing-zone-validation.zip"

mkdir -p "${DIR_ADD_ON}"
pushd "${DIR_ADD_ON}"
# typo is fixed for so[l]ution
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.template"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-ad-with-rdgw-ad-connector.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.zip"
curl --fail -LO "${BUCKET_PREFIX}/${ZONE_VERSION}/${DIR_ADD_ON}/aws-centralized-logging-solution.template"
popd
popd


# DIR_ZIP
popd
