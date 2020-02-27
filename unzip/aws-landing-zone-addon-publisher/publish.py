#!/usr/bin/python
# -*- coding: utf-8 -*-
###################################################################################################################### 
#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           # 
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

# publish.py
# Once new Add-on(s) will be published by the AWS Solutions team
# This lambda, running on a schedule by CloudWatch, will check the version in
# the template and perform any required stack updates to update portfolio and notify customers to review new products.
# This lambda will _not_ update the provisioned products.

from botocore.exceptions import ClientError
from lib.logger import Logger
from lib.cloudformation import Stacks
from lib.sns import SNS
import os
import time
import inspect

NOCHANGE = "No Change"
UPDATE = "Updated"
PROGRESS = "Update In Progress"
ADDON_TEMPLATE = os.getenv('AddonTemplate')
ADDON_STACK = os.getenv('AddonStack')
ADDON_TOPIC = os.getenv('AddonTopic')
RELEASE_NOTES_PAGE = os.getenv('ReleaseNotes')
# CloudFormation Stack Status, polling units in seconds
POLL_FREQUENCY = 15
POLL_TIMEOUT = 720

log_level = os.getenv('log_level')
logger = Logger(loglevel=log_level)


# Lambda will read the s3 source location from environment variables
# Find Add-on Version in template description
def get_version(response):
    try:
        version = response['Description']
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        return 'NOT_FOUND'
    return version


# Find the stack update status
def get_stack_status(response):
    try:
        status = response['Stacks'][0]['StackStatus']
    except Exception as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        return 'NOT_FOUND'
    return status


# Check to see if a new version has been published
def run_update():
    logger.info('>>> Checking For Updates')
    logger.info('Template: ' + ADDON_TEMPLATE)
    logger.info('Stack: ' + ADDON_STACK)
    logger.info('Topic: ' + ADDON_TOPIC)

    if ADDON_TEMPLATE is None:
        logger.error('No source template specified.')
        return NOCHANGE

    if ADDON_STACK is None:
        logger.error('No Stack ID specified.')
        return NOCHANGE

    try:
        cf_client = Stacks(logger)

        logger.info('ADDON_STACK: ' + ADDON_STACK)
        logger.info('ADDON_TEMPLATE: ' + ADDON_TEMPLATE)

        # Check version of CloudFormation stack
        cur_meta = cf_client.get_stack_summary(ADDON_STACK)

        cur_version = get_version(cur_meta)
        logger.info('Current Version: ' + cur_version)

        # Check version of update template
        new_meta = cf_client.get_template_summary(ADDON_TEMPLATE)
        new_version = get_version(new_meta)
        logger.info('New Version: ' + new_version)

        # lower works for case insensitive compare except greek letters
        if cur_version.lower() == new_version.lower():
            return NOCHANGE

        # ready for update
        logger.info('Running Update')
        return update_addons(cf_client, new_version, cur_meta)

    except ClientError as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)

    return NOCHANGE


# Run an update
def update_addons(cf_client, version, cur_meta):

    logger.info('>>> Update Stack')
    logger.info('Version: ' + version)
    try:
        # Parse the params from the metadata and set the update to
        # keep the existing values (not defaults)
        params = cur_meta['Parameters']
        parameters = []
        for param in params:
            d = {'ParameterKey': param['ParameterKey'], 'UsePreviousValue': True}
            parameters.append(d)

        # Check initial stack status
        # If status is in any state besides *COMPLETE
        # then DON'T try to update. Send user a message and try again tomorrow
        response = cf_client.describe_stacks(ADDON_STACK)
        status = get_stack_status(response)

        if not status.endswith('COMPLETE'):
            logger.error('Unable to update stack: ' + ADDON_STACK)
            msg = "%s %s%s" % ('AWS Landing Zone stack status:', status,
                               '. Please review the stack events for details. Will retry tomorrow.')
            notify_users(msg)
            return NOCHANGE

        cf_client.update_stack(ADDON_STACK,
                               parameters,
                               ADDON_TEMPLATE,
                               ['CAPABILITY_NAMED_IAM'])

        # Check the stack status for specified frequency and timeout
        logger.info('Starting update for version: ' + version)
        seconds = 0
        while seconds < POLL_TIMEOUT:
            time.sleep(POLL_FREQUENCY)
            response = cf_client.describe_stacks(ADDON_STACK)
            status = get_stack_status(response)
            if status == 'NOT_FOUND':
                logger.error('No stack found: ' + ADDON_STACK)
                msg = "%s %s %s" % ('Unable to check the update status.', 'AWS Landing Zone stack status:', status)
                notify_users(msg)
                return NOCHANGE
            elif status == 'UPDATE_COMPLETE':
                logger.info('Stack has been updated: ' + ADDON_STACK)
                msg = "%s %s %s%s %s %s %s" % ('New and Updated Add-On(s) are available in the Add-On Portfolio. \nStack Description:',
                                               version, '\nPlease see the release notes for details.\n',
                                               RELEASE_NOTES_PAGE,
                                               '\nAWS Landing Zone stack status: UPDATE_COMPLETE. The update stack took',
                                               str(seconds+POLL_FREQUENCY), 'seconds to update.')
                notify_users(msg)
                return UPDATE
            else:
                logger.info('Polling Stack Status: ' + status)

            seconds += POLL_FREQUENCY
            msg = "%s %s %s %s %s" % ('Polled', str(seconds), 'of', str(POLL_TIMEOUT), 'seconds.')
            logger.info(msg)

        # Stack still updating after polling, send message to check manually
        msg = "%s %s %s %s %s %s" % ('The update poller timed out. AWS Landing Zone stack could not update within', str(POLL_TIMEOUT),
                                     'seconds.',
                                     '\nPlease review the events for the stack to validate if it successfully updated.',
                                     '\nStack Description: ', version)
        notify_users(msg)
        return PROGRESS

    except ClientError as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)
        return NOCHANGE


# Post messages to our message queue. Interested users will be subscribed.
def notify_users(msg):
    logger.info('>>> Notifying users with message: ' + msg)

    if ADDON_TOPIC in (None, ''):
        logger.error('No update notification topic specified. Cannot notify users.')
        return False

    try:
        sns_client = SNS(logger)
        sns_client.publish(ADDON_TOPIC, msg,
                           'AWS Landing Zone Add-On(s) Update')
        logger.info('>>> Notified Users')
    except ClientError as e:
        message = {'FILE': __file__.split('/')[-1], 'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
        logger.exception(message)

    return True


# the equivalent of "main()" for a lambda
def lambda_handler(event, context):
    logger.info(">>>>>> Running Publisher")
    result = run_update()
    logger.info("Execution: " + result)
    logger.info(">>>>>> Publishing Complete")

    return True

if __name__ == '__main__':
    lambda_handler("", "")
