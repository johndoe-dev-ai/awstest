def filter_partitioned_data_chunked(
    input_path: str,
    output_path: str,
    filter_ids: set,
    id_column: str,
    chunk_size: int = 100000,
    compression: str = "snappy"
) -> None:
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
    
    # Get the Arrow schema from the dataset (without partition columns)
    arrow_schema = dataset.schema
    
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
                
                # Add partition columns to the DataFrame
                for col, val in part_values.items():
                    df[col] = val
                
                # Filter the batch
                filtered_df = df[~df[id_column].isin(filter_ids)]
                kept_rows += len(filtered_df)
                
                # Initialize writer with first batch if we have data
                if len(filtered_df) > 0 and writer is None:
                    # Create new schema including partition columns
                    new_fields = list(arrow_schema)
                    for col, val in part_values.items():
                        # Add partition columns to schema with appropriate type
                        if col not in arrow_schema.names:
                            new_fields.append(pa.field(col, pa.string()))
                    full_schema = pa.schema(new_fields)
                    
                    writer = pq.ParquetWriter(
                        output_file,
                        schema=full_schema,
                        compression=compression
                    )
                
                # Write the filtered batch if we have data
                if len(filtered_df) > 0:
                    table = pa.Table.from_pandas(filtered_df, schema=full_schema)
                    writer.write_table(table)
                
                print(f"  Processed {len(df)} rows, kept {len(filtered_df)} rows")
        
        finally:
            if writer:
                writer.close()
        
        print(f"  Total: {total_rows} rows processed, {kept_rows} rows kept "
              f"({total_rows - kept_rows} rows filtered out)")
