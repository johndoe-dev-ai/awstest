import sys
from pyspark.sql import SparkSession

def convert_csv_to_parquet(spark, input_path, output_path):
    # Read CSV
    df = spark.read.option("header", "true").csv(input_path)
    
    # Write Parquet
    df.write.parquet(output_path, mode="overwrite")

def run_glue_job(glue_context, params):
    spark = glue_context.spark_session
    convert_csv_to_parquet(spark, params['input_path'], params['output_path'])

if __name__ == "__main__":
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from awsglue.utils import getResolvedOptions

    args = getResolvedOptions(sys.argv, ['JOB_NAME', 'input_path', 'output_path'])
    glue_context = GlueContext(SparkContext.getOrCreate())
    job = Job(glue_context)
    job.init(args['JOB_NAME'], args)

    run_glue_job(glue_context, {
        'input_path': args['input_path'],
        'output_path': args['output_path']
    })

    job.commit()
