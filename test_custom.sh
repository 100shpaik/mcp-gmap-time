#!/bin/bash

# Custom test script - edit the variables below to test your own route
# Uses FAST parallel version for maximum speed
# Run: ./test_custom.sh

# Activate virtual environment
source .venv/bin/activate
# Load API key from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# ===== CUSTOMIZE THESE =====
ORIGIN="Evans Hall, UC Berkeley"
DESTINATION="San Francisco International Airport (SFO)"
DATE="2025-11-20"
START_TIME="00:00"
END_TIME="23:59"
INTERVAL=15  # minutes between samples (15 min gives detailed analysis)
SAVE_MAP="outputs/route_map.png"  # Leave empty ("") to skip saving map
# ===========================

echo "🚀 Testing your custom route (Fast Mode)"
echo "From: $ORIGIN"
echo "To: $DESTINATION"
echo "Date: $DATE"
echo "Time range: $START_TIME - $END_TIME (every $INTERVAL minutes)"
echo ""
echo "⚡ Using parallel API requests for fast results..."
echo ""

if [ -z "$SAVE_MAP" ]; then
  # No map
  python cli/driveplot_fast.py \
    --origin "$ORIGIN" \
    --destination "$DESTINATION" \
    --date "$DATE" \
    --start "$START_TIME" --end "$END_TIME" --interval "$INTERVAL" \
    --ascii --yes
else
  # With map
  python cli/driveplot_fast.py \
    --origin "$ORIGIN" \
    --destination "$DESTINATION" \
    --date "$DATE" \
    --start "$START_TIME" --end "$END_TIME" --interval "$INTERVAL" \
    --ascii --save-map "$SAVE_MAP" --yes

  if [ -f "$SAVE_MAP" ]; then
    echo ""
    echo "📍 Map saved to: $SAVE_MAP"
    echo "   Open it with: open $SAVE_MAP"
  fi
fi

echo ""
echo "✅ Test complete!"
