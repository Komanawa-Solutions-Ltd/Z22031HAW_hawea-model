"""
created matt_dumont 
on: 14/11/23
"""
import numpy as np
import pandas as pd
from scipy.signal import argrelmax, argrelmin
import matplotlib.pyplot as plt
from historical_investigation.get_historical_data import get_historical_well_heads, get_lake_heads, \
    historical_time_start, historical_time_end, historical_well_colors, historical_well_names
from model_build.project_model_tools import smt
from historical_investigation.plot_historical_data import add_locator_to_ax
from project_base import historical_figure_dir

outdir = historical_figure_dir.joinpath('well_lake_extrema')
outdir.mkdir(exist_ok=True)


def get_smooth_shift_lake_hist_heads(well, rolling, shift):
    measured = get_historical_well_heads(well, freq='D').rolling(rolling, center=True).mean()
    lake = get_lake_heads(
        historical_time_start, historical_time_end).rolling(rolling, center=True).mean()

    lake.index = lake.index + pd.Timedelta(days=shift)
    return measured, lake


def find_peak_lows(well_name, rolling, order):
    well, lake = get_smooth_shift_lake_hist_heads(well_name, rolling, 0)
    well_max = argrelmax(well.values, order=order)
    well_min = argrelmin(well.values, order=order)
    lake_max = argrelmax(lake.values, order=order)
    lake_min = argrelmin(lake.values, order=order)

    min_diffs = []
    for lmin in lake.index[lake_min]:
        temp = well.index[well_min] - lmin
        temp = temp[temp.days > 0]
        if len(temp) > 0:
            min_diffs.append(temp.min())
        else:
            min_diffs.append(np.nan)
    max_diffs = []
    for lmax in lake.index[lake_max]:
        temp = well.index[well_max] - lmax
        temp = temp[temp.days > 0]
        if len(temp) > 0:
            max_diffs.append(temp.min())
        else:
            max_diffs.append(np.nan)

    return well_max, well_min, lake_max, lake_min, min_diffs, max_diffs


def plot_extrema(well_name, rolling, order, c='k', lab=''):
    well_max, well_min, lake_max, lake_min, min_diffs, max_diffs = find_peak_lows(well_name, rolling, order)
    well, lake = get_smooth_shift_lake_hist_heads(well_name, rolling, 0)

    fig = plt.figure(figsize=(14, 9))
    gs = plt.GridSpec(2, 2, height_ratios=(1, 1), width_ratios=(1, 0.2))
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)
    ax3 = fig.add_subplot(gs[:, 1])
    add_locator_to_ax(ax3, [well_name], False)

    ax1.plot(well.index, well.values, color=c, label=f'well' + lab)
    ax2.plot(lake.index, lake.values, color=c, label=f'lake' + lab)
    ax1.scatter(well.index[well_max], well.values[well_max], color=c, )
    ax1.scatter(well.index[well_min], well.values[well_min], color=c, )
    ax2.scatter(lake.index[lake_max], lake.values[lake_max], color=c, )
    ax2.scatter(lake.index[lake_min], lake.values[lake_min], color=c, )

    # plot lines

    y1, y2 = ax1.get_ylim()
    ax1.vlines(well.index[well_max], y1, y2, color=c, ls=':', alpha=0.3)
    ax1.vlines(well.index[well_min], y1, y2, color=c, ls=':', alpha=0.3)

    y1, y2 = ax2.get_ylim()
    ydif = y2 - y1
    y1 = y1 - ydif * .1
    y2 = y2 + ydif * .1
    ax2.vlines(lake.index[lake_max], y1, y2, color=c, ls=':', alpha=0.3)
    ax2.vlines(lake.index[lake_min], y1, y2, color=c, ls=':', alpha=0.3)

    for idx, dif in zip(lake.index[lake_max], max_diffs):
        ax2.text(idx, y2, f'{dif.days} days\nto next well max', ha='center', va='top')
    for idx, dif in zip(lake.index[lake_min], min_diffs):
        ax2.text(idx, y1, f'{dif.days} days\nto next well min', ha='center', va='bottom')

    ax2.set_ylim(y1 - ydif * 0.05, y2 + ydif * 0.05)
    ax1.legend()
    ax2.legend()
    ax1.set_ylabel('well head (m)')
    ax2.set_ylabel('lake head (m)')
    fig.suptitle(f'{well_name.capitalize()}\nwell and lake heads with {rolling} day centered rolling mean')
    fig.tight_layout()
    return fig


def plot_all_extrema():
    for wn, c in historical_well_colors.items():
        fig = plot_extrema(wn, 100, 100, c=c, lab=f'roll 100')
        fig.savefig(outdir.joinpath(f'{wn}_extrema.png'))
        plt.close(fig)


use_shifts = {
    'bore_13': 26,
    'bore_315': 21,
    'bore_513': 45,
    'bore_515': 45,
    'bore_butterfields': 71,
}


def plot_lake_well_delta(well_name, rolling=20):
    well, lake = get_smooth_shift_lake_hist_heads(well_name, rolling, shift=use_shifts[well_name])

    fig = plt.figure(figsize=(14, 9))
    gs = plt.GridSpec(2, 2, height_ratios=(1, 1), width_ratios=(1, 0.3))
    ax_lake_diff = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[1, 0], sharex=ax_lake_diff)
    ax3 = fig.add_subplot(gs[:, 1])
    add_locator_to_ax(ax3, [well_name], False)
    well_lake = pd.merge(pd.DataFrame({'well': well}), pd.DataFrame({'lake': lake}), how='outer',
                         left_index=True, right_index=True)

    ax2.plot(well_lake.index, well_lake.well, color='r', label=f'well', alpha=0.5)
    ax2.plot(well_lake.index, well_lake.lake, color='b', label=f'lake', alpha=0.5)
    ax2.legend()
    ax2.set_ylabel('head (m)')

    # plot diff vs heads

    ax_lake_diff.plot(well_lake.index, well_lake.well.diff(1), color='r', label='well head change')
    ax_lake_diff.plot(well_lake.index, well_lake.lake.diff(1), color='b', label='blue head change')
    ax_lake_diff.set_xlabel('Time')
    ax_lake_diff.set_ylabel('head change (m)')
    fig.suptitle(f'{well_name.capitalize()}, lake and well {rolling} day mean\n'
                 f'Lake time series shifted by {use_shifts[well_name]} days to account for lag to well')
    fig.tight_layout()
    return fig




if __name__ == '__main__':
    plot_all_extrema()
    for wellnm in historical_well_names:
        plot_lake_well_delta(wellnm)
    plt.show()
