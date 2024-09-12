import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

def convert_csv_to_parquet(glueContext, raw_bucket, raw_key, prep_bucket, prep_key):
    # Create dynamic frame from CSV
    dynamic_frame = glueContext.create_dynamic_frame.from_options(
        format_options={"quoteChar": '"', "withHeader": True, "separator": ","},
        connection_type="s3",
        format="csv",
        connection_options={
            "paths": [f"s3://{raw_bucket}/{raw_key}"],
            "recurse": True,
        },
        transformation_ctx="datasource0",
    )
    
    # Convert to Parquet and write to prep bucket
    glueContext.write_dynamic_frame.from_options(
        frame=dynamic_frame,
        connection_type="s3",
        format="parquet",
        connection_options={
            "path": f"s3://{prep_bucket}/{prep_key}",
            "partitionKeys": [],
        },
        transformation_ctx="datasink1",
    )

def run_job(raw_bucket, raw_key, prep_bucket, prep_key):
    args = getResolvedOptions(sys.argv, ['JOB_NAME'])
    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)
    
    convert_csv_to_parquet(glueContext, raw_bucket, raw_key, prep_bucket, prep_key)
    
    job.commit()

if __name__ == "__main__":
    run_job(
        raw_bucket=sys.argv[1],
        raw_key=sys.argv[2],
        prep_bucket=sys.argv[3],
        prep_key=sys.argv[4]
    )
