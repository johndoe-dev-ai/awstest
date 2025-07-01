#!/usr/bin/env python3
"""
Script to filter large Parquet files in chunks to avoid memory issues
"""

import pyarrow.parquet as pq
import pyarrow as pa
import pandas as pd
import os
import argparse
from pathlib import Path

def filter_large_parquet(
    input_path: str,
    output_path: str,
    filter_ids: list,
    id_column: str = "partyid",
    chunk_size: int = 100000
) -> None:
    """
    Process large Parquet files in chunks to avoid memory limits
    
    Args:
        input_path: Path to input Parquet file
        output_path: Path for output filtered file
        filter_ids: List of IDs to filter out
        id_column: Name of column containing IDs
        chunk_size: Number of rows per chunk
    """
    # Convert filter IDs to set for faster lookups
    filter_set = set(filter_ids)
    
    # Get schema from first row
    parquet_file = pq.ParquetFile(input_path)
    schema = parquet_file.schema
    
    # Prepare output writer
    writer = None
    
    try:
        for batch in parquet_file.iter_batches(batch_size=chunk_size):
            df = batch.to_pandas()
            
            # Filter the batch
            filtered_df = df[~df[id_column].isin(filter_set)]
            
            # Initialize writer with first batch
            if writer is None:
                writer = pq.ParquetWriter(
                    output_path,
                    schema=schema,
                    compression='snappy'
                )
            
            # Write the filtered batch
            table = pa.Table.from_pandas(filtered_df, schema=schema)
            writer.write_table(table)
            
            print(f"Processed {len(df)} rows, kept {len(filtered_df)} rows")
    
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise
    
    finally:
        if writer:
            writer.close()
    
    print(f"Successfully created filtered file: {output_path}")
    print(f"Original file size: {os.path.getsize(input_path)/1024/1024:.2f} MB")
    print(f"Filtered file size: {os.path.getsize(output_path)/1024/1024:.2f} MB")

def read_filter_ids(file_path: str) -> list:
    """
    Read filter IDs from JSONL file
    
    Args:
        file_path: Path to JSONL file containing IDs
    
    Returns:
        List of IDs to filter
    """
    ids = []
    with open(file_path, 'r') as f:
        for line in f:
            try:
                # Extract partyid from JSON-like lines
                if '"partyid":' in line:
                    id_start = line.find('"partyid":"') + 10
                    id_end = line.find('"', id_start)
                    ids.append(line[id_start:id_end])
            except Exception as e:
                print(f"Warning: Could not parse line: {line.strip()}")
                continue
    return ids

def main():
    parser = argparse.ArgumentParser(
        description="Filter large Parquet files in chunks to avoid memory limits"
    )
    parser.add_argument("--input", required=True, help="Input Parquet file path")
    parser.add_argument("--output", required=True, help="Output Parquet file path")
    parser.add_argument("--filter-file", required=True, 
                       help="File containing IDs to filter (JSONL format)")
    parser.add_argument("--id-column", default="partyid", 
                       help="Column name containing IDs")
    parser.add_argument("--chunk-size", type=int, default=100000,
                       help="Number of rows to process at once")
    
    args = parser.parse_args()
    
    print("Reading filter IDs...")
    filter_ids = read_filter_ids(args.filter_file)
    print(f"Loaded {len(filter_ids)} IDs to filter")
    
    print("Starting filtering process...")
    filter_large_parquet(
        input_path=args.input,
        output_path=args.output,
        filter_ids=filter_ids,
        id_column=args.id_column,
        chunk_size=args.chunk_size
    )

if __name__ == "__main__":
    main()
