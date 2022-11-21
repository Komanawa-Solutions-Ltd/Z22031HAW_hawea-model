"""
created matt_dumont 
on: 7/09/22
"""
import itertools
import shutil
import time
import py7zr
import flopy
from copy import deepcopy
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from targets_and_sensitive_sites.head_targets import get_all_hds_targets, plot_hds_zone_locator, \
    plot_hds_regular_locator, get_annual_mean_head_targets, base_regular_groupnames
from targets_and_sensitive_sites.riv_gain_loss_targets import get_riv_target_locs, get_hawea_gain_loss_nper
from optimisation.optimisation_period import tdis
from model_build.supporting_data_analysis import get_river_loc_data
from model_build.utils import get_colors, plot_1_to_1
from model_build.project_model_tools import get_bottom, get_top, get_ibound, smt
from matplotlib.colors import SymLogNorm
from model_tools.util_functions.list_file_utils import ListSolverInfo

# thoughts target groups
"""
1. high frequency head targets  (high weight)
2. low frequency head targets   (high weight)
3. piezo data (mod weight)
4. single targets (weight by quality code)
5. river targets (high weight)

consider applying a temporal weighting to high frequency targets (later has better pumping data)
how to manage dry cells... weight misfit higher???

"""

import inspect


def myself():
    return inspect.stack()[1][3]


def generate_outputs(hds_path, cbc_path):
    all_hds = flopy.utils.HeadFile(hds_path).get_alldata()
    all_hds[all_hds > 1e20] = np.nan
    hds = get_all_hds_targets(tdis)
    # keynote this assumes 1 saved step per stress period
    max_nper = all_hds.shape[0] - 1
    idx = hds.nper <= max_nper
    hds.loc[idx, 'modelled'] = all_hds[hds.loc[idx, 'nper'], hds.loc[idx, 'k'],
                                       hds.loc[idx, 'i'], hds.loc[idx, 'j']]
    bots = get_bottom()
    tops = get_top()
    ibound = get_ibound()[0]
    #  keynote set dry observations to bottom of cell -5m
    hds.loc[hds.modelled < -666, 'modelled'] = bots[hds.loc[hds.modelled < -666, 'i'],
                                                    hds.loc[hds.modelled < -666, 'j']] - 5

    # get annual mean heads (weekly)
    annual_mean = get_annual_mean_head_targets(hds)
    hds = pd.concat([hds, annual_mean])

    # dry cells at non-target data points
    dry_hds = (all_hds < -666) & (ibound == 1)

    # flooded cells
    flooded_cells = (all_hds > tops) & (ibound == 1)

    # extract riv targets
    riv = get_hawea_gain_loss_nper(tdis).reset_index()
    riv_locs = get_riv_target_locs()
    # keynote change if saving multiple steps
    t = flopy.utils.CellBudgetFile(cbc_path).get_data(text='STREAM LEAKAGE', full3D=True)
    mask = t[0].mask[np.newaxis, 0]
    all_riv = np.array(t)[:, 0]
    all_riv[np.repeat(mask, all_riv.shape[0], axis=0)] = np.nan

    riv.loc[:, 'modelled'] = np.nan
    for i, target_key, nper in riv.loc[:, ['target_key', 'nper']].itertuples(True, None):
        if nper > max_nper:
            continue
        riv.loc[i, 'modelled'] = all_riv[nper][riv_locs[target_key]].sum()

    # get stream flow out
    t = flopy.utils.CellBudgetFile(cbc_path).get_data(text='STREAM FLOW OUT', full3D=True)
    mask = t[0].mask[np.newaxis, 0]
    all_str_flow = np.array(t)[:, 0]
    all_str_flow[np.repeat(mask, all_str_flow.shape[0], axis=0)] = np.nan

    all_riv_loc = get_river_loc_data()

    str_flow_out = pd.DataFrame(
        index=tdis.pers,
        columns=[f'{k}_{s}' for k, s in itertools.product(all_riv_loc.rname.unique(), ['head', 'tail'])])
    str_flow_out.index.name = 'nper'
    for key in str_flow_out.columns:
        temp = all_riv_loc.loc[all_riv_loc.rname == key.split('_')[0]]
        if 'head' in key:
            i, j = temp.loc[temp.reach == temp.reach.min(), ['i', 'j']].iloc[0]
        else:
            i, j = temp.loc[temp.reach == temp.reach.max(), ['i', 'j']].iloc[0]
        str_flow_out.loc[str_flow_out.index <= max_nper, key] = all_str_flow[:, i, j]

        # observations for clutha and hawea losses to see range
    param_zones = all_riv_loc.param.unique()
    all_riv_obs = pd.DataFrame(index=tdis.pers, columns=param_zones)
    all_riv_obs.index.name = 'nper'
    for p in param_zones:
        temp = all_riv_loc.loc[all_riv_loc.param == p]
        all_riv_obs.loc[all_riv_obs.index <= max_nper, p] = all_riv[:, temp.i, temp.j].sum(axis=1)

    out_obs = []
    need_keys = ['name', 'group', 'zone', 'nper', 'measured', 'modelled']
    # add hds
    out_obs.append(hds.rename(columns={'head': 'measured'}).loc[:, need_keys])

    # add riv
    riv.loc[:, 'name'] = 'riv_h' + riv.target_key.astype(str) + '_' + riv.nper.astype(str)
    riv.loc[:, 'group'] = 'riv'
    riv.loc[:, 'zone'] = 'riv'
    out_obs.append(riv.rename(columns={'target_val': 'measured'}).loc[:, need_keys])

    out_obs = pd.concat(out_obs)
    return out_obs, all_riv_obs, dry_hds.sum(axis=(0, 1)), flooded_cells.sum(
        axis=(0, 1)), all_hds, all_riv, all_str_flow, str_flow_out


def _plot_spatial_heads(all_hds, ibound, plot_dir, dry_hds, flooded_cells):
    print(myself())
    # plot hds (ss, min, max, range)
    all_plt_hds = {
        'Steady state heads': all_hds[0, 0],
        'Min heads': np.nanmin(all_hds[1:, 0], axis=0),
        'Max heads': np.nanmax(all_hds[1:, 0], axis=0),
        'Range of Heads': np.nanmax(all_hds[1:, 0], axis=0) - np.nanmin(all_hds[1:, 0], axis=(0))
    }
    for key, plt_hds in all_plt_hds.items():
        plt_hds[ibound != 1] = np.nan
        clevels = np.arange((np.nanmin(plt_hds) // 5) * 5, np.nanmax(plt_hds) // 5 * 5 + 5, 10)
        fig, ax = smt.plot.plt_matrix(plt_hds, no_flow_layer=0, base_map=True, title=key,
                                      contour=True, label_contours=True, contour_levels=clevels)
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'{key.replace(" ", "_")}.png'))
        plt.close(fig)

    # plot dry hds
    dry_hds = dry_hds.astype(float)
    dry_hds[np.isclose(dry_hds, 0)] = np.nan
    fig, ax = smt.plot.plt_matrix(dry_hds, base_map=True, no_flow_layer=0, title='Dry cells (# of steps)')
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('dry_cells.png'))
    plt.close(fig)

    # plot flooded cells
    flooded_cells = flooded_cells.astype(float)
    flooded_cells[np.isclose(flooded_cells, 0)] = np.nan
    fig, ax = smt.plot.plt_matrix(flooded_cells, base_map=True, no_flow_layer=0, title='flooded cells (# of steps)')
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('flooded_cells.png'))
    plt.close(fig)


def _plot_all_riv_obs(all_riv_obs, plot_dir, riv_keys, riv_colors, out_obs):
    print(myself())
    # plot all river observations
    fig, axs1 = plt.subplots(4, sharex=True, figsize=(12, 9))  # hawea/clutha sections
    fig2, axs2 = plt.subplots(2, sharex=True, figsize=(12, 9))  # hill catchment sections
    axs = np.concatenate((axs1, axs2))
    for ax, k, c in zip(axs, riv_keys, riv_colors):
        ax.plot(all_riv_obs.index, all_riv_obs.loc[:, k], color=c, marker='.', label=k)
        temp = out_obs.loc[(out_obs.name.str.contains(k)) & (out_obs.group == 'riv')]
        if not temp.empty:
            ax.scatter(temp.nper, temp.measured, color=c, label=f'{k.capitalize()} target',
                       marker="X")
        ax.axhline(0, ls=':', color='k')
        ax.set_yscale('symlog')
        ax.legend()
    fig.supxlabel('Period')
    fig.supylabel('River Gain(-)/loss(+)')
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('all_river_fluxes_large.png'))
    plt.close(fig)
    fig2.supxlabel('Period')
    fig2.supylabel('River Gain(-)/loss(+)')
    fig2.tight_layout()
    fig2.savefig(plot_dir.joinpath('all_river_fluxes_hill.png'))
    plt.close(fig2)


def _plot_hds_modelled_v_measured(hds_groups, hds_colors, hds_obs, plot_dir, regular_wells, regular_colors, zones,
                                  zcolors):
    print(myself())
    # all hds (color by group)
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.set_aspect('equal')
    for g, c in zip(hds_groups, hds_colors):
        temp = hds_obs.loc[hds_obs.group == g]
        ax.scatter(temp.modelled, temp.measured, color=c, label=g.capitalize())
    ax.set_title('All hds measured vs modelled')
    ax.set_xlabel('Modelled')
    ax.set_ylabel('Measured')
    plot_1_to_1(ax, ls=':', c='k', label='1:1 line')
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('hds_all_mod_v_meas.png'))
    plt.close(fig)

    # all hds by group, color by zone/name
    for g in hds_groups:
        fig, (ax, ax_loc) = plt.subplots(ncols=2, figsize=(12, 9), gridspec_kw=dict(width_ratios=(2, 1)))
        temp = hds_obs.loc[hds_obs.group == g]
        ax.set_aspect('equal')
        if g == 'regular':
            for n, nc in zip(regular_wells, regular_colors):
                temp2 = temp.loc[temp.name.str.contains(n)]
                ax.scatter(temp2.modelled, temp2.measured, color=nc, label=n.capitalize())
            plot_hds_regular_locator(ax_loc, {n: nc for n, nc in zip(regular_wells, regular_colors)})
        else:
            for z, zc in zip(zones, zcolors):
                temp2 = temp.loc[temp.zone == z]
                ax.scatter(temp2.modelled, temp2.measured, color=zc, label=z.capitalize())
            plot_hds_zone_locator(ax_loc, {z: zc for z, zc in zip(zones, zcolors)})

        ax.set_title(f'{g.capitalize()} hds measured vs modelled')
        ax.set_xlabel('Modelled (m)')
        ax.set_ylabel('Measured (m)')
        plot_1_to_1(ax, ls=':', c='k', label='1:1 line')
        ax.legend()
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'hds_{g}_mod_v_meas.png'))
        plt.close(fig)


def _plot_hds_temporal_residuals(hds_groups, hds_colors, hds_obs, plot_dir, regular_wells, regular_colors, zones,
                                 zcolors):
    print(myself())
    # residuals by time(color by group)
    fig, ax = plt.subplots(figsize=(9, 9))
    for g, c in zip(hds_groups, hds_colors):
        temp = hds_obs.loc[hds_obs.group == g]
        ax.scatter(temp.nper, temp.modelled - temp.measured, color=c, label=g.capitalize())
    ax.set_title('All hds residuals vs time')
    ax.set_xlabel('Model period')
    ax.set_yscale('symlog')
    ax.set_ylabel('Residual (modelled - measured, m)')
    ax.axhline(0, ls=':', c='k', label='0 line')
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('hds_all_residual_time.png'))
    plt.close(fig)

    # residuals by time by group, color by zone???
    for g in hds_groups:
        fig, (ax, ax_loc) = plt.subplots(ncols=2, figsize=(12, 9), gridspec_kw=dict(width_ratios=(2, 1)))
        temp = hds_obs.loc[hds_obs.group == g]
        if g == 'regular':
            for n, nc in zip(regular_wells, regular_colors):
                temp2 = temp.loc[temp.name.str.contains(n)]
                ax.scatter(temp2.nper, temp2.modelled - temp2.measured, color=nc, label=n.capitalize())
            plot_hds_regular_locator(ax_loc, {n: nc for n, nc in zip(regular_wells, regular_colors)})
        else:
            for z, zc in zip(zones, zcolors):
                temp2 = temp.loc[temp.zone == z]
                ax.scatter(temp2.nper, temp2.modelled - temp2.measured, color=zc, label=z.capitalize())
            plot_hds_zone_locator(ax_loc, {z: zc for z, zc in zip(zones, zcolors)})
        ax.set_title(f'{g.capitalize()} hds residuals vs time')
        ax.set_xlabel('Model period')
        ax.set_ylabel('Residual (modelled - measured, m)')
        ax.set_yscale('symlog')
        ax.axhline(0, ls=':', c='k', label='0 line')
        ax.legend()
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'hds_{g}_residual_time.png'))
        plt.close(fig)


def _plot_regular_hds_closeup(regular_wells, regular_colors, regular_hds, plot_dir):
    print(myself())
    # extra plots for regular heads
    # plot each regular heads
    for n, nc in zip(regular_wells, regular_colors):
        # full dataset
        fig, (ax, ax_loc) = plt.subplots(ncols=2, figsize=(12, 9), gridspec_kw=dict(width_ratios=(2, 1)))
        temp2 = regular_hds.loc[regular_hds.well_name == n].sort_values('date')
        ax.scatter(temp2.date, temp2.measured, color=nc, label=f'{n.capitalize()} measured')
        ax.plot(temp2.date, temp2.modelled, color=nc, label=f'{n.capitalize()} modelled')
        plot_hds_regular_locator(ax_loc, {n: nc})
        ax.set_title(f'{n.capitalize()} hds')
        ax.set_xlabel('Date')
        ax.set_ylabel('Weekly mean Head (m)')
        ax.legend()
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'hds_closeup_{n}.png'))
        plt.close(fig)


def _plot_aaverage_modelled_vs_measured(aaverage_data, regular_wells, regular_colors, plot_dir):
    print(myself())
    fig, (ax, ax_loc) = plt.subplots(ncols=2, figsize=(12, 9), gridspec_kw=dict(width_ratios=(2, 1)))
    temp = aaverage_data
    ax.set_aspect('equal')
    for n, nc in zip(regular_wells, regular_colors):
        temp2 = temp.loc[temp.name.str.contains(n)]
        ax.scatter(temp2.modelled, temp2.measured, color=nc, label=n.capitalize())
    plot_hds_regular_locator(ax_loc, {n: nc for n, nc in zip(regular_wells, regular_colors)})
    ax.set_title(f'Normal year hds measured vs modelled')
    ax.set_xlabel('Modelled (m)')
    ax.set_ylabel('Measured (m)')
    plot_1_to_1(ax, ls=':', c='k', label='1:1 line')
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath(f'hds_normal_year_mod_v_meas.png'))
    plt.close(fig)


def _plot_aaverage_temporal(regular_wells, regular_colors, aaverage_data, plot_dir):
    print(myself())
    # full dataset plots
    fig, (ax, ax_loc) = plt.subplots(ncols=2, figsize=(12, 9), gridspec_kw=dict(width_ratios=(2, 1)))
    temp = aaverage_data
    ax.set_aspect('equal')
    for n, nc in zip(regular_wells, regular_colors):
        temp2 = temp.loc[temp.name.str.contains(n)]
        ax.scatter(temp2.nper, temp2.measured, color=nc, label=f'{n.capitalize()} measured')
        ax.plot(temp2.nper, temp2.modelled, color=nc, label=f'{n.capitalize()} modelled')
    plot_hds_regular_locator(ax_loc, {n: nc for n, nc in zip(regular_wells, regular_colors)})
    ax.set_title(f'Normal year hds temporal')
    ax.set_xlabel('Week of year')
    ax.set_ylabel('Head (m)')
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath(f'hds_normal_year_all.png'))
    plt.close(fig)

    # individaul plots
    for n, nc in zip(regular_wells, regular_colors):
        if n not in aaverage_data.well_name.unique():
            continue
        fig, (ax, ax_loc) = plt.subplots(ncols=2, figsize=(12, 9), gridspec_kw=dict(width_ratios=(2, 1)))
        temp2 = aaverage_data.loc[aaverage_data.well_name == n].sort_values('nper')
        ax.scatter(temp2.nper, temp2.measured, color=nc, label=f'{n.capitalize()} measured')
        ax.plot(temp2.nper, temp2.modelled, color=nc, label=f'{n.capitalize()} modelled')
        plot_hds_regular_locator(ax_loc, {n: nc})
        ax.set_title(f'{n.capitalize()} regular year hds')
        ax.set_xlabel('Week of year')
        ax.set_ylabel('Weekly mean Head (m)')
        ax.legend()
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'hds_regyear_{n}.png'))
        plt.close(fig)


def _plot_riv_obs(riv_keys, riv_colors, out_obs, plot_dir):
    print(myself())
    # river observations
    fig, ax = plt.subplots(figsize=(9, 9))
    for n, c in zip(riv_keys, riv_colors):
        temp = out_obs.loc[(out_obs.name.str.contains(n)) & (out_obs.group == 'riv')]
        if not temp.empty:
            ax.scatter(temp.modelled, temp.measured, color=c, label=n.capitalize())
    ax.set_title('All river measured vs modelled')
    ax.set_xscale('symlog')
    ax.set_xlabel('Modelled')
    ax.set_yscale('symlog')
    ax.set_ylabel('Measured')
    ax.set_aspect('equal')
    plot_1_to_1(ax, ls=':', c='k', label='1:1 line')
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('all_riv_targets_mes_mod.png'))
    plt.close(fig)

    # riv obs by time
    fig, axs = plt.subplots(3, sharex=True, figsize=(12, 9))
    for ax, n, c in zip(axs, riv_keys[:-3], riv_colors[:-3]):
        temp = out_obs.loc[(out_obs.name.str.contains(n)) & (out_obs.group == 'riv')]
        ax.scatter(temp.nper, temp.modelled - temp.measured, color=c, label=n.capitalize())
        ax.legend()
        ax.set_yscale('symlog')
        ax.axhline(0, ls=':', c='k', label='0 line')

    fig.suptitle('All riv residuals vs time')
    fig.supxlabel('Model period')
    fig.supylabel('Residual (modelled - measured, m3/day)')
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('all_riv_targets_residual.png'))
    plt.close(fig)


def _plot_budget(list_file, plot_dir, plot_transient_budget):
    print(myself())
    # pull out budgets and plot
    bud_names = [
        'STORAGE', 'CONSTANT_HEAD', 'WELLS', 'STREAM_LEAKAGE', 'HEAD_DEP_BOUNDS', 'RECHARGE', 'TOTAL'
    ]
    bud_colors = get_colors(bud_names)
    inc_bud = pd.DataFrame(flopy.utils.MfListBudget(list_file).get_incremental()).set_index('stress_period')
    all_pers = list(inc_bud.index)
    # plot ss budget
    fig, ax = plt.subplots(figsize=(12, 9))
    temp = inc_bud.loc[0]
    for i, (k, c) in enumerate(zip(bud_names, bud_colors)):
        if k == 'STORAGE':
            continue
        ax.bar(i, temp.loc[f'{k}_IN'], color=c, label=k.lower().capitalize())
        ax.bar(i, temp.loc[f'{k}_OUT'] * -1, color=c)
    # ax.set_yscale('symlog')
    ax.set_xticks([])
    ax.set_xticklabels([])
    ax.axhline(0, color='k')
    ax.set_ylabel('M3/day')
    ax.set_title('Steady state model budget')
    ax.legend()
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath(f'SS_budget.png'))
    plt.close(fig)

    if plot_transient_budget:
        nper_ax = 20
        naxs_needed = np.ceil(259 / nper_ax)
        nrows = 2
        nfigs = int(np.ceil(naxs_needed / nrows))
        figs, axs = [], []
        for i in range(nfigs):
            fig, axes = plt.subplots(nrows=nrows, sharey=True, figsize=(12, 9))
            figs.append(fig)
            axs.extend(axes)
        naxs = len(axs)
        npers = len(all_pers)
        for i, ax in enumerate(axs):
            start = i * npers // naxs
            stop = (i + 1) * npers // naxs
            if i == naxs - 1:
                use_pers = all_pers[start:]
            else:
                use_pers = all_pers[start:stop]

            # plot data (bar charg
            temp = inc_bud.loc[use_pers]
            xs = np.arange(len(temp)) * len(bud_names)
            for i, (k, c) in enumerate(zip(bud_names, bud_colors)):
                ax.bar(xs + i, temp.loc[:, f'{k}_IN'], color=c, label=k.lower().capitalize())
                ax.bar(xs + i, temp.loc[:, f'{k}_OUT'] * -1, color=c)

            for x in xs[1:]:
                ax.axvline(x, ls=':', color='k', alpha=0.5)
                ax.set_yscale('symlog')
            ax.set_xticks(xs + len(bud_names) / 2 + 0.5)
            ax.set_xticklabels(use_pers)

            ax.axhline(0, color='k')
            ax.legend()
        for i, fig in enumerate(figs):
            fig.supylabel('M3/day')
            fig.supxlabel('Period')
            fig.suptitle(f'Budgets: {i:02d}')
            fig.tight_layout()
            fig.savefig(plot_dir.joinpath(f'transient budget_{i:02d} of {len(figs) - 1}.png'))
            plt.close(fig)


def _plot_spatial_riv(all_riv, plot_dir):
    print(myself())
    if plot_dir is not None:
        assert isinstance(plot_dir, Path)
        outdir = plot_dir.joinpath('spatial_riv')
        outdir.mkdir(exist_ok=True)
    to_plots = {
        'min': np.nanmin(all_riv, axis=0),
        'mean': np.nanmean(all_riv, axis=0),
        'max': np.nanmax(all_riv, axis=0)

    }

    for p in [5, 25, 50, 75, 95]:
        to_plots[f'{p:02d} percentile'] = np.nanpercentile(all_riv, p, axis=0)

    discriptor = '\n- is gaining stream (water out of model)\n+ is losing stream (water into model)'
    for k, to_plot in to_plots.items():
        norm = SymLogNorm(100, 1, vmin=np.nanmin(to_plot), vmax=np.nanmax(to_plot))
        fig, ax = smt.plot.plt_matrix(to_plot, base_map=True, alpha=1, cmap='RdBu', norm=norm, title=k + discriptor)
        fig.tight_layout()
        if plot_dir is not None:
            fig.savefig(outdir.joinpath(f'riv_{k.replace(" ", "_")}.png'))
            plt.close(fig)
    if plot_dir is None:
        plt.show()


def _plot_spatial_strflow_out(all_str_flow, plot_dir):
    print(myself())
    if plot_dir is not None:
        assert isinstance(plot_dir, Path)
        outdir = plot_dir.joinpath('str_flow')
        outdir.mkdir(exist_ok=True)
    all_str_flow = deepcopy(all_str_flow)
    all_str_flow *= 1 / 86400
    to_plots = {
        'min': np.nanmin(all_str_flow, axis=0),
        'mean': np.nanmean(all_str_flow, axis=0),
        'max': np.nanmax(all_str_flow, axis=0)

    }

    for p in [5, 25, 50, 75, 95]:
        to_plots[f'{p:02d} percentile'] = np.nanpercentile(all_str_flow, p, axis=0)

    discriptor = '\n stream flow (m3/s)'
    for k, to_plot in to_plots.items():
        norm = SymLogNorm(1, 1, vmin=np.nanmin(to_plot), vmax=np.nanmax(to_plot))
        fig, ax = smt.plot.plt_matrix(to_plot, base_map=True, alpha=1, cmap='RdBu', norm=norm, title=k + discriptor)
        fig.tight_layout()
        if plot_dir is not None:
            fig.savefig(outdir.joinpath(f'str_flow_{k.replace(" ", "_")}.png'))
            plt.close(fig)
    if plot_dir is None:
        plt.show()


def _plot_str_along_str(all_str_flow, plot_dir):
    print(myself())
    if plot_dir is not None:
        assert isinstance(plot_dir, Path)
        outdir = plot_dir.joinpath('str_flow')
        outdir.mkdir(exist_ok=True)
    all_str_flow = deepcopy(all_str_flow)
    all_str_flow *= 1 / 86400
    rlocs = get_river_loc_data()
    for riv in rlocs.rname.unique():
        temp = rlocs.loc[rlocs.rname == riv]
        to_plots = {
            'max': np.nanmax(all_str_flow[:, temp.i, temp.j], axis=0),
            f'{95} percentile': np.nanpercentile(all_str_flow[:, temp.i, temp.j], 95, axis=0),
            f'{75} percentile': np.nanpercentile(all_str_flow[:, temp.i, temp.j], 75, axis=0),
            'mean': np.nanmean(all_str_flow[:, temp.i, temp.j], axis=0),
            f'{50} percentile': np.nanpercentile(all_str_flow[:, temp.i, temp.j], 50, axis=0),
            f'{25} percentile': np.nanpercentile(all_str_flow[:, temp.i, temp.j], 25, axis=0),
            f'{5} percentile': np.nanpercentile(all_str_flow[:, temp.i, temp.j], 5, axis=0),
            'min': np.nanmin(all_str_flow[:, temp.i, temp.j], axis=0),

        }

        for p in [5, 25, 50, 75, 95]:
            to_plots[f'{p:02d} percentile'] = np.nanpercentile(all_str_flow[:, temp.i, temp.j], p, axis=0)
        fig, ax = plt.subplots(figsize=(8, 10))
        colors = get_colors(to_plots.keys(), 'RdBu')
        for c, (k, v) in zip(colors, to_plots.items()):
            ax.plot(np.arange(len(v)), v, label=k, color=c)
        ax.legend()
        ax.set_xlabel('seg downstream')
        ax.set_ylabel('flow in seg (m3/s)')
        if riv in ['clutha', 'hawea']:
            ax.set_yscale('log')
        ax.set_title(riv)
        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{riv}_flow_along.png'))


def _plot_str_flow(str_flow_out, plot_dir):
    print(myself())
    outdir = plot_dir.joinpath('str_flow')
    outdir.mkdir(exist_ok=True)
    rivers = [e.split('_')[0] for e in str_flow_out.columns]
    for r in pd.unique(rivers):
        fig, ax = plt.subplots(figsize=(10, 8))
        for k, c in zip(['head', 'tail'], ['b', 'r']):
            ax.plot(str_flow_out.index, str_flow_out.loc[:, f'{r}_{k}'] / 86400, color=c, marker='.', label=f'{r}_{k}')
        ax.legend()
        ax.set_title(f'stream flow {r}')
        ax.set_xlabel('nper')
        ax.set_ylabel('steamflow (m3/s)')
        ax.set_yscale('log')
        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{r}_head_tail_flow.png'))


def visualise_model(model_ws, all_hds, dry_hds, out_obs, all_riv_obs, flooded_cells, all_riv, list_file,
                    all_str_flow, str_flow_out, plot_transient_budget=False, plot_dir=None):
    assert isinstance(model_ws, Path)

    # data management
    if plot_dir is None:
        plot_dir = model_ws.joinpath('plots')
    plot_dir.mkdir(exist_ok=True)
    ibound = smt.get_no_flow(0)
    hds_groups = ['h_piezo', 'h_single_3', 'h_single_1', 'regular']
    hds_colors = get_colors(hds_groups)
    reg_colormap = 'tab10'

    hds_obs = out_obs.loc[np.in1d(out_obs.group, hds_groups + base_regular_groupnames)]
    mapper = {'h_piezo': 'h_piezo',
              'h_single_3': 'h_single_3',
              'h_single_1': 'h_single_1'}
    mapper.update({k: 'regular' for k in base_regular_groupnames})
    hds_obs.loc[:, 'group'] = hds_obs.loc[:, 'group'].replace(mapper)
    hds_obs.loc[:, 'well_name'] = [f'{"_".join(e.split("_")[:-1])}' for e in hds_obs.loc[:, 'name']]
    hds_obs.loc[:, 'date'] = tdis.get_date(hds_obs.loc[:, 'nper'])
    hds_obs.loc[:, 'week'] = hds_obs.date.dt.isocalendar().loc[:, 'week']
    regular_hds = hds_obs.loc[hds_obs.loc[:, 'group'] == 'regular']
    aaverage_data = out_obs.loc[out_obs.group.str.contains('rwh_')]
    aaverage_data.loc[:, 'well_name'] = [f'{"_".join(e.split("_")[:-1])}' for e in aaverage_data.loc[:, 'name']]
    aaverage_data.loc[:, 'nper'] *= -1

    # names and colors
    regular_wells = sorted(regular_hds.well_name.unique())
    regular_colors = get_colors(regular_wells, reg_colormap)
    zones = hds_obs.zone.unique()
    zcolors = get_colors(zones)
    riv_keys = all_riv_obs.keys()
    riv_colors = get_colors(riv_keys)

    ## Plotting ##
    _plot_str_along_str(all_str_flow, plot_dir)

    _plot_budget(list_file, plot_dir, plot_transient_budget)

    _plot_spatial_strflow_out(all_str_flow, plot_dir)

    _plot_str_flow(str_flow_out, plot_dir)

    _plot_aaverage_modelled_vs_measured(aaverage_data, regular_wells, regular_colors, plot_dir)

    _plot_aaverage_temporal(regular_wells, regular_colors, aaverage_data, plot_dir)

    _plot_spatial_heads(all_hds, ibound, plot_dir, dry_hds, flooded_cells)

    _plot_all_riv_obs(all_riv_obs, plot_dir, riv_keys, riv_colors, out_obs)

    _plot_hds_modelled_v_measured(hds_groups, hds_colors, hds_obs, plot_dir, regular_wells, regular_colors, zones,
                                  zcolors)

    _plot_hds_temporal_residuals(hds_groups, hds_colors, hds_obs, plot_dir, regular_wells, regular_colors, zones,
                                 zcolors)

    _plot_regular_hds_closeup(regular_wells, regular_colors, regular_hds, plot_dir)

    _plot_riv_obs(riv_keys, riv_colors, out_obs, plot_dir)

    _plot_spatial_riv(all_riv, plot_dir)


def plot_list_failures(list_file, plot_dir):
    temp = ListSolverInfo(list_file)
    all_overs = temp.get_over(50, 0)

    limits = [50, 100, 300, 500, 800]
    for l in limits:
        temp = all_overs.loc[all_overs.outer_iter >= l]
        temp = temp.drop_duplicates(subset=['layer', 'row', 'column', 'nper', 'nstp'])
        plt_data = temp.groupby(['layer', 'row', 'column']).count().outer_iter.reset_index()
        fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
        ax.scatter(*smt.convert_matrix_to_coords(plt_data.row, plt_data.column), color='r')
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'more_than_{l}_outers.png'))


def modflow_converged(list_path):
    """
    returned convergence of the model

    :param list_path: path to the list file
    :return: True if converged, False if not, None if not realised
    """
    # could make this faster by only loading the last n lines? or through a regular expression?,
    # but not super slow
    converg = True
    end_neg = 'FAILED TO MEET SOLVER'.lower()
    with open(list_path) as temp:
        for i in temp:
            if end_neg in i.lower():
                converg = False
                break
    return converg


def process_model_output(model_ws, hds_file, plot=False, savelist=True, save_param=True, plot_dir=None,
                         run_if_unconverged=False):
    model_ws = Path(model_ws)
    hds_file = Path(hds_file)
    list_file = hds_file.with_suffix('.list')
    cbc_file = hds_file.with_suffix('.cbc')
    parameter_file = model_ws.joinpath('parameters.dat')

    if plot:
        if plot_dir is None:
            plot_dir = model_ws.joinpath('plots')
        plot_dir.mkdir(exist_ok=True)

        # plot listfile failures
        plot_list_failures(list_file, plot_dir)

    # save listfile and parameter file
    if savelist:
        save_list_dir = model_ws.joinpath('list_file_repo')
        save_list_dir.mkdir(exist_ok=True)
        n = max([-1] + [int(e.stem.split('_')[-1]) for e in save_list_dir.glob('*')]) + 1
        new_path = save_list_dir.joinpath(f'list_{n}.list')
        with py7zr.SevenZipFile(new_path.with_suffix(".7z"), 'w') as archive:
            archive.write(list_file, list_file.name)

    if save_param:
        save_param_dir = model_ws.joinpath('param_file_repo')
        save_param_dir.mkdir(exist_ok=True)
        n = max([-1] + [int(e.stem.split('_')[-1]) for e in save_param_dir.glob('*')]) + 1
        new_path = save_param_dir.joinpath(f'parameter_{n}.dat')
        shutil.copyfile(parameter_file, new_path)

    # check convergence
    if not modflow_converged(list_file) and not run_if_unconverged:
        return

    # output information
    (out_obs, all_riv_obs, dry_hds, flooded_cells,
     all_hds, all_riv, all_str_flow, str_flow_out) = generate_outputs(hds_file, cbc_file)

    # save output
    out_obs.to_csv(model_ws.joinpath('observations.dat'), sep='\t', index=False)
    np.savetxt(model_ws.joinpath('dry_cells.txt'), dry_hds, fmt='%d')
    np.savetxt(model_ws.joinpath('flooded_cells.txt'), flooded_cells, fmt='%d')

    # plot stuff
    if plot:
        visualise_model(model_ws, all_hds, dry_hds, out_obs, all_riv_obs, flooded_cells, all_riv, list_file,
                        all_str_flow, str_flow_out,
                        plot_dir=plot_dir)


if __name__ == '__main__':
    t = time.time()
    test_hds = Path('/home/matt_dumont/unbacked/hawea/structure_v9/init_v9/base_model/opt_model.hds')
    process_model_output(test_hds.parent,
                         test_hds,
                         plot=True,
                         run_if_unconverged=True)
    print(f'took {time.time() - t}s to process output')
