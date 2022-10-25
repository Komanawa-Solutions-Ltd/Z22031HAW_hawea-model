"""
created matt_dumont 
on: 25/10/22
"""
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from targets_and_sensitive_sites.model_output import process_model_output
from optimisation.model_utils_for_forward_run import read_param_data, build_run_model
from model_tools.plot_optimisation import plot_optimisation_and_extract_info


def plot_opt(pest_dir):
    base_plot_dir = Path(pest_dir).joinpath('Base_Optimisation_plots')
    base_optimised_model_dir = Path(pest_dir).joinpath('Final_opt_model')

    # run final model
    name = 'final_opt_model'
    model_ws = base_optimised_model_dir
    kh_param, sy_param, riv_params, hill_param, race_param = read_param_data(model_ws,
                                                                             parameter_file=)  # todo set parameter file
    build_run_model(
        model_name=name, model_ws=model_ws,
        kh_param=kh_param,
        sy_param=sy_param,
        riv_params=riv_params,
        hill_param=hill_param,
        race_param=race_param
    )
    process_model_output(model_ws=model_ws,
                         hds_file=model_ws.joinpath(f'{name}.hds'),
                         plot=True,
                         plot_dir=base_plot_dir.joinpath('final_opt_model'))

    # add from model tools
    plot_optimisation_and_extract_info(pest_dir=pest_dir, base_plot_dir=base_plot_dir)

    # todo location of parameters at bound

    # todo location of failures (e.g. model cells with max change over n iterations)


if __name__ == '__main__':
    for d in [
        '/home/matt_dumont/Downloads/beopest_2022_10_21',
        '/home/matt_dumont/Downloads/beopest_2022_10_22',
        '/home/matt_dumont/Downloads/beopest_2022_10_22.2',
        '/home/matt_dumont/Downloads/beopest_2022_10_22.2_increase_sy_mult_bounds',
    ]:
        print(f'plotting: {d}')
        plot_opt(Path(d))
