import pytest
from base_lambda_test import BaseLambdaTest
from s3_lambda_function import lambda_handler

@pytest.mark.aws_services(['s3'])
class TestS3Lambda(BaseLambdaTest):
    def setup_test_data(self):
        s3 = self.aws_services['s3']
        self.bucket_name = 'test-bucket'
        self.object_key = 'test-object.txt'
        self.test_content = 'Hello, World!'
        
        s3.create_bucket(Bucket=self.bucket_name)
        s3.put_object(Bucket=self.bucket_name, Key=self.object_key, Body=self.test_content)

    def test_lambda_handler_success(self):
        self.setup_test_data()
        event = {
            'bucket_name': self.bucket_name,
            'object_key': self.object_key
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        assert response['body'] == self.test_content

    def test_lambda_handler_error(self):
        event = {
            'bucket_name': 'non-existent-bucket',
            'object_key': 'test-object.txt'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 500
        assert 'NoSuchBucket' in response['body']
