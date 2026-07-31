#!/usr/bin/env python3
"""Save one chart as a static PNG in the current folder.

Needs the PNG extra:  pip install "msds-comms-plotter[png]"

    python -m msds_comms_plotter.examples.save_png   ->  ./passing_chart.png
"""

from pathlib import Path

from msds_comms_plotter import altair_charts as ac

OUT = Path.cwd() / "passing_chart.png"


def main() -> None:
    ac.linked_scatter_passing().save(OUT, ppi=200)   # bundled data
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
