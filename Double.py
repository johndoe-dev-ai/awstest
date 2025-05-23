import yaml

# Custom class to enforce double quotes
class DoubleQuoted(str): pass

def quoted_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

yaml.add_representer(DoubleQuoted, quoted_presenter)

# Construct YAML data
data = {
    "inputs": [
        {
            "type": "file",
            "format": "csv",
            "alias": "csv_to_parquet",
            "path": "s3://dmt-wh-xxx/trade_store/processed/dormancy_position/businessdate=20250510/",
            "skip_rows": 0,
            "delimiter": ","
        }
    ],
    "outputs": [
        {
            "type": "file",
            "format": "parquet",
            "mode": "overwrite",
            "alias": "csv_to_parquet",
            "path": "s3://dmt-wh-xxx/temp/dormancy/dormancy_position/"
        }
    ],
    "post_processing": {
        "type": "replace",
        "table": "cd_tradomsmart.tradestore",
        "alias": "dormancy_position",
        "temp_loc": "s3://datalens-service/data-xxx/"
    },
    "transformations": [
        {
            "type": "csv_to_parquet",
            "alias": "csv_to_parquet",
            "action": [
                {
                    "type": "transform",
                    "list": [
                        {
                            "businessdate": DoubleQuoted("regexp_replace(businessdate, '-', '')")
                        }
                    ]
                }
            ]
        }
    ]
}

# Dump to YAML with enforced double quotes
yaml_str = yaml.dump(data, default_flow_style=False)
print(yaml_str)
