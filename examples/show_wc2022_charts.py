#!/usr/bin/env python3
"""Build the "Passing: volume vs accuracy" chart and open it in a browser.

Run it:  python examples/show_wc2022_charts.py

What it does:

1. Loads the per-player-per-match table from the committed processed parquet
   (``data/processed/wc2022_player_match_stats.parquet``). If that's missing,
   it builds the table from the cached StatsBomb JSON — unpack it once with::

       tar -xJf data/raw/wc2022_raw.tar.xz -C data/raw

2. Builds the passing chart via
   :func:`msds_comms_plotter.altair_charts.linked_scatter_passing` — a
   linked-brush scatter (passes vs completion %) with count-by-position bars, a
   player-name search box, and a color-scheme dropdown.
3. Writes a **self-contained** HTML file (``inline=True`` embeds the Vega
   libraries, so it stays interactive offline) and opens it in your browser.

Output: ``reports/figures/passing_chart.html`` — open it again any time.
"""

from __future__ import annotations

import webbrowser

import pandas as pd

from msds_comms_plotter import altair_charts as ac
from msds_comms_plotter import worldcup

PROCESSED = worldcup.PROJECT_ROOT / "data" / "processed"
OUT = worldcup.PROJECT_ROOT / "reports" / "figures" / "passing_chart.html"


def load_stats():
    """Return the per-player-per-match table, building it if not cached."""
    path = PROCESSED / "wc2022_player_match_stats.parquet"
    if path.exists():
        return pd.read_parquet(path)
    print("Processed table not found — building from the StatsBomb cache.")
    print("(If this fails, unpack the raw data first: "
          "tar -xJf data/raw/wc2022_raw.tar.xz -C data/raw)")
    return worldcup.build_all()


def main() -> None:
    stats = load_stats()
    chart = ac.linked_scatter_passing(stats=stats)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:  # inline=True embeds Vega JS so the file works offline, no server
        chart.save(OUT, inline=True)
    except Exception:  # pragma: no cover - falls back to CDN-linked HTML
        chart.save(OUT)

    print(f"Wrote {OUT}")
    url = OUT.resolve().as_uri()
    if webbrowser.open(url):
        print(f"Opened {url} in your default browser.")
    else:  # headless / no browser available
        print("Could not launch a browser automatically. Open this file "
              f"manually:\n  {OUT}")


if __name__ == "__main__":
    main()
