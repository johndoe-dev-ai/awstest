import pytest
from moto import mock_aws
import boto3

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "aws_services(services): mark test to use specific AWS services"
    )

@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture(scope='function')
def aws_services(request, aws_credentials):
    """
    Fixture to mock AWS services based on the services specified in the test marker.
    Usage: @pytest.mark.aws_services(['s3', 'dynamodb'])
    """
    services = request.node.get_closest_marker('aws_services')
    if services is not None:
        services = services.args[0]
    else:
        services = []

    with mock_aws():
        mocked_services = {}
        for service in services:
            mocked_services[service] = boto3.client(service, region_name='us-east-1')
        yield mocked_services
