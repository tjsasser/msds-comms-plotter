#!/usr/bin/env python3
"""Build the "Passing: volume vs accuracy" chart and open it in a browser.

Works from anywhere against the installed package — it uses the data bundled
inside `msds_comms_plotter` and writes the output to the folder you run it from.

    python show_wc2022_charts.py   ->  ./passing_chart.html  (opens in browser)
"""

import webbrowser
from pathlib import Path

from msds_comms_plotter import altair_charts as ac

# Write next to wherever you run this, NOT inside the installed package.
OUT = Path.cwd() / "passing_chart.html"


def main() -> None:
    chart = ac.linked_scatter_passing()          # uses the bundled World Cup data
    chart.save(OUT, inline=True)                  # self-contained, works offline
    print(f"Wrote {OUT}")
    if webbrowser.open(OUT.resolve().as_uri()):
        print("Opened it in your default browser.")
    else:
        print(f"Open this file manually:\n  {OUT}")


if __name__ == "__main__":
    main()
