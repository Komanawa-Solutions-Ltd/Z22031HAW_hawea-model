"""
created matt_dumont 
on: 25/10/22
"""
import os.path
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.colors import FuncNorm
import pandas as pd
from model_build.project_model_tools import smt
from targets_and_sensitive_sites.model_output import process_model_output
from optimisation.model_utils_for_forward_run import read_param_data, build_run_model
from model_tools.plot_optimisation import plot_optimisation_and_extract_info
from model_parameterisation.inital_parametersiation import *
from model_parameterisation.pilot_points import interpolate_rch_pilot_points, interpolate_sy_pilot_points, \
    interpolate_kh_pilot_points
from model_tools.util_functions.list_file_utils import ListSolverInfo
import py7zr


def plot_opt(pest_dir, replot=False, plot_failure_points=True):
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

    # location of parameters at bound # todo not working right???, check
    init_sy_param = get_inital_sy()
    init_kh_param = get_inital_kh()
    init_race_param = get_race_multiplier()
    init_hill_param = get_hillslope_multiplier()
    init_riv_param = get_initial_riv_conductance()
    init_rch_param = get_initial_rch_mult()
    pp_locs = get_pilot_point_locations()
    rch_pp_locs = get_rch_pilot_point_locations()

    # plot rch multiplier array, kh, sy array
    rch_mult_array = interpolate_rch_pilot_points(rch_param)
    sy_array = interpolate_sy_pilot_points(sy_param)
    kh_array = interpolate_kh_pilot_points(kh_param)

    fig, ax = smt.plot.plt_matrix(rch_mult_array, base_map=True, no_flow_layer=0, title='Rch multiplier')
    fig.tight_layout()
    fig.savefig(base_plot_dir.joinpath('rch_mult_array.png'))

    fig, ax = smt.plot.plt_matrix(sy_array[0], base_map=True, no_flow_layer=0, title='Sy field')
    fig.tight_layout()
    fig.savefig(base_plot_dir.joinpath('sy_array.png'))

    fig, (ax, ax1) = plt.subplots(ncols=2)
    smt.plot.plt_matrix(kh_array[0], base_map=True, no_flow_layer=0, title='Kh field', ax=ax)
    smt.plot.plt_matrix(np.log10(kh_array[0]), base_map=True, no_flow_layer=0, title='log10 Kh field', ax=ax1)
    fig.tight_layout()
    fig.savefig(base_plot_dir.joinpath('kh_array.png'))

    out = pd.DataFrame(columns=['group', 'norm_param_val'])
    out.index.name = 'pname'
    for pref in ['race', 'hill', 'riv', 'sy', 'kh', 'rch']:
        init = eval(f'init_{pref}_param')
        meas = eval(f'{pref}_param')
        for k, (start, (upper, lower)) in init.items():
            imesure = meas[k]
            out.loc[k, 'group'] = pref
            out.loc[k, 'norm_param_val'] = (imesure - lower) / (upper - lower)
    with open(base_plot_dir.joinpath('parameters_norm_to_bounds.txt'), 'w') as f:
        f.write(out.to_string())
    out = out.loc[(out.norm_param_val >= 0.9) | (out.norm_param_val <= 0.1)]
    with open(base_plot_dir.joinpath('parameters_norm_to_bounds_close.txt'), 'w') as f:
        f.write(out.to_string())

    # pps at locs
    prefs = ['sy', 'kh', 'rch']
    locs = [pp_locs, pp_locs, rch_pp_locs]
    for pref, plocs in zip(prefs, locs):
        init = eval(f'init_{pref}_param')
        meas = eval(f'{pref}_param')
        for k, (start, (upper, lower)) in init.items():
            imesure = meas[k]
            norm_val = (imesure - lower) / (upper - lower)
            plocs.loc[k, pref] = norm_val

    fig, (ax1, ax2, ax3) = plt.subplots(ncols=3, figsize=(10, 8))
    smt.plot.plt_basemap(ax1)
    smt.plot.plt_basemap(ax2)
    smt.plot.plt_basemap(ax3)
    ax1.set_title('Kh normalised')
    ax2.set_title('Sy normalised')
    ax3.set_title('Rch mult normalised')
    norm = FuncNorm((_dummy, _dummy), vmin=0, vmax=1)

    ax1.scatter(pp_locs.x, pp_locs.y, c=pp_locs.kh, cmap='plasma', norm=norm)
    sc = ax2.scatter(pp_locs.x, pp_locs.y, c=pp_locs.sy, cmap='plasma', norm=norm)
    ax3.scatter(rch_pp_locs.x, rch_pp_locs.y, c=rch_pp_locs.rch, cmap='plasma', norm=norm)
    fig.colorbar(sc, location='bottom')
    fig.tight_layout()
    fig.savefig(base_plot_dir.joinpath('parameter_norm_sy_kh.png'))

    if plot_failure_points:
        # location of failures (e.g. model cells with max change over n iterations), use utls.listfilestuff that I wrote.
        all_overs, all_itters = get_all_list_data(pest_dir, 50, 0)

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


def _dummy(x):
    return x


def get_all_list_data(pest_dir, outer, inner):
    pest_dir = Path(pest_dir)
    listfiles = []
    temp = [open(e, 'r') for e in pest_dir.rglob("**/*.list")]
    listfiles.extend(temp)
    for i, p in enumerate(pest_dir.rglob('**/list_*.7z')):
        if i % 100 == 0:
            print(f'reading file {i}: {p}')
        with py7zr.SevenZipFile(p, 'r') as zip:
            listfiles.extend(zip.readall().values())
    outdata_solver = []
    outdata_itters = []
    for i, f in enumerate(listfiles):
        if i % 100 == 0:
            print(f'extracting file {i}')
        temp = ListSolverInfo(f)
        outdata_solver.append(temp.get_over(outer, inner))
        outdata_itters.append(temp.itteration_overview)
        f.close()
    outdata_solver = pd.concat(outdata_solver).reset_index()
    outdata_itters = pd.concat(outdata_itters).reset_index()
    return outdata_solver, outdata_itters


if __name__ == '__main__':
    from project_base import unbacked_dir

    plot_failures = False  # keynote this can take a really long time with a long optimisation
    re_plot = False  # keynote don't set this to True!
    pest_runs = unbacked_dir.joinpath(branch).glob('*/Optimisations')

    for d in pest_runs:
        print(f'plotting: {d}')
        plot_opt(d, replot=re_plot, plot_failure_points=False)
