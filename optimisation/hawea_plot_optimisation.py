"""
created matt_dumont 
on: 25/10/22
"""
import os.path
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import FuncNorm, Normalize
from matplotlib.colorbar import ColorbarBase
import pandas as pd
from model_build.project_model_tools import smt
from model_build.utils import get_colors
from targets_and_sensitive_sites.model_output import process_model_output
from optimisation.model_utils_for_forward_run import read_param_data, build_run_model
from model_tools.plot_optimisation import plot_optimisation_and_extract_info
from model_parameterisation.inital_parametersiation import *
from model_parameterisation.pilot_points import interpolate_sy_pilot_points, interpolate_kh_pilot_points
from model_tools.util_functions.list_file_utils import ListSolverInfo
import py7zr
from targets_and_sensitive_sites.model_output import plot_hds_regular_locator, base_regular_groupnames
from optimisation.optimisation_period import tdis

# todo check carefully with multiple layers


def plot_opt(pest_dir, replot=False, plot_failure_points=True, check_success=False):
    base_plot_dir = Path(pest_dir).joinpath('Base_Optimisation_plots')
    if base_plot_dir.exists() and not replot:
        print('optimisation plots already present')
        return
    base_plot_dir.mkdir(exist_ok=True)
    base_optimised_model_dir = Path(pest_dir).joinpath('Final_opt_model')

    # run final model
    name = 'final_opt_model'
    model_ws = base_optimised_model_dir
    opt_par_file = list(pest_dir.glob('[!trial]*.par'))
    assert len(opt_par_file) == 1
    opt_par_file = opt_par_file[0]

    kh_param, sy_param, riv_param, hill_param, race_param, rch_param = read_param_data(model_ws,
                                                                                       parameter_file=opt_par_file,
                                                                                       format='pest')

    build_run_model(
        model_name=name, model_ws=model_ws,
        kh_param=kh_param,
        sy_param=sy_param,
        riv_params=riv_param,
        hill_param=hill_param,
        race_param=race_param,
        rch_param=rch_param
    )
    opt_plot_dir = base_plot_dir.joinpath('final_opt_model')
    opt_plot_dir.mkdir(exist_ok=True)
    process_model_output(model_ws=model_ws,
                         hds_file=model_ws.joinpath(f'{name}.hds'),
                         plot=True,
                         plot_dir=opt_plot_dir,
                         savelist=False,
                         save_param=False)

    # add from model tools
    plot_optimisation_and_extract_info(pest_dir=pest_dir, base_plot_dir=base_plot_dir)
    _plot_high_freq_heads(pest_dir, base_plot_dir.joinpath('regular_hds_closeup'))

    pp_locs = get_pilot_point_locations()
    pp_locs.loc[:, 'hk'] = [kh_param[e] for e in pp_locs.index]
    pp_locs.loc[:, 'sy'] = [sy_param[e] for e in pp_locs.index]

    _plot_spatial_kh_sy(sy_param, kh_param, base_plot_dir, pp_locs)
    _plot_param_at_bounds(base_plot_dir, pp_locs, kh_param, sy_param, riv_param, hill_param, race_param, rch_param)

    if plot_failure_points:
        _plot_failures(pest_dir, base_plot_dir)
    elif check_success:
        _just_check_success(pest_dir, base_plot_dir)


def _dummy(x):
    return x


def _plot_param_at_bounds(base_plot_dir, pp_locs, kh_param, sy_param, riv_param, hill_param, race_param, rch_param):
    init_sy_param = get_inital_sy()
    init_kh_param = get_inital_kh()
    init_race_param = get_race_multiplier()
    init_hill_param = get_hillslope_multiplier()
    init_riv_param = get_initial_riv_conductance()
    init_rch_param = get_initial_rch_mult()
    out = pd.DataFrame(columns=['group', 'norm_param_val'])
    out.index.name = 'pname'
    for pref in ['race', 'hill', 'riv', 'sy', 'kh', 'rch']:
        init = eval(f'init_{pref}_param')
        meas = eval(f'{pref}_param')
        for k, (start, (upper, lower)) in init.items():
            imesure = meas[k]
            out.loc[k, 'group'] = pref
            if pref in ['riv', 'kh']:
                out.loc[k, 'norm_param_val'] = ((np.log10(imesure) - np.log10(lower))
                                                / (np.log10(upper) - np.log10(lower)))
            else:
                out.loc[k, 'norm_param_val'] = (imesure - lower) / (upper - lower)
    with open(base_plot_dir.joinpath('parameters_norm_to_bounds.txt'), 'w') as f:
        f.write(out.to_string())
    out = out.loc[(out.norm_param_val >= 0.9) | (out.norm_param_val <= 0.1)]
    with open(base_plot_dir.joinpath('parameters_norm_to_bounds_close.txt'), 'w') as f:
        f.write(out.to_string())

    # pps at locs
    prefs = ['sy', 'kh', ]
    locs = [pp_locs, pp_locs]
    for pref, plocs in zip(prefs, locs):
        init = eval(f'init_{pref}_param')
        meas = eval(f'{pref}_param')
        for k, (start, (upper, lower)) in init.items():
            imesure = meas[k]
            if pref == 'kh':
                norm_val = ((np.log10(imesure) - np.log10(lower))
                            / (np.log10(upper) - np.log10(lower)))
            else:
                norm_val = (imesure - lower) / (upper - lower)
            plocs.loc[k, pref] = norm_val

    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10, 8))
    smt.plot.plt_basemap(ax1)
    smt.plot.plt_basemap(ax2)
    ax1.set_title('Kh normalised')
    ax2.set_title('Sy normalised')
    norm = FuncNorm((_dummy, _dummy), vmin=0, vmax=1)

    ax1.scatter(pp_locs.x, pp_locs.y, c=pp_locs.kh, cmap='plasma', norm=norm)
    sc = ax2.scatter(pp_locs.x, pp_locs.y, c=pp_locs.sy, cmap='plasma', norm=norm)
    fig.colorbar(sc, location='bottom')
    fig.tight_layout()
    fig.savefig(base_plot_dir.joinpath('parameter_norm_sy_kh.png'))


def _plot_spatial_kh_sy(sy_param, kh_param, base_plot_dir, pp_locs):
    # plot rch multiplier array, kh, sy array
    sy_array = interpolate_sy_pilot_points(sy_param)
    kh_array = interpolate_kh_pilot_points(kh_param)

    fig, ax = smt.plot.plt_matrix(sy_array[0], base_map=True, no_flow_layer=0, title='Sy field')
    fig.tight_layout()
    fig.savefig(base_plot_dir.joinpath('sy_array.png'))

    fig, (ax, ax1) = plt.subplots(ncols=2, figsize=(10, 8))
    smt.plot.plt_matrix(kh_array[0], base_map=True, no_flow_layer=0, title='Kh field', ax=ax)
    smt.plot.plt_matrix(np.log10(kh_array[0]), base_map=True, no_flow_layer=0, title='log10 Kh field', ax=ax1)
    fig.tight_layout()
    fig.savefig(base_plot_dir.joinpath('kh_array.png'))

    for k in ['hk', 'sy']:
        title_key = f'{k} data'
        if k == 'kh':
            title_key = f'{k} log10 data'

        fig, ax = smt.plot.plt_basemap(base_map=True, no_flow_layer=0)
        ax.set_title(title_key)
        ax.scatter(pp_locs.x, pp_locs.y)
        for x, y, s in pp_locs.loc[:, ['x', 'y', k]].itertuples(False, None):
            if k == 'kh':
                s = np.log10(s)
            ax.text(x, y, str(round(s, 2)))
        fig.tight_layout()
        fig.savefig(base_plot_dir.joinpath(f'{k}_values.png'))


def _plot_failures(pest_dir, base_plot_dir):
    # location of failures (e.g. model cells with max change over n iterations), use utls.listfilestuff that I wrote.
    all_overs, all_itters, model_converged = get_all_list_data(pest_dir, 50, 0)
    with open(base_plot_dir.joinpath('convergence_record.txt'), 'w') as f:
        f.write(f'model convergence percentage: {np.array(model_converged).sum() / len(model_converged) * 100}')

    limits = [50, 100, 300, 500, 800]
    for l in limits:
        temp = all_overs.loc[all_overs.outer_iter >= l]
        temp = temp.drop_duplicates(subset=['layer', 'row', 'column', 'nper', 'nstp'])
        plt_data = temp.groupby(['layer', 'row', 'column']).count().outer_iter.reset_index()
        fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
        ax.scatter(*smt.convert_matrix_to_coords(plt_data.row, plt_data.column), s=plt_data.outer_iter, color='r')
        fig.tight_layout()
        fig.savefig(base_plot_dir.joinpath(f'more_than_{l}_outers.png'))

    t = all_itters.loc[:, ['nper', 'outer_itts']].groupby('nper').describe().loc[:, 'outer_itts']
    fig, ax = plt.subplots(figsize=(8, 10))
    t.loc[:, ['min', 'mean', 'max']].plot(ax=ax)
    ax.set_xlabel('nper')
    ax.set_ylabel('outer iterations')
    fig.tight_layout()
    fig.savefig(base_plot_dir.joinpath('iterations_per_nper.png'))
    t = t.sort_values('mean', ascending=False)

    with open(base_plot_dir.joinpath('num_outer_itts.txt'), 'w') as f:
        f.write(t.to_string())


def get_all_list_data(pest_dir, outer, inner):
    pest_dir = Path(pest_dir)
    listfiles = []
    temp = [open(e, 'r') for e in pest_dir.rglob("**/*.list")]
    listfiles.extend(temp)
    outdata_solver = []
    outdata_itters = []
    model_converged = []
    nfailed = 0
    for i, f in enumerate(listfiles):
        if i % 100 == 0:
            print(f'extracting file {i}')
        try:
            temp = ListSolverInfo(f)
            outdata_solver.append(temp.get_over(outer, inner))
            outdata_itters.append(temp.itteration_overview)
            model_converged.append(smt.modelchecks.modflow_converged(lines=temp.lines))
        except Exception as val:
            nfailed += 1
            print(f'{nfailed} total lists have failed to be read: {val}')
        f.close()

    for i, p in enumerate(pest_dir.rglob('**/list_*.7z')):
        if i % 100 == 0:
            print(f'reading and extracting zipped file {i}: {p}')
        temp_listfiles = []
        with py7zr.SevenZipFile(p, 'r') as zip:
            temp_listfiles.extend(zip.readall().values())
        for f in temp_listfiles:
            try:
                temp = ListSolverInfo(f)
                model_converged.append(smt.modelchecks.modflow_converged(lines=temp.lines))
                outdata_solver.append(temp.get_over(outer, inner))
                outdata_itters.append(temp.itteration_overview)
            except Exception as val:
                nfailed += 1
                print(f'{nfailed} total lists have failed to be read: {val}')
            f.close()
    outdata_solver = pd.concat(outdata_solver).reset_index()
    outdata_itters = pd.concat(outdata_itters).reset_index()
    return outdata_solver, outdata_itters, model_converged


def _just_check_success(pest_dir, base_plot_dir):
    pest_dir = Path(pest_dir)
    model_converged = []
    raw_listfiles = [open(e, 'r') for e in pest_dir.rglob("**/*.list")]
    nfailed = []
    for i, f in enumerate(raw_listfiles):
        if i % 100 == 0:
            print(f'extracting file {i}')
        model_converged.append(smt.modelchecks.modflow_converged(f))

    for i, p in enumerate(pest_dir.rglob('**/list_*.7z')):
        if i % 100 == 0:
            print(f'reading and extracting zipped file {i}: {p}')
        temp_listfiles = []
        with py7zr.SevenZipFile(p, 'r') as zip:
            temp_listfiles.extend(zip.readall().values())
        for f in temp_listfiles:
            try:
                model_converged.append(smt.modelchecks.modflow_converged(f))
            except Exception as val:
                nfailed += 1
                print(f'{nfailed} total lists have failed to be read: {val}')
            f.close()
    with open(base_plot_dir.joinpath('convergence_record.txt'), 'w') as f:
        f.write(f'model convergence percentage: {np.array(model_converged).sum() / len(model_converged) * 100}')


def _plot_high_freq_heads(pest_dir, plot_dir):
    plot_dir.mkdir(exist_ok=True)
    regular_hds = {}
    all_obs_files = pest_dir.glob('*.rei.*')
    # read in all of the regualr heads
    for f in all_obs_files:
        i = int(f.name.split('.')[-1])
        hds_obs = pd.read_fwf(f, skiprows=4)
        hds_obs.rename(columns={e: e.lower() for e in hds_obs.keys()}, inplace=True)
        hds_obs.loc[:, 'weight'] = pd.to_numeric(hds_obs.loc[:, 'weight'], 'coerce')
        hds_obs.loc[:, 'residual'] = pd.to_numeric(hds_obs.loc[:, 'residual'], 'coerce')
        hds_obs.loc[:, 'modelled'] = pd.to_numeric(hds_obs.loc[:, 'modelled'], 'coerce')
        hds_obs.loc[:, 'measured'] = pd.to_numeric(hds_obs.loc[:, 'measured'], 'coerce')
        hds_obs.loc[:, 'iphi'] = (hds_obs.loc[:, 'residual'] * hds_obs.loc[:, 'weight']) ** 2
        mapper = {'h_piezo': 'h_piezo',
                  'h_single_3': 'h_single_3',
                  'h_single_1': 'h_single_1'}
        mapper.update({k: 'regular' for k in base_regular_groupnames})
        hds_obs.loc[:, 'group'] = hds_obs.loc[:, 'group'].replace(mapper)
        hds_obs.loc[:, 'well_name'] = [f'{"_".join(e.split("_")[:-1])}' for e in hds_obs.loc[:, 'name']]
        hds_obs = hds_obs.loc[hds_obs.loc[:, 'group'] == 'regular']
        hds_obs.loc[:, 'nper'] = hds_obs.name.str.split('_').str.get(-1).astype(int)
        hds_obs.loc[:, 'date'] = tdis.get_date(hds_obs.loc[:, 'nper'])
        hds_obs.loc[:, 'week'] = hds_obs.date.dt.isocalendar().loc[:, 'week']

        regular_hds[i] = hds_obs

    opt_steps = sorted(list(regular_hds.keys()))
    colors = get_colors(opt_steps, 'plasma')

    reg_colormap = 'tab10'
    regular_wells = sorted(regular_hds[opt_steps[0]].well_name.unique())
    regular_colors = get_colors(regular_wells, reg_colormap)

    for n, nc in zip(regular_wells, regular_colors):
        # full dataset
        fig, axs = plt.subplots(nrows=2, ncols=2, figsize=(14, 9),
                                gridspec_kw=dict(width_ratios=(2, 1), height_ratios=(50, 1)))
        ax = axs[0, 0]
        ax_loc = axs[0, 1]
        cbar = axs[1, 0]
        for k, c in zip(opt_steps, colors):
            temp2 = regular_hds[k].loc[regular_hds[k].well_name == n].sort_values('date')
            ax.plot(temp2.date, temp2.modelled, color=c)

        ax.scatter(temp2.date, temp2.measured, color=nc, label=f'{n.capitalize()} measured')
        ax.plot([temp2.date.iloc[0]], [temp2.modelled.iloc[0]], color=nc, label=f'{n.capitalize()} modelled')
        plot_hds_regular_locator(ax_loc, {n: nc})
        ax.set_title(f'{n.capitalize()} hds')
        ax.set_xlabel('Date')
        ax.set_ylabel('Weekly mean Head (m)')
        ax.legend()
        norm = Normalize(vmin=min(opt_steps), vmax=max(opt_steps))

        cb1 = ColorbarBase(cbar, cmap='plasma',
                           norm=norm,
                           orientation='horizontal')
        cb1.set_label('Opt step')
        for cmap_ax in axs[:, 1]:
            cmap_ax.set_xticks([])
            cmap_ax.set_yticks([])

            # kill frame around ax..
            cmap_ax.spines["top"].set_visible(False)
            cmap_ax.spines["right"].set_visible(False)
            cmap_ax.spines["left"].set_visible(False)
            cmap_ax.spines["bottom"].set_visible(False)
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'hds_closeup_{n}.png'))
        plt.close(fig)


if __name__ == '__main__':
    from project_base import unbacked_dir
    from optimisation.a_build_run_optimisation_version import branch

    plot_failures = False  # keynote this can take a really long time with a long optimisation
    check_success = False  # takes too long
    re_plot = False  # keynote don't set this to True!
    pest_runs = unbacked_dir.joinpath(branch).glob('*/Optimisations')

    for d in pest_runs:
        print(f'plotting: {d}')
        plot_opt(d, replot=re_plot, plot_failure_points=plot_failures, check_success=check_success)
