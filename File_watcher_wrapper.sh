#!/bin/bash

# Path to the date control file
DATE_CONTROL_FILE="date_control.txt"

# Path to the file watcher script
FILE_WATCHER_SCRIPT="./file_watcher.sh"

# Function to convert date from DD-MM-YYYY to YYYYMMDD format
convert_date() {
    date -d "$1" +"%Y%m%d"
}

# Check if date control file exists
if [ ! -f "$DATE_CONTROL_FILE" ]; then
    echo "Error: $DATE_CONTROL_FILE not found"
    exit 1
fi

# Read the date control file
IFS='|' read -r prev_date current_date next_date < "$DATE_CONTROL_FILE"

# Convert current date to YYYYMMDD format
formatted_date=$(convert_date "$current_date")

# Check if file watcher script exists and is executable
if [ ! -x "$FILE_WATCHER_SCRIPT" ]; then
    echo "Error: $FILE_WATCHER_SCRIPT not found or not executable"
    exit 1
fi

# Call the file watcher script with the formatted date
"$FILE_WATCHER_SCRIPT" "$formatted_date"
