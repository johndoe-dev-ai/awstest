import boto3
import yaml

def load_yaml_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def add_partition_to_athena_table(config, database_name):
    if 'output' in config and 'partition' in config['output']:
        table_name = config['output']['table']
        partition_columns = config['output']['partition']
        # Assuming the partition values are provided in the config
        partition_values = config['output'].get('partition_values', {})

        # Construct the partition clause
        partition_clause = ', '.join([f"{col}='{partition_values.get(col)}'" for col in partition_columns])

        # Construct the SQL query
        query = f"ALTER TABLE {database_name}.{table_name} ADD PARTITION ({partition_clause})"

        # Execute the query in Athena
        execute_athena_query(query)
        print(f"Executed query: {query}")
    else:
        print("No partition specified in the output section.")

def execute_athena_query(query, database_name='your_database_name', output_location='s3://your-output-bucket/'):
    # Initialize the Athena client
    client = boto3.client('athena')

    # Run the query
    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database_name},
        ResultConfiguration={'OutputLocation': output_location}
    )
    
    # Retrieve the execution ID
    query_execution_id = response['QueryExecutionId']
    print(f"Query Execution ID: {query_execution_id}")
    # Optional: you could add code to wait for the query to complete

# Example usage
file_path = 'config.yaml'
database_name = 'your_database_name'
config = load_yaml_config(file_path)
add_partition_to_athena_table(config, database_name)
