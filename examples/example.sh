#!/usr/bin/env bash
set -euo pipefail

python cli/driveplot.py \
  --origin "Ferry Building, San Francisco" \
  --destination "Stanford University" \
  --date 2025-11-18 \
  --start 07:00 --end 10:00 --interval 15 \
  --provider google \
  --ascii \
  --save-map map.png \
  --yes
