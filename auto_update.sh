#!/bin/bash

# Configuration
PROJECT_DIR="/Users/a1234/Desktop/ai-server/YouTube"
LOG_FILE="$PROJECT_DIR/auto_update.log"
DATE=$(date "+%Y-%m-%d %H:%M:%S")

# Navigate to project directory
cd "$PROJECT_DIR" || exit

# Log start
echo "[$DATE] Starting daily update..." >> "$LOG_FILE"

# Run Data Fetching & Analysis via Docker
# We use 'run --rm' to clean up container after exit
echo "[$DATE] Running YIAPS in Docker..." >> "$LOG_FILE"
/usr/local/bin/docker-compose run --rm yiaps sh -c "python fetch_data.py && python analyze_data.py" >> "$LOG_FILE" 2>&1

# Git Sync
echo "[$DATE] Syncing with GitHub..." >> "$LOG_FILE"
git add -f data/*.csv dashboard_data.json dashboard_data.js index.html
git commit -m "Daily Update: $DATE" >> "$LOG_FILE" 2>&1
git push origin main >> "$LOG_FILE" 2>&1

echo "[$DATE] Update completed." >> "$LOG_FILE"
