"""
chartkit — one consistent look for matplotlib *and* Altair.

matplotlib and Altair are independent renderers: matplotlib draws static
figures in Python, while Altair emits Vega-Lite JSON that renders in a
browser. You can't stack one on the other. What this module does instead
is give both the *same* visual identity — a single monospaced typeface
(JetBrains Mono), one shared palette, and matching minimal chrome — so a
static matplotlib figure and an interactive Altair chart look like siblings.

Usage
-----
    from msds_comms_plotter import chartkit

    # matplotlib
    chartkit.ensure_font()              # warns if JetBrains Mono is missing
    chartkit.apply_matplotlib_theme()   # sets rcParams globally
    fig, ax = plt.subplots()
    ax.plot(x, y)
    chartkit.style_axes(ax, title="Revenue", ylabel="USD")

    # Altair
    chartkit.enable_altair_theme()      # registers + enables the theme
    chartkit.alt_line(df, x="date:T", y="price:Q", color="symbol:N")

Note: JetBrains Mono must be installed for matplotlib to use it, and
available to the browser (e.g. via a webfont) for Altair. Both fall back
to a generic monospace stack otherwise.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Shared design tokens                                                         #
# --------------------------------------------------------------------------- #

FONT = "JetBrains Mono"
FONT_STACK = [FONT, "DejaVu Sans Mono", "Menlo", "Consolas", "monospace"]

# Calm, colorblind-aware categorical palette, used by both libraries.
PALETTE = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # teal
    "#eda100",  # amber
    "#e87ba4",  # pink
    "#4a3aa7",  # violet
    "#008300",  # green
    "#e34948",  # red
]

INK = "#2c2c2a"       # primary text / axis domain
MUTED = "#6b6a66"     # secondary text / tick labels
GRID = "#e1e0d9"      # gridlines
SURFACE = "#ffffff"   # chart background

SEQUENTIAL = "viridis"   # magnitude scales (heatmaps, choropleths)
DIVERGING = "redblue"    # polarity scales (deltas vs. a baseline)

SIZE_TITLE = 15
SIZE_LABEL = 12
SIZE_TICK = 10
SIZE_LEGEND = 11


# --------------------------------------------------------------------------- #
# matplotlib                                                                   #
# --------------------------------------------------------------------------- #

def apply_matplotlib_theme() -> dict:
    """Apply the chartkit look to matplotlib globally via rcParams."""
    import matplotlib as mpl
    from cycler import cycler

    rc = {
        # font
        "font.family": "monospace",
        "font.monospace": FONT_STACK,
        "font.size": SIZE_TICK,
        "text.color": INK,
        # figure & saving
        "figure.figsize": (7, 4.5),
        "figure.dpi": 120,
        "figure.facecolor": SURFACE,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.facecolor": SURFACE,
        # axes
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.linewidth": 1.0,
        "axes.titlesize": SIZE_TITLE,
        "axes.titleweight": "bold",
        "axes.titlepad": 12,
        "axes.titlecolor": INK,
        "axes.labelsize": SIZE_LABEL,
        "axes.labelcolor": INK,
        "axes.labelpad": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": cycler(color=PALETTE),
        # grid (horizontal only — quieter)
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "grid.alpha": 1.0,
        # ticks
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": SIZE_TICK,
        "ytick.labelsize": SIZE_TICK,
        "xtick.direction": "out",
        "ytick.direction": "out",
        # lines & markers
        "lines.linewidth": 2.0,
        "lines.markersize": 6,
        "lines.solid_capstyle": "round",
        # legend
        "legend.frameon": False,
        "legend.fontsize": SIZE_LEGEND,
    }
    mpl.rcParams.update(rc)
    return dict(rc)


def style_axes(ax, title=None, xlabel=None, ylabel=None, ygrid_only=True):
    """Per-axes finishing touches the global rcParams can't express."""
    if title:
        ax.set_title(title, loc="left")
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.tick_params(length=0)  # hide tick marks, keep labels
    if ygrid_only:
        ax.grid(axis="y")
        ax.grid(axis="x", visible=False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    return ax


def ensure_font(name: str = FONT) -> bool:
    """Return True if `name` is available to matplotlib; warn otherwise."""
    from matplotlib import font_manager
    available = {f.name for f in font_manager.fontManager.ttflist}
    if name in available:
        return True
    import warnings
    warnings.warn(
        f"Font {name!r} not found; matplotlib will fall back to "
        f"{FONT_STACK[1]!r}. Install JetBrains Mono system-wide, or call "
        f"register_font('/path/to/JetBrainsMono-Regular.ttf').",
        stacklevel=2,
    )
    return False


def register_font(path: str) -> str:
    """Register a .ttf/.otf with matplotlib at runtime; return its family name."""
    from matplotlib import font_manager
    font_manager.fontManager.addfont(path)
    return font_manager.FontProperties(fname=path).get_name()


# --------------------------------------------------------------------------- #
# Altair                                                                       #
# --------------------------------------------------------------------------- #

def altair_theme() -> dict:
    """Return the chartkit Vega-Lite config as a plain dict."""
    return {
        "config": {
            "background": SURFACE,
            "font": FONT,
            "view": {"stroke": "transparent", "continuousWidth": 480,
                     "continuousHeight": 300},
            "title": {"font": FONT, "fontSize": SIZE_TITLE, "fontWeight": "bold",
                      "color": INK, "anchor": "start", "offset": 12},
            "axis": {"labelFont": FONT, "titleFont": FONT,
                     "labelFontSize": SIZE_TICK, "titleFontSize": SIZE_LABEL,
                     "labelColor": MUTED, "titleColor": INK,
                     "gridColor": GRID, "domainColor": GRID, "tickColor": GRID,
                     "tickSize": 0, "labelPadding": 6, "titlePadding": 8},
            "legend": {"labelFont": FONT, "titleFont": FONT,
                       "labelFontSize": SIZE_TICK, "titleFontSize": SIZE_LEGEND,
                       "labelColor": INK, "titleColor": INK},
            "header": {"labelFont": FONT, "titleFont": FONT,
                       "labelColor": INK, "titleColor": INK},
            "range": {"category": PALETTE,
                      "heatmap": {"scheme": SEQUENTIAL},
                      "ramp": {"scheme": SEQUENTIAL},
                      "diverging": {"scheme": DIVERGING}},
            "line": {"strokeWidth": 2},
            "point": {"filled": True, "size": 60},
            "bar": {"cornerRadiusEnd": 3},
        }
    }


def enable_altair_theme(name: str = "chartkit") -> str:
    """Register + enable the theme, handling both new and legacy Altair APIs."""
    import altair as alt
    cfg = altair_theme()
    try:  # Altair >= 5.5 (decorator-based theme API)
        @alt.theme.register(name, enable=True)
        def _theme():
            return cfg
    except AttributeError:  # Altair < 5.5 (legacy registry API)
        alt.themes.register(name, lambda: cfg)
        alt.themes.enable(name)
    return name


def alt_line(data, x, y, color=None, title=""):
    """Thin styled line-chart builder. Channels use Altair shorthand, e.g. 'date:T'."""
    import altair as alt
    enc = {"x": x, "y": y}
    if color:
        enc["color"] = color
    return alt.Chart(data, title=title).mark_line().encode(**enc)


def alt_bar(data, x, y, color=None, title=""):
    """Thin styled bar-chart builder."""
    import altair as alt
    enc = {"x": x, "y": y}
    if color:
        enc["color"] = color
    return alt.Chart(data, title=title).mark_bar().encode(**enc)


def alt_scatter(data, x, y, color=None, title=""):
    """Thin styled scatter builder."""
    import altair as alt
    enc = {"x": x, "y": y}
    if color:
        enc["color"] = color
    return alt.Chart(data, title=title).mark_point().encode(**enc)


__all__ = [
    "FONT", "FONT_STACK", "PALETTE", "INK", "MUTED", "GRID", "SURFACE",
    "SEQUENTIAL", "DIVERGING",
    "apply_matplotlib_theme", "style_axes", "ensure_font", "register_font",
    "altair_theme", "enable_altair_theme", "alt_line", "alt_bar", "alt_scatter",
]
