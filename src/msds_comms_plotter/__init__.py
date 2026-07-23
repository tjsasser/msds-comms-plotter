"""msds_comms_plotter: a small pandas-based library.

The distribution name is ``msds-comms-plotter`` (hyphens); the import name
uses underscores, so use ``import msds_comms_plotter``.
"""

from msds_comms_plotter.core import load_data, summarize

__all__ = ["load_data", "summarize"]
__version__ = "0.1.0"
