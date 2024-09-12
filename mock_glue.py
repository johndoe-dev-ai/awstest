from pyspark.sql import SparkSession

class MockGlueContext:
    def __init__(self):
        self.spark_session = SparkSession.builder.getOrCreate()
