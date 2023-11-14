"""
created matt_dumont 
on: 2/11/23
"""
import datetime
import pickle
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from project_base import processed_historical_data_dir
from model_build.supporting_data_analysis import get_lake_heads
from optimisation.manual_optimisations.explore_lake_g40_0415 import _fit_func as simple_smoothing_model
from optimisation.manual_optimisations.explore_lake_g40_0415 import curve_min as get_simple_smoothing_params
from historical_investigation.get_historical_data import get_historical_well_heads
from historical_investigation.plot_historical_data import add_locator_to_ax
from scipy.optimize import brute

def fit_simple_smoothing_model(lake):
    out = get_simple_smoothing_params()
    out = out.x
    return simple_smoothing_model(lake, *out, clip=False)

def _minimize_func_bore_13(params):
    step, lag, amplitude, smooth = params
        high_freq, lake = None, None # todo
    fit = simple_smoothing_model(lake, step, lag, amplitude, smooth)
    out = ((high_freq - fit) ** 2).sum()
    return out

bounds = {
    'bore_13': {
        'step': None,  # todo
        'lag': None,  # todo
        'amplitude': None,  # todo
        'smooth': None,  # todo
        'func': _minimize_func_bore_13,
    },
    'bore_315': 'navy',
    'bore_513': 'darkred',
    'bore_515': 'darkgreen',
    'bore_butterfields': 'goldenrod',

}


def brute_min(well, recalc=False):
    save_path = processed_historical_data_dir.joinpath(f'min_fit_lake_{well}_curve.p')

    if not recalc and save_path.exists():
        with save_path.open('rb') as f:
            out = pickle.load(f)
        return out

    if not recalc and save_path.exists():
        with save_path.open('rb') as f:
            out = pickle.load(f)
        return out
    else:
        bounds = np.array([bounds[well][e] for e in ['step', 'lag', 'amplitude', 'smooth']])

        print(np.prod([np.mgrid[e].shape for e in bounds]))

        out = brute(bounds[well]['func'], full_output=True, ranges=bounds, workers=-1, disp=True)

        with save_path.open('wb') as f:
            pickle.dump(out, f)

        return out


def fit_lake():
    lake = get_lake_heads('1975-12-30', '2020-01-01')
    temp = fit_simple_smoothing_model(lake)
    historical_well = get_historical_well_heads('bore_315')

    fig = plt.figure(figsize=(14, 9))
    gs = plt.GridSpec(3, 2, height_ratios=(1, 0.5, 0.5), width_ratios=(1, 0.3))
    ax = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[1, 0], sharex=ax)
    ax3 = fig.add_subplot(gs[:, 1])
    ax4 = fig.add_subplot(gs[2, 0], sharex=ax)
    add_locator_to_ax(ax3, ['bore_315'], False)

    ax.plot(lake.index, lake.values, label='Lake Head')
    ax.plot(lake.index, temp.values, label='Simple Smoothing Model')
    ax.plot(historical_well.index, historical_well.values, label='Historical Well Head')
    ax.legend()
    ax.set_xlim(historical_well.index.min() - datetime.timedelta(days=50), historical_well.index.max())
    ax.set_ylabel('Head (m msl)')
    temp.name = 'ssm'
    historical_well.name = 'obs'
    # todo fill between difference between model and observed
    joint = pd.merge(temp, historical_well, left_index=True, right_index=True)
    lake.name = 'lake'
    joint = pd.merge(joint, lake, left_index=True, right_index=True)
    ax2.plot(joint.index, joint.obs - joint.ssm, label='Observed - Simple Smoothing Model', color='k', ls='--')
    ax2.fill_between(joint.index, joint.obs - joint.ssm, 0, color='r', alpha=0.5)

    ax4.plot(joint.index, joint.lake - joint.obs, label='Observed - Simple Smoothing Model', color='k', ls='--')
    ax4.fill_between(joint.index, joint.lake - joint.obs, 0, color='r', alpha=0.5)

    ax3.set_xlabel('Date')

    fig.suptitle('Lake Head and Simple Smoothing Model (fit from G40/0415) at Bore 315')
    fig.tight_layout()
    plt.show()
    pass


# todo bespoke ssm from non low lake heads

if __name__ == '__main__':
    fit_lake()
