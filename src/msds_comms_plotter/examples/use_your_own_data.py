#!/usr/bin/env python3
"""Feed a chart your own data instead of the bundled table.

`linked_scatter_passing(stats=df)` accepts any DataFrame with these columns:
    player, team, position, passes, passes_completed, minutes_played
Here we start from the bundled table and keep only high-volume passers, but you
could read your own parquet/CSV with pandas instead.

    python -m msds_comms_plotter.examples.use_your_own_data   ->  ./passing_filtered.html
"""

from pathlib import Path

from msds_comms_plotter import altair_charts as ac, worldcup

OUT = Path.cwd() / "passing_filtered.html"


def main() -> None:
    stats = worldcup.sample_player_match_stats()      # bundled table
    # ...or your own:  import pandas as pd; stats = pd.read_parquet("my_data.parquet")

    stats = stats[stats["passes"] >= 30]              # example filter
    ac.linked_scatter_passing(stats=stats).save(OUT, inline=True)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
