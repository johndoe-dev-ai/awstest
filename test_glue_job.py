import pytest
from pyspark.sql import SparkSession
from mock_glue import MockGlueContext
from glue_job import convert_csv_to_parquet, run_glue_job

@pytest.fixture(scope="session")
def spark():
    return SparkSession.builder.getOrCreate()

@pytest.fixture(scope="function")
def mock_glue_context():
    return MockGlueContext()

def test_convert_csv_to_parquet(spark, tmp_path):
    # Create a sample CSV file
    input_data = [("1", "Alice", "25"), ("2", "Bob", "30"), ("3", "Charlie", "35")]
    input_df = spark.createDataFrame(input_data, ["id", "name", "age"])
    input_path = str(tmp_path / "input.csv")
    input_df.write.csv(input_path, header=True)

    # Set up output path
    output_path = str(tmp_path / "output.parquet")

    # Run the conversion
    convert_csv_to_parquet(spark, input_path, output_path)

    # Read the Parquet file and verify
    output_df = spark.read.parquet(output_path)
    assert output_df.count() == 3
    assert output_df.columns == ["id", "name", "age"]

def test_run_glue_job(mock_glue_context, tmp_path):
    # Set up input and output paths
    input_path = str(tmp_path / "input.csv")
    output_path = str(tmp_path / "output.parquet")

    # Create a sample CSV file
    spark = mock_glue_context.spark_session
    input_data = [("1", "Alice", "25"), ("2", "Bob", "30"), ("3", "Charlie", "35")]
    input_df = spark.createDataFrame(input_data, ["id", "name", "age"])
    input_df.write.csv(input_path, header=True)

    # Run the Glue job
    params = {
        'input_path': input_path,
        'output_path': output_path
    }
    run_glue_job(mock_glue_context, params)

    # Verify the output
    output_df = spark.read.parquet(output_path)
    assert output_df.count() == 3
    assert output_df.columns == ["id", "name", "age"]
