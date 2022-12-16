"""
created matt_dumont 
on: 16/11/22
"""
import matplotlib.pyplot as plt
import pandas as pd
from modflow_tools_gen_utils import get_colors
from model_build.project_model_tools import smt
from targets_and_sensitive_sites.head_targets import get_high_freq_head_targets, get_low_freq_head_targets, \
    get_all_wells, plot_hds_regular_locator
from model_build.supporting_data_analysis import get_lake_heads, get_river_stage_data, get_river_loc_data
from optimisation.optimisation_period import tdis

# todo check carefully with multiple layers
#  re-run to dble check new systems

def check_riv_stage_near_g40_0366():
    rstage = get_river_stage_data(*tdis.date_limits)
    rlocs = get_river_loc_data()
    bottoms = smt.get_bottoms()[0]  # todo check multiple layers
    tops = smt.get_tops()[0]
    high = get_high_freq_head_targets(*tdis.date_limits)
    all_wells = get_all_wells()
    w = 'g40_0366'
    i, j = all_wells.loc[w, 'i'], all_wells.loc[w, 'j']
    temp = ((rlocs.i - i) ** 2 + (rlocs.j - j) ** 2) ** 0.5
    closest_riv = rlocs.index[temp == temp.min()][0]

    fig, ax = plt.subplots()
    ax.plot(high.index, high.loc[:, w], label=w, color='r', marker='.')
    ax.plot(rstage.index, rstage.loc[:, closest_riv], label='river stage', color='b')
    ax.axhline(tops[i, j], ls=':', label='top', color='grey')
    ax.axhline(bottoms[i, j], ls=':', label='bot', color='k')
    ax.legend()
    ax.set_title(w)
    plt.show()


def bottom_vs_mean_for_all_regular_targets():
    bottoms = smt.get_bottoms()[0] # todo check targets with multiple layers
    tops = smt.get_tops()[0]
    high = get_high_freq_head_targets(*tdis.date_limits)
    low = get_low_freq_head_targets(*tdis.date_limits)
    all_wells = get_all_wells()

    hds = pd.merge(high, low, right_index=True, left_index=True, how='outer')
    for w in hds.columns:
        fig, ax = plt.subplots()
        ax.plot(hds.index, hds.loc[:, w], label=w, color='r', marker='.')
        ax.axhline(tops[all_wells.loc[w, 'i'], all_wells.loc[w, 'j']], ls=':', label='top', color='grey')
        ax.axhline(bottoms[all_wells.loc[w, 'i'], all_wells.loc[w, 'j']], ls=':', label='bot', color='k')
        ax.legend()
        ax.set_title(w)
    plt.show()


def Lake_stage_vs_g40_0415():
    lake = get_lake_heads(*tdis.date_limits)
    bottoms = smt.get_bottoms()[0] # todo multiple layers
    tops = smt.get_tops()[0]
    high = get_high_freq_head_targets(*tdis.date_limits)
    all_wells = get_all_wells()
    w = 'g40_0415'
    fig, ax = plt.subplots()
    ax.plot(high.index, high.loc[:, w], label=w, color='r', marker='.')
    ax.plot(lake.index, lake, label='lake stage', color='b')
    ax.axhline(tops[all_wells.loc[w, 'i'], all_wells.loc[w, 'j']], ls=':', label='top', color='grey')
    ax.axhline(bottoms[all_wells.loc[w, 'i'], all_wells.loc[w, 'j']], ls=':', label='bot', color='k')
    ax.legend()
    ax.set_title(w)

    plt.show()


def check_target_datums():
    bottoms = smt.get_bottoms()[0] # todo check with multiple layers
    tops = smt.get_tops()[0]
    high = get_high_freq_head_targets(*tdis.date_limits)
    low = get_low_freq_head_targets(*tdis.date_limits)
    hds = pd.merge(high, low, right_index=True, left_index=True, how='outer')
    all_wells = get_all_wells()
    all_wells = all_wells.loc[hds.columns]
    all_wells.loc[hds.columns, 'mean_hd'] = hds.mean()
    all_wells.loc[:, 'top'] = tops[all_wells.i, all_wells.j]
    all_wells.loc[:, 'bot'] = bottoms[all_wells.i, all_wells.j]

    fig, ax = plt.subplots()
    x = range(len(all_wells))
    keys = [
        'top',
        'elevation',
        'depth_to_water_elv',
        'depth_elevation',
        'mean_hd',
        'bot',
    ]
    colors = get_colors(keys)
    for k, c in zip(keys, colors):
        ax.scatter(x, all_wells.loc[:, k], label=k, color=c)
    ax.legend()
    ax.set_xticks(x)
    mapper = {True: 'miselv',
              False: ''}
    xlabs = [f'{e}_{mapper[i]}' for e, i in zip(all_wells.index, all_wells.missing_elv)]
    ax.set_xticklabels(xlabs, rotation=-40)
    fig.tight_layout()

    fig, ax  = plt.subplots()
    plot_hds_regular_locator(ax, {n: nc for n, nc in zip(all_wells.index, get_colors(all_wells.index))})
    plt.show()


if __name__ == '__main__':
    bottom_vs_mean_for_all_regular_targets()
    check_target_datums()
    check_riv_stage_near_g40_0366()
    Lake_stage_vs_g40_0415()
