#!/usr/bin/env python3
"""Build the World Cup 2022 Altair chart gallery and open it in a browser.

Run this for an interactive gallery. Every chart has hover tooltips; the line
and scatter charts also zoom and pan (scroll to zoom, drag to pan):

    python examples/show_wc2022_charts.py

What it does:

1. Loads the processed data (``data/processed/*.parquet``); if that's missing,
   it builds the tables from the cached StatsBomb JSON. That cache lives in the
   compressed archive, so unpack it once first::

       tar -xJf data/raw/wc2022_raw.tar.xz -C data/raw

2. Builds every chart (bar, line, scatter, histogram, heatmap, two linked-brush
   charts, and the point-paths chart) via :mod:`msds_comms_plotter.altair_charts`,
   themed with ``chartkit``.
3. Stacks them into one page with two **color pickers pinned to the top** — a
   "Category" scheme that recolors every category-colored chart at once, and a
   "Heatmap" ramp for the heatmap. It writes a **self-contained** HTML file
   (``inline=True`` embeds the Vega libraries, so it stays interactive with no
   internet connection and no local server).
4. Opens that file in your default web browser.

The output is written to ``reports/figures/wc2022_altair_gallery.html`` — open
it again any time without re-running.
"""

from __future__ import annotations

import re
import webbrowser

import altair as alt
import pandas as pd

from msds_comms_plotter import altair_charts as ac
from msds_comms_plotter import worldcup

PROCESSED = worldcup.PROJECT_ROOT / "data" / "processed"
OUT = worldcup.PROJECT_ROOT / "reports" / "figures" / "wc2022_altair_gallery.html"


def _load():
    """Return (goals, player_match_stats), building them if not already cached."""
    goals_path = PROCESSED / "wc2022_goals.parquet"
    stats_path = PROCESSED / "wc2022_player_match_stats.parquet"
    if goals_path.exists() and stats_path.exists():
        return pd.read_parquet(goals_path), pd.read_parquet(stats_path)

    print("Processed tables not found — building from the StatsBomb cache.")
    print("(If this fails, unpack the raw data first: "
          "tar -xJf data/raw/wc2022_raw.tar.xz -C data/raw)")
    goals = worldcup.build_goal_events()
    stats = worldcup.build_all()
    return goals, stats


def build_gallery() -> alt.VConcatChart:
    """Assemble all the charts into a single vertically stacked view.

    The two color scheme params are **unbound** (no Vega-Lite ``binding_select``)
    so Vega-Lite emits no dropdowns of its own — the page instead renders its own
    color pickers at the top (see :func:`_inject_color_controls`) and drives
    these signals from them. Each param is still added once, at the top level, so
    one control recolors every chart that references it.
    """
    goals, stats = _load()
    cat_scheme = alt.param(name="cat_scheme", value=ac.CAT_SCHEME_OPTIONS[0])
    seq_scheme = alt.param(name="seq_scheme", value=ac.SEQ_SCHEME_OPTIONS[0])

    # NOTE: scatter_point_paths_hover is placed LAST on purpose. Its bound input
    # widgets (the "Match" slider and "Search" box) render in a single block at
    # the very bottom of the page, so the chart they control must be last for the
    # controls to sit directly beneath it.
    charts = [
        ac.bar_goals_by_team(goals=goals, scheme_param=cat_scheme),
        ac.line_cumulative_goals(goals=goals, scheme_param=cat_scheme),
        ac.scatter_xg_vs_goals(stats=stats, scheme_param=cat_scheme),
        ac.histogram_goal_minutes(goals=goals, scheme_param=cat_scheme),
        ac.heatmap_team_phase(goals=goals, scheme_param=seq_scheme),
        ac.linked_scatter_position_counts(stats=stats, scheme_param=cat_scheme),
        ac.linked_scatter_passing(stats=stats, scheme_param=cat_scheme),
        ac.scatter_point_paths_hover(stats=stats, scheme_param=cat_scheme),  # LAST
    ]
    # Independent color scales so the heatmap's sequential ramp doesn't leak
    # into the other charts; the two scheme params are added once, at the top.
    return (alt.vconcat(*charts)
            .resolve_scale(color="independent")
            .add_params(cat_scheme, seq_scheme)
            .properties(title="World Cup 2022 — an Altair chart gallery"))


def _select(el_id: str, values, labels) -> str:
    opts = "".join(f'<option value="{v}">{lab}</option>'
                   for v, lab in zip(values, labels))
    return f'<select id="{el_id}">{opts}</select>'


def _inject_color_controls(html: str) -> str:
    """Add a sticky color-picker bar at the TOP of the page and wire it up.

    Vega-Lite only ever renders bound inputs at the bottom, so instead the color
    params are left unbound and this injects real ``<select>`` elements above the
    chart, then patches the ``vegaEmbed`` call to hand the live view to a small
    script that sets the ``cat_scheme`` / ``seq_scheme`` signals on change.
    """
    controls = (
        '<div id="color-controls" style="position:sticky;top:0;z-index:10;'
        'background:#fff;border-bottom:1px solid #e1e0d9;padding:12px 16px;'
        "margin-bottom:12px;font-family:'JetBrains Mono',monospace;font-size:13px;"
        'color:#2c2c2a;display:flex;gap:28px;align-items:center;flex-wrap:wrap;">'
        "<strong>Colors</strong>"
        "<label>Category&nbsp;"
        + _select("sel-cat-scheme", ac.CAT_SCHEME_OPTIONS, ac.CAT_SCHEME_LABELS)
        + "</label><label>Heatmap&nbsp;"
        + _select("sel-seq-scheme", ac.SEQ_SCHEME_OPTIONS, ac.SEQ_SCHEME_LABELS)
        + "</label></div>\n"
        "<script>\n"
        "window.__wireColorControls = function (view) {\n"
        "  function bind(id, signal) {\n"
        "    var el = document.getElementById(id);\n"
        "    if (!el) return;\n"
        "    var apply = function () { view.signal(signal, el.value); "
        "view.runAsync(); };\n"
        "    el.addEventListener('change', apply);\n"
        "    apply();\n"
        "  }\n"
        "  bind('sel-cat-scheme', 'cat_scheme');\n"
        "  bind('sel-seq-scheme', 'seq_scheme');\n"
        "};\n"
        "</script>\n")

    patched = html.replace("<body>", "<body>\n" + controls, 1)
    # Hand the live view to the wiring script. The embed call's quote style
    # differs between Altair's inline and CDN templates, so match either.
    patched, n = re.subn(
        r"vegaEmbed\((['\"])#vis\1, spec, embedOpt\)",
        lambda m: m.group(0) + ".then(function (res) { if "
        "(window.__wireColorControls) window.__wireColorControls(res.view); })",
        patched, count=1)
    if n == 0 or "sel-cat-scheme" not in patched:
        raise RuntimeError("Could not inject color controls — Altair HTML "
                           "template changed; check <body> / vegaEmbed markers.")
    return patched


def main() -> None:
    gallery = build_gallery()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:  # inline=True embeds Vega JS so the file works offline, no server
        html = gallery.to_html(inline=True)
    except Exception:  # pragma: no cover - falls back to CDN-linked HTML
        html = gallery.to_html()
    OUT.write_text(_inject_color_controls(html), encoding="utf-8")

    print(f"Wrote {OUT}")
    url = OUT.resolve().as_uri()
    if webbrowser.open(url):
        print(f"Opened {url} in your default browser.")
    else:  # headless / no browser available
        print("Could not launch a browser automatically. Open this file "
              f"manually:\n  {OUT}")


if __name__ == "__main__":
    main()
