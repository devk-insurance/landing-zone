##############################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.   #
#                                                                            #
#  Licensed under the Apache License, Version 2.0 (the "License").           #
#  You may not use this file except in compliance                            #
#  with the License. A copy of the License is located at                     #
#                                                                            #
#      http://www.apache.org/licenses/LICENSE-2.0                            #
#                                                                            #
#  or in the "license" file accompanying this file. This file is             #
#  distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY  #
#  KIND, express or implied. See the License for the specific language       #
#  governing permissions  and limitations under the License.                 #
##############################################################################
from manifest.stage_to_s3 import StageFile
from lib.logger import Logger
logger = Logger('info')


def test_convert_url():
    relative_path = "s3://bucket-name/key-name"
    sf = StageFile(logger, relative_path)
    s3_url = sf.get_staged_file()
    logger.info(s3_url)
    assert s3_url.startswith("https://")