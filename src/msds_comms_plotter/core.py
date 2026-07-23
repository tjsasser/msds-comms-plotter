"""Core functionality for :mod:`msds_comms_plotter`.

This module uses pandas only.
"""

import pandas as pd


def load_data(path):
    """Load a CSV file into a :class:`pandas.DataFrame`.

    Parameters
    ----------
    path : str
        Path to a CSV file.

    Returns
    -------
    pandas.DataFrame
        The loaded data.
    """
    return pd.read_csv(path)


def summarize(df):
    """Return summary statistics for a :class:`pandas.DataFrame`.

    Parameters
    ----------
    df : pandas.DataFrame
        The data to summarize.

    Returns
    -------
    pandas.DataFrame
        Descriptive statistics as produced by :meth:`pandas.DataFrame.describe`.
    """
    return df.describe()
