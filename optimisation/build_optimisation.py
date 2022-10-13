"""
created matt_dumont 
on: 11/10/22
"""

import os
import shutil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pyemu
import flopy
import sys
from pathlib import Path
from optimisation.optimisation_period import start
from model_parameterisation.inital_parametersiation import get_race_multiplier, get_hillslope_multiplier, \
    get_initial_riv_conductance, get_inital_sy, get_inital_kh


def make_template_and_infiles(pst_dir):
    param_fs = [get_race_multiplier, get_hillslope_multiplier,
                get_initial_riv_conductance, get_inital_sy, get_inital_kh]
    param_groups = ['race', 'hill', 'riv', 'sy', 'kh']
    param_names = []
    param_starts = []
    tpl_file = pst_dir.joinpath('parameters.dat.tpl')
    input_file = pst_dir.joinpath('parameters.dat')

    for f, g in zip(param_fs, param_groups):
        temp = f()
        keys = list(temp.keys())
        param_names.extend([f'{g}_{k}' for k in keys])
        param_starts.extend([temp[k][0] for k in keys])

    param_data = pd.DataFrame({'name': param_names, 'start': param_starts})

    param_data.to_csv(input_file, sep=' ', header=False, index=False)
    param_data.loc[:, 'start'] = [f'~{e:^20}~' for e in param_data.name]
    with open(tpl_file, 'w') as f:
        f.write('ptf ~\n')
    param_data.to_csv(tpl_file, sep='\t', header=False, index=False, mode='a')

    return [str(input_file)], [str(tpl_file)]
    # todo format correct, proably???


def make_ins_and_output_files(pst_dir):
    # todo make observation files

    ins_file = pst_dir.joinpath('observations.ins')
    output_file = pst_dir.joinpath('observations.dat')
    return [str(ins_file)], [str(output_file)]  # todo format correct


def raw_pest(pst_dir=Path.home().joinpath('Downloads/raw_pst_trial')):
    # todo manage env and others
    # see https://github.com/pypest/pyemu/blob/develop/examples/modflow_to_pest_like_a_boss.ipynb

    # todo use optimisation/pest_run_data
    # todo I like this better for the way that I expect to run the thing.
    pst_dir.mkdir(exist_ok=True)

    pst_path = pst_dir.joinpath('opt.pst')

    # make parameter files
    input_files, tpl_files = make_template_and_infiles(pst_dir)

    ins_files, output_files = make_ins_and_output_files(pst_dir)

    # todo add observations

    pst = pyemu.Pst.from_io_files(tpl_files, input_files, ins_files, output_files)


    # todo prior information

    # todo regularisation???

    # todo make obj function inc weights

    # todo modify, need to use the right python env
    pst.model_command = ["python forward_run.py"]

    pass


if __name__ == '__main__':
    make_template_and_infiles(Path.home().joinpath('Downloads/raw_pst_trial'))
    raw_pest()
pass
