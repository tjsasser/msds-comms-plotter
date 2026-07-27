#!/usr/bin/env python3
"""Build the "Passing: volume vs accuracy" chart and open it in a browser.

Run it:  python examples/show_wc2022_charts.py

Builds the passing chart via
:func:`msds_comms_plotter.altair_charts.linked_scatter_passing` — a linked-brush
scatter (passes vs completion %) with count-by-position bars, a player-name
search box, and a color-scheme dropdown. It uses the data bundled inside the
package, so no raw data, network, or build step is needed. The output is a
**self-contained** HTML file (the Vega libraries are embedded, so it stays
interactive offline).

Output: ``reports/figures/passing_chart.html`` — open it again any time.
"""

from __future__ import annotations

import webbrowser

from msds_comms_plotter import altair_charts as ac
from msds_comms_plotter import worldcup

OUT = worldcup.PROJECT_ROOT / "reports" / "figures" / "passing_chart.html"


def main() -> None:
    chart = ac.linked_scatter_passing()   # uses the bundled World Cup data
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
