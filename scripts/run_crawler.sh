#!/bin/bash

# Default values
WORKERS=8
DEPTH=100
MAX_STEPS=150
RANDOM_ARTICLES=100
DB_HOST="localhost"
DB_PORT=1521
DB_SERVICE="XE"
DB_USER="sys"
DB_PASSWORD="cyvsi5-vapzUk-qizveb"
SYSDBA="--sysdba"
MAX_SIZE_GB=2

# Help message
function show_help {
    echo "Usage: ./run_crawler.sh [options]"
    echo ""
    echo "Options:"
    echo "  -w, --workers NUM     Number of parallel workers (default: 8)"
    echo "  -d, --depth NUM       Target path depth (default: 100)"
    echo "  -m, --max-steps NUM   Maximum steps per path (default: 150)"
    echo "  -r, --random NUM      Number of random articles (default: 100)"
    echo "  -a, --articles LIST   Comma-separated list of specific articles"
    echo "  --host HOST           Database host (default: localhost)"
    echo "  --port PORT           Database port (default: 1521)"
    echo "  --service SERVICE     Database service name (default: XE)"
    echo "  --user USER           Database username (default: sys)"
    echo "  --password PASS       Database password"
    echo "  --sysdba              Connect as SYSDBA (default: enabled)"
    echo "  --max-size SIZE       Maximum database size in GB (default: 2)"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Example:"
    echo "  ./run_crawler.sh -w 8 -d 15 -r 10 -a \"Python,Mathematics,Physics\""
}

# Parse command line arguments
ARTICLES=""
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -h|--help)
            show_help
            exit 0
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -d|--depth)
            DEPTH="$2"
            shift 2
            ;;
        -m|--max-steps)
            MAX_STEPS="$2"
            shift 2
            ;;
        -r|--random)
            RANDOM_ARTICLES="$2"
            shift 2
            ;;
        -a|--articles)
            ARTICLES="$2"
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
        --sysdba)
            SYSDBA="--sysdba"
            shift
            ;;
        --max-size)
            MAX_SIZE_GB="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Build article arguments if any specified
ARTICLE_ARGS=""
if [ ! -z "$ARTICLES" ]; then
    # Convert comma-separated list to space-separated for Python script
    IFS=',' read -ra ARTICLE_LIST <<< "$ARTICLES"
    for article in "${ARTICLE_LIST[@]}"; do
        ARTICLE_ARGS="$ARTICLE_ARGS -a \"$article\""
    done
fi

# Build the command
CMD="python3 parallel_wiki_crawler.py -w $WORKERS -d $DEPTH -m $MAX_STEPS -r $RANDOM_ARTICLES $ARTICLE_ARGS --host $DB_HOST --port $DB_PORT --service $DB_SERVICE --user $DB_USER --password $DB_PASSWORD $SYSDBA --max-size $MAX_SIZE_GB"

# Show the command being executed
echo "Running command:"
echo "$CMD"
echo ""

# Execute the command
eval $CMD

# Check if it ran successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "Crawler completed successfully!"
    echo "Run 'python3 analyze_wiki_paths.py --port $DB_PORT --user $DB_USER --password $DB_PASSWORD $SYSDBA' to analyze the collected data."
else
    echo ""
    echo "Crawler encountered an error. Check the output above for details."
fi 