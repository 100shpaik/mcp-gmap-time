from __future__ import annotations

import os
import requests
from typing import Dict, List, Tuple

from .utils import LatLng, Place

GOOGLE_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
BASE_GEOCODE = "https://maps.googleapis.com/maps/api/geocode/json"
BASE_DIRECTIONS = "https://maps.googleapis.com/maps/api/directions/json"
BASE_STATIC = "https://maps.googleapis.com/maps/api/staticmap"


class GoogleMapsError(RuntimeError):
    pass


def _require_key():
    if not GOOGLE_KEY:
        raise GoogleMapsError("Missing GOOGLE_MAPS_API_KEY env var")


def geocode_address(query: str) -> List[Place]:
    """Return up to 5 candidates for a textual location."""
    _require_key()
    params = {
        "address": query,
        "key": GOOGLE_KEY,
    }
    r = requests.get(BASE_GEOCODE, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("status") not in {"OK", "ZERO_RESULTS"}:
        raise GoogleMapsError(f"Geocoding failed: {data.get('status')}")
    results = data.get("results", [])[:5]
    out: List[Place] = []
    for res in results:
        loc = res["geometry"]["location"]
        out.append(
            Place(
                query=query,
                formatted_address=res.get("formatted_address", query),
                location=LatLng(loc["lat"], loc["lng"]),
                place_id=res.get("place_id"),
            )
        )
    return out


def directions_duration_in_traffic(
    origin: LatLng,
    destination: LatLng,
    departure_epoch: int,
    traffic_model: str = "best_guess",
) -> int:
    """Return duration_in_traffic in seconds for driving mode.

    traffic_model in {best_guess, optimistic, pessimistic}
    """
    _require_key()
    params = {
        "origin": origin.as_str(),
        "destination": destination.as_str(),
        "mode": "driving",
        "departure_time": departure_epoch,  # must be now or future
        "traffic_model": traffic_model,
        "key": GOOGLE_KEY,
    }
    r = requests.get(BASE_DIRECTIONS, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "OK":
        raise GoogleMapsError(
            f"Directions failed: {data.get('status')} - {data.get('error_message')}"
        )
    route = data["routes"][0]
    leg = route["legs"][0]
    dit = leg.get("duration_in_traffic")
    if not dit:
        # Fallback to plain duration
        dit = leg.get("duration")
    return int(dit["value"])  # seconds


def build_static_map(
    origin: LatLng,
    destination: LatLng,
    size: str = "640x400",
    scale: int = 2,
    maptype: str = "roadmap",
) -> str:
    """Return a Static Maps URL with origin/destination markers."""
    _require_key()
    markers = [
        f"color:green|label:S|{origin.as_str()}",
        f"color:red|label:E|{destination.as_str()}",
    ]
    params = {
        "size": size,
        "scale": scale,
        "maptype": maptype,
        "markers": markers,
        "key": GOOGLE_KEY,
    }
    # requests will encode list params as multiple keys as required
    from urllib.parse import urlencode

    return f"{BASE_STATIC}?{urlencode(params, doseq=True)}"
