"""
created matt_dumont 
on: 27/02/23
"""
import warnings

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from Scenarios.boundary_conditions import get_scen_ghb_data, get_lake_heads
from scipy import optimize
from project_base import processed_scen_dir, proj_root


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


def mod_sin_asym(x, d, low_a, low_b, low_k,
                 high_a=None, high_b=None, high_k=None,
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
    if high_a is None:
        high_a = low_a
    if high_b is None:
        high_b = low_b
    if high_k is None:
        high_k = low_k

    x = np.atleast_1d(x).astype(float)
    temp = np.sin((x - d) / 52 * 2 * np.pi)
    idx = temp < 0
    temp = np.abs(temp)
    temp[~idx] = temp[~idx] ** high_k
    temp[~idx] *= high_a
    temp[~idx] += high_b

    temp[idx] = temp[idx] ** low_k
    temp[idx] *= -low_a
    temp[idx] += low_b

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
        fig.tight_layout()
        plt.show()
    np.save(save_path, params)
    return params


def get_low_lake_params(recalc=False, plot=False):
    save_path = processed_scen_dir.joinpath('low_lake_params.npy')
    if save_path.exists() and not recalc:
        return np.load(save_path)

    data = pd.DataFrame(get_lake_heads('1980-07-18', '2020-12-01'))
    data.loc[:, 'isoweek'] = data.index.isocalendar().week
    data.loc[:, 'year'] = data.index.year
    low_data = data.loc[(data.year >= 2015) | ((data.year <= 2009) & (data.year >= 2004))].groupby('isoweek').mean()
    low_data.drop(53, inplace=True)
    data = low_data.groupby('isoweek').mean()
    f =lake_sin
    params, params_covariance = optimize.curve_fit(f,
                                                   xdata=data.index,
                                                   ydata=data.lake_stage.values, maxfev=10000
                                                   )
    if plot:
        print(f'params: {params}')
        fig, ax = plt.subplots(figsize=(10, 8))
        from matplotlib.pyplot import Line2D
        ax.plot(data.index, data.lake_stage.values, label='observed')
        ax.plot(data.index, f(data.index, *params), color='k', ls=':', label='modelled')
        handles, labels = ax.get_legend_handles_labels()
        for n, v in zip(['a', 'b', 'd'], params):
            labels.append(f'{n}: {v:.2f}')
            handles.append(Line2D([0], [0], color='w'))
        ax.legend(handles=handles, labels=labels)
        ax.set_ylabel('lake head (m)')
        ax.set_xlabel('time')
        ax.set_title('Fit for typological lake variations')
        fig.tight_layout()
        fig.savefig(proj_root.joinpath('Scenarios/boundary_condition_plots', 'low_lake_fit.png'))
        plt.show()
    np.save(save_path, params)
    return params


def explore_options():
    data = pd.DataFrame(get_lake_heads('1980-07-18', '2020-12-01'))
    data.loc[:, 'isoweek'] = data.index.isocalendar().week
    data.loc[:, 'year'] = data.index.year
    fig, ax = plt.subplots()
    ax.plot(data.index, data.lake_stage)
    fig, ax = plt.subplots()

    for y in data.year.unique():
        temp = data.loc[data.year == y]
        ax.plot(temp.isoweek, temp.lake_stage)

    low_years = (data.groupby('year').min().lake_stage < 338.5).index
    low_data = data.loc[(data.year >= 2015) | ((data.year <= 2009) & (data.year >= 2004))].groupby('isoweek').mean()
    low_data.drop(53, inplace=True)

    data = data.groupby('isoweek').mean()
    a, b, d = params = get_low_lake_params()
    print(f'params: {params}')
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.plot(data.index, data.lake_stage.values, label='observed mean')
    ax.plot(low_data.index, low_data.lake_stage.values, label='observed low mean mean', c='cornflowerblue')

    ax.plot(data.index, lake_sin(data.index, *params), color='k', ls=':', label='modelled (base)')
    ax.plot(data.index, lake_sin(data.index, 2 * a, b, d), color='r', ls='--', label='modelled 2a')
    ax.plot(data.index, mod_sin_asym(data.index, d=d, low_a=2 * a, low_b=b, low_k=2 / 3), color='cyan', ls='--',
            label='modelled k=2/3')
    ax.plot(data.index, mod_sin_asym(data.index, d=d, low_a=2 * a, low_b=b, low_k=1 / 3), color='g', ls='--',
            label='modelled k=1/3')
    ax.plot(data.index, mod_sin_asym(data.index, d=d, low_a=2 * a, low_b=b, low_k=1 / 5), color='orange', ls='--',
            label='modelled k=1/5')
    ax.plot(data.index, mod_sin_asym(data.index, d=d, low_a=2 * a, low_b=b, low_k=4 / 5), color='magenta', ls='--',
            label='modelled k=4/5')
    ax.plot(data.index, mod_sin_asym(data.index, d=d, low_a=2 * a, high_a=a, low_b=b, low_k=1 / 3, high_k=1),
            color='yellow', ls='--', label='modelled pos_k=4/5, negk = 1/3')
    ax.legend()
    ax.set_ylabel('lake head (m)')
    ax.set_xlabel('time')
    ax.set_title('Example Lake Level Perturbations')
    fig.tight_layout()
    fig.savefig(proj_root.joinpath('Scenarios/boundary_condition_plots', 'low_lake_perturbations.png'))
    plt.show()


if __name__ == '__main__':
    get_low_lake_params(recalc=True, plot=True)
    explore_options()
    pass
