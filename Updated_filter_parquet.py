#!/usr/bin/env python3
"""
Script for working with Hive-partitioned Parquet files with automatic partition preservation
Structure: parts/alerts/parquet/businessdate=XXX/region=YYY/version=ZZZ/
"""

import pyarrow.dataset as ds
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path
import argparse
import os

def get_partition_values_from_path(file_path: str) -> dict:
    """
    Extract partition values from a file path
    
    Args:
        file_path: Full path to a parquet file
    
    Returns:
        Dictionary of partition key-value pairs
    """
    path_parts = Path(file_path).parts
    partitions = {}
    
    for part in path_parts:
        if '=' in part:
            key, value = part.split('=', 1)
            partitions[key] = value
    
    return partitions

def read_partitioned_parquet(base_path: str) -> tuple:
    """
    Read Hive-partitioned Parquet files
    
    Args:
        base_path: Root path containing partitioned data
    
    Returns:
        Tuple of (DataFrame, list of partition columns)
    """
    dataset = ds.dataset(
        base_path,
        partitioning="hive",
        format="parquet"
    )
    
    # Get partition columns from schema
    partition_cols = [
        field.name for field in dataset.partitioning.schema
    ]
    
    return dataset.to_table().to_pandas(), partition_cols

def write_preserving_partitions(
    df: pd.DataFrame,
    input_path: str,
    output_path: str,
    compression: str = "snappy"
) -> None:
    """
    Write DataFrame to Parquet while preserving input partition structure
    
    Args:
        df: DataFrame to write
        input_path: Original input path (to detect partitions)
        output_path: Root output directory
        compression: Compression algorithm
    """
    # Read one file to detect partition structure
    sample_file = next(Path(input_path).rglob('*.parquet'), None)
    if not sample_file:
        raise ValueError("No parquet files found in input path")
    
    partitions = get_partition_values_from_path(str(sample_file))
    partition_cols = list(partitions.keys())
    
    # Verify all partition columns exist in DataFrame
    missing_cols = [col for col in partition_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"DataFrame missing partition columns: {missing_cols}")
    
    # Write with same partition structure
    pq.write_to_dataset(
        table=pa.Table.from_pandas(df),
        root_path=output_path,
        partition_cols=partition_cols,
        compression=compression,
        existing_data_behavior="overwrite_or_ignore",
        use_legacy_dataset=False
    )

def main():
    parser = argparse.ArgumentParser(
        description="Process partitioned Parquet files with automatic partition preservation"
    )
    parser.add_argument("--input", required=True, help="Base input path")
    parser.add_argument("--output", required=True, help="Output path for writing")
    parser.add_argument("--compression", default="snappy", 
                       help="Compression algorithm (snappy, gzip, etc.)")
    
    args = parser.parse_args()
    
    print(f"Reading partitioned data from {args.input}...")
    df, partition_cols = read_partitioned_parquet(args.input)
    print(f"Loaded {len(df)} records with partition columns: {partition_cols}")
    
    print(f"Writing to {args.output} with preserved partition structure...")
    write_preserving_partitions(
        df,
        args.input,
        args.output,
        compression=args.compression
    )
    
    print("Operation completed successfully")

if __name__ == "__main__":
    main()
