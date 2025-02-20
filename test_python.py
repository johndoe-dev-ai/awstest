import sys
from unittest.mock import MagicMock, patch
import pytest
from moto import mock_aws
import boto3
import json
from psycopg2 import OperationalError
from deploy_to_redshift import (
    create_conn,
    execute_sql_file,
    execute_dynamic_grants,
    execute_ddl,
    execute_hotfix,
    logger
)

# Fixtures ----------------------------------------------------------------

@pytest.fixture
def mock_secrets():
    with mock_aws():
        secmgr = boto3.client('secretsmanager')
        
        # Create test secrets
        secmgr.create_secret(
            Name='test-dl-secret',
            SecretString=json.dumps({
                'username': 'testuser',
                'password': 'testpass',
                'host': 'localhost',
                'port': 5439,
                'dbname': 'testdb'
            })
        )
        
        secmgr.create_secret(
            Name='test-consumer-secret',
            SecretString=json.dumps({
                'username': 'consumer',
                'password': 'consumerpass',
                'host': 'consumer-host',
                'port': 5439,
                'dbname': 'consumer_db'
            })
        )
        yield secmgr

@pytest.fixture
def mock_s3():
    with mock_aws():
        s3 = boto3.resource('s3')
        bucket = s3.create_bucket(Bucket='test-bucket')
        yield s3

@pytest.fixture
def mock_dynamodb():
    with mock_aws():
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.create_table(
            TableName='DataLensRedshiftAccessDetails',
            KeySchema=[{'AttributeName': 'SchemaName', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'SchemaName', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        yield table

@pytest.fixture
def mock_redshift_connection():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor

# Tests --------------------------------------------------------------------

@mock_aws
def test_create_conn_datalens_flow(mock_secrets, mock_redshift_connection):
    """Test connection creation for DataLens flow"""
    with patch('psycopg2.connect') as mock_connect:
        mock_connect.return_value = mock_redshift_connection[0]
        
        conn = create_conn("datalens-redshift-consumer-objects-flow")
        
        mock_connect.assert_called_once_with(
            dbname='consumer_db',
            host='consumer-host',
            port=5439,
            user='consumer',
            password='consumerpass'
        )
        assert conn == mock_redshift_connection[0]

@mock_aws
def test_create_conn_regular_flow(mock_secrets, mock_redshift_connection):
    """Test connection creation for regular flow"""
    with patch('psycopg2.connect') as mock_connect:
        mock_connect.return_value = mock_redshift_connection[0]
        
        conn = create_conn("other-flow")
        
        mock_connect.assert_called_once_with(
            dbname='testdb',
            host='localhost',
            port=5439,
            user='testuser',
            password='testpass'
        )

def test_execute_sql_file(mock_s3, mock_redshift_connection):
    """Test SQL file execution from S3"""
    conn, cursor = mock_redshift_connection
    
    # Upload test SQL file
    s3_object = mock_s3.Object('test-bucket', 'test-script.sql')
    s3_object.put(Body="CREATE TABLE test (id INT);\nSELECT 1;")
    
    execute_sql_file([], 'test-script.sql')
    
    assert cursor.execute.call_count == 2
    conn.commit.assert_called()

def test_execute_dynamic_grants(mock_dynamodb, mock_redshift_connection):
    """Test dynamic grants execution from DynamoDB"""
    _, cursor = mock_redshift_connection
    
    # Add test items to DynamoDB
    mock_dynamodb.put_item(Item={
        'SchemaName': 'public',
        'IsActive': True,
        'ClusterAccessType': 'PROD'
    })
    
    execute_dynamic_grants("test-flow", cursor)
    
    cursor.execute.assert_called_with("GRANT USAGE ON SCHEMA public TO ROLE read_access;")

def test_execute_ddl_success(mock_s3, mock_redshift_connection, caplog):
    """Test DDL execution success scenario"""
    _, cursor = mock_redshift_connection
    s3_object = mock_s3.Object('test-bucket', 'ddl-script.sql')
    s3_object.put(Body="CREATE TABLE test (id INT);")
    
    result = execute_ddl('s3://test-bucket/ddl-script.sql')
    
    assert "Executing DDLs at" in caplog.text
    assert result == 1  # Assuming 1 statement executed

def test_main_execution_flow(mock_secrets, mock_s3, mock_dynamodb, mocker):
    """Test full main execution flow"""
    with mock_aws(), \
         patch('deploy_to_redshift.getResolvedOptions') as mock_args, \
         patch('psycopg2.connect') as mock_connect, \
         patch('deploy_to_redshift.is_object_exists') as mock_exists:
        
        # Setup mocks
        mock_args.return_value = {
            'FlowName': 'test-flow',
            'ExecutionID': 'test.123',
            'SQLScript': 's3://test-bucket/ddl-script.sql',
            'Secret': 'test-consumer-secret',
            'DLSecret': 'test-dl-secret'
        }
        
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Setup S3 content
        s3_object = mock_s3.Object('test-bucket', 'ddl-script.sql')
        s3_object.put(Body="CREATE TABLE test (id INT);")
        
        # Setup hotfix check
        mock_exists.side_effect = lambda path: "hotfix" in path
        
        # Execute main
        with patch.object(sys, 'argv', ['']):
            import deploy_to_redshift
            deploy_to_redshift.main()
        
        # Verify execution flow
        assert mock_cursor.execute.call_count >= 1
        assert "Connection closed" in caplog.text

# Error Handling Tests -----------------------------------------------------

def test_create_conn_failure():
    """Test connection failure handling"""
    with mock_aws(), \
         patch('psycopg2.connect') as mock_connect, \
         pytest.raises(OperationalError):
        
        mock_connect.side_effect = OperationalError("Connection failed")
        create_conn("test-flow")

def test_execute_sql_failure(mock_s3, mock_redshift_connection):
    """Test SQL execution failure handling"""
    conn, cursor = mock_redshift_connection
    cursor.execute.side_effect = OperationalError("SQL Error")
    
    s3_object = mock_s3.Object('test-bucket', 'bad-script.sql')
    s3_object.put(Body="INVALID SQL;")
    
    with pytest.raises(Exception):
        execute_sql_file([], 'bad-script.sql')
    
    conn.rollback.assert_called()
