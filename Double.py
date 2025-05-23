import yaml
import boto3

# Define custom type for double-quoted strings
class DoubleQuoted(str): pass

def double_quoted_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

yaml.add_representer(DoubleQuoted, double_quoted_representer)

# Prepare the data
data = {
    "inputs": [
        {
            "type": "file",
            "format": "{format}",
            "alias": "csv_to_parquet",
            "path": "{upload_csv_path}",
            "skip_rows": "{skip_rows}",
            "delimiter": "{input.delimiter}"
        },
        {
            "name": "Transformations",
            "type": "csv_to_parquet",
            "alias": "csv_to_parquet",
            "action": [
                {
                    "type": "transform",
                    "list": [
                        {
                            "businessdate": DoubleQuoted('regexp_replace(businessdate, "-", "")')
                        }
                    ]
                }
            ]
        },
        {
            "output": {
                "type": "file",
                "format": "parquet",
                "mode": "overwrite",
                "alias": "csv_to_parquet{output_string}"
            }
        }
    ],
    "post_processing": {
        "type": "replace",
        "table": "{database.name}",
        "table_name": "{table.name}",
        "temp_loc": "{temp_location}"
    }
}

# Dump the YAML string
yaml_string = yaml.dump(data, default_flow_style=False)

# Upload to S3
s3 = boto3.client('s3')
s3.put_object(
    Bucket='your-bucket-name',
    Key='your/path/file.yaml',
    Body=yaml_string.encode('utf-8')
)

print("YAML uploaded to S3 successfully.")
