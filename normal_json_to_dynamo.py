def convert_to_dynamodb_json(normal_json):
    dynamodb_json = {}

    for key, value in normal_json.items():
        dynamodb_json[key] = convert_value(value)

    return dynamodb_json

def convert_value(value):
    if isinstance(value, str):
        return {"S": value}
    elif isinstance(value, (int, float)):
        return {"N": str(value)}
    elif isinstance(value, bool):
        return {"BOOL": value}
    elif value is None:
        return {"NULL": True}
    elif isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return {"SS": value}  # String set
        elif all(isinstance(item, (int, float)) for item in value):
            return {"NS": [str(item) for item in value]}  # Number set
        else:
            return {"L": [convert_value(item) for item in value]}  # List
    elif isinstance(value, dict):
        return {"M": {k: convert_value(v) for k, v in value.items()}}  # Map
    else:
        raise TypeError(f"Unsupported data type: {type(value)}")

# Example usage
normal_json = {
    "ID": "001",
    "Name": "John Doe",
    "Age": 30,
    "IsActive": True,
    "Scores": [100, 95, 85],
    "Address": {
        "City": "New York",
        "ZipCode": "10001"
    },
    "Tags": ["Student", "Athlete"]
}

dynamodb_json = convert_to_dynamodb_json(normal_json)
print(dynamodb_json)
