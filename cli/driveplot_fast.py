from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

import plotext as plt
import requests

from mcp_server.google_maps import (
    geocode_address,
    directions_duration_in_traffic,
    build_static_map,
    GoogleMapsError,
)
from mcp_server.utils import LatLng, minute_grid

console = Console()
load_dotenv()


def ask_confirm(prompt: str) -> bool:
    resp = input(f"{prompt} [y/N]: ").strip().lower()
    return resp in {"y", "yes"}


def save_image(url: str, path: str) -> None:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)


def fetch_single_eta(origin: LatLng, dest: LatLng, dt: datetime, traffic_model: str, max_retries: int = 3) -> tuple[datetime, str, float]:
    """Fetch a single ETA for a given time and traffic model with retry logic."""
    import time
    epoch = int(dt.timestamp())

    for attempt in range(max_retries):
        try:
            duration_sec = directions_duration_in_traffic(origin, dest, epoch, traffic_model)
            duration_min = round(duration_sec / 60, 1)
            return (dt, traffic_model, duration_min)
        except Exception as e:
            if attempt < max_retries - 1:
                # Wait a bit before retrying (exponential backoff)
                wait_time = (attempt + 1) * 0.5
                time.sleep(wait_time)
            else:
                # Final attempt failed, return None to indicate failure
                console.print(f"[yellow]Warning: Failed to fetch {traffic_model} for {dt.strftime('%H:%M')} after {max_retries} attempts[/yellow]")
                return (dt, traffic_model, None)


def run_cli(args: argparse.Namespace) -> int:
    # 1) Geocode origin / destination
    orig_candidates = geocode_address(args.origin)
    dest_candidates = geocode_address(args.destination)

    origin = orig_candidates[0]
    dest = dest_candidates[0]

    console.print("[bold]Origin candidates:[/bold]")
    for i, c in enumerate(orig_candidates, start=1):
        console.print(f"  {i}. {c.formatted_address}  ({c.location.lat:.6f},{c.location.lng:.6f})")
    console.print("[bold]Destination candidates:[/bold]")
    for i, c in enumerate(dest_candidates, start=1):
        console.print(f"  {i}. {c.formatted_address}  ({c.location.lat:.6f},{c.location.lng:.6f})")

    if not args.yes:
        if not ask_confirm(
            f"Proceed with\n  ORIGIN: {origin.formatted_address} ({origin.location.as_str()})\n  DEST:   {dest.formatted_address} ({dest.location.as_str()})"
        ):
            console.print("Okay. Re-run with --origin/--destination set to lat,lng directly.")
            return 2

    # 2) Optional static map
    if args.save_map:
        url = build_static_map(origin.location, dest.location)
        save_image(url, args.save_map)
        console.print(f"Saved static map → {args.save_map}")

    # 3) Build time grid
    dts = minute_grid(args.date, args.start, args.end, args.interval, args.tz)

    times: List[str] = []
    opt_min: List[float] = []
    pes_min: List[float] = []

    # 4) Fetch ETAs in parallel using ThreadPoolExecutor with smart retry
    console.print(f"\n[bold]Fetching {len(dts)} time points in parallel...[/bold]")

    # Create all tasks (2 per time point: optimistic + pessimistic)
    tasks = []
    for dt in dts:
        tasks.append((origin.location, dest.location, dt, "optimistic"))
        tasks.append((origin.location, dest.location, dt, "pessimistic"))

    results = {}
    failed_tasks = tasks.copy()  # Start with all tasks
    retry_round = 0
    max_retry_rounds = 3

    # Retry loop: Keep retrying failed requests until all succeed or max rounds reached
    while failed_tasks and retry_round < max_retry_rounds:
        retry_round += 1
        current_workers = 30 if retry_round == 1 else 10  # First round: 30 workers, retries: 10 workers

        round_description = "Querying Google Maps API..." if retry_round == 1 else f"Retry round {retry_round - 1}: retrying {len(failed_tasks)} failed queries..."

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(round_description, total=len(failed_tasks))

            # Use ThreadPoolExecutor for parallel requests
            with ThreadPoolExecutor(max_workers=current_workers) as executor:
                future_to_args = {
                    executor.submit(fetch_single_eta, *task_args): task_args
                    for task_args in failed_tasks
                }

                new_failed_tasks = []
                for future in as_completed(future_to_args):
                    dt, traffic_model, duration_min = future.result()
                    if dt not in results:
                        results[dt] = {}
                    # Store valid results or track failures
                    if duration_min is not None:
                        results[dt][traffic_model] = duration_min
                    else:
                        # Remember this failed task for next retry round
                        new_failed_tasks.append(future_to_args[future])
                    progress.advance(task)

                failed_tasks = new_failed_tasks

        # Log progress after each round
        if failed_tasks and retry_round < max_retry_rounds:
            console.print(f"[yellow]{len(failed_tasks)} queries still failed, will retry...[/yellow]\n")

    # Final report on any remaining failures
    if failed_tasks:
        console.print(f"[yellow]Warning: {len(failed_tasks)} queries failed after {max_retry_rounds} rounds of retries[/yellow]")

    # 5) Sort results by time and extract values, filtering out incomplete data
    sorted_times = sorted(results.keys())
    failed_count = 0
    for dt in sorted_times:
        opt = results[dt].get("optimistic")
        pes = results[dt].get("pessimistic")

        # Only include time points where both models succeeded
        if opt is not None and pes is not None:
            times.append(dt.strftime("%H:%M"))
            opt_min.append(opt)
            pes_min.append(pes)
        else:
            failed_count += 1

    if failed_count > 0:
        console.print(f"\n[yellow]Note: {failed_count} time points were skipped due to API failures[/yellow]")

    if len(times) == 0:
        console.print("[red]Error: No valid data points retrieved. Please check your API key and network connection.[/red]")
        return 1

    # 6) Print a nice table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Departure", justify="right")
    table.add_column("Optimistic (min)", justify="right")
    table.add_column("Pessimistic (min)", justify="right")
    for t, o, p in zip(times, opt_min, pes_min):
        table.add_row(t, f"{o:.1f}", f"{p:.1f}")
    console.print("\n")
    console.print(table)

    # 7) ASCII Plot
    if args.ascii:
        plt.clear_figure()

        # Set plot size with 5:3 aspect ratio (width:height)
        # plotext uses character dimensions, adjust for terminal
        plt.plotsize(100, 30)  # 100 chars wide, 30 chars tall ≈ 5:3 ratio

        x = list(range(len(times)))

        # Calculate average line
        avg_min = [(o + p) / 2 for o, p in zip(opt_min, pes_min)]

        # Find min and max on average line
        min_idx = avg_min.index(min(avg_min))
        max_idx = avg_min.index(max(avg_min))

        # Plot the three lines
        plt.plot(x, opt_min, label="optimistic", color="cyan")
        plt.plot(x, pes_min, label="pessimistic", color="magenta")
        plt.plot(x, avg_min, label="average", color="white")

        # X-axis: Show markers every 30 minutes, but labels only at top of hour
        step_30min = max(1, int((30 // args.interval)))
        xtick_positions = list(range(0, len(times), step_30min))

        # Create labels: only show hour labels (like "7", "12", "16")
        # For times at top of hour, show just the hour number
        # For other 30-min marks, show empty string
        xtick_labels = []
        for idx in xtick_positions:
            time_str = times[idx]
            hour, minute = time_str.split(':')
            if minute == '00':
                # Top of hour: show just hour number
                xtick_labels.append(hour.lstrip('0') or '0')  # Remove leading zero
            else:
                # Half-hour mark: empty label (but marker still shows)
                xtick_labels.append('')

        plt.xticks(xtick_positions, xtick_labels)

        plt.title("Driving time vs departure time")
        plt.xlabel("Departure time (hour)")
        plt.ylabel("Minutes")

        # VS Code Dark+ theme colors
        plt.canvas_color("black")  # Dark background
        plt.axes_color("black")     # Dark background for plot area
        plt.ticks_color("white")    # White text for ticks and labels

        plt.show()

        # Print min/max points on average line
        console.print("\n[bold]Key Points (Average Drive Time):[/bold]")
        console.print(f"  [green]🟢 Best time:[/green]    {times[min_idx]} → {avg_min[min_idx]:.1f} minutes")
        console.print(f"  [yellow]🟡 Worst time:[/yellow]   {times[max_idx]} → {avg_min[max_idx]:.1f} minutes")
        console.print(f"  [cyan]📊 Difference:[/cyan] {avg_min[max_idx] - avg_min[min_idx]:.1f} minutes")

        # Also print simple text plot for Claude Code
        print("\n" + "="*80)
        print("SIMPLE TEXT PLOT (for Claude Code responses)")
        print("="*80 + "\n")
        print_simple_text_plot(times, opt_min, pes_min, avg_min, min_idx, max_idx, args.interval)

    return 0


def print_simple_text_plot(times, opt_min, pes_min, avg_min, min_idx, max_idx, interval):
    """Print a simple text plot using +, o, * characters"""

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

    # Print plot
    for i in range(height):
        val = max_val - (i / (height - 1)) * (max_val - min_val)
        print(f"{int(val):3d} min | {''.join(grid[i])}")

    print(f"        +{'-' * width}")

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

    print(x_axis)
    print("          Hour of Day")
    print()
    print("LEGEND:")
    print("  + = Optimistic  |  o = Pessimistic  |  * = Average")
    print(f"  B = Best ({times[min_idx]}, {avg_min[min_idx]:.1f} min)  |  W = Worst ({times[max_idx]}, {avg_min[max_idx]:.1f} min)")
    print()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Plot driving time across a day (FAST VERSION with parallel requests)")
    p.add_argument("--origin", required=True, help="Origin (text or 'lat,lng')")
    p.add_argument("--destination", required=True, help="Destination (text or 'lat,lng')")
    p.add_argument("--date", required=True, help="YYYY-MM-DD (local to tz)")
    p.add_argument("--start", required=True, help="HH:MM 24h")
    p.add_argument("--end", required=True, help="HH:MM 24h")
    p.add_argument("--interval", type=int, default=15, help="Minutes between samples")
    p.add_argument("--provider", choices=["google", "apple"], default="google")
    p.add_argument("--tz", default="America/Los_Angeles")
    p.add_argument("--ascii", action="store_true", help="Render ASCII plot to terminal")
    p.add_argument("--save-map", metavar="PNG_PATH", help="Save a static map PNG")
    p.add_argument("--yes", action="store_true", help="Skip interactive confirmation")

    args = p.parse_args()
    raise SystemExit(run_cli(args))
