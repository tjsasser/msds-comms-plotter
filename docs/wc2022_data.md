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
and writes the processed tables to `data/processed/`.

The raw event data is also committed in compact form as
`data/raw/wc2022_raw.tar.xz` (~12 MB; minified JSON, solid `xz -9`). To restore
the loose JSON tree the pipeline reads from:

```bash
tar -xJf data/raw/wc2022_raw.tar.xz -C data/raw
```

Processed tables written to `data/processed/`:

| File | Grain | Rows |
|------|-------|------|
| `wc2022_player_match_stats.parquet` | one row per player per match | ~3,244 |
| `wc2022_player_tournament_totals.parquet` | one row per player (tournament totals) | ~833 |

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

## Goal timings & plots

`build_goal_events()` returns one row per goal with the exact clock time
(`minute`, `second`, `time_min`), `goal_type` (open_play / penalty / own_goal),
and `goal_number` (the team's Nth goal in that match). Saved to
`data/processed/wc2022_goals.parquet`.

`msds_comms_plotter.plots` (matplotlib only) renders to `reports/figures/`:

```bash
python -m msds_comms_plotter.plots
```

- `goal_timing_top3_vs_average.png` — goal number (x) vs clock time (y) for the
  top 3 teams (Argentina, France, Croatia) with faint per-match points and bold
  per-ordinal means, against the all-teams average line.
- `goal_timing_dotplot.png` — Cleveland dot plot: each goal number as a row,
  mean clock time on the x-axis, comparing the top 3 teams to the average of all
  *other* teams.
- `all_goals_by_team.png` — strip plot of all 172 goals: one row per team
  (ordered by total goals), x = minute scored, one dot per goal colored by type
  (open play / penalty / own goal), with HT/FT/ET markers.
- `goal_heatmap.png` — heatmap of goal counts by team (rows) and 15-minute bin
  (columns), single-hue sequential shading, with the top 3 teams outlined and
  bold-labeled in their colors.
- `goal_bubble.png` — scatter/bubble version of the heatmap: same team x
  time-bin grid, goal count encoded as bubble size; top 3 teams in color.

## Altair charts

`msds_comms_plotter.altair_charts` builds interactive Altair versions of the
same data, all themed with `chartkit` so they match the matplotlib figures. It
walks through the five most common Altair chart types — one per mark — plus a
linked-brush interaction:

```bash
python -m msds_comms_plotter.altair_charts
```

Each builder returns a plain `alt.Chart` (keep chaining `.properties`,
`.interactive`, …). Run as a script, each writes an interactive `.html` and,
if `vl-convert-python` is installed, a static `.png` to `reports/figures/`:

| Chart type | Mark | File (`alt_*`) | What it shows |
|------------|------|----------------|---------------|
| Bar chart | `mark_bar` | `alt_bar_goals_by_team` | Total goals per team (top N), sorted, value-labeled. |
| Line chart | `mark_line` | `alt_line_cumulative_goals` | Cumulative goals over the tournament calendar (→ 172). |
| Scatter plot | `mark_point` | `alt_scatter_xg_vs_goals` | Player xG vs actual goals, with a y = x reference line; standouts labeled. |
| Histogram | `mark_bar` (binned) | `alt_hist_goal_minutes` | Distribution of goals by match minute (5-min bins), with 45'/90' markers. |
| Heatmap | `mark_rect` | `alt_heatmap_team_phase` | Goals by team (rows) × 15-minute phase (cols), sequential `viridis` shading. |
| Linked brush | `mark_point` + `mark_bar` | `alt_brush_position_counts` | Scatter colored by position; drag a box and the count-by-position bars below recount only the selected players, while unselected points fade to grey (`selection_interval`). Mirrors Altair's README linked-histogram example. |
| Point paths on hover | `mark_trail` + `mark_circle` | `alt_point_paths_hover` | Team-match scatter (xG vs goals, colored by stage). A match-number slider, hover to trace a team's whole path through the tournament, and a search box to spotlight a team by name. |
| Linked brush (synthetic) | `mark_point` + `mark_bar` | `alt_brush_random_demo` | The same linked-brush interaction on a **synthetic** ~400-point cloud (three "makes", negative power/efficiency correlation) shaped to resemble Altair's cars scatter. Not World Cup data — a demo of the pattern on a fuller, continuous cloud. Seeded, so it's reproducible. |

**Interactivity:** every chart has hover tooltips. The line and scatter charts
also zoom (scroll) and pan (drag). The linked-brush chart filters its bar view
from an interval selection you draw on the scatter — the classic Altair
crossfilter. The point-paths chart adds a match-number slider, hover-to-trace
paths, and a team search box. (Static PNGs capture only the initial state — the
slider/hover/search interactions need the HTML in a browser.)

**Fonts for PNG export:** the HTML output uses the browser's fonts, but the
PNG backend (`vl-convert`) does not read system fonts automatically. The module
best-effort-registers the usual font directories so JetBrains Mono is picked up;
without the font installed, PNGs fall back to a generic monospace (nothing
breaks). See `chartkit`'s font note in the top-level README.

### Making the synthetic linked-brush chart

`linked_scatter_random_demo(seed=42, save=False)` generates its own data, so it
needs no World Cup tables. Call it with a different `seed` to get a different
random cloud (same shape, different points):

```python
from msds_comms_plotter import altair_charts as ac

ac.linked_scatter_random_demo()          # default cloud (seed=42), returns an alt.Chart
ac.linked_scatter_random_demo(seed=7)    # a different random cloud
ac.linked_scatter_random_demo(save=True) # also write alt_brush_random_demo.html/.png
```

The data comes from `ac._random_cloud(seed)` — a DataFrame with `make` (three
categories), `power`, and `efficiency` (negatively correlated). Edit the
`_DEMO_MAKES` table in `altair_charts.py` to change the category centres,
spreads, or counts.

**Building the pattern yourself** on any DataFrame with an x, a y, and a
category column is just a few lines — an interval selection drives both the
point color and a filtered `count()` bar chart:

```python
import altair as alt

brush = alt.selection_interval()
color = alt.Color("category:N")

points = alt.Chart(df).mark_point(filled=True).encode(
    x="x:Q", y="y:Q",
    # selected points keep their category color; the rest fade to grey
    color=alt.when(brush).then(color).otherwise(alt.value("lightgray")),
).add_params(brush)

bars = alt.Chart(df).mark_bar().encode(
    y="category:N", x="count():Q", color=color,
).transform_filter(brush)   # only the brushed points are counted

points & bars   # vertical concatenation
```

## Notes / validation

- Penalty **shootout** goals (StatsBomb period 5) are excluded from all stats,
  matching official statistics.
- Sanity checks against the real tournament: top scorers Kylian Mbappé (8) and
  Lionel Messi (7); 169 goals from open play/penalties + 3 own goals = **172**
  total goals, matching the official count.
