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

default_output_path = Path(
    '/home/matt_dumont/Downloads/test_model/observations.dat')  # todo replace with repo when done


def _get_param_data():
    param_fs = [get_race_multiplier, get_hillslope_multiplier,
                get_initial_riv_conductance, get_inital_sy, get_inital_kh]
    param_groups = ['race', 'hill', 'riv', 'sy', 'kh']
    param_names = []
    param_starts = []
    param_low = []
    param_up = []

    for f, g in zip(param_fs, param_groups):
        temp = f()
        keys = list(temp.keys())
        param_names.extend([f'{g}_{k}' for k in keys])
        param_starts.extend([temp[k][0] for k in keys])
        param_low.extend([temp[k][1][0] for k in keys])
        param_up.extend([temp[k][1][1] for k in keys])

    param_data = pd.DataFrame({'name': param_names, 'start': param_starts,
                               'low': param_low, 'up': param_up})
    return param_data


def _get_base_obs():
    default_data = pd.read_csv(default_output_path, sep='\t')
    return default_data


def make_template_and_infiles(pst_dir):
    tpl_file = pst_dir.joinpath('parameters.dat.tpl')
    input_file = pst_dir.joinpath('parameters.dat')
    param_data = _get_param_data()
    param_data.to_csv(input_file, sep='\t', header=False, index=False)
    param_data.loc[:, 'start'] = [f'~{e:^20}~' for e in param_data.name]
    with open(tpl_file, 'w') as f:
        f.write('ptf ~\n')
    param_data.to_csv(tpl_file, sep='\t', header=False, index=False, mode='a')

    return [str(input_file)], [str(tpl_file)]
    # todo format correct, proably???


def make_ins_and_output_files(pst_dir):
    output_file = pst_dir.joinpath('observations.dat')
    ins_file = pst_dir.joinpath('observations.dat.ins')
    output_file.unlink(missing_ok=True)

    shutil.copyfile(default_output_path, output_file)

    default_data = _get_base_obs()

    # make observation instruction files
    with open(ins_file, 'w') as f:
        f.write('pif ~\n')
        f.write('~name~\n')
        for n in default_data.loc[:, 'name']:
            f.write(f'l1 w w w w !{n}!\n')

    return [str(ins_file)], [str(output_file)]  # todo format correct, probably


def raw_pest(name='opt',pst_dir=Path.home().joinpath('Downloads/raw_pst_trial')):
    # todo manage env and others
    # see https://github.com/pypest/pyemu/blob/develop/examples/modflow_to_pest_like_a_boss.ipynb

    # todo use optimisation/pest_run_data
    # todo I like this better for the way that I expect to run the thing.
    pst_dir.mkdir(exist_ok=True)

    pst_path = pst_dir.joinpath('opt.pst')

    # make parameter files
    input_files, tpl_files = make_template_and_infiles(pst_dir)

    ins_files, output_files = make_ins_and_output_files(pst_dir)

    pst = pyemu.Pst.from_io_files(tpl_files, input_files, ins_files, output_files)
    # todo control infomration
    pst.control_data.rstfle='restart'
    pst.control_data.pestmode = 'estimation'




    # todo add parameter details
    # set tranformation
    pst.parameter_data.loc[:, 'partrans'] = 'none'
    pst.parameter_data.loc[pst.parameter_data.index.str.contains('kh'), 'partrans'] = 'log'

    param_data = _get_param_data().set_index('name')
    # set inital values, lower, upper bounds
    all_params = pst.parameter_data.index
    pst.parameter_data.loc[all_params, 'parval1'] = param_data.loc[all_params, 'start']
    pst.parameter_data.loc[all_params, 'parlbnd'] = param_data.loc[all_params, 'low']
    pst.parameter_data.loc[all_params, 'parubnd'] = param_data.loc[all_params, 'up']
    pst.parameter_data.loc[all_params, 'pargp'] = all_params.str.split('_').str.get(0)
    # Not using scale and offset
    # 'dercom' # not using as only 1 model command (so far)

    'parchglim' # todo set kh to factor, multipliers to absolute, conductance to factor, sy as factor
    # add observation details
    base_obs = _get_base_obs().set_index('name')
    all_obs = pst.observation_data.index
    pst.observation_data.loc[:, 'obgnme'] = base_obs.loc[all_obs, 'group'].str.split('_').str.get(0)
    pst.observation_data.loc[:, 'obsval'] = base_obs.loc[all_obs, 'measured']
    temp = np.full(all_obs.shape, 1)
    temp[base_obs.group == 'single_3'] = 2  # Keynote weight single targets qual 3  2x qual 1
    pst.observation_data.loc[:, 'weight'] = temp

    # todo group weights??? how do I address intergroup


    # todo prior information

    # todo regularisation???

    # todo make obj function inc weights

    # todo modify, need to use the right python env
    pst.model_command = ["python forward_run.py"]
    pst.write(pst_dir.joinpath(f'{name}.pst'))
    pass


if __name__ == '__main__':
    raw_pest()
pass
