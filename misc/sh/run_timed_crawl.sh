#!/bin/bash

# Calculate when to stop (5 hours from now)
END_TIME=$(($(date +%s) + 5*60*60))

echo "Starting 5-hour Wikipedia crawl at $(date)"
echo "Will end at $(date -r $END_TIME)"
echo "---------------------------------------------"

# Run the crawler until the time is up
while [ $(date +%s) -lt $END_TIME ]
do
    python run_crawl.py --workers 12 --batch-size 50 --depth 8 --max-steps 25 --max-size 20 --service XEPDB1 --user system --password Oracle21c --delay 3
    
    # If we still have time, start another batch
    if [ $(date +%s) -lt $END_TIME ]; then
        echo "---------------------------------------------"
        echo "Crawler stopped. Restarting for next batch..."
        echo "Time remaining: $(( ($END_TIME - $(date +%s)) / 60 )) minutes"
        echo "---------------------------------------------"
        sleep 5
    fi
done

echo "---------------------------------------------"
echo "5-hour crawl completed at $(date)"
echo "Run visualize_wiki_data.py and generate_wiki_report.py to see the results" 