#!/bin/bash

# Define the full path to Asterisk command
asterisk_cmd="/usr/sbin/asterisk"

# Initialize variables to store call counts
inbound_calls=0
outbound_calls=0
num_pri_lines=0

# Get active channels from Asterisk
asterisk_output=$("${asterisk_cmd}" -rx "dahdi show channels")

# Process each active channel line
while IFS= read -r line; do
    # Extract the extension number (phone number) from the line
    number=$(echo "$line" | awk '{print $2}')

    if [[ $number =~ ^[0-9]+$ ]]; then
        # Calculate the total number of digits
        digit_count=${#number}

        # Determine call type based on digit count
        if [[ $digit_count -eq 10 ]]; then
            ((outbound_calls++))
        elif [[ $digit_count -eq 4 || $digit_count -eq 6 || $digit_count -eq 8 ]]; then
            ((inbound_calls++))
        fi
    fi
done <<< "$asterisk_output"

# Get the number of active PRI lines
num_pri_lines=$("${asterisk_cmd}" -rx "dahdi show status" | grep -c "wanpipe")

# Output the results in a format Zabbix or other monitoring tools can understand
echo "inbound_calls:${inbound_calls}"
echo "outbound_calls:${outbound_calls}"
echo "pri_lines:${num_pri_lines}"
