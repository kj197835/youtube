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
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "[$DATE] ERROR: Data update failed with exit code $EXIT_CODE. Aborting git push." >> "$LOG_FILE"
    exit $EXIT_CODE
fi

echo "[$DATE] Data update successful. Proceeding to Build & Deploy..." >> "$LOG_FILE"
# Build React Dashboard
echo "[$DATE] Building Dashboard..." >> "$LOG_FILE"
/usr/local/bin/docker-compose run --rm dashboard sh -c "npm install && npm run build" >> "$LOG_FILE" 2>&1

# Copy build artifacts to root for GitHub Pages
echo "[$DATE] Deploying to root..." >> "$LOG_FILE"
cp -r dashboard/dist/* .

# Git Sync
echo "[$DATE] Syncing with GitHub..." >> "$LOG_FILE"
git add -f data/*.csv dashboard_data.json analyze_data.py fetch_data.py auto_update.sh index.html assets/
git commit -m "Daily Update: $DATE" >> "$LOG_FILE" 2>&1
git push origin main >> "$LOG_FILE" 2>&1

echo "[$DATE] Update completed." >> "$LOG_FILE"
