"""
created matt_dumont 
on: 19/09/22
"""
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from pathlib import Path
from model_build.project_model_tools import smt, get_starting_heads
from model_build.utils import get_colors
from model_parameterisation.pilot_points import get_pilot_point_locations, interpolate_kh_pilot_points, \
    interpolate_kh_pilot_points, get_param_zones, get_lake_array
from model_tools.model_plotting import plot_spd, first, last, FakePath
from model_build.get_boundary_condition_data import get_well_data, get_rch_data, get_ghb_data, get_riv_data
from model_parameterisation.inital_parametersiation import *
from optimisation.optimisation_period import tdis
from project_base import proj_root

save_path = proj_root.joinpath('optimisation/pre_optimisation_plots')
save_path.mkdir(exist_ok=True)


# todo forms write up
# todo check all of the data going into the model!

def plot_starting_heads():  # todo
    raise NotImplementedError


def plot_parameterisation(save=False):  # todo
    outdir = save_path.joinpath('parameterisation')
    outdir.mkdir(exist_ok=True)
    # todo parameter overview

    # todo river conductnace


    # plot_example_rbf_interp
    pps = get_pilot_point_locations()
    options = [10, 50, 100, 200, 300, 500]
    np.random.seed(1656)
    a = np.random.choice(options)
    np.random.seed(155683)
    b = np.random.choice(options)
    np.random.seed(165653)
    c = np.random.choice(options)
    kh_data = {
        'sandyhill': a,
        'mangawera': b,
        'lake_conductance': c,
    }

    ncols = 3
    fig1, axs1 = plt.subplots(ncols=ncols, figsize=(16, 9))
    np.random.seed(35873)
    randoms = np.random.choice(options, len(pps))
    for i, r in zip(pps.index, randoms):
        kh_data[i] = r

    kh, df = interpolate_kh_pilot_points(kh_data, return_df=True)
    smt.plot.plt_matrix(kh[0], base_map=True, no_flow_layer=0, title=f'real kh', ax=axs1[0], vmin=0,
                        )
    smt.plot.plt_matrix(np.log10(kh[0]), base_map=True, no_flow_layer=0, title=f'log10 kh', ax=axs1[1], vmin=0, vmax=3)
    smt.plot.plt_matrix(kh[0] * np.nan, base_map=True, no_flow_layer=0, title='data', ax=axs1[2], color_bar=False)
    ax = axs1[2]
    ax.scatter(df.x, df.y)
    for x, y, s in df.loc[:, ['x', 'y', 'value']].itertuples(False, None):
        ax.text(x, y, str(round(s, 2)))
    fig1.suptitle('example RBF multiquadric interpolation')
    fig1.tight_layout()
    if save:
        fig1.savefig(outdir.joinpath('example_rbf.png'))

    # inital transmisivity
    khs = get_inital_kh()
    lake = get_lake_array()
    thick = get_starting_heads()[0] - smt.get_bottoms()[0]
    kh = np.full(smt.model_array_shape[1:], khs['sandyhill'][0])
    kh[np.isfinite(lake)] = khs['lake_conductance'][0]

    thick[smt.get_no_flow(0) != 1] = np.nan
    fig, ax = smt.plot.plt_matrix(thick, title='Initial Transmissivity', base_map=True,
                                  no_flow_layer=0, contour=True, label_contours=True,
                                  contour_levels=[0, 10, 20, 30, 40, 50, 60, 80, 100])
    fig.tight_layout()

    if save:
        fig.savefig(outdir.joinpath('inital_trans.png'))

    # parameter zones
    pilot_locs = get_pilot_point_locations()
    zone_plotter = smt.get_model_zeros() * np.nan
    zone_plotter[np.isfinite(get_lake_array())] = 0
    param_zones = get_param_zones()
    zone_plotter[param_zones == 1] = 1
    zone_plotter[param_zones == 2] = 2

    # plot zones
    zone_colors = ['b', 'tan', 'thistle']
    zone_names = ['lake_conductance', 'sandyhill', 'mangawera']
    cmap = ListedColormap(zone_colors)

    fig, (ax1, legendax) = plt.subplots(ncols=2, gridspec_kw={'width_ratios': [5, 1], },
                                        figsize=(10, 9))
    fig, ax = smt.plot.plt_matrix(zone_plotter, title='Kh / sy zones and pilot points', ax=ax1, base_map=True,
                                  cmap=cmap, color_bar=False, no_flow_layer=0)
    handles, labels = [Patch(facecolor='w')], ['name: (initial, (min, max)']
    for c, n in zip(zone_colors, zone_names):
        handles.append(Patch(facecolor=c))
        labels.append(f'{n.capitalize()} zone: {khs[n]}')

    # plot pilot points
    groups = pilot_locs.group.unique()
    for group, c in zip(groups, get_colors(groups)):
        markersize = 3
        marker = 'o'
        temp = pilot_locs.loc[pilot_locs.group == group]
        ax.scatter(temp.x, temp.y, color=c, marker='o')
        handles.append(Line2D([0], [0], marker=marker, color='w',
                              markerfacecolor=c, markersize=markersize * 5))
        labels.append(f'PP Group: {group.capitalize()}')

    legendax.legend(handles, labels)
    legendax.set_xticks([])
    legendax.set_yticks([])
    legendax.spines["top"].set_visible(False)
    legendax.spines["right"].set_visible(False)
    legendax.spines["left"].set_visible(False)
    legendax.spines["bottom"].set_visible(False)
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath('kh_sy_params.png'))
    plt.show()
    raise NotImplementedError


def plot_thickness_top_bot(save=False):
    data = dict(model_tops=smt.get_tops()[0],
                model_bottoms=smt.get_bottoms()[0],
                model_thickness=smt.get_thickness()[0])

    for k, v in data.items():
        fig, ax = smt.plot.plt_matrix(v, title=k, no_flow_layer=0,
                                      base_map=True, contour=True, label_contours=True)
        if save:
            outpath = save_path.joinpath('model_structure', f'{k}.png')
            outpath.parent.mkdir(exist_ok=True)
            fig.savefig(outpath)


def plot_boundary_locs():  # todo
    raise NotImplementedError


def plot_all_spd(save=False):
    if save:
        outdir = save_path.joinpath('stress_period_data')
        outdir.mkdir(exist_ok=True)
    else:
        outdir = FakePath()
    # well boundary conditions
    well_data = get_well_data(tdis, hill_param=get_hillslope_multiplier(True), race_param=get_race_multiplier(True),
                              return_unique_spd=True)
    for k, v in well_data.items():
        plot_spd(v, smt, tdis, is_array=False, key='flux', func=np.nansum, title=f'wel: {k}',
                 outpath=outdir.joinpath(f'well_{k}_time.png'))

    # recharge
    plot_spd(get_rch_data(tdis), smt, tdis, is_array=True, key='total LSR',
             func=np.nansum, mult_by_area=True, title='recharge', outpath=outdir.joinpath('rch_time.png'))

    # lake
    plot_spd(get_ghb_data(tdis), smt, tdis,
             func=np.nanmean,
             key='bhead', title='lake heads', outpath=outdir.joinpath('lake_time.png'))

    # river
    plot_spd(get_riv_data(tdis, get_initial_riv_conductance(True)), smt, tdis,
             func=first, key='stage', title='first river cell stage',
             outpath=outdir.joinpath('riv_first_cell_time.png'))
    plot_spd(get_riv_data(tdis, get_initial_riv_conductance(True)), smt, tdis,
             func=last, key='stage', title='last river cell stage',
             outpath=outdir.joinpath('riv_last_cell_time.png'))

    # todo copy over the river height and stage over time plot from river_data.py


def plot_steady_state_water_budget():
    raise NotImplementedError  # todo various zones


def plot_steady_state_water_bud_locs(save=False):
    # todo plot starting heads
    # todo plot mean recharge
    # todo plot pumping/inflows
    # todo plot
    raise NotImplementedError


def plot_targets():
    # todo spatially and temporally
    #  objective function and weighting
    raise NotImplementedError


if __name__ == '__main__':
    plot_parameterisation()
    plot_all_spd()
    plt.show()
