from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List

from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

from .google_maps import (
    GoogleMapsError,
    build_static_map,
    directions_duration_in_traffic,
    geocode_address,
)
from .utils import LatLng, Place, minute_grid, sleep_backoff

load_dotenv()

mcp = FastMCP(
    name="DriveTime Plotter",
    instructions=(
        "Tools for verifying locations, computing traffic-aware ETAs over a time grid, "
        "and generating static maps for origin/destination. Uses Google Maps Platform.\n\n"
        "IMPORTANT USAGE PATTERN:\n"
        "1. When user asks about traffic/drive times, respond QUICKLY:\n"
        "   - Show simple text plot\n"
        "   - Give best/worst times (consider human sleep/work schedules)\n"
        "   - Provide one clear recommendation\n"
        "   - Ask if they want more detailed analysis\n\n"
        "2. Provide detailed analysis ONLY if:\n"
        "   - User explicitly asks for it\n"
        "   - User has specific constraints (flight time, meeting, etc.)\n"
        "   - User says 'yes' to wanting more details\n\n"
        "3. Consider realistic human constraints:\n"
        "   - Don't recommend 12 AM-5 AM unless user specifically mentions it\n"
        "   - Consider work hours, sleep needs, meal times\n"
        "   - Give time ranges, not exact times\n\n"
        "4. Speed requirements:\n"
        "   - Initial response: < 10 seconds total\n"
        "   - Be concise first, detailed on request\n\n"
        "See CLAUDE_CODE_USAGE.md for detailed behavior guidelines."
    ),
)


@mcp.tool()
def geocode(query: str) -> dict:
    """Geocode a textual place. Returns up to 5 candidates with formatted address and lat/lng."""
    try:
        candidates = geocode_address(query)
        return {
            "candidates": [
                {
                    "formatted_address": c.formatted_address,
                    "lat": c.location.lat,
                    "lng": c.location.lng,
                    "place_id": c.place_id,
                }
                for c in candidates
            ]
        }
    except GoogleMapsError as e:
        return {"error": str(e)}


@mcp.tool()
def static_map(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> dict:
    """Return a Google Static Maps URL with start/end markers."""
    url = build_static_map(LatLng(origin_lat, origin_lng), LatLng(dest_lat, dest_lng))
    return {"url": url}


@mcp.tool()
def eta_series(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    date: str,
    start: str,
    end: str,
    interval_minutes: int = 15,
    tz: str = "America/Los_Angeles",
    include_plot: bool = False,
) -> dict:
    """Compute optimistic/pessimistic ETAs across a time grid for the given date.

    Returns dict with ISO8601 times and durations (minutes) for two traffic models.

    Args:
        origin_lat: Origin latitude
        origin_lng: Origin longitude
        dest_lat: Destination latitude
        dest_lng: Destination longitude
        date: Date string in YYYY-MM-DD format
        start: Start time in HH:MM format
        end: End time in HH:MM format
        interval_minutes: Minutes between samples (default: 15)
        tz: Timezone string (default: "America/Los_Angeles")
        include_plot: If True, generate matplotlib PNG as base64 (for Claude chat).
                     If False, return only data (for Claude Code to render ASCII).
    """
    origin = LatLng(origin_lat, origin_lng)
    dest = LatLng(dest_lat, dest_lng)
    dts = minute_grid(date, start, end, interval_minutes, tz)

    rows: List[dict] = []
    times = []
    opt_min = []
    pes_min = []

    for i, dt in enumerate(dts, start=1):
        epoch = int(dt.timestamp())
        optimistic_sec = directions_duration_in_traffic(origin, dest, epoch, "optimistic")
        pessimistic_sec = directions_duration_in_traffic(origin, dest, epoch, "pessimistic")

        opt_val = round(optimistic_sec / 60, 1)
        pes_val = round(pessimistic_sec / 60, 1)

        rows.append(
            {
                "departure": dt.isoformat(),
                "optimistic_min": opt_val,
                "pessimistic_min": pes_val,
                "average_min": round((opt_val + pes_val) / 2, 1),
            }
        )
        times.append(dt.strftime("%H:%M"))
        opt_min.append(opt_val)
        pes_min.append(pes_val)

        sleep_backoff(i)

    # Calculate key insights
    avg_min = [(o + p) / 2 for o, p in zip(opt_min, pes_min)]
    min_idx = avg_min.index(min(avg_min))
    max_idx = avg_min.index(max(avg_min))

    result = {
        "series": rows,
        "insights": {
            "best_time": {
                "departure": times[min_idx],
                "average_min": round(avg_min[min_idx], 1),
                "optimistic_min": opt_min[min_idx],
                "pessimistic_min": pes_min[min_idx],
            },
            "worst_time": {
                "departure": times[max_idx],
                "average_min": round(avg_min[max_idx], 1),
                "optimistic_min": opt_min[max_idx],
                "pessimistic_min": pes_min[max_idx],
            },
            "time_difference_min": round(avg_min[max_idx] - avg_min[min_idx], 1),
        }
    }

    # Generate plot if requested (for Claude chat)
    if include_plot:
        try:
            import base64
            import io
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(12, 7))

            x = list(range(len(times)))

            # Plot three lines
            ax.plot(x, opt_min, label='Optimistic', color='cyan', linewidth=2)
            ax.plot(x, pes_min, label='Pessimistic', color='magenta', linewidth=2)
            ax.plot(x, avg_min, label='Average', color='white', linewidth=2)

            # Highlight min/max points
            ax.scatter([min_idx], [avg_min[min_idx]], color='green', s=200, zorder=5, label=f'Best: {times[min_idx]}')
            ax.scatter([max_idx], [avg_min[max_idx]], color='yellow', s=200, zorder=5, label=f'Worst: {times[max_idx]}')

            # X-axis: show markers every 30 min, labels only at top of hour
            step_30min = max(1, int((30 // interval_minutes)))
            xtick_positions = list(range(0, len(times), step_30min))
            xtick_labels = []
            for idx in xtick_positions:
                hour, minute = times[idx].split(':')
                if minute == '00':
                    xtick_labels.append(hour.lstrip('0') or '0')
                else:
                    xtick_labels.append('')

            ax.set_xticks(xtick_positions)
            ax.set_xticklabels(xtick_labels)

            ax.set_title('Driving Time vs Departure Time', fontsize=16, color='white')
            ax.set_xlabel('Departure Time (hour)', fontsize=12, color='white')
            ax.set_ylabel('Minutes', fontsize=12, color='white')
            ax.legend(loc='best', facecolor='#1e1e1e', edgecolor='white', labelcolor='white')
            ax.grid(True, alpha=0.3, color='gray')

            # Dark theme
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('white')

            # Convert to base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

            result["plot_png_base64"] = img_base64

        except ImportError:
            result["plot_error"] = "matplotlib not available - install with: pip install matplotlib"

    return result


if __name__ == "__main__":
    # Direct execution mode; compatible with `python -m mcp_server.server`
    mcp.run()
