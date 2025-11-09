#!/bin/bash

# Simple test script for MCP Drive-Time Plotter (FAST VERSION)
# Just run: ./test.sh

# Activate virtual environment
source .venv/bin/activate

# Load API key from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run a simple test
echo "🚀 Testing MCP Drive-Time Plotter (Fast Mode)"
echo "Route: Mountain View, CA → San Francisco, CA"
echo "Time: 8:00 AM - 9:00 AM (every 15 minutes)"
echo ""
echo "⚡ Using parallel requests for maximum speed..."
echo ""

python cli/driveplot_fast.py \
  --origin "Mountain View, CA" \
  --destination "San Francisco, CA" \
  --date 2025-11-20 \
  --start 08:00 --end 09:00 --interval 15 \
  --ascii --yes

echo ""
echo "✅ Test complete!"
