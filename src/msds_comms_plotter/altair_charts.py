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
    bars = base.mark_bar(color=chartkit.PALETTE[0])
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
        title="Goals accumulate across World Cup 2022 (172 total)")
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
        title=f"Finishing vs expected — players with ≥ {min_shots} shots")
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


ALL_CHARTS = [
    bar_goals_by_team,
    line_cumulative_goals,
    scatter_xg_vs_goals,
    histogram_goal_minutes,
    heatmap_team_phase,
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


if __name__ == "__main__":
    main()
