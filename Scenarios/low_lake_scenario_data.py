"""
created matt_dumont 
on: 27/02/23
"""
import warnings

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from model_build.project_model_tools import bund_top
from Scenarios.boundary_conditions import get_scen_ghb_data, get_lake_heads
from scipy import optimize
from project_base import processed_scen_dir


# scenarios ideas todo
# 3. decline below bund level
# 1. longer period at lower lake levels (e.g. highly skewed) (above bund)
# 1. longer period at lower lake levels (e.g. highly skewed) (below bund)???? only if it converges above
# long lower
#
#
#
#
#
#


def lake_sin(x, a, b, d):
    """
    :param x: iso week
    :param a: params
    :param b: params
    :param c: params
    :param d: params
    :return:
    """
    return a * np.sin((x - d) / 52 * 2 * np.pi) + b


def mod_sin(x, a, b,
            d, k):
    """
    do not mod d
    :param x:
    :param a:
    :param b:
    :param k:
    :param d:
    :return:
    """
    x = np.atleast_1d(x).astype(float)
    temp = np.sin((x - d) / 52 * 2 * np.pi)
    idx = temp < 0
    temp = np.abs(temp)
    temp[idx] = temp[idx] ** k
    temp[idx] *= -1
    return a * temp + b


def mod_sin_asym(x, d, pos_a, pos_b, pos_k,
                 neg_a=None, neg_b=None, neg_k=None,
                 ):
    """
    do not mod d
    :param x:
    :param a:
    :param b:
    :param k:
    :param d:
    :return:
    """
    if neg_a is None:
        neg_a = pos_a
    if neg_b is None:
        neg_b = pos_b
    if neg_k is None:
        neg_k = pos_k

    x = np.atleast_1d(x).astype(float)
    temp = np.sin((x - d) / 52 * 2 * np.pi)
    idx = temp < 0
    temp = np.abs(temp)
    temp[idx] = temp[idx] ** neg_k
    temp[idx] *= -neg_a
    temp[idx] += neg_b

    temp[~idx] = temp[~idx] ** pos_k
    temp[~idx] *= pos_a
    temp[~idx] += pos_b

    return temp


def get_lake_sin_params(recalc=False, plot=False):
    save_path = processed_scen_dir.joinpath('lake_sin_params.npy')
    if save_path.exists() and not recalc:
        return np.load(save_path)

    data = pd.DataFrame(get_lake_heads('1980-07-18', '2020-12-01'))
    data.loc[:, 'isoweek'] = data.index.isocalendar().week
    data = data.groupby('isoweek').mean()
    params, params_covariance = optimize.curve_fit(lake_sin,
                                                   xdata=data.index,
                                                   ydata=data.lake_stage.values,
                                                   )
    if plot:
        print(f'params: {params}')
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.plot(data.index, data.lake_stage.values, label='observed')
        ax.plot(data.index, lake_sin(data.index, *params), color='k', ls=':', label='modelled')
        ax.legend()
        ax.set_ylabel('lake head (m)')
        ax.set_xlabel('time')
        plt.show()
    np.save(save_path, params)
    return params


def lake_step_change(tdis, step_change):
    lake_hds = get_scen_ghb_data(tdis=tdis)
    min_hds = [v['bhead'].min() for v in lake_hds.values()]
    min_hds = min(min_hds)
    if min_hds - step_change <= bund_top:
        warnings.warn('lake heads will be at or below bund top')
    for v in lake_hds.values():
        v['bhead'] += - step_change
    return lake_hds


def lengthen_low_period(tdis, an_per_at_low, step_change):
    lake_hds = get_scen_ghb_data(tdis=tdis)
    min_hds = [v['bhead'].min() for v in lake_hds.values()]
    min_hds = min(min_hds)
    if min_hds - step_change <= bund_top:
        warnings.warn('lake heads will be at or below bund top')
    for v in lake_hds.values():
        v['bhead'] += - step_change
    return lake_hds
    raise NotImplementedError


def explore_options():
    data = pd.DataFrame(get_lake_heads('1980-07-18', '2020-12-01'))
    data.loc[:, 'isoweek'] = data.index.isocalendar().week
    data = data.groupby('isoweek').mean()
    a, b, d = params = get_lake_sin_params()
    print(f'params: {params}')
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.plot(data.index, data.lake_stage.values, label='observed')
    ax.plot(data.index, lake_sin(data.index, *params), color='k', ls=':', label='modelled (base)')
    ax.plot(data.index, lake_sin(data.index, 2 * a, b, d), color='r', ls='--', label='modelled 2a')
    ax.plot(data.index, mod_sin_asym(data.index,d=d, pos_a=2 * a, pos_b=b, pos_k=2 / 3), color='cyan', ls='--', label='modelled k=2/3')
    ax.plot(data.index, mod_sin_asym(data.index,d=d, pos_a=2 * a, pos_b=b, pos_k=1 / 3), color='g', ls='--', label='modelled k=1/3')
    ax.plot(data.index, mod_sin_asym(data.index,d=d, pos_a=2 * a, pos_b=b, pos_k=1 / 5), color='orange', ls='--', label='modelled k=1/5')
    ax.plot(data.index, mod_sin_asym(data.index,d=d, pos_a=2 * a, pos_b=b, pos_k=4 / 5), color='magenta', ls='--', label='modelled k=4/5')
    # todo switch kwargs to low/high which corresponds with the ISO week and low/high waterlevels (neg is high water level)
    ax.plot(data.index, mod_sin_asym(data.index,d=d, pos_a=2*a, neg_a=a, pos_b=b, pos_k=1/3, neg_k=1), color='yellow', ls='--', label='modelled pos_k=4/5, negk = 1/3')
    ax.legend()
    ax.set_ylabel('lake head (m)')
    ax.set_xlabel('time')

    plt.show()


if __name__ == '__main__':
    explore_options()
    pass
