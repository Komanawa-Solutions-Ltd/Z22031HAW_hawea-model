"""
created matt_dumont 
on: 7/12/22
"""
import pickle

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from project_base import processed_target_dir
from targets_and_sensitive_sites.get_raw_target_data import get_high_freq_head_targets
from model_build.supporting_data_analysis import get_lake_heads
from model_build.supporting_data_analysis.lake_data import _read_lake_level
from scipy.optimize import curve_fit, minimize, brute
from copy import deepcopy
from model_build.utils import get_colors


def save_min_data():
    data_path = processed_target_dir.joinpath('lake_g40_0415_curve_data.p')
    high_freq = get_high_freq_head_targets(None, None).loc[:, 'g40_0415'].dropna()
    lake = get_lake_heads('2015', None)
    high_freq = high_freq.loc[high_freq.index <= lake.index.max()]
    with open(data_path, 'wb') as f:
        pickle.dump((high_freq, lake), f)


def brute_min(recalc=False):
    save_path = processed_target_dir.joinpath('min_fit_lake_g40_0415_curve_brute.p')

    if not recalc and save_path.exists():
        with save_path.open('rb') as f:
            out = pickle.load(f)
        return out
    else:
        bounds = np.array([
            slice(-13, -7, 0.2),  # step
            slice(0, 20, 1),  # lag
            slice(0.75, 1., 0.05),  # amplitude
            slice(5, 6),  # smooth
        ])
        print(np.prod([np.mgrid[e].shape for e in bounds]))

        out = brute(_minimize_func, full_output=True, ranges=bounds, workers=-1, disp=True)

        with save_path.open('wb') as f:
            pickle.dump(out, f)

        return out


def curve_min(recalc=False):
    save_path = processed_target_dir.joinpath('min_fit_lake_g40_0415_curve.p')

    if not recalc and save_path.exists():
        with save_path.open('rb') as f:
            out = pickle.load(f)
        return out
    else:
        bounds = np.array([
            [-13, -7],  # step
            [0, 20],  # lag
            [0.5, 1],  # amplitude
            [5, 6],  # smooth
        ])

        inits = brute_min()[0]

        out = minimize(_minimize_func, x0=inits, args=(), method=None,
                       bounds=bounds, tol=1e-15, callback=None, options=dict(disp=True))

        with save_path.open('wb') as f:
            pickle.dump(out, f)

        return out


def get_simple_curve_fit(recalc=False):
    save_path = processed_target_dir.joinpath('simple_fit_lake_g40_0415_curve.p')
    high_freq = get_high_freq_head_targets(None, None).loc[:, 'g40_0415'].dropna()
    lake = get_lake_heads('2015', None)
    high_freq = high_freq.loc[high_freq.index <= lake.index.max()]
    if not recalc and save_path.exists():
        with save_path.open('rb') as f:
            out = pickle.load(f)
        return out
    else:
        bounds = np.array([
            [-20, 10],  # step
            [0, 150],  # lag
            [0.5, 2],  # amplitude
            [0, 150],  # smooth
        ]).transpose()

        inits = [
            -10,  # step
            20,  # lag
            1,  # amplitude
            3,  # smooth
        ]

        out = curve_fit(_fit_func, lake, high_freq, inits,
                        bounds=bounds, full_output=True, method='dogbox')
        with save_path.open('wb') as f:
            pickle.dump(out, f)

    return out


def _minimize_func(params):
    step, lag, amplitude, smooth = params
    data_path = processed_target_dir.joinpath('lake_g40_0415_curve_data.p')
    with data_path.open('rb') as f:
        high_freq, lake = pickle.load(f)
    fit = _fit_func(lake, step, lag, amplitude, smooth)
    out = ((high_freq - fit) ** 2).sum()
    return out


def _fit_func(x, step, lag, amplitude, smooth, plot=False):
    x0 = deepcopy(x)
    x = deepcopy(x)
    x += step

    # amplitude
    xmean = x.mean()
    x2 = ((x - xmean) * amplitude) + xmean

    # lag
    x3 = float_shift(x2, lag)

    # smooth
    x4 = float_rolling(x3, smooth)

    if plot:
        fig, ax = plt.subplots(figsize=(10, 3))
        names = ['org', 'step', 'amp', 'lag', 'smooth']
        colors = get_colors(names)

        vals = [x, x0, x2, x3, x4]
        for k, v, c in zip(names, vals, colors):
            ax.plot(v.index, v, color=c, label=k)
        ax.legend()
        plt.show()
    return x4.loc[(x4.index >= '2017-11-02') & (x4.index <= '2021-12-31')]  # clip


def float_rolling(x, days):
    if days == 0:
        return deepcopy(x)
    low = int(days)
    high = int(days) + 1
    temp = np.concatenate((x.rolling(low).mean().values[np.newaxis], x.rolling(high).mean().values[np.newaxis]))
    xmin = temp.min(axis=0)
    xmax = temp.min(axis=0)
    return pd.Series(xmin + (xmax - xmin) * (days - low), index=x.index)


def float_shift(x, days):
    if days == 0:
        return deepcopy(x)
    low = int(days)
    high = int(days) + 1
    temp = np.concatenate([x.shift(low).values[np.newaxis], x.shift(high).values[np.newaxis]])
    xmin = temp.min(axis=0)
    xmax = temp.min(axis=0)
    return pd.Series(xmin + (xmax - xmin) * (days - low), index=x.index)


def plot_lake_well(inc_fit=True):
    high_freq = get_high_freq_head_targets(None, None).loc[:, 'g40_0415'].dropna()
    lake = get_lake_heads('2015', None)
    high_freq = high_freq.loc[high_freq.index <= lake.index.max()]
    fig, ax = plt.subplots(figsize=(10, 8))
    names = ['G40_0415', 'lake']

    vals = [high_freq, lake]
    if inc_fit:
        out = curve_min()
        out = out.x
        names.append('fit')
        vals.append(_fit_func(lake, *out))
        names.extend([f'{n}: {round(x, 2)}' for n, x in zip(['step', 'lag', 'amplitude', 'smooth'], out)])
        vals.extend([high_freq.iloc[0:2] for x in out])

    colors = get_colors(names)
    for k, v, c in zip(names, vals, colors):
        v = v.loc[v.index >= high_freq.index.min()]
        ax.plot(v.index, v, color=c, label=k)
    ax.legend()
    plt.show()


def examine_lake_record_step_change():
    lake = get_lake_heads(None, None)


    raise NotImplementedError


if __name__ == '__main__':
    plot_lake_well()
