from lib.metrics import Metrics
from lib.logger import Logger
from decimal import Decimal

log_level = 'info'
logger = Logger(loglevel=log_level)

send = Metrics(logger)


def test_backend_metrics():
    solution_id = 'SO_unit_test'
    data = {'key_string1': '2018-06-15',
            'key_string2': 'A1B2',
            'decimal': Decimal('5')
            }
    url = 'https://oszclq8tyh.execute-api.us-east-1.amazonaws.com/prod/generic'
    response = send.metrics(solution_id, data, url)
    logger.info(response)
    assert response == 200
