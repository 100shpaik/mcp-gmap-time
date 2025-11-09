from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

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
        "1. When user asks about traffic/drive times:\n"
        "   - Call eta_series with include_plot=False (default)\n"
        "   - ALWAYS show the text_plot from the response (it's a visual ASCII plot)\n"
        "   - Give best/worst times (consider human sleep/work schedules)\n"
        "   - Provide one clear recommendation\n\n"
        "2. Text plot visualization:\n"
        "   - The text_plot field contains an ASCII visualization showing all three lines\n"
        "   - Always display it in a code block for proper formatting\n"
        "   - It uses: + (optimistic), o (pessimistic), * (average), B (best), W (worst)\n\n"
        "3. Image plots:\n"
        "   - DO NOT use include_plot=True unless user specifically asks for a PNG image\n"
        "   - Base64 PNG is very large and fills context window\n"
        "   - The text_plot is sufficient for most users\n\n"
        "3. Time windows:\n"
        "   - For 24-hour queries: Use start='00:00' end='23:59'\n"
        "   - Tool now uses parallel processing - full 24 hours completes in ~5 seconds\n"
        "   - No need to reduce time window for performance\n\n"
        "4. Consider realistic human constraints:\n"
        "   - Don't recommend 12 AM-5 AM unless user specifically mentions it\n"
        "   - Consider work hours, sleep needs, meal times\n"
        "   - Give time ranges, not exact times\n\n"
        "5. Response format:\n"
        "   - Be concise and actionable\n"
        "   - Mention best times, worst times, time savings\n"
        "   - Give specific recommendations based on user's scenario"
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


def fetch_single_eta_parallel(
    origin: LatLng, dest: LatLng, dt: datetime, traffic_model: str, max_retries: int = 3
) -> Tuple[datetime, str, Optional[float]]:
    """Fetch a single ETA for parallel execution with retry logic."""
    epoch = int(dt.timestamp())

    for attempt in range(max_retries):
        try:
            duration_sec = directions_duration_in_traffic(origin, dest, epoch, traffic_model)
            duration_min = round(duration_sec / 60, 1)
            return (dt, traffic_model, duration_min)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.5
                time.sleep(wait_time)
            else:
                # Final attempt failed
                return (dt, traffic_model, None)

    return (dt, traffic_model, None)


def generate_simple_text_plot(times, opt_min, pes_min, avg_min, min_idx, max_idx, interval):
    """Generate a simple text plot using +, o, * characters"""

    min_val = min(min(opt_min), min(pes_min))
    max_val = max(max(opt_min), max(pes_min))

    height = 20
    width = len(times)

    def scale(val):
        return int((val - min_val) / (max_val - min_val) * (height - 1))

    # Create grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Plot lines
    for i in range(width):
        opt_y = height - 1 - scale(opt_min[i])
        pes_y = height - 1 - scale(pes_min[i])
        avg_y = height - 1 - scale(avg_min[i])

        if grid[pes_y][i] == ' ':
            grid[pes_y][i] = 'o'
        if grid[opt_y][i] == ' ':
            grid[opt_y][i] = '+'
        if grid[avg_y][i] == ' ':
            grid[avg_y][i] = '*'
        elif grid[avg_y][i] in ['+', 'o']:
            grid[avg_y][i] = '*'

    # Mark best/worst
    min_y = height - 1 - scale(avg_min[min_idx])
    max_y = height - 1 - scale(avg_min[max_idx])
    grid[min_y][min_idx] = 'B'
    grid[max_y][max_idx] = 'W'

    # Build plot string
    lines = []
    for i in range(height):
        val = max_val - (i / (height - 1)) * (max_val - min_val)
        lines.append(f"{int(val):3d} min | {''.join(grid[i])}")

    lines.append(f"        +{'-' * width}")

    # X-axis with proper spacing
    intervals_per_hour = 60 // interval
    x_axis = "          "
    prev_hour_len = 0

    for i, t in enumerate(times):
        hour, minute = t.split(':')
        if minute == '00':
            hour_num = int(hour)
            hour_str = str(hour_num)

            if i == 0:
                spacing = 0
            else:
                spacing = intervals_per_hour - prev_hour_len

            x_axis += " " * spacing + hour_str
            prev_hour_len = len(hour_str)

    lines.append(x_axis)
    lines.append("          Hour of Day")
    lines.append("")
    lines.append("LEGEND:")
    lines.append("  + = Optimistic  |  o = Pessimistic  |  * = Average")
    lines.append(f"  B = Best ({times[min_idx]}, {avg_min[min_idx]:.1f} min)  |  W = Worst ({times[max_idx]}, {avg_min[max_idx]:.1f} min)")

    return "\n".join(lines)


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
    """Compute optimistic/pessimistic ETAs across a time grid for the given date using PARALLEL requests.

    Returns dict with ISO8601 times and durations (minutes) for two traffic models.

    NOTE: The plot (base64 PNG) is VERY LARGE and can fill the context window. Only request it
    when the user specifically asks for a visual plot. Otherwise, use the data to describe findings.

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
        include_plot: If True, generate matplotlib PNG as base64. WARNING: Very large, use sparingly!
    """
    origin = LatLng(origin_lat, origin_lng)
    dest = LatLng(dest_lat, dest_lng)
    dts = minute_grid(date, start, end, interval_minutes, tz)

    # Create all tasks (2 per time point: optimistic + pessimistic)
    tasks = []
    for dt in dts:
        tasks.append((origin, dest, dt, "optimistic"))
        tasks.append((origin, dest, dt, "pessimistic"))

    results = {}
    failed_tasks = tasks.copy()
    retry_round = 0
    max_retry_rounds = 3

    # Retry loop with parallel processing
    while failed_tasks and retry_round < max_retry_rounds:
        retry_round += 1
        current_workers = 30 if retry_round == 1 else 10

        with ThreadPoolExecutor(max_workers=current_workers) as executor:
            future_to_args = {
                executor.submit(fetch_single_eta_parallel, *task_args): task_args
                for task_args in failed_tasks
            }

            new_failed_tasks = []
            for future in as_completed(future_to_args):
                dt, traffic_model, duration_min = future.result()
                if dt not in results:
                    results[dt] = {}
                if duration_min is not None:
                    results[dt][traffic_model] = duration_min
                else:
                    new_failed_tasks.append(future_to_args[future])

            failed_tasks = new_failed_tasks

    # Build output arrays filtering only complete data points
    rows: List[dict] = []
    times = []
    opt_min = []
    pes_min = []

    sorted_times = sorted(results.keys())
    for dt in sorted_times:
        opt = results[dt].get("optimistic")
        pes = results[dt].get("pessimistic")

        # Only include if both models succeeded
        if opt is not None and pes is not None:
            rows.append(
                {
                    "departure": dt.isoformat(),
                    "optimistic_min": opt,
                    "pessimistic_min": pes,
                    "average_min": round((opt + pes) / 2, 1),
                }
            )
            times.append(dt.strftime("%H:%M"))
            opt_min.append(opt)
            pes_min.append(pes)

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
        },
        "text_plot": generate_simple_text_plot(times, opt_min, pes_min, avg_min, min_idx, max_idx, interval_minutes)
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
