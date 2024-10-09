import yaml

def load_yaml_config(file_path):
    # Load the YAML configuration
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def add_partition_to_table(config):
    # Check if 'output' section and 'partition' key are present
    if 'output' in config and 'partition' in config['output']:
        table = config['output']['table']
        partition_columns = config['output']['partition']
        
        # Assuming a function `alter_table_to_add_partition` adds the partitions
        alter_table_to_add_partition(table, partition_columns)
        print(f"Added partition {partition_columns} to table {table}.")
    else:
        print("No partition specified in the output section.")

def alter_table_to_add_partition(table, partition_columns):
    # Here you would have the logic to alter the table and add partitions
    # This is a placeholder function
    print(f"Altering table {table} to add partitions {partition_columns}.")

# Example usage
file_path = 'config.yaml'
config = load_yaml_config(file_path)
add_partition_to_table(config)
