"""
created matt_dumont 
on: 7/09/22
"""
import shutil
import time
import py7zr
import flopy
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from targets_and_sensitive_sites.head_targets import get_all_hds_targets, plot_hds_zone_locator, \
    plot_hds_regular_locator
from targets_and_sensitive_sites.riv_gain_loss_targets import get_riv_target_locs, get_hawea_gain_loss_nper
from optimisation.optimisation_period import tdis
from model_build.supporting_data_analysis import get_river_loc_data
from model_build.utils import get_colors, plot_1_to_1
from model_build.project_model_tools import get_bottom, get_top, get_ibound, smt

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


def generate_outputs(hds_path, cbc_path):
    all_hds = flopy.utils.HeadFile(hds_path).get_alldata()
    all_hds[all_hds > 1e20] = np.nan
    hds = get_all_hds_targets(tdis)
    # keynote this assumes 1 step per stress period
    hds.loc[:, 'modelled'] = all_hds[hds.nper, hds.k, hds.i, hds.j]
    bots = get_bottom()
    tops = get_top()
    ibound = get_ibound()
    #  keynote set dry observations to bottom of cell -5m
    hds.loc[hds.modelled < -666, 'modelled'] = bots[hds.loc[hds.modelled < -666, 'i'],
                                                    hds.loc[hds.modelled < -666, 'j']] - 5

    # dry cells at non-target data points
    dry_hds = (all_hds < -666) & (ibound == 1)

    # flooded cells
    flooded_cells = (all_hds > tops) & (ibound == 1)

    # extract riv targets
    riv = get_hawea_gain_loss_nper(tdis).reset_index()
    riv_locs = get_riv_target_locs()
    # keynote change if multiple steps
    pers = riv.nper.unique()
    all_riv = np.array(flopy.utils.CellBudgetFile(cbc_path).get_data(text='RIVER LEAKAGE', full3D=True))[:, 0]

    for per in pers:
        riv_leak = flopy.utils.CellBudgetFile(cbc_path).get_data(kstpkper=(0, per), text='RIVER LEAKAGE', full3D=True)
        all_riv[per] = np.array(riv_leak[0])[0]
    for i, target_key, nper in riv.loc[:, ['target_key', 'nper']].itertuples(True, None):
        riv.loc[i, 'modelled'] = all_riv[nper][riv_locs[target_key]].sum()

    # observations for clutha and hawea losses to see range
    all_riv_loc = get_river_loc_data()
    param_zones = all_riv_loc.param.unique()
    all_riv_obs = pd.DataFrame(index=tdis.pers, columns=param_zones)
    all_riv_obs.index.name = 'nper'
    for p in param_zones:
        temp = all_riv_loc.loc[all_riv_loc.param == p]
        all_riv_obs.loc[:, p] = all_riv[:, temp.i, temp.j].sum(axis=1)

    out_obs = []
    need_keys = ['name', 'group', 'zone', 'nper', 'measured', 'modelled']
    # add hds
    out_obs.append(hds.rename(columns={'head': 'measured'}).loc[:, need_keys])

    # add riv
    riv.loc[:, 'name'] = 'riv_h' + riv.target_key.astype(str) + '_' + riv.nper.astype(str)
    riv.loc[:, 'group'] = 'riv'
    riv.loc[:, 'zone'] = 'riv'
    out_obs.append(riv.rename(columns={'target_val': 'measured'}).loc[:, need_keys])

    # todo add dry hds?!?! to objective function????, probably not
    out_obs = pd.concat(out_obs)
    return out_obs, all_riv_obs, dry_hds.sum(axis=(0, 1)), flooded_cells.sum(axis=(0, 1)), all_hds


def visualise_model(model_ws, all_hds, dry_hds, out_obs, all_riv_obs, flooded_cells, list_file,
                    plot_transient_budget=False, plot_dir=None):
    assert isinstance(model_ws, Path)
    if plot_dir is None:
        plot_dir = model_ws.joinpath('plots')
    plot_dir.mkdir(exist_ok=True)
    ibound = smt.get_no_flow(0)

    reg_colormap = 'brg'

    # plot hds (ss)
    plt_hds = all_hds[0, 0]
    plt_hds[ibound != 1] = np.nan
    clevels = np.arange(np.nanmin(plt_hds), np.nanmax(plt_hds), 20)
    fig, ax = smt.plot.plt_matrix(plt_hds, no_flow_layer=0, base_map=True, title='Steady state heads',
                                  contour=True, label_contours=True, contour_levels=clevels)
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('ss_hds.png'))
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

    # plot all river observations
    fig, axs = plt.subplots(4, sharex=True, figsize=(12, 9))
    riv_keys = all_riv_obs.keys()
    riv_colors = get_colors(riv_keys)
    for ax, k, c in zip(axs, riv_keys, riv_colors):
        ax.plot(all_riv_obs.index, all_riv_obs.loc[:, k], color=c, marker='.', label=k)
        ax.axhline(0, ls=':', color='k')
        ax.set_yscale('symlog')
        ax.legend()
    fig.supxlabel('Period')
    fig.supylabel('River Gain/loss(-)')
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('all_river_fluxes.png'))
    plt.close(fig)

    hds_groups = ['piezo', 'single_3', 'single_1', 'regular']
    hds_colors = get_colors(hds_groups)

    # plot observations/objectiv function
    hds_obs = out_obs.loc[np.in1d(out_obs.group, hds_groups)]

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
    zones = hds_obs.zone.unique()
    zcolors = get_colors(zones)
    for g in hds_groups:
        fig, (ax, ax_loc) = plt.subplots(ncols=2, figsize=(12, 9), gridspec_kw=dict(width_ratios=(2, 1)))
        temp = hds_obs.loc[hds_obs.group == g]
        ax.set_aspect('equal')
        if g == 'regular':
            use_names = np.unique([f'{"_".join(e.split("_")[:-1])}' for e in temp.name])
            names = sorted(use_names)
            ncolors = get_colors(names, reg_colormap)
            for n, nc in zip(names, ncolors):
                temp2 = temp.loc[temp.name.str.contains(n)]
                ax.scatter(temp2.modelled, temp2.measured, color=nc, label=n.capitalize())
            plot_hds_regular_locator(ax_loc, {n: nc for n, nc in zip(names, ncolors)})
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
            use_names = np.unique([f'{"_".join(e.split("_")[:-1])}' for e in temp.name])
            names = sorted(use_names)
            ncolors = get_colors(names, reg_colormap)
            for n, nc in zip(names, ncolors):
                temp2 = temp.loc[temp.name.str.contains(n)]
                ax.scatter(temp2.nper, temp2.modelled - temp2.measured, color=nc, label=n.capitalize())
            plot_hds_regular_locator(ax_loc, {n: nc for n, nc in zip(names, ncolors)})
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

    # river observations
    fig, ax = plt.subplots(figsize=(9, 9))
    for n, c in zip(riv_keys, riv_colors):
        temp = out_obs.loc[(out_obs.name.str.contains(n)) & (out_obs.group == 'riv')]
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
    fig.savefig(plot_dir.joinpath('all_riv_targets.png'))
    plt.close(fig)

    # riv obs by time
    fig, axs = plt.subplots(3, sharex=True, figsize=(12, 9))
    for ax, n, c in zip(axs, riv_keys[:-1], riv_colors[:-1]):
        temp = out_obs.loc[(out_obs.name.str.contains(n)) & (out_obs.group == 'riv')]
        ax.scatter(temp.nper, temp.modelled - temp.measured, color=c, label=n.capitalize())
        ax.legend()
        ax.set_yscale('symlog')
        ax.axhline(0, ls=':', c='k', label='0 line')

    fig.suptitle('All riv residuals vs time')
    fig.supxlabel('Model period')
    fig.supylabel('Residual (modelled - measured, m3/day)')
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('all_riv_targets.png'))
    plt.close(fig)

    # pull out budgets and plot
    bud_names = [
        'STORAGE', 'CONSTANT_HEAD', 'WELLS', 'RIVER_LEAKAGE', 'HEAD_DEP_BOUNDS', 'RECHARGE', 'TOTAL'
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
    ax.set_yscale('symlog')
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

    # todo parameter shifts, need prior info, so later


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


def process_model_output(model_ws, hds_file, plot=False, savelist=True, save_param=True, plot_dir=None):
    model_ws = Path(model_ws)
    hds_file = Path(hds_file)
    list_file = hds_file.with_suffix('.list')
    cbc_file = hds_file.with_suffix('.cbc')
    parameter_file = model_ws.joinpath('parameters.dat')

    # save listfile and parameter file
    if savelist:
        save_list_dir = model_ws.joinpath('list_file_repo')
        save_list_dir.mkdir(exist_ok=True)
        n = max([-1] + [int(e.stem.split('_')[-1]) for e in save_list_dir.glob('*')]) + 1
        new_path = save_list_dir.joinpath(f'list_{n}.list')
        with py7zr.SevenZipFile(new_path.with_suffix(".7z"), 'w') as archive:
            archive.write(list_file)

    if save_param:
        save_param_dir = model_ws.joinpath('param_file_repo')
        save_param_dir.mkdir(exist_ok=True)
        n = max([-1] + [int(e.stem.split('_')[-1]) for e in save_param_dir.glob('*')]) + 1
        new_path = save_param_dir.joinpath(f'parameter_{n}.dat')
        shutil.copyfile(parameter_file, new_path)

    # check convergence
    if not modflow_converged(list_file):
        return

    # output information
    out_obs, all_riv_obs, dry_hds, flooded_cells, all_hds, = generate_outputs(hds_file, cbc_file)

    # save output
    out_obs.to_csv(model_ws.joinpath('observations.dat'), sep='\t', index=False)
    np.savetxt(model_ws.joinpath('dry_cells.txt'), dry_hds, fmt='%d')
    np.savetxt(model_ws.joinpath('dry_cells.txt'), flooded_cells, fmt='%d')

    # plot stuff
    if plot:
        visualise_model(model_ws, all_hds, dry_hds, out_obs, all_riv_obs, flooded_cells, list_file,
                        plot_dir=plot_dir)


if __name__ == '__main__':
    t = time.time()
    process_model_output('/home/matt_dumont/Downloads/test_model',
                         '/home/matt_dumont/Downloads/test_model/test.hds',
                         plot=True)
    print(f'took {time.time() - t}s to process output')
