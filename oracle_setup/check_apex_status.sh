#!/bin/bash

# Script to check Oracle APEX installation status periodically

echo "Checking APEX installation status every 5 minutes..."
echo "Press Ctrl+C to stop the checks"
echo ""

while true; do
    echo "----------------------------------------"
    echo "Checking APEX status at $(date)"
    echo "----------------------------------------"
    
    docker exec -i oracle-apex-21c sqlplus -s / as sysdba << EOF
    SET LINESIZE 200
    SET PAGESIZE 100
    SELECT comp_name, version, status FROM dba_registry WHERE comp_name = 'Oracle APEX';
    EXIT;
EOF
    
    echo ""
    echo "Checking installation processes..."
    docker exec -i oracle-apex-21c bash -c "ps -ef | grep -i apex | grep -v grep | wc -l"
    echo ""
    
    echo "Waiting 5 minutes for next check..."
    sleep 300
done 