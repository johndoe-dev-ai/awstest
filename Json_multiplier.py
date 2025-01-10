import sys
import json
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

# Initialize GlueContext and SparkContext
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# Get parameters passed to the Glue job
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_INPUT_PATH', 'S3_OUTPUT_PATH', 'SOURCE_SYSTEM_ATTRIBUTE'])

# Parameters
input_path = args['S3_INPUT_PATH']
output_path = args['S3_OUTPUT_PATH']
source_system_attribute = args['SOURCE_SYSTEM_ATTRIBUTE']

# Read the JSON file from S3
dynamic_frame = glueContext.create_dynamic_frame.from_options(
    format_options={"multiline": True},
    connection_type="s3",
    format="json",
    connection_options={"paths": [input_path]},
)

# Convert DynamicFrame to DataFrame
df = dynamic_frame.toDF()

# Process and write 1000 files with different source system values
for i in range(1, 1001):
    new_source_system = f"HOME{i}"
    
    # Update the source system attribute
    updated_df = df.withColumn(source_system_attribute, F.lit(new_source_system))
    
    # Define output file path
    output_file_path = f"{output_path}/output_{i}.json"
    
    # Write the updated DataFrame back to S3
    updated_df.write.json(output_file_path, mode='overwrite', multiline=True)

    print(f"Created {output_file_path} with {source_system_attribute} set to {new_source_system}")

# Commit the job (required for Glue jobs)
glueContext.commit()
