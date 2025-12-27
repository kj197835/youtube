#!/bin/bash

# Set PATH for Cron execution
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
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
echo "[$DATE]# 2. Run Data Fetching & AI Analysis" >> "$LOG_FILE"
echo "[$DATE] Running Data Fetching & AI Analysis..." >> "$LOG_FILE"
docker compose run --rm yiaps python fetch_data.py >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "[$DATE] ERROR: Data fetching failed with exit code $EXIT_CODE. Aborting git push." >> "$LOG_FILE"
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
git add -f data/*.csv dashboard_data.json prediction_data.json database.py fetch_data.py prediction.py auto_update.sh index.html assets/ thumbnails/ AI_SOUND_LAB1.png
git commit -m "Daily Update: $DATE" >> "$LOG_FILE" 2>&1
git push origin main >> "$LOG_FILE" 2>&1

echo "[$DATE] Update completed." >> "$LOG_FILE"
