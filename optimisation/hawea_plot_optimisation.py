"""
created matt_dumont 
on: 25/10/22
"""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.colors import FuncNorm
import pandas as pd
from model_build.project_model_tools import smt
from targets_and_sensitive_sites.model_output import process_model_output
from optimisation.model_utils_for_forward_run import read_param_data, build_run_model
from model_tools.plot_optimisation import plot_optimisation_and_extract_info
from model_parameterisation.inital_parametersiation import *


def plot_opt(pest_dir):
    base_plot_dir = Path(pest_dir).joinpath('Base_Optimisation_plots')
    base_plot_dir.mkdir(exist_ok=True)
    base_optimised_model_dir = Path(pest_dir).joinpath('Final_opt_model')

    # run final model
    name = 'final_opt_model'
    model_ws = base_optimised_model_dir
    opt_par_file = list(pest_dir.glob('*.par'))
    assert len(opt_par_file) == 1
    opt_par_file = opt_par_file[0]

    kh_param, sy_param, riv_param, hill_param, race_param = read_param_data(model_ws,
                                                                            parameter_file=opt_par_file,
                                                                            format='pest')

    build_run_model(
        model_name=name, model_ws=model_ws,
        kh_param=kh_param,
        sy_param=sy_param,
        riv_params=riv_param,
        hill_param=hill_param,
        race_param=race_param
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

    # location of parameters at bound
    init_sy_param = get_inital_sy()
    init_kh_param = get_inital_kh()
    init_race_param = get_race_multiplier()
    init_hill_param = get_hillslope_multiplier()
    init_riv_param = get_initial_riv_conductance()
    pp_locs = get_pilot_point_locations()

    out = pd.DataFrame(columns=['group', 'norm_param_val'])
    out.index.name = 'pname'
    for pref in ['race', 'hill', 'riv', 'sy', 'kh']:
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
    for pref in ['sy', 'kh']:
        init = eval(f'init_{pref}_param')
        meas = eval(f'{pref}_param')
        for k, (start, (upper, lower)) in init.items():
            imesure = meas[k]
            norm_val = (imesure - lower) / (upper - lower)
            if k in ['sandy', 'mang']:
                pp_locs.loc[pp_locs.group == k, pref] = norm_val
            else:
                pp_locs.loc[k, pref] = norm_val

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


# todo location of failures (e.g. model cells with max change over n iterations)
def _dummy(x):
    return x


if __name__ == '__main__':
    for d in [
        '/home/matt_dumont/Downloads/beopest_2022_10_21',
        # '/home/matt_dumont/Downloads/beopest_2022_10_22',
        # '/home/matt_dumont/Downloads/beopest_2022_10_22.2',
        # '/home/matt_dumont/Downloads/beopest_2022_10_22.2_increase_sy_mult_bounds',
    ]:
        print(f'plotting: {d}')
        plot_opt(Path(d))
