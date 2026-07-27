"""Altair passing chart for the World Cup 2022 data, themed with :mod:`chartkit`.

**Passing: volume vs accuracy** — a linked-brush scatter of passes attempted
(volume) vs pass completion % (accuracy), colored by position, with a
count-by-position bar chart below, a player-name search box, and a live
color-scheme dropdown. Drag a box on the scatter and the bars recount only the
selected players; type a name to filter both views.

Run as a script::

    python -m msds_comms_plotter.altair_charts
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from msds_comms_plotter import chartkit, worldcup

# Reuse the project's figures directory.
FIG_DIR = worldcup.PROJECT_ROOT / "reports" / "figures"

# Enable the shared look once, at import time.
chartkit.enable_altair_theme()

# Outfield position groups (goalkeepers are dropped). Three well-separated
# categories used as the color-scale domain.
POSITION_ORDER = ["Defender", "Midfielder", "Forward"]

# Categorical color schemes for the "Category colors" dropdown. Values are Vega
# scheme names bound live into the color scale; labels are the dropdown text.
CAT_SCHEME_OPTIONS = ["category10", "dark2", "tableau10", "set2",
                      "set1", "tableau20", "paired", "accent",
                      "observable10", "set3", "category20", "category20b",
                      "category20c", "pastel1", "pastel2"]
CAT_SCHEME_LABELS = ["Category 10", "Dark 2", "Tableau 10", "Set 2 (soft)",
                     "Set 1 (bold)", "Tableau 20", "Paired", "Accent",
                     "Observable 10", "Set 3", "Category 20", "Category 20b",
                     "Category 20c", "Pastel 1", "Pastel 2"]


def categorical_scheme_param():
    """A 'Category colors' dropdown, bound to the categorical color scheme.

    Reference it in a color scale with ``scheme=alt.ExprRef(expr="cat_scheme")``.
    Pass one instance to the chart (and add it once at the enclosing level) to
    drive its colors from an external control instead of the built-in dropdown.
    """
    return alt.param(
        name="cat_scheme", value=CAT_SCHEME_OPTIONS[0],
        bind=alt.binding_select(options=CAT_SCHEME_OPTIONS,
                                labels=CAT_SCHEME_LABELS,
                                name="Category colors "))


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


def _players_passing(stats: pd.DataFrame | None, min_minutes: int = 90,
                     min_passes: int = 20) -> pd.DataFrame:
    """Per-player passing totals (volume + completion %) plus position group.

    A player's group is the most common position they played. Restricted to
    players with real involvement (``>= min_minutes`` minutes and
    ``>= min_passes`` passes) so passing rates are meaningful.
    """
    if stats is None:
        stats = worldcup.sample_player_match_stats()
    s = stats.copy()
    s["_grp"] = s["position"].map(_position_group)
    modal = (s.dropna(subset=["_grp"]).groupby(["player", "team"])["_grp"]
             .agg(lambda x: x.mode().iloc[0]).rename("position_group")
             .reset_index())
    tot = (stats.groupby(["player", "team"], as_index=False)
           .agg(passes=("passes", "sum"),
                passes_completed=("passes_completed", "sum"),
                minutes=("minutes_played", "sum")))
    tot = tot.merge(modal, on=["player", "team"], how="left")
    tot["completion_pct"] = (tot["passes_completed"] / tot["passes"]
                             * 100).round(1)
    return tot[(tot["minutes"] >= min_minutes)
               & (tot["passes"] >= min_passes)
               & tot["position_group"].notna()].copy()


def linked_scatter_passing(stats=None, scheme_param=None, save=False):
    """Brush passing volume vs accuracy; count-by-position bars recount selection.

    A linked-brush chart on two continuous passing measures — passes attempted
    (volume) vs pass completion % (accuracy) — colored by position. **Drag a
    box** on the scatter and the bars below recount only the selected players
    while the rest fade to grey. Defenders and midfielders cluster
    high-volume / high-accuracy; forwards spread lower and looser.

    A **player search box** filters both views to names containing the typed
    text (any part of the full name, case-insensitive); an empty box shows
    everyone. Search and brush compose — search narrows the pool, brush selects
    within it. A **"Category colors" dropdown** switches the position palette
    live; pass a shared ``scheme_param`` to drive it from an external control.
    """
    df = _players_passing(stats)

    # The selected Vega scheme name is bound straight into the color scale, so
    # points, bars, and legend recolor together. Shared when scheme_param is
    # passed; otherwise this chart supplies its own dropdown.
    owns_param = scheme_param is None
    scheme = scheme_param or categorical_scheme_param()
    color = alt.Color(
        "position_group:N", title="Position",
        scale=alt.Scale(domain=POSITION_ORDER,
                        scheme=alt.ExprRef(expr="cat_scheme")),
        sort=POSITION_ORDER)
    brush = alt.selection_interval(name="passing_brush")

    # Free-text search over the full player name. Declared at the top level (so
    # both sub-views can filter on it); an empty string's regexp matches every
    # name, so the default view shows all players.
    name_search = alt.param(
        name="player_search", value="",
        bind=alt.binding(input="search", placeholder="e.g. Messi",
                         name="Player "))
    name_matches = alt.expr.test(
        alt.expr.regexp(name_search, "i"), alt.datum.player)

    points = alt.Chart(df).mark_point(filled=True, size=60).encode(
        x=alt.X("passes:Q", title="Passes attempted"),
        y=alt.Y("completion_pct:Q", scale=alt.Scale(zero=False),
                title="Pass completion (%)"),
        color=alt.when(brush).then(color).otherwise(alt.value("#cbcac4")),
        tooltip=[alt.Tooltip("player:N", title="Player"),
                 alt.Tooltip("team:N", title="Team"),
                 alt.Tooltip("position_group:N", title="Position"),
                 alt.Tooltip("passes:Q", title="Passes"),
                 alt.Tooltip("completion_pct:Q", title="Completion %"),
                 alt.Tooltip("minutes:Q", title="Minutes")],
    ).transform_filter(name_matches).add_params(brush).properties(
        width=460, height=360, title="Drag a box to select players →")

    bars = alt.Chart(df).mark_bar().encode(
        y=alt.Y("position_group:N", sort=POSITION_ORDER, title=None),
        x=alt.X("count():Q", title="Players selected",
                axis=alt.Axis(tickMinStep=1)),
        color=color,
        tooltip=[alt.Tooltip("position_group:N", title="Position"),
                 alt.Tooltip("count():Q", title="Players")],
    ).transform_filter(brush).transform_filter(name_matches).properties(
        width=460, height=150, title="Selected players by position")

    chart = alt.vconcat(points, bars).add_params(name_search).properties(
        title="Passing: volume vs accuracy — search a name or brush the cloud")
    if owns_param:
        chart = chart.add_params(scheme)
    return _save(chart, "alt_brush_passing") if save else chart


ALL_CHARTS = [linked_scatter_passing]


def main():
    """Build the passing chart and save it to reports/figures/."""
    linked_scatter_passing(save=True)


if __name__ == "__main__":
    main()
