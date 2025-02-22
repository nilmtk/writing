"""Contains helper functions"""
import pandas as pd
import numpy as np
import requests
from StringIO import StringIO
import matplotlib as mpl
import matplotlib.pyplot as plt


uuid_path = "http://energy.iiitd.edu.in:9102/backend/api"
data_path = "http://energy.iiitd.edu.in:9102/backend/api/data/"


import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from math import sqrt

SPINE_COLOR = 'gray'

_to_ordinalf_np_vectorized = np.vectorize(mdates._to_ordinalf)

def plot_series(series, **kwargs):
    """Plot function for series which is about 5 times faster than
    pd.Series.plot().

    Parameters
    ----------
    series : pd.Series
    ax : matplotlib Axes, optional
        If not provided then will generate our own axes.
    fig : matplotlib Figure
    date_format : str, optional, default='%d/%m/%y %H:%M:%S'
    tz_localize : boolean, optional, default is True
        if False then display UTC times.

    Can also use all **kwargs expected by `ax.plot`
    """
    ax = kwargs.pop('ax', None)
    fig = kwargs.pop('fig', None)
    date_format = kwargs.pop('date_format', '%d/%m/%y %H:%M:%S')
    tz_localize = kwargs.pop('tz_localize', True)

    if ax is None:
        ax = plt.gca()

    if fig is None:
        fig = plt.gcf()

    x = _to_ordinalf_np_vectorized(series.index.to_pydatetime())
    ax.plot(x, series, **kwargs)
    tz = series.index.tzinfo if tz_localize else None
    ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format, 
                                                      tz=tz))
    ax.set_ylabel('watts')
    fig.autofmt_xdate()
    return ax


def latexify(fig_width=None, fig_height=None, columns=1):
    """Set up matplotlib's RC params for LaTeX plotting.
    Call this before plotting a figure.

    Parameters
    ----------
    fig_width : float, optional, inches
    fig_height : float,  optional, inches
    columns : {1, 2}
    """

    # code adapted from http://www.scipy.org/Cookbook/Matplotlib/LaTeX_Examples

    # Width and max height in inches for IEEE journals taken from
    # computer.org/cms/Computer.org/Journal%20templates/transactions_art_guide.pdf

    assert(columns in [1,2])

    if fig_width is None:
        fig_width = 3.39 if columns==1 else 6.9 # width in inches

    if fig_height is None:
        golden_mean = (sqrt(5)-1.0)/2.0    # Aesthetic ratio
        fig_height = fig_width*golden_mean # height in inches

    MAX_HEIGHT_INCHES = 8.0
    if fig_height > MAX_HEIGHT_INCHES:
        print("WARNING: fig_height too large:" + fig_height + 
              "so will reduce to" + MAX_HEIGHT_INCHES + "inches.")
        fig_height = MAX_HEIGHT_INCHES

    params = {'backend': 'ps',
              'text.latex.preamble': ['\usepackage{gensymb}'],
              'axes.labelsize': 8, # fontsize for x and y labels (was 10)
              'axes.titlesize': 8,
              'text.fontsize': 8, # was 10
              'legend.fontsize': 8, # was 10
              'xtick.labelsize': 8,
              'ytick.labelsize': 8,
              'text.usetex': True,
              'figure.figsize': [fig_width,fig_height],
              'font.family': 'serif'
    }

    matplotlib.rcParams.update(params)


def format_axes(ax):

    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)

    for spine in ['left', 'bottom']:
        ax.spines[spine].set_color(SPINE_COLOR)
        ax.spines[spine].set_linewidth(0.5)

    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')

    for axis in [ax.xaxis, ax.yaxis]:
        axis.set_tick_params(direction='out', color=SPINE_COLOR)

#    matplotlib.pyplot.tight_layout()

    return ax


def get_readings_csv(uuid, start_time, end_time):
        """Get readings from sMAP server for a `uuid` between 
        start_time and end_time

        Parameters
        ---------
        uuid : string
            Unique identifier for the sMAP channel
        start_time : long int
            Timestamp in milliseconds
        end_time : long int
            Timestamp in milliseconds

        Returns
        -------
        smap_data : List of Lists
            Contains data in sMAP format as follows: [[timestamp (ms), power]]
        """
        query = "{}uuid/{}?starttime={}&endtime={}&format=csv".format(data_path,
                                                           uuid, start_time, end_time)
        response = requests.get(query)
        return response


def pd_to_epoch(pd_time):
    temp = pd.DatetimeIndex([pd_time]).astype(np.int64) //10**6
    return temp[0]

def create_df(query, start_time, end_time, uuid=None):
    start_time = pd_to_epoch(start_time)
    end_time = pd_to_epoch(end_time)
    if uuid is None:
        uuid = find_uuid(query)
    temp = get_readings_csv(uuid,start_time,end_time)
    df = pd.read_csv(StringIO(temp.content), names=['timestamp','value'])
    df.index = pd.to_datetime(df.timestamp, unit='ms')
    df = df.drop('timestamp',1)
    df = df.tz_localize("UTC").tz_convert("Asia/Kolkata")
    return df  

def find_uuid(query = None):
    """Returns the UUID corresponding to a home"""
    response = requests.post(uuid_path, query)
    
    uuid = response.json()[0]["uuid"]
    return uuid

def heatmap(df,
            edgecolors='w',
            cmap=mpl.cm.RdYlBu_r,
            log=False):    
    width = len(df.columns)/4
    height = len(df.index)/4
    
    fig, ax = plt.subplots(figsize=(width,height))
      
    heatmap = ax.pcolor(df,
                        edgecolors=edgecolors,  # put white lines between squares in heatmap
                        cmap=cmap,
                        norm=mpl.colors.LogNorm() if log else None)
    
    ax.autoscale(tight=True)  # get rid of whitespace in margins of heatmap
    ax.set_aspect('equal')  # ensure heatmap cells are square
    ax.xaxis.set_ticks_position('top')  # put column labels at the top
    ax.tick_params(bottom='off', top='off', left='off', right='off')  # turn off ticks
    
    plt.yticks(np.arange(len(df.index)) + 0.5, df.index)
    plt.xticks(np.arange(len(df.columns)) + 0.5, df.columns, rotation=90)
    
    # ugliness from http://matplotlib.org/users/tight_layout_guide.html
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", "3%", pad="1%")
    plt.colorbar(heatmap, cax=cax)