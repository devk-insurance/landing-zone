#!/usr/bin/env python

import boto3

def get_available_regions(service_name):
    """ Returns list of regions for the given AWS service.
    Example: ['ap-northeast-1', 'ap-northeast-2', 'ap-south-1', 'ap-southeast-1', 'ap-southeast-2',
     'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'sa-east-1', 'us-east-1',
      'us-east-2', 'us-west-1', 'us-west-2']
    """
    session = boto3.session.Session()
    return session.get_available_regions(service_name)

if __name__ == '__main__':
    service_name = 'guardduty'
    regions = get_available_regions(service_name)

    for region in regions:
        # Creating Boto Client
        client = boto3.client(service_name=service_name,
                              region_name=region)
        # List Detectors
        list_response = client.list_detectors()
        # Delete Detector
        for detector_id in list_response['DetectorIds']:
            if detector_id:
                print('Deleting detector id: {} in {}'.format(detector_id, region))
                delete_response = client.delete_detector(DetectorId=detector_id)
                print(delete_response)
            else:
                print('Existing detector not found in {}'.format(detector_id, region))
