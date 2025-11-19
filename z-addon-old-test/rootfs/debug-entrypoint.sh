#!/bin/bash

# Debug entrypoint script that will be executed when the container starts

echo "====== CONTAINER ENTRYPOINT DEBUG ======"
echo "Date: $(date)"
echo "Host: $(hostname)"
echo "Arguments: $@"
echo "User: $(whoami) ($(id))"
echo "Working directory: $(pwd)"
echo "Environment variables:"
env | sort

# Alert if we're not running as PID 1
if [ $$ -ne 1 ]; then
    echo "WARNING: This process is NOT running as PID 1 (actual PID: $$)"
    echo "This will likely cause s6-overlay to fail"
else
    echo "INFO: Running as PID 1 as required by s6-overlay"
fi

echo "Process tree:"
ps -ef

echo "===== END ENTRYPOINT DEBUG ====="

# Execute the original entrypoint
exec /init
