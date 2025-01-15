import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

# Initialize Glue context and job
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Parameters
job.init('your_job_name', sys.argv)

# Specify the S3 bucket and folder
s3_bucket = "datalens-servicedata-356040817761"
s3_prefix = "output_1M/"

# Read JSON files from S3 into a Glue DynamicFrame
dynamic_frame = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={
        "paths": [f"s3://{s3_bucket}/{s3_prefix}"],
        "recurse": True  # Ensure it reads files from all subdirectories
    },
    format="json"
)

# Convert to DataFrame if needed
data_frame = dynamic_frame.toDF()

# Get record count
record_count = data_frame.count()

# Print the record count
print(f"Total record count: {record_count}")

# Commit the job
job.commit()
