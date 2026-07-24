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

## Notes / validation

- Penalty **shootout** goals (StatsBomb period 5) are excluded from all stats,
  matching official statistics.
- Sanity checks against the real tournament: top scorers Kylian Mbappé (8) and
  Lionel Messi (7); 169 goals from open play/penalties + 3 own goals = **172**
  total goals, matching the official count.
