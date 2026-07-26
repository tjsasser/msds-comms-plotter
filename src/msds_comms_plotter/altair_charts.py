"""Altair explorations of the World Cup 2022 data, themed with :mod:`chartkit`.

A tour of the five most common Altair chart types, each built on the shared
``chartkit`` visual identity (JetBrains Mono, the colorblind-aware palette,
minimal chrome) so they read as one family and sit beside the matplotlib
figures in :mod:`msds_comms_plotter.plots`.

===  ==================  ===============  =======================================
#    Chart type          Altair mark      Question it answers
===  ==================  ===============  =======================================
1    Bar chart           ``mark_bar``     Which teams scored the most goals?
2    Line chart          ``mark_line``    How did goals accumulate over the
                                          tournament calendar?
3    Scatter plot        ``mark_point``   Who over/under-performed their xG?
4    Histogram           ``mark_bar``     When in a match are goals scored?
5    Heatmap             ``mark_rect``    Which teams score in which phases?
===  ==================  ===============  =======================================

Each builder returns a plain ``alt.Chart`` — keep chaining Altair methods
(``.properties``, ``.interactive``, …) or ``.save`` it yourself. With
``save=True`` (the default when run as a script) an interactive ``.html`` and,
if `vl-convert-python` is installed, a static ``.png`` are written to
``reports/figures/``.

Run as a script::

    python -m msds_comms_plotter.altair_charts
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from msds_comms_plotter import chartkit, worldcup

# Reuse the project's figures directory so Altair and matplotlib output land
# side by side.
FIG_DIR = worldcup.PROJECT_ROOT / "reports" / "figures"

# Enable the shared look once, at import time.
chartkit.enable_altair_theme()

# Goal-type colors, drawn from the validated chartkit palette. These three
# slots clear the all-pairs CVD checks and are never the green/red adjacent
# pair the validator flags; a legend (always shown) is the required relief for
# the lower-contrast fills.
GOAL_TYPE_DOMAIN = ["open_play", "penalty", "own_goal"]
GOAL_TYPE_RANGE = [chartkit.PALETTE[0], chartkit.PALETTE[3], chartkit.PALETTE[4]]
GOAL_TYPE_TITLES = {"open_play": "Open play", "penalty": "Penalty",
                    "own_goal": "Own goal"}

# Tournament stages in order, with a chartkit palette slot each (six of the
# eight categorical slots — all well-separated for CVD).
STAGE_ORDER = ["Group Stage", "Round of 16", "Quarter-finals",
               "Semi-finals", "3rd Place Final", "Final"]
STAGE_RANGE = chartkit.PALETTE[:6]

# Outfield position groups (goalkeepers don't shoot, so they're dropped), each
# with a chartkit palette slot. Three well-separated categories — the World Cup
# analogue of the cars example's three "Origin" values.
POSITION_ORDER = ["Defender", "Midfielder", "Forward"]
POSITION_RANGE = chartkit.PALETTE[:3]

# StatsBomb stores full legal names, so the last token isn't always the
# familiar one (e.g. Mbappé is recorded as "Kylian Mbappé Lottin"). Override
# the handful of stars we direct-label; everything else falls back to the
# last name token.
KNOWN_NAMES = {
    "Kylian Mbappé Lottin": "Mbappé",
    "Lionel Andrés Messi Cuccittini": "Messi",
}


def _short_name(full: str) -> str:
    """Recognizable short label for a player: known override, else last token."""
    return KNOWN_NAMES.get(full, full.split()[-1])


# --------------------------------------------------------------------------- #
# Data helpers
# --------------------------------------------------------------------------- #
def _goals(goals: pd.DataFrame | None) -> pd.DataFrame:
    """Return the one-row-per-goal table, building it from cache if needed."""
    return worldcup.build_goal_events() if goals is None else goals


def _player_totals(stats: pd.DataFrame | None) -> pd.DataFrame:
    """Per-player tournament totals (goals, xG, shots, minutes)."""
    if stats is None:
        stats = worldcup.build_all()
    tot = (stats.groupby(["player", "team"], as_index=False)
           .agg(goals=("goals", "sum"), xg=("xg", "sum"),
                shots=("shots", "sum"), minutes=("minutes_played", "sum")))
    tot["xg"] = tot["xg"].round(2)
    return tot


def _team_match(stats: pd.DataFrame | None) -> pd.DataFrame:
    """One row per team per match: team goals, team xG, stage, and match_num.

    ``match_num`` is the team's 1-based match index in date order — its path
    through the tournament (1 = opening game, up to 7 for the finalists).
    """
    if stats is None:
        stats = worldcup.build_all()
    tm = (stats.groupby(["team", "match_id", "match_date", "stage"],
                        as_index=False)
          .agg(goals=("goals", "sum"), xg=("xg", "sum")))
    tm["xg"] = tm["xg"].round(2)
    tm = tm.sort_values(["team", "match_date"])
    tm["match_num"] = tm.groupby("team").cumcount() + 1
    return tm


def _position_group(pos):
    """Collapse a detailed StatsBomb position into a broad outfield group.

    Order matters: "Wing Back" contains "Back", so defenders are matched before
    wingers. Goalkeepers and unknown positions return ``None`` (dropped).
    """
    if not isinstance(pos, str):
        return None
    if "Goalkeeper" in pos:
        return None
    if "Back" in pos:
        return "Defender"
    if "Midfield" in pos:
        return "Midfielder"
    if "Wing" in pos or "Forward" in pos:
        return "Forward"
    return None


def _shooters_by_position(stats: pd.DataFrame | None) -> pd.DataFrame:
    """Per-player totals (goals, xG, shots) plus a broad position group.

    Each player's group is the most common of the positions they played.
    Restricted to outfield players who took at least one shot, so the scatter
    shows finishers and the position bars have something to count.
    """
    if stats is None:
        stats = worldcup.build_all()
    s = stats.copy()
    s["_grp"] = s["position"].map(_position_group)
    modal = (s.dropna(subset=["_grp"]).groupby(["player", "team"])["_grp"]
             .agg(lambda x: x.mode().iloc[0]).rename("position_group")
             .reset_index())
    tot = (stats.groupby(["player", "team"], as_index=False)
           .agg(goals=("goals", "sum"), xg=("xg", "sum"),
                shots=("shots", "sum")))
    tot["xg"] = tot["xg"].round(2)
    tot = tot.merge(modal, on=["player", "team"], how="left")
    return tot[(tot["shots"] >= 1) & tot["position_group"].notna()].copy()


def _register_png_fonts() -> None:
    """Point vl-convert (the PNG backend) at any locally installed fonts.

    vl-convert doesn't read the system font config, so a named font like
    JetBrains Mono is invisible to it unless its directory is registered —
    without this, PNG export silently drops *all* text. Best-effort: scans the
    common user/system font locations and registers those that exist. HTML
    output is unaffected (the browser handles font fallback itself).
    """
    from pathlib import Path
    try:
        import vl_convert as vlc
    except ImportError:  # pragma: no cover - optional dependency
        return
    for d in ("~/.fonts", "~/.local/share/fonts", "/usr/share/fonts",
              "/usr/local/share/fonts", "/Library/Fonts",
              "~/Library/Fonts", "C:/Windows/Fonts"):
        p = Path(d).expanduser()
        if p.is_dir():
            try:
                vlc.register_font_directory(str(p))
            except Exception:  # pragma: no cover - non-fatal
                pass


def _save(chart: alt.Chart, name: str) -> alt.Chart:
    """Write ``<name>.html`` (always) and ``<name>.png`` (if vl-convert present)."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    html = FIG_DIR / f"{name}.html"
    chart.save(html)
    print(f"Wrote {html}")
    try:
        _register_png_fonts()
        png = FIG_DIR / f"{name}.png"
        chart.save(png, ppi=200)
        print(f"Wrote {png}")
    except Exception as exc:  # pragma: no cover - optional dependency
        print(f"(skipped {name}.png — install vl-convert-python: {exc})")
    return chart


# --------------------------------------------------------------------------- #
# 1. Bar chart  —  mark_bar
# --------------------------------------------------------------------------- #
def bar_goals_by_team(goals=None, top=12, save=False):
    """Bar chart: total goals per team (top ``top`` teams), sorted descending.

    The canonical magnitude-by-identity chart. One measure across one
    categorical axis, so a single hue is correct — rank is carried by length
    and the sort, not by color. Values are direct-labeled at the bar ends.
    """
    g = _goals(goals)
    by_team = (g.groupby("team", as_index=False).size()
               .rename(columns={"size": "goals"})
               .sort_values("goals", ascending=False).head(top))

    base = alt.Chart(by_team).encode(
        y=alt.Y("team:N", sort="-x", title=None),
        x=alt.X("goals:Q", title="Goals scored",
                axis=alt.Axis(tickMinStep=1)),
    )
    bars = base.mark_bar(color=chartkit.PALETTE[0]).encode(
        tooltip=[alt.Tooltip("team:N", title="Team"),
                 alt.Tooltip("goals:Q", title="Goals")])
    labels = base.mark_text(align="left", dx=4, color=chartkit.INK).encode(
        text="goals:Q")
    chart = (bars + labels).properties(
        width=440, height=28 * len(by_team),
        title=f"Goals scored by team — World Cup 2022 (top {top})")
    return _save(chart, "alt_bar_goals_by_team") if save else chart


# --------------------------------------------------------------------------- #
# 2. Line chart  —  mark_line
# --------------------------------------------------------------------------- #
def line_cumulative_goals(goals=None, save=False):
    """Line chart: cumulative tournament goals over the calendar.

    Change-over-time is the line's job. Goals are summed per match-day and
    accumulated, giving a monotone curve from the opening match to the final.
    Points mark each match-day; a crosshair-style tooltip reads off the total.
    """
    g = _goals(goals).copy()
    g["match_date"] = pd.to_datetime(g["match_date"])
    daily = (g.groupby("match_date", as_index=False).size()
             .rename(columns={"size": "goals"}).sort_values("match_date"))
    daily["cumulative_goals"] = daily["goals"].cumsum()

    base = alt.Chart(daily).encode(
        x=alt.X("match_date:T", title="Match date",
                axis=alt.Axis(format="%b %d")),
        y=alt.Y("cumulative_goals:Q", title="Cumulative goals"),
    )
    line = base.mark_line(color=chartkit.PALETTE[0], point=True)
    hover = base.mark_point(size=80, opacity=0).encode(
        tooltip=[alt.Tooltip("match_date:T", title="Date", format="%b %d"),
                 alt.Tooltip("goals:Q", title="Goals that day"),
                 alt.Tooltip("cumulative_goals:Q", title="Running total")])
    chart = (line + hover).properties(
        width=560, height=320,
        title="Goals accumulate across World Cup 2022 (172 total)").interactive()
    return _save(chart, "alt_line_cumulative_goals") if save else chart


# --------------------------------------------------------------------------- #
# 3. Scatter plot  —  mark_point
# --------------------------------------------------------------------------- #
def scatter_xg_vs_goals(stats=None, min_shots=6, save=False):
    """Scatter plot: expected goals (xG) vs actual goals, one dot per player.

    Relationship between two measures. A dashed y = x reference line splits
    clinical finishers (above) from the wasteful (below). Only high-volume
    shooters (``>= min_shots``) are plotted to keep the cloud legible; the
    standout scorers are direct-labeled.
    """
    tot = _player_totals(stats)
    tot = tot[tot["shots"] >= min_shots].copy()
    tot["short_name"] = tot["player"].map(_short_name)

    hi = max(tot["goals"].max(), tot["xg"].max()) + 0.5
    diagonal = alt.Chart(pd.DataFrame({"v": [0, hi]})).mark_line(
        color=chartkit.MUTED, strokeDash=[4, 4]).encode(x="v:Q", y="v:Q")

    base = alt.Chart(tot).encode(
        x=alt.X("xg:Q", title="Expected goals (xG)",
                scale=alt.Scale(domain=[0, hi])),
        y=alt.Y("goals:Q", title="Goals scored",
                scale=alt.Scale(domain=[0, hi])),
        tooltip=[alt.Tooltip("player:N", title="Player"),
                 alt.Tooltip("team:N", title="Team"),
                 alt.Tooltip("goals:Q", title="Goals"),
                 alt.Tooltip("xg:Q", title="xG"),
                 alt.Tooltip("shots:Q", title="Shots")],
    )
    points = base.mark_point(color=chartkit.PALETTE[0], filled=True, size=70,
                             opacity=0.75)
    labels = base.transform_filter(alt.datum.goals >= 4).mark_text(
        align="left", dx=7, dy=-2, color=chartkit.INK).encode(text="short_name:N")
    chart = (diagonal + points + labels).properties(
        width=460, height=420,
        title=f"Finishing vs expected — players with ≥ {min_shots} shots").interactive()
    return _save(chart, "alt_scatter_xg_vs_goals") if save else chart


# --------------------------------------------------------------------------- #
# 4. Histogram  —  mark_bar (binned)
# --------------------------------------------------------------------------- #
def histogram_goal_minutes(goals=None, step=5, save=False):
    """Histogram: distribution of goals by the match minute they were scored.

    A histogram is a bar chart of a *binned continuous* variable — here the
    clock minute, in ``step``-minute bins. It surfaces the well-known late-half
    surges. Single hue; the 45/90-minute half markers give context.
    """
    g = _goals(goals)

    bars = alt.Chart(g).mark_bar(color=chartkit.PALETTE[2]).encode(
        x=alt.X("minute:Q", bin=alt.Bin(step=step), title="Match minute"),
        y=alt.Y("count():Q", title="Goals scored"),
        tooltip=[alt.Tooltip("minute:Q", bin=alt.Bin(step=step),
                             title="Minute range"),
                 alt.Tooltip("count():Q", title="Goals")],
    )
    rules = alt.Chart(pd.DataFrame({"m": [45, 90]})).mark_rule(
        color=chartkit.MUTED, strokeDash=[3, 3]).encode(x="m:Q")
    chart = (bars + rules).properties(
        width=560, height=320,
        title=f"When goals are scored — {step}-minute bins (172 goals)")
    return _save(chart, "alt_hist_goal_minutes") if save else chart


# --------------------------------------------------------------------------- #
# 5. Heatmap  —  mark_rect
# --------------------------------------------------------------------------- #
def heatmap_team_phase(goals=None, save=False):
    """Heatmap: goals by team (rows) x 15-minute phase (columns).

    Two categorical axes with a magnitude in each cell — the rect/heatmap's
    natural job. A single-hue sequential ramp (chartkit's ``viridis``) encodes
    count; a 2px surface gap separates the cells. Rows are ordered by total
    goals so the busiest teams rise to the top.
    """
    g = _goals(goals).copy()
    edges = [0, 15, 30, 45, 60, 75, 90, 120]
    labels = ["0–15", "16–30", "31–45", "46–60", "61–75", "76–90", "90+"]
    g["phase"] = pd.cut(g["minute"], bins=edges, labels=labels,
                        include_lowest=True, right=True)

    counts = (g.groupby(["team", "phase"], observed=True, as_index=False)
              .size().rename(columns={"size": "goals"}))
    order = (g.groupby("team").size().sort_values(ascending=False).index.tolist())

    chart = alt.Chart(counts).mark_rect(stroke=chartkit.SURFACE,
                                        strokeWidth=2).encode(
        x=alt.X("phase:N", sort=labels, title="Match phase (minutes)"),
        y=alt.Y("team:N", sort=order, title=None),
        color=alt.Color("goals:Q", title="Goals",
                        scale=alt.Scale(scheme=chartkit.SEQUENTIAL)),
        tooltip=[alt.Tooltip("team:N", title="Team"),
                 alt.Tooltip("phase:N", title="Phase"),
                 alt.Tooltip("goals:Q", title="Goals")],
    ).properties(
        width=440, height=22 * len(order),
        title="Where goals come from — team x match phase")
    return _save(chart, "alt_heatmap_team_phase") if save else chart


# --------------------------------------------------------------------------- #
# 6. Linked brush  —  interval selection filtering a count-by-category bar chart
# --------------------------------------------------------------------------- #
def linked_scatter_position_counts(stats=None, save=False):
    """Brushable scatter (xG vs goals) linked to a count-by-position bar chart.

    Faithful to Altair's README linked-histogram example (cars → Origin),
    mapped to the World Cup: points are colored by the player's **position**;
    **drag a box** and everything outside it fades to grey while the bars below
    recount how many *selected* players play each position. One
    ``selection_interval`` drives both marks — no manual aggregation.
    """
    df = _shooters_by_position(stats)

    color = alt.Color(
        "position_group:N", title="Position",
        scale=alt.Scale(domain=POSITION_ORDER, range=POSITION_RANGE),
        sort=POSITION_ORDER)
    brush = alt.selection_interval()

    points = alt.Chart(df).mark_point(filled=True, size=70).encode(
        x=alt.X("xg:Q", scale=alt.Scale(zero=False),
                title="Expected goals (xG)"),
        y=alt.Y("goals:Q", title="Goals scored"),
        # Selected points keep their position color; the rest fade to grey.
        color=alt.when(brush).then(color).otherwise(alt.value("#cbcac4")),
        tooltip=[alt.Tooltip("player:N", title="Player"),
                 alt.Tooltip("team:N", title="Team"),
                 alt.Tooltip("position_group:N", title="Position"),
                 alt.Tooltip("goals:Q", title="Goals"),
                 alt.Tooltip("xg:Q", title="xG")],
    ).add_params(brush).properties(
        width=460, height=340, title="Drag a box to select players →")

    bars = alt.Chart(df).mark_bar().encode(
        y=alt.Y("position_group:N", sort=POSITION_ORDER, title=None),
        x=alt.X("count():Q", title="Players selected",
                axis=alt.Axis(tickMinStep=1)),
        color=color,
        tooltip=[alt.Tooltip("position_group:N", title="Position"),
                 alt.Tooltip("count():Q", title="Players")],
    ).transform_filter(brush).properties(
        width=460, height=150, title="Selected players by position")

    chart = alt.vconcat(points, bars).properties(
        title="Who's finishing — brush the scatter to recount by position")
    return _save(chart, "alt_brush_position_counts") if save else chart


# --------------------------------------------------------------------------- #
# 7. Point paths on hover  —  mark_trail + hover selection + search box
# --------------------------------------------------------------------------- #
def scatter_point_paths_hover(stats=None, save=False):
    """Scatter of team-matches (xG vs goals) with hover paths and a search box.

    Adapted from Altair's "point paths on hover" gallery example. Each team's
    matches are a trajectory through the tournament (ordered by date). Interact:

    * **Match slider** — pick a match number (1 = opening game … 7 = final);
      the solid circles show every team's result in that match.
    * **Hover a team** — traces its whole path across matches as a tapering
      trail, with the match number at each stop and the team name in bold.
    * **Search box** — type part of a team name to spotlight it (others fade).

    Points are colored by tournament stage. One ``mark_trail`` + a hover
    ``selection_point`` + a search ``param`` — no aggregation.
    """
    tm = _team_match(stats)
    n_matches = int(tm["match_num"].max())

    # Match-number slider (like the example's year slider).
    match_slider = alt.binding_range(min=1, max=n_matches, step=1, name="Match ")
    match_select = alt.selection_point(
        name="match_select", fields=["match_num"], bind=match_slider,
        value=3)

    # Hover on a team. `hover` is empty=False (nothing highlighted until you
    # hover); `hover_fade` keeps empty=True so "not hovering" selects everyone.
    hover = alt.selection_point(on="mouseover", fields=["team"], empty=False)
    hover_fade = alt.selection_point(on="mouseover", fields=["team"])

    # Free-text search over team names.
    search_box = alt.param(
        value="",
        bind=alt.binding(input="search", placeholder="Team", name="Search "))
    search_matches = alt.expr.test(
        alt.expr.regexp(search_box, "i"), alt.datum.team)

    base = alt.Chart(tm).encode(
        x=alt.X("xg:Q", scale=alt.Scale(zero=False),
                title="Expected goals (xG) in the match"),
        y=alt.Y("goals:Q", scale=alt.Scale(zero=False),
                title="Goals scored in the match"),
        color=alt.Color("stage:N", title="Stage",
                        scale=alt.Scale(domain=STAGE_ORDER, range=STAGE_RANGE),
                        sort=STAGE_ORDER),
        detail="team:N",
    )

    # Circles for the selected match number; opacity spotlights the hovered
    # team and/or the search match (both "empty" states select all → full).
    opacity = (alt.when(hover_fade, search_matches)
               .then(alt.value(0.85)).otherwise(alt.value(0.12)))
    visible_points = base.mark_circle(size=110).encode(
        opacity=opacity,
        tooltip=[alt.Tooltip("team:N", title="Team"),
                 alt.Tooltip("stage:N", title="Stage"),
                 alt.Tooltip("match_num:Q", title="Match #"),
                 alt.Tooltip("goals:Q", title="Goals"),
                 alt.Tooltip("xg:Q", title="xG")],
    ).transform_filter(match_select).add_params(
        hover, hover_fade, match_select)

    when_hover = alt.when(hover)
    # The hovered team's full trajectory: a tapering trail plus its points.
    hover_path = alt.layer(
        base.mark_trail().encode(
            order=alt.Order("match_num:Q", sort="ascending"),
            size=alt.Size("match_num:Q",
                          scale=alt.Scale(domain=[1, n_matches], range=[1, 12]),
                          legend=None),
            opacity=when_hover.then(alt.value(0.35)).otherwise(alt.value(0)),
            color=alt.value(chartkit.MUTED)),
        base.mark_point(size=55, filled=True).encode(
            opacity=when_hover.then(alt.value(0.85)).otherwise(alt.value(0))),
    )

    # Match-number label at each stop along the hovered trail.
    match_labels = base.mark_text(align="left", dx=6, dy=-6, fontSize=11).encode(
        text="match_num:Q", color=alt.value(chartkit.INK),
        opacity=when_hover.then(alt.value(1)).otherwise(alt.value(0)))

    # The hovered team's name, once, in bold near its best match.
    team_label = alt.Chart(tm).mark_text(
        align="left", dx=-15, dy=-22, fontSize=17, fontWeight="bold").encode(
        x="xg:Q", y="goals:Q", text="team:N", color=alt.value(chartkit.INK),
        opacity=when_hover.then(alt.value(1)).otherwise(alt.value(0)),
    ).transform_window(
        rank="rank(goals)",
        sort=[alt.SortField("goals", order="descending")],
        groupby=["team"],
    ).transform_filter(alt.datum.rank == 1)

    chart = alt.layer(
        hover_path, visible_points, match_labels, team_label
    ).add_params(search_box).properties(
        width=520, height=460,
        title="Each team's path through the World Cup — hover to trace, search to find")
    return _save(chart, "alt_point_paths_hover") if save else chart


# --------------------------------------------------------------------------- #
# 8. Linked brush on synthetic data  —  a fuller cloud, same interaction
# --------------------------------------------------------------------------- #
# Synthetic "makes" for the demo cloud: label, x-centre, x-spread, count. Make C
# is shifted to high power / low efficiency, the way the cars example's USA
# points sit low-MPG / high-horsepower.
_DEMO_MAKES = [("Make A", 90, 20, 130),
               ("Make B", 115, 24, 120),
               ("Make C", 185, 30, 150)]
DEMO_ORDER = [m[0] for m in _DEMO_MAKES]
DEMO_RANGE = chartkit.PALETTE[:3]


def _random_cloud(seed: int = 42) -> pd.DataFrame:
    """A synthetic power-vs-efficiency cloud: 3 makes, negative correlation.

    Deterministic given ``seed``. Shaped to resemble the Altair cars example
    (Horsepower vs MPG) — a fuller, continuous scatter than the discrete
    World Cup goal counts.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    frames = []
    for make, x_centre, x_spread, n in _DEMO_MAKES:
        power = rng.normal(x_centre, x_spread, n).clip(40, 260)
        efficiency = (55 - 0.16 * power + rng.normal(0, 4, n)).clip(8, 52)
        frames.append(pd.DataFrame({"make": make,
                                    "power": power.round(1),
                                    "efficiency": efficiency.round(1)}))
    return pd.concat(frames, ignore_index=True)


def linked_scatter_random_demo(seed: int = 42, save=False):
    """The linked-brush pattern on a synthetic cloud that looks like the example.

    Same interaction as :func:`linked_scatter_position_counts` — brush the
    scatter, the count-by-category bars below recount the selection, unselected
    points fade to grey — but on a larger, continuous **randomly generated**
    dataset (three "makes", negative power/efficiency correlation) so the cloud
    resembles Altair's cars scatter rather than the discrete goal counts.
    """
    df = _random_cloud(seed)

    color = alt.Color(
        "make:N", title="Make",
        scale=alt.Scale(domain=DEMO_ORDER, range=DEMO_RANGE), sort=DEMO_ORDER)
    brush = alt.selection_interval()

    points = alt.Chart(df).mark_point(filled=True, size=60).encode(
        x=alt.X("power:Q", scale=alt.Scale(zero=False), title="Power"),
        y=alt.Y("efficiency:Q", scale=alt.Scale(zero=False), title="Efficiency"),
        color=alt.when(brush).then(color).otherwise(alt.value("#cbcac4")),
        tooltip=[alt.Tooltip("make:N", title="Make"),
                 alt.Tooltip("power:Q", title="Power"),
                 alt.Tooltip("efficiency:Q", title="Efficiency")],
    ).add_params(brush).properties(
        width=460, height=360, title="Drag a box to select points →")

    bars = alt.Chart(df).mark_bar().encode(
        y=alt.Y("make:N", sort=DEMO_ORDER, title=None),
        x=alt.X("count():Q", title="Points selected"),
        color=color,
        tooltip=[alt.Tooltip("make:N", title="Make"),
                 alt.Tooltip("count():Q", title="Points")],
    ).transform_filter(brush).properties(
        width=460, height=150, title="Selected points by make")

    chart = alt.vconcat(points, bars).properties(
        title="Linked brush on synthetic data (≈400 random points)")
    return _save(chart, "alt_brush_random_demo") if save else chart


ALL_CHARTS = [
    bar_goals_by_team,
    line_cumulative_goals,
    scatter_xg_vs_goals,
    histogram_goal_minutes,
    heatmap_team_phase,
    linked_scatter_position_counts,
    scatter_point_paths_hover,
    linked_scatter_random_demo,
]


def main():
    """Build every chart once, reusing shared data, and save to reports/figures/."""
    goals = worldcup.build_goal_events()
    stats = worldcup.build_all()
    bar_goals_by_team(goals=goals, save=True)
    line_cumulative_goals(goals=goals, save=True)
    scatter_xg_vs_goals(stats=stats, save=True)
    histogram_goal_minutes(goals=goals, save=True)
    heatmap_team_phase(goals=goals, save=True)
    linked_scatter_position_counts(stats=stats, save=True)
    scatter_point_paths_hover(stats=stats, save=True)
    linked_scatter_random_demo(save=True)


if __name__ == "__main__":
    main()
