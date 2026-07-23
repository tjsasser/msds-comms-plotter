"""Fetch and build FIFA World Cup 2022 player statistics from StatsBomb open data.

Source: https://github.com/statsbomb/open-data (free, event-level data).
FIFA World Cup 2022 -> competition_id=43, season_id=106 (64 matches).

This module uses **pandas** only (plus the standard library and ``requests``).
Raw JSON is cached under ``data/raw/`` and the processed per-player-per-match
table is written to ``data/processed/`` as Parquet (never CSV).

Run as a script::

    python -m msds_comms_plotter.worldcup
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
COMPETITION_ID = 43
SEASON_ID = 106

# Resolve project directories relative to this file (src/msds_comms_plotter/).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "statsbomb"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

SHOTS_ON_TARGET = {"Goal", "Saved", "Saved to Post"}
YELLOW = {"Yellow Card", "Second Yellow"}
RED = {"Red Card", "Second Yellow"}


# --------------------------------------------------------------------------- #
# Fetching (with a simple on-disk cache so we never re-download)
# --------------------------------------------------------------------------- #
def _get_json(url: str, cache_path: Path, session: requests.Session):
    """Return parsed JSON for ``url``, caching the raw bytes at ``cache_path``."""
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    for attempt in range(4):
        try:
            resp = session.get(url, timeout=60)
            resp.raise_for_status()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(resp.content)
            return resp.json()
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def get_matches(session: requests.Session) -> list:
    """Return the list of match metadata dicts for the 2022 World Cup."""
    url = f"{BASE}/matches/{COMPETITION_ID}/{SEASON_ID}.json"
    return _get_json(url, RAW_DIR / "matches.json", session)


def get_events(match_id: int, session: requests.Session) -> list:
    url = f"{BASE}/events/{match_id}.json"
    return _get_json(url, RAW_DIR / "events" / f"{match_id}.json", session)


def get_lineups(match_id: int, session: requests.Session) -> list:
    url = f"{BASE}/lineups/{match_id}.json"
    return _get_json(url, RAW_DIR / "lineups" / f"{match_id}.json", session)


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
def _name(d, key):
    """Safely pull a nested ``{key: {'name': ...}}`` value."""
    v = d.get(key)
    return v.get("name") if isinstance(v, dict) else None


def _blank_record():
    return {
        "minutes_played": 0,
        "starter": False,
        "position": None,
        "goals": 0,
        "penalty_goals": 0,
        "own_goals": 0,
        "assists": 0,
        "key_passes": 0,
        "shots": 0,
        "shots_on_target": 0,
        "xg": 0.0,
        "passes": 0,
        "passes_completed": 0,
        "crosses": 0,
        "dribbles": 0,
        "dribbles_completed": 0,
        "tackles": 0,
        "interceptions": 0,
        "blocks": 0,
        "ball_recoveries": 0,
        "clearances": 0,
        "fouls_committed": 0,
        "fouls_won": 0,
        "yellow_cards": 0,
        "red_cards": 0,
        "free_kicks_taken": 0,
    }


def _match_end_minute(events: list) -> int:
    """Approximate the final whistle minute from the last recorded event.

    Penalty shootouts (period 5) are excluded so they don't inflate minutes.
    """
    return max((e.get("minute", 0) for e in events if e.get("period") != 5),
               default=90)


def build_match_stats(match: dict, events: list, lineups: list) -> pd.DataFrame:
    """Build a per-player stats table for a single match."""
    match_id = match["match_id"]
    end_minute = _match_end_minute(events)

    # Seed every player from the official lineups so bench players who never
    # touched the ball still appear (with zeroed stats).
    records: dict[int, dict] = {}
    meta: dict[int, dict] = {}
    for team in lineups:
        team_name = team.get("team_name")
        for pl in team.get("lineup", []):
            pid = pl["player_id"]
            records[pid] = _blank_record()
            meta[pid] = {"player": pl.get("player_name"), "team": team_name}

    def rec(ev):
        pl = ev.get("player")
        if not pl:
            return None
        pid = pl["id"]
        if pid not in records:  # safety net for anyone missing from lineups
            records[pid] = _blank_record()
            meta[pid] = {"player": pl.get("name"), "team": _name(ev, "team")}
        return records[pid]

    # Minutes: starters play from 0; subs/red cards adjust the window.
    on_min: dict[int, int] = {}
    off_min: dict[int, int] = {}

    for ev in events:
        # Skip penalty-shootout events (period 5): shootout goals are not
        # counted as match goals in official statistics.
        if ev.get("period") == 5:
            continue

        etype = _name(ev, "type")

        if etype == "Starting XI":
            for pl in ev.get("tactics", {}).get("lineup", []):
                pid = pl["player"]["id"]
                if pid in records:
                    records[pid]["starter"] = True
                    records[pid]["position"] = _name(pl, "position")
                    on_min[pid] = 0
            continue

        r = rec(ev)
        if r is None:
            continue
        minute = ev.get("minute", 0)

        if etype == "Substitution":
            off_min[ev["player"]["id"]] = minute
            repl = ev.get("substitution", {}).get("replacement")
            if repl and repl["id"] in records:
                on_min[repl["id"]] = minute
                if records[repl["id"]]["position"] is None:
                    records[repl["id"]]["position"] = _name(ev, "position")

        elif etype == "Shot":
            shot = ev.get("shot", {})
            r["shots"] += 1
            r["xg"] += shot.get("statsbomb_xg", 0.0) or 0.0
            outcome = _name(shot, "outcome")
            is_pen = _name(shot, "type") == "Penalty"
            if _name(shot, "type") == "Free Kick":
                r["free_kicks_taken"] += 1
            if outcome in SHOTS_ON_TARGET:
                r["shots_on_target"] += 1
            if outcome == "Goal":
                r["goals"] += 1
                if is_pen:
                    r["penalty_goals"] += 1

        elif etype == "Pass":
            p = ev.get("pass", {})
            r["passes"] += 1
            if p.get("outcome") is None:  # StatsBomb omits outcome on completions
                r["passes_completed"] += 1
            if p.get("goal_assist"):
                r["assists"] += 1
            if p.get("shot_assist"):
                r["key_passes"] += 1
            if p.get("cross"):
                r["crosses"] += 1
            if _name(p, "type") == "Free Kick":
                r["free_kicks_taken"] += 1

        elif etype == "Dribble":
            r["dribbles"] += 1
            if _name(ev.get("dribble", {}), "outcome") == "Complete":
                r["dribbles_completed"] += 1

        elif etype == "Duel":
            if _name(ev.get("duel", {}), "type") == "Tackle":
                r["tackles"] += 1

        elif etype == "Interception":
            r["interceptions"] += 1
        elif etype == "Block":
            r["blocks"] += 1
        elif etype == "Ball Recovery":
            r["ball_recoveries"] += 1
        elif etype == "Clearance":
            r["clearances"] += 1

        elif etype == "Foul Committed":
            r["fouls_committed"] += 1
            card = _name(ev.get("foul_committed", {}), "card")
            if card in YELLOW:
                r["yellow_cards"] += 1
            if card in RED:
                r["red_cards"] += 1
                off_min[ev["player"]["id"]] = minute

        elif etype == "Foul Won":
            r["fouls_won"] += 1

        elif etype == "Bad Behaviour":
            card = _name(ev.get("bad_behaviour", {}), "card")
            if card in YELLOW:
                r["yellow_cards"] += 1
            if card in RED:
                r["red_cards"] += 1
                off_min[ev["player"]["id"]] = minute

        elif etype == "Own Goal Against":
            r["own_goals"] += 1

    # Finalise minutes played.
    for pid, r in records.items():
        if pid in on_min:
            start = on_min[pid]
            end = off_min.get(pid, end_minute)
            r["minutes_played"] = max(0, end - start)

    df = pd.DataFrame.from_dict(records, orient="index")
    df.insert(0, "player_id", df.index)
    df.insert(1, "player", [meta[p]["player"] for p in df.index])
    df.insert(2, "team", [meta[p]["team"] for p in df.index])
    df.reset_index(drop=True, inplace=True)

    # Attach match context.
    df["match_id"] = match_id
    df["match_date"] = match.get("match_date")
    df["stage"] = _name(match, "competition_stage")
    df["home_team"] = (match.get("home_team") or {}).get("home_team_name")
    df["away_team"] = (match.get("away_team") or {}).get("away_team_name")
    df["home_score"] = match.get("home_score")
    df["away_score"] = match.get("away_score")
    return df


def build_all(limit: int | None = None) -> pd.DataFrame:
    """Download every match and return the combined per-player-per-match table."""
    session = requests.Session()
    matches = get_matches(session)
    matches.sort(key=lambda m: m.get("match_date", ""))
    if limit:
        matches = matches[:limit]

    frames = []
    for i, match in enumerate(matches, 1):
        mid = match["match_id"]
        print(f"[{i}/{len(matches)}] match {mid}: "
              f"{(match.get('home_team') or {}).get('home_team_name')} vs "
              f"{(match.get('away_team') or {}).get('away_team_name')}")
        events = get_events(mid, session)
        lineups = get_lineups(mid, session)
        frames.append(build_match_stats(match, events, lineups))

    df = pd.concat(frames, ignore_index=True)
    df["pass_completion_pct"] = (
        (df["passes_completed"] / df["passes"]).where(df["passes"] > 0) * 100
    ).round(1)
    return df


def main():
    df = build_all()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "wc2022_player_match_stats.parquet"
    df.to_parquet(out, index=False)
    print(f"\nWrote {len(df):,} player-match rows to {out}")
    print(f"Players: {df['player_id'].nunique()}  Matches: {df['match_id'].nunique()}")
    return df


if __name__ == "__main__":
    main()
