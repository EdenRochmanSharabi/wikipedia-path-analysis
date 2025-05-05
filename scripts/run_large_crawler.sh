#!/bin/bash

# Run the large Wikipedia graph crawler with appropriate parameters
# This script allows for easy resumption after interruption

# Default settings
WORKERS=6
MAX_STEPS=1000  # Maximum steps per path
MAX_SIZE=10     # Maximum database size in GB
INITIAL=6       # Number of initial articles

# Database connection settings
DB_HOST="localhost"
DB_PORT=1521
DB_SERVICE="XE"
DB_USER="sys"
DB_PASSWORD="cyvsi5-vapzUk-qizveb"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --workers|-w)
      WORKERS="$2"
      shift 2
      ;;
    --max-steps|-s)
      MAX_STEPS="$2"
      shift 2
      ;;
    --max-size|-m)
      MAX_SIZE="$2"
      shift 2
      ;;
    --initial|-i)
      INITIAL="$2"
      shift 2
      ;;
    --host)
      DB_HOST="$2"
      shift 2
      ;;
    --port)
      DB_PORT="$2"
      shift 2
      ;;
    --service)
      DB_SERVICE="$2"
      shift 2
      ;;
    --user)
      DB_USER="$2"
      shift 2
      ;;
    --password)
      DB_PASSWORD="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--workers|-w N] [--max-steps|-s N] [--max-size|-m N] [--initial|-i N]"
      echo "          [--host HOST] [--port PORT] [--service SERVICE] [--user USER] [--password PASSWORD]"
      exit 1
      ;;
  esac
done

# Create a log directory if it doesn't exist
mkdir -p logs

# Generate a timestamp for log files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/large_crawler_${TIMESTAMP}.log"

# Display startup information
echo "Starting large Wikipedia graph crawler with:"
echo "- $WORKERS workers"
echo "- $MAX_SIZE GB maximum size"
echo "- $MAX_STEPS maximum steps per path"
echo "- $INITIAL initial random articles"
echo "- Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_SERVICE"
echo "Logging to: $LOG_FILE"

# Function to handle interruption
function cleanup {
  echo 
  echo "Crawler interrupted. To resume, run this script again."
  echo "The crawler will automatically continue from where it left off by loading existing articles from the database."
  exit 0
}

# Set up trap for Ctrl+C
trap cleanup SIGINT

# Run the crawler
python3 large_wiki_graph_crawler.py \
  --workers $WORKERS \
  --max-steps $MAX_STEPS \
  --max-size $MAX_SIZE \
  --initial $INITIAL \
  --host $DB_HOST \
  --port $DB_PORT \
  --service $DB_SERVICE \
  --user $DB_USER \
  --password "$DB_PASSWORD" \
  --sysdba | tee -a "$LOG_FILE"

# Display completion message
echo "Crawler completed. Log saved to $LOG_FILE" 