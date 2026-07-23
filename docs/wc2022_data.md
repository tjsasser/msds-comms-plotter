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
and writes the processed tables to `data/processed/`:

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

## Notes / validation

- Penalty **shootout** goals (StatsBomb period 5) are excluded from all stats,
  matching official statistics.
- Sanity checks against the real tournament: top scorers Kylian Mbappé (8) and
  Lionel Messi (7); 169 goals from open play/penalties + 3 own goals = **172**
  total goals, matching the official count.
