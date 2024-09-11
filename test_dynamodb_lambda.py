import pytest
from base_lambda_test import BaseLambdaTest
from dynamodb_lambda_function import lambda_handler

@pytest.mark.aws_services(['dynamodb'])
class TestDynamoDBLambda(BaseLambdaTest):
    def setup_test_data(self):
        dynamodb = self.aws_services['dynamodb']
        self.table_name = 'test-table'
        
        dynamodb.create_table(
            TableName=self.table_name,
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        dynamodb.put_item(
            TableName=self.table_name,
            Item={'id': {'S': '1'}, 'data': {'S': 'test data'}}
        )

    def test_lambda_handler_success(self):
        self.setup_test_data()
        event = {
            'table_name': self.table_name,
            'item_id': '1'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        assert 'test data' in response['body']

    def test_lambda_handler_error(self):
        event = {
            'table_name': self.table_name,
            'item_id': 'non-existent-id'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 404
        assert 'Item not found' in response['body']
