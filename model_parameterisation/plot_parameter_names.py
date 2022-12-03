"""
created matt_dumont 
on: 28/11/22
"""
import matplotlib.pyplot as plt
from model_build.project_model_tools import smt
from model_parameterisation.inital_parametersiation import *
from model_parameterisation.pilot_points import get_pilot_point_locations
from targets_and_sensitive_sites.head_targets import plot_hds_regular_locator
from pathlib import Path
from model_build.utils import get_colors


def plot_parameter_locator(show=False):
    kh_param = get_inital_kh(True)
    sy_param = get_inital_sy(True)
    riv_params = get_initial_riv_conductance(True)
    hill_param = get_hillslope_multiplier(True)
    race_param = get_race_multiplier(True)
    rch_param = get_initial_rch_mult(True)
    all_params = (kh_param, sy_param, riv_params, hill_param, race_param, rch_param)
    tags = ['kh', 'sy', 'riv', 'hill', 'race', 'rch']
    base_pdict = {t: p for t, p in zip(tags, all_params)}

    pplocs = get_pilot_point_locations()

    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(14, 10), gridspec_kw=dict(width_ratios=(3, 1)))

    regular_wells = [
        'g40_0041',
        'g40_0120',
        'g40_0129',
        'g40_0366',
        'g40_0367',
        'g40_0415',
        'g40_0416', ]
    reg_colormap = 'tab10'
    regular_colors = get_colors(regular_wells, reg_colormap)

    plot_hds_regular_locator(ax1, {n: c for n, c in zip(regular_wells, regular_colors)})
    ax1.set_ylim(pplocs.y.min() - 100, smt.get_xlim_ylim()[1][1])
    ax1.set_title('kh | sy')
    for n, (x, y) in pplocs.loc[:, ['x', 'y']].iterrows():
        if n == 'riv_g30':
            y += 150
        t = ax1.text(x + 200, y, n)
        t.set_bbox(dict(facecolor='w', alpha=0.5, edgecolor=None))
    ax1.scatter(pplocs.x, pplocs.y, color='red', s=100)

    use_names = []
    for t, p in base_pdict.items():
        if t in ['kh', 'sy']:
            continue
        use_names.extend([f'{t}_{e}' for e in p.keys()])
    for i, n in enumerate(use_names):
        if i > len(use_names) // 2:
            dif = 0.5 - len(use_names) // 2
            x = 1.5
        else:
            dif = 0.5
            x = 0.5
        ax2.text(x, i + dif, n)
    ax2.set_xlim(0, 2)
    ax2.set_ylim(0, len(use_names) // 2 + 1.5)

    fig.tight_layout()
    if show:
        plt.show()
    else:
        fig.savefig(Path(__file__).parent.joinpath('parameter_map.png'))


if __name__ == '__main__':
    plot_parameter_locator(show=True)
