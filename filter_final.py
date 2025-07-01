#!/usr/bin/env python3
"""
Script to filter partitioned Parquet files using pipe-separated IDs from a text file,
with chunked processing and automatic partition preservation.
"""

import pyarrow.dataset as ds
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path
import argparse
import os

def read_filter_ids(filter_file: str) -> set:
    """
    Read pipe-separated IDs from filter file
    
    Args:
        filter_file: Path to text file with pipe-separated IDs
    
    Returns:
        Set of IDs to filter
    """
    with open(filter_file, 'r') as f:
        content = f.read().strip()
        if not content:
            return set()
        return set(content.split('|'))

def get_partition_columns(input_path: str) -> list:
    """
    Detect partition columns from directory structure
    
    Args:
        input_path: Path to partitioned dataset
    
    Returns:
        List of partition column names
    """
    path = Path(input_path)
    partition_cols = []
    
    for item in path.iterdir():
        if item.is_dir() and '=' in item.name:
            partition_cols.append(item.name.split('=')[0])
            break  # Just need first level to detect pattern
    
    return partition_cols

def filter_partitioned_data_chunked(
    input_path: str,
    output_path: str,
    filter_ids: set,
    id_column: str,
    chunk_size: int = 100000,
    compression: str = "snappy"
) -> None:
    """
    Filter partitioned data in chunks while preserving partition structure
    
    Args:
        input_path: Input directory with partitioned data
        output_path: Output directory for filtered data
        filter_ids: Set of IDs to filter out
        id_column: Column name containing IDs to filter
        chunk_size: Number of rows per chunk
        compression: Compression algorithm
    """
    # Detect partition columns from input structure
    partition_cols = get_partition_columns(input_path)
    if not partition_cols:
        raise ValueError("No partition columns detected in input path")
    
    print(f"Detected partition columns: {partition_cols}")
    print(f"Filtering on column '{id_column}' with {len(filter_ids)} IDs to exclude")

    # Create dataset with hive partitioning
    dataset = ds.dataset(
        input_path,
        partitioning="hive",
        format="parquet"
    )
    
    # Process each fragment (file) separately to maintain partitions
    for fragment in dataset.get_fragments():
        # Get partition values from fragment path
        part_values = {}
        for part in str(fragment.path).split('/'):
            if '=' in part:
                key, val = part.split('=', 1)
                part_values[key] = val
        
        # Create output directory structure
        output_dir = output_path
        for col in partition_cols:
            if col in part_values:
                output_dir = os.path.join(output_dir, f"{col}={part_values[col]}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Process this fragment in chunks
        filename = os.path.basename(fragment.path)
        output_file = os.path.join(output_dir, filename)
        
        print(f"\nProcessing {fragment.path} -> {output_file}")
        
        # Open input file
        reader = pq.ParquetFile(fragment.path)
        writer = None
        total_rows = 0
        kept_rows = 0
        
        try:
            for batch in reader.iter_batches(batch_size=chunk_size):
                df = batch.to_pandas()
                total_rows += len(df)
                
                # Filter the batch
                filtered_df = df[~df[id_column].isin(filter_ids)]
                kept_rows += len(filtered_df)
                
                # Initialize writer with first batch if we have data
                if len(filtered_df) > 0 and writer is None:
                    writer = pq.ParquetWriter(
                        output_file,
                        schema=reader.schema,
                        compression=compression
                    )
                
                # Write the filtered batch if we have data
                if len(filtered_df) > 0:
                    table = pa.Table.from_pandas(filtered_df, schema=reader.schema)
                    writer.write_table(table)
                
                print(f"  Processed {len(df)} rows, kept {len(filtered_df)} rows")
        
        finally:
            if writer:
                writer.close()
        
        print(f"  Total: {total_rows} rows processed, {kept_rows} rows kept "
              f"({total_rows - kept_rows} rows filtered out)")

def main():
    parser = argparse.ArgumentParser(
        description="Filter partitioned Parquet files using pipe-separated IDs"
    )
    parser.add_argument("--input", required=True, 
                       help="Input directory with partitioned data")
    parser.add_argument("--output", required=True, 
                       help="Output directory for filtered data")
    parser.add_argument("--filter-file", required=True,
                       help="Text file with pipe-separated IDs to filter")
    parser.add_argument("--id-column", required=True,
                       help="Column name containing IDs to filter")
    parser.add_argument("--chunk-size", type=int, default=100000,
                       help="Number of rows to process at once")
    parser.add_argument("--compression", default="snappy",
                       help="Compression algorithm (snappy, gzip, etc.)")
    
    args = parser.parse_args()
    
    # Read filter IDs
    filter_ids = read_filter_ids(args.filter_file)
    if not filter_ids:
        print("Warning: No filter IDs found in filter file")
    
    print(f"Starting processing with {len(filter_ids)} filter IDs...")
    filter_partitioned_data_chunked(
        input_path=args.input,
        output_path=args.output,
        filter_ids=filter_ids,
        id_column=args.id_column,
        chunk_size=args.chunk_size,
        compression=args.compression
    )
    
    print("\nProcessing completed successfully")

if __name__ == "__main__":
    main()
