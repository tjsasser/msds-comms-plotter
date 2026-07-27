# FIFA World Cup 2022 — Player Statistics

Per-player, per-match statistics for the 2022 FIFA World Cup (Qatar), built from
[StatsBomb open data](https://github.com/statsbomb/open-data) (free, event-level;
`competition_id=43`, `season_id=106`, 64 matches).

## Regenerating the data

```bash
pip install -e .
python -m msds_comms_plotter.worldcup
```

This downloads the raw JSON to `data/raw/statsbomb/` (cached, ~193 MB, git-ignored)
and writes the processed table to `data/processed/`.

The raw event data is also committed in compact form as
`data/raw/wc2022_raw.tar.xz` (~12 MB; minified JSON, solid `xz -9`). To restore
the loose JSON tree the pipeline reads from:

```bash
tar -xJf data/raw/wc2022_raw.tar.xz -C data/raw
```

Processed table written to `data/processed/`:

| File | Grain | Rows |
|------|-------|------|
| `wc2022_player_match_stats.parquet` | one row per player per match | ~3,244 |

Load with pandas:

```python
import pandas as pd
df = pd.read_parquet("data/processed/wc2022_player_match_stats.parquet")
```

## Columns

**Identity / context:** `player_id`, `player`, `team`, `match_id`, `match_date`,
`stage`, `home_team`, `away_team`, `home_score`, `away_score`.

**Appearance:** `minutes_played` (approx., from starting XI + substitutions +
red cards), `starter`, `position`.

**Attacking:** `goals`, `penalty_goals`, `own_goals`, `assists`, `key_passes`,
`shots`, `shots_on_target`, `xg` (StatsBomb expected goals).

**Passing:** `passes`, `passes_completed`, `pass_completion_pct`, `crosses`,
`free_kicks_taken`.

**Dribbling:** `dribbles`, `dribbles_completed`.

**Defending:** `tackles`, `interceptions`, `blocks`, `ball_recoveries`,
`clearances`.

**Discipline:** `fouls_committed`, `fouls_won`, `yellow_cards`, `red_cards`
(a second yellow counts as both a yellow and a red).

## Passing chart (Altair)

`msds_comms_plotter.altair_charts` builds one chart — **Passing: volume vs
accuracy** — themed with `chartkit`. It's a linked-brush scatter (passes
attempted vs pass completion %, colored by position) with a count-by-position
bar chart, a player-name search box, and a color-scheme dropdown. See the
[chart cookbook](chart_cookbook.md) for the code, or just call it:

```python
import pandas as pd
from msds_comms_plotter import altair_charts as ac, worldcup

stats = pd.read_parquet(worldcup.PROCESSED_DIR / "wc2022_player_match_stats.parquet")
chart = ac.linked_scatter_passing(stats=stats)
chart.save("passing.html")
```

Or run the example, which builds it and opens it in your browser:

```bash
python examples/show_wc2022_charts.py   # -> reports/figures/passing_chart.html
```

**Interactivity:** hover tooltips throughout; drag a box on the scatter to
recount the bars; type in the player search box to filter both views; switch the
color-scheme dropdown (fifteen categorical schemes) to recolor live.

**Fonts for PNG export:** the HTML output uses the browser's fonts, but the PNG
backend (`vl-convert`) does not read system fonts automatically. The module
best-effort-registers the usual font directories so JetBrains Mono is picked up;
without the font installed, PNGs fall back to a generic monospace (nothing
breaks). See `chartkit`'s font note in the top-level README.

## Notes / validation

- Penalty **shootout** goals (StatsBomb period 5) are excluded from all stats,
  matching official statistics.
- Sanity checks against the real tournament: top scorers Kylian Mbappé (8) and
  Lionel Messi (7); 169 goals from open play/penalties + 3 own goals = **172**
  total goals, matching the official count.
