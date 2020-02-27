
#!/bin/bash

for region in "ap-south-1" "eu-west-3" "eu-west-2" "eu-west-1" "ap-northeast-2" "ap-northeast-1" "sa-east-1" "ca-central-1" "ap-southeast-1" "ap-southeast-2" "eu-central-1" "us-east-1" "us-east-2" "us-west-1" "us-west-2";
do
    echo ""
    echo "---------- list-detectors output $region ----------"
    aws guardduty list-detectors --region $region;
    export PYTHONIOENCODING=utf8
    detector_id=`aws guardduty list-detectors --region $region | python -c "import sys, json; print json.load(sys.stdin)['DetectorIds'][0]"`
    if [ $detector_id != "" ]; then
        echo "Found GuardDuty Detector Id: $detector_id ... deleting  in $region"
        aws guardduty delete-detector --detector-id  $detector_id --region $region
    else
        echo "No detector ID found ... skipping $region region"
    fi
done