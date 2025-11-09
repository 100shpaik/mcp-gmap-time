# Drive-Time Plotter MCP

A Model Context Protocol (MCP) server that analyzes traffic patterns throughout the day using Google Maps API, providing fast visual insights and recommendations.

**Motivated by the [Hugging Face MCP Hackathon](https://huggingface.co/MCP-1st-Birthday)** - A production-ready MCP server for intelligent commute planning.

## What It Does

- Analyzes traffic patterns across 24 hours with 15-minute intervals
- Shows optimistic/pessimistic/average drive time predictions
- Completes full analysis in ~4 seconds using parallel API requests (120x faster than sequential!)
- Works with Claude Desktop, Claude Code, and standalone CLI
- Generates both terminal ASCII plots and route maps

## Quick Start

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2. Setup API Key

Get your Google Maps API key from https://console.cloud.google.com/apis/credentials

Enable these APIs:
- Geocoding API
- Directions API
- Maps Static API

**Create `.env` file from template:**
```bash
cp .env.example .env
# Edit .env and add your key:
# GOOGLE_MAPS_API_KEY=your_key_here
```

### 3. Test

```bash
./test.sh
```

You should see traffic analysis in ~4 seconds!

---

## Usage

### Terminal (Fastest)

```bash
./test_custom.sh
```

Edit `test_custom.sh` to customize:
- Origin/Destination (default: Evans Hall, UC Berkeley → SFO)
- Date
- Time range
- Interval

**Or use the CLI directly:**

```bash
python cli/driveplot_fast.py \
  --origin "Your Home" \
  --destination "Your Work" \
  --date 2025-11-20 \
  --start 06:00 --end 10:00 \
  --interval 15 \
  --ascii --save-map outputs/route.png --yes
```

### As MCP Server with Claude

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "drivetime-plotter": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "GOOGLE_MAPS_API_KEY": "your_key_here"
      },
      "cwd": "/path/to/mcp-hackathon"
    }
  }
}
```

Restart Claude Desktop. You can now ask Claude: "When should I drive from X to Y?"

---

## How It Works

### For Terminal Users

1. Run `./test_custom.sh`
2. Get results in ~4 seconds (parallel API calls)
3. See two outputs:
   - **Colored ANSI plot** (beautiful terminal visualization)
   - **Simple text plot** (plain text using +, o, * characters for Claude Code)

### For Claude/Claude Code

When you ask "When should I drive from X to Y?":

1. **Quick Response** (< 10 seconds):
   ```
   [Show simple text plot]
   🟢 BEST: 5-7 AM (35 min)
   🔴 WORST: 2-4 PM (60 min)
   💡 Recommendation: Leave before 7 AM

   Want more details?
   ```

2. **Detailed Response** (if you say yes):
   - Hour-by-hour breakdown
   - Specific scenarios
   - Multiple options

### Key AI Behavior

**Human-Realistic Recommendations:**
- ✅ "Leave 5-7 AM" (reasonable)
- ❌ "Leave 2 AM" (unrealistic for most people - humans need sleep!)

**Adapts to Specificity:**
- Vague question → Quick answer + ask for more
- Specific constraint → Calculate and provide options
- Flight time → Work backwards with buffer

---

## Architecture

### File Structure

```
mcp-hackathon/
├── .env                       # API key (gitignored, copy from .env.example)
├── .env.example               # Template for API key
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup (enables `pip install -e .`)
├── test.sh                    # Quick smoke test (~2 sec)
├── test_custom.sh             # Main usage script (customizable route)
├── outputs/                   # Generated maps and plots (gitignored)
├── cli/
│   └── driveplot_fast.py      # Fast CLI with parallel requests
└── mcp_server/
    ├── __init__.py            # Makes mcp_server a Python package
    ├── server.py              # MCP server (exposes tools to Claude)
    ├── google_maps.py         # Google Maps API integration
    └── utils.py               # Helper functions (LatLng, minute_grid, etc.)
```

### Why These Files?

**Core Files:**
- `cli/driveplot_fast.py` - Standalone terminal tool (works without MCP)
- `mcp_server/server.py` - MCP server for Claude integration
- `mcp_server/google_maps.py` - API calls (shared by CLI and MCP)
- `mcp_server/utils.py` - Shared utilities
- `mcp_server/__init__.py` - Required for Python package (enables `from mcp_server import ...`)

**Configuration:**
- `.env` - Your API key (never committed to git)
- `.env.example` - Template for new users
- `setup.py` - Package metadata and dependencies (needed for `pip install -e .`)
- `requirements.txt` - Direct dependencies list

**Testing:**
- `test.sh` - Quick verification (1-hour window, ~2 seconds)
- `test_custom.sh` - Real usage (24 hours, ~4 seconds)

### API Key Management

**Single Source of Truth:**

```
.env file (GOOGLE_MAPS_API_KEY=...)
  ↓
  ├─→ Shell scripts (loaded via `export $(grep -v '^#' .env | xargs)`)
  └─→ Python code (os.getenv("GOOGLE_MAPS_API_KEY"))
```

Only `mcp_server/google_maps.py` defines:
```python
GOOGLE_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
```

All other code imports and uses this variable.

### Performance

- **Parallel API calls**: Up to 30 concurrent requests (first pass)
- **Smart retry with while loop**: Retries only failed requests with reduced concurrency (10 workers)
- **Multiple retry rounds**: Up to 3 rounds total, ensures maximum success rate
- **Speed**: ~4 seconds for full 24-hour analysis (96 data points)
- **120x speedup** vs sequential approach

---

## MCP Tools Exposed

When running as an MCP server, Claude can use these tools:

### 1. `geocode(query: str)`
- Converts address to coordinates
- Returns candidates with formatted addresses and lat/lng
- Example: "Berkeley, CA" → [(37.8715, -122.2730), ...]

### 2. `static_map(origin_lat, origin_lng, dest_lat, dest_lng)`
- Generates Google Maps static image URL
- Shows route with markers
- Returns URL to PNG image

### 3. `eta_series(...)`
- Gets traffic data across time range
- Returns optimistic/pessimistic/average drive times
- Parameters:
  - `origin_lat`, `origin_lng`
  - `dest_lat`, `dest_lng`
  - `date`, `start_time`, `end_time`
  - `interval_minutes`
  - `include_plot` (optional, for matplotlib PNG in Claude chat)

### Google Maps APIs Used

- **Geocoding API**: Address → Coordinates
- **Directions API**: Traffic-aware route duration
- **Static Maps API**: Route visualization

**Traffic Models:**
- `optimistic` - Best-case scenario (light traffic)
- `pessimistic` - Worst-case scenario (heavy traffic)
- Average - Calculated from both (realistic expectation)

---

## Output Format

### Simple Text Plot (for Claude Code)

```
 66 min |                                  o
 64 min |                                 o ooo
 62 min |                               oo
 ...
 32 min |        **********************
 30 min | +++++++++++++++++++++++++++++++
        +------------------------------------------------------------
          0   1   2   3   4   5   6   7   8   9   10  11  12  ...
          Hour of Day

LEGEND:
  + = Optimistic  |  o = Pessimistic  |  * = Average
  B = Best time   |  W = Worst time
```

**Features:**
- Shows all 24 hours
- Three traffic scenarios
- Marks best/worst times
- Human-readable x-axis (proper spacing for single/double-digit hours)
- No ANSI codes (renders in Claude Code responses)

### Colored ANSI Plot (for Terminal)

Same layout but with beautiful colors using plotext library.

---

## Troubleshooting

### API Errors

**"Missing GOOGLE_MAPS_API_KEY"**
→ Check `.env` file exists and has your key
→ Make sure you copied from `.env.example`: `cp .env.example .env`

**"REQUEST_DENIED"**
→ Enable APIs in Google Cloud Console (Geocoding, Directions, Maps Static)
→ Verify billing is active (you get $200/month free credit)

### Performance Issues

**Retrying failed queries multiple times**
→ Some API requests failing due to rate limits
→ Script automatically retries with reduced concurrency
→ Wait for completion - most queries eventually succeed

**Slow (> 10 seconds)**
→ Network issues
→ Try again later
→ Default: 30 workers → 10 workers for retries (adjustable in code)

### Installation Issues

**"Module not found" when running MCP server**
→ Run `pip install -e .` to install package in editable mode

**"Permission denied" on .sh files**
→ Run `chmod +x test.sh test_custom.sh`

**Output files not saved**
→ Check `outputs/` folder exists (created automatically)
→ Verify path in `--save-map` flag

---

## Cost

**Very cheap!**
- Full 24-hour query (96 points): ~$0.001
- $200/month free credit = ~200,000 queries
- You won't hit limits during development or normal usage

---

## For Hackathon Judges

### What We Built

A production-ready MCP server for traffic analysis with:
- ✅ **120x speedup** (10 min → 4 sec via parallel processing)
- ✅ **Beautiful terminal visualizations** (dual output: ANSI + plain text)
- ✅ **Human-friendly AI behavior** (considers sleep/work schedules)
- ✅ **Smart retry logic** (while loop with multiple rounds, only retries failures)
- ✅ **Clean, publishable code** (minimal necessary files, comprehensive docs)

### Key Innovations

1. **Two-tier response system**
   - Quick answer first (< 10 sec)
   - Detailed analysis on request
   - Prevents slow, overwhelming responses

2. **Human-realistic constraints**
   - Don't recommend 2 AM departures
   - Consider work hours, sleep needs
   - Practical time windows

3. **Dual output formats**
   - Colored ANSI for terminal users
   - Simple text (+, o, *) for Claude Code responses
   - Solves ANSI rendering limitation

4. **Robust API handling**
   - Parallel requests with ThreadPoolExecutor
   - While loop retry (not just 2 passes)
   - Smart concurrency reduction (30 → 10 workers)
   - Graceful degradation on failures

### Track

**Track 1: Building MCP**

This is a complete, production-ready MCP server that:
- Exposes useful tools (geocode, eta_series, static_map)
- Solves real problems (commute planning, meeting scheduling)
- Works with both Claude Desktop and Claude Code
- Has excellent documentation
- Is ready to publish and use

---

## Advanced Usage

### Custom Time Range

```bash
python cli/driveplot_fast.py \
  --origin "Your Home" \
  --destination "Your Work" \
  --date 2025-11-20 \
  --start 06:00 --end 10:00 \  # Morning only
  --interval 30 \               # Every 30 min
  --ascii --yes
```

### Different Intervals

- **15 min**: Detailed analysis (96 data points, ~4 sec)
- **30 min**: Balanced (48 points, ~2 sec)
- **60 min**: Quick overview (24 points, ~1 sec)

### Save Map to outputs/

```bash
python cli/driveplot_fast.py \
  --origin "Berkeley, CA" \
  --destination "San Francisco, CA" \
  --date 2025-11-20 \
  --ascii --save-map outputs/my_route.png --yes
```

---

## Security

✅ **API key protected:**
- Stored in `.env` (gitignored)
- Never committed to version control
- Single source of truth
- Easy to rotate
- Template provided (`.env.example`)

✅ **No hardcoded secrets** anywhere in codebase

✅ **Best practices:**
- Environment variables via python-dotenv
- Clear separation of code and config
- Comprehensive .gitignore

---

## Future Improvements

Ideas for extension:
- Add Apple Maps support (already structured for it)
- Historical data tracking (compare traffic patterns over time)
- Calendar integration (auto-suggest departure times)
- Multiple routes comparison (A vs B)
- Web UI with Gradio (for Track 2 submission)

---

## License

**MIT License** - use freely!

This is the standard license for MCP servers. Feel free to:
- Use in commercial projects
- Modify and redistribute
- Incorporate into closed-source software

---

## Credits

Built for the **Hugging Face MCP Hackathon (Track 1)**

Technologies used:
- **FastMCP** - MCP server framework
- **Google Maps Platform APIs** - Geocoding, Directions, Static Maps
- **plotext** - Terminal plotting
- **rich** - Beautiful terminal output
- **ThreadPoolExecutor** - Parallel API requests

---

## Questions?

For issues or questions:
1. Check the Troubleshooting section above
2. Verify your `.env` file is set up correctly
3. Run `./test.sh` to verify installation
4. Check that Google Maps APIs are enabled in Cloud Console
