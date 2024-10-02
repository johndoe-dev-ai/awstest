#!/bin/bash

# Directory to watch
WATCH_DIR="/path/to/your/directory"

# Maximum wait time in seconds (10 hours)
MAX_WAIT_TIME=$((10 * 60 * 60))

# Check interval in seconds (5 minutes)
CHECK_INTERVAL=$((5 * 60))

# Function to check for .done file
check_done_file() {
    local current_date=$(date +%Y%m%d)
    local done_file_pattern="*_${current_date}_*.done"
    
    if ls ${WATCH_DIR}/${done_file_pattern} 1> /dev/null 2>&1; then
        echo ".done file found for ${current_date} in ${WATCH_DIR}"
        return 0
    else
        return 1
    fi
}

# Main loop
start_time=$(date +%s)

while true; do
    if check_done_file; then
        exit 0
    fi

    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))

    if [ $elapsed_time -ge $MAX_WAIT_TIME ]; then
        echo "Timeout: .done file not found within 10 hours"
        exit 1
    fi

    sleep $CHECK_INTERVAL
done
