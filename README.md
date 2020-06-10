# landing-zone

Vendored copy of the AWS LandingZone solution using CloudFormation.

This repository contains the AWS LandingZone solution from version 1.0.2 until 2.4.0

## repository structure

The repository contains 2 directories, `unzip` and `zip`.

### zip

The `zip` directory contains the zip-files for the respective landing-zone-version. You can use the zip-files directly and unzip them in a place to work on them.

### unzip

The `unzip` directory contains the up-to-date landingzone files extracted from the zip-file of the respective landing-zone-version. Depending on the git-commit of this repositry/git tag, the `unzip` directorie's file-content changes. This way it is possible to track what are the actual file-changes between each landing-zone.

## download zip-files

You can download the zip-files yourself using the `downloadLandingZones.sh` shell-script. The script downloads all resources, including those who had typos.

