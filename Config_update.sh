#!/bin/bash

# Load configurations from config.txt
config_file="config.txt"

if [[ ! -f $config_file ]]; then
  echo "Configuration file $config_file not found!"
  exit 1
fi

declare -A config_map

# Read the config.txt file
while IFS='=' read -r key value; do
  if [[ -n "$key" && -n "$value" ]]; then
    config_map[$key]="$value"
  fi
done < "$config_file"

# Check if source parameter is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <source>"
  exit 1
fi

source_dir="$1"
current_date=$(date +"%Y%m%d")
target_dir="$source_dir/$current_date"

# Check if the target directory exists
if [ ! -d "$target_dir" ]; then
  echo "Directory $target_dir does not exist."
  exit 1
fi

# Create directories if they don't exist
for dir in "${!config_map[@]}"; do
  mkdir -p "$target_dir/$dir"
done

# Segregate files based on the config file conditions
for file in "$target_dir"/*; do
  for dir in "${!config_map[@]}"; do
    if [[ "$file" == *"${config_map[$dir]}"* ]]; then
      mv "$file" "$target_dir/$dir/"
      break
    fi
  done
done

echo "Files segregated successfully."
