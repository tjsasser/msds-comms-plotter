#!/usr/bin/env python3
"""Build the five World Cup 2022 Altair charts and open them in a browser.

Run this for an interactive gallery. Every chart has hover tooltips; the line
and scatter charts also zoom and pan (scroll to zoom, drag to pan):

    python examples/show_wc2022_charts.py

What it does:

1. Loads the processed data (``data/processed/*.parquet``); if that's missing,
   it builds the tables from the cached StatsBomb JSON. That cache lives in the
   compressed archive, so unpack it once first::

       tar -xJf data/raw/wc2022_raw.tar.xz -C data/raw

2. Builds all five charts (bar, line, scatter, histogram, heatmap) via
   :mod:`msds_comms_plotter.altair_charts`, themed with ``chartkit``.
3. Stacks them into one page and writes a **self-contained** HTML file
   (``inline=True`` embeds the Vega libraries, so it stays interactive with no
   internet connection and no local server).
4. Opens that file in your default web browser.

The output is written to ``reports/figures/wc2022_altair_gallery.html`` — open
it again any time without re-running.
"""

from __future__ import annotations

import webbrowser
from pathlib import Path

import altair as alt
import pandas as pd

from msds_comms_plotter import altair_charts as ac
from msds_comms_plotter import worldcup

PROCESSED = worldcup.PROJECT_ROOT / "data" / "processed"
OUT = worldcup.PROJECT_ROOT / "reports" / "figures" / "wc2022_altair_gallery.html"


def _load():
    """Return (goals, player_match_stats), building them if not already cached."""
    goals_path = PROCESSED / "wc2022_goals.parquet"
    stats_path = PROCESSED / "wc2022_player_match_stats.parquet"
    if goals_path.exists() and stats_path.exists():
        return pd.read_parquet(goals_path), pd.read_parquet(stats_path)

    print("Processed tables not found — building from the StatsBomb cache.")
    print("(If this fails, unpack the raw data first: "
          "tar -xJf data/raw/wc2022_raw.tar.xz -C data/raw)")
    goals = worldcup.build_goal_events()
    stats = worldcup.build_all()
    return goals, stats


def build_gallery() -> alt.VConcatChart:
    """Assemble all six charts into a single vertically stacked view."""
    goals, stats = _load()
    charts = [
        ac.bar_goals_by_team(goals=goals),
        ac.line_cumulative_goals(goals=goals),
        ac.scatter_xg_vs_goals(stats=stats),
        ac.histogram_goal_minutes(goals=goals),
        ac.heatmap_team_phase(goals=goals),
        ac.linked_scatter_goals_by_team(stats=stats),  # drag a box to filter
    ]
    # Independent color scales so the heatmap's sequential ramp doesn't leak
    # into the other charts.
    return (alt.vconcat(*charts)
            .resolve_scale(color="independent")
            .properties(title="World Cup 2022 — an Altair chart gallery"))


def main() -> None:
    gallery = build_gallery()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:  # inline=True embeds Vega JS so the file works offline, no server
        gallery.save(OUT, inline=True)
    except Exception:  # pragma: no cover - falls back to CDN-linked HTML
        gallery.save(OUT)

    print(f"Wrote {OUT}")
    url = OUT.resolve().as_uri()
    if webbrowser.open(url):
        print(f"Opened {url} in your default browser.")
    else:  # headless / no browser available
        print("Could not launch a browser automatically. Open this file "
              f"manually:\n  {OUT}")


if __name__ == "__main__":
    main()
