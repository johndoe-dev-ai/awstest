#!/usr/bin/env python3
"""
Script for working with Hive-partitioned Parquet files
Structure: parts/alerts/parquet/businessdate=XXX/region=YYY/version=ZZZ/
"""

import pyarrow.dataset as ds
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path
from datetime import datetime
import argparse

def read_partitioned_parquet(base_path: str) -> pd.DataFrame:
    """
    Read Hive-partitioned Parquet files into a single DataFrame
    
    Args:
        base_path: Root path containing partitioned data (e.g., "parts/alerts/parquet")
    
    Returns:
        Combined DataFrame with partition columns
    """
    dataset = ds.dataset(
        base_path,
        partitioning=["businessdate", "region", "version"],
        format="parquet"
    )
    return dataset.to_table().to_pandas()

def filter_partitioned_data(
    base_path: str,
    businessdate: str = None,
    region: str = None,
    version: str = None
) -> pd.DataFrame:
    """
    Filter partitioned data without loading all files
    
    Args:
        base_path: Root path of partitioned data
        businessdate: Filter value for businessdate partition
        region: Filter value for region partition
        version: Filter value for version partition
    
    Returns:
        Filtered DataFrame
    """
    dataset = ds.dataset(
        base_path,
        partitioning=["businessdate", "region", "version"],
        format="parquet"
    )
    
    conditions = []
    if businessdate:
        conditions.append(ds.field("businessdate") == businessdate)
    if region:
        conditions.append(ds.field("region") == region)
    if version:
        conditions.append(ds.field("version") == version)
    
    if conditions:
        filtered_dataset = dataset.filter(pa.compute.and_(*conditions))
        return filtered_dataset.to_table().to_pandas()
    return dataset.to_table().to_pandas()

def write_partitioned_parquet(
    df: pd.DataFrame,
    output_path: str,
    partition_cols: list,
    compression: str = "snappy"
) -> None:
    """
    Write DataFrame to Hive-partitioned Parquet format
    
    Args:
        df: DataFrame to write
        output_path: Root output directory
        partition_cols: List of columns to partition by
        compression: Compression algorithm (snappy, gzip, etc.)
    """
    table = pa.Table.from_pandas(df)
    
    pq.write_to_dataset(
        table=table,
        root_path=output_path,
        partition_cols=partition_cols,
        compression=compression,
        existing_data_behavior="overwrite_or_ignore"
    )

def list_partitions(base_path: str) -> dict:
    """
    List all partition values in the dataset
    
    Args:
        base_path: Root path of partitioned data
    
    Returns:
        Dictionary of partition values
    """
    path = Path(base_path)
    partitions = {
        "businessdate": set(),
        "region": set(),
        "version": set()
    }
    
    for businessdate_dir in path.glob("businessdate=*"):
        businessdate = businessdate_dir.name.split("=")[1]
        partitions["businessdate"].add(businessdate)
        
        for region_dir in businessdate_dir.glob("region=*"):
            region = region_dir.name.split("=")[1]
            partitions["region"].add(region)
            
            for version_dir in region_dir.glob("version=*"):
                version = version_dir.name.split("=")[1]
                partitions["version"].add(version)
    
    return partitions

def main():
    parser = argparse.ArgumentParser(description="Process partitioned Parquet files")
    parser.add_argument("--input", required=True, help="Base input path")
    parser.add_argument("--output", help="Output path for writing")
    parser.add_argument("--list", action="store_true", help="List partition values")
    parser.add_argument("--businessdate", help="Filter by businessdate")
    parser.add_argument("--region", help="Filter by region")
    parser.add_argument("--version", help="Filter by version")
    
    args = parser.parse_args()
    
    if args.list:
        partitions = list_partitions(args.input)
        print("Available partitions:")
        for key, values in partitions.items():
            print(f"{key}: {sorted(values)}")
        return
    
    # Example usage
    print("Reading and processing partitioned data...")
    
    # Option 1: Read all data
    # df = read_partitioned_parquet(args.input)
    
    # Option 2: Read filtered data
    df = filter_partitioned_data(
        args.input,
        businessdate=args.businessdate,
        region=args.region,
        version=args.version
    )
    
    print(f"Loaded {len(df)} records")
    print(df.head())
    
    if args.output:
        print(f"Writing partitioned data to {args.output}...")
        write_partitioned_parquet(
            df,
            args.output,
            partition_cols=["businessdate", "region", "version"]
        )
        print("Write completed")

if __name__ == "__main__":
    main()
