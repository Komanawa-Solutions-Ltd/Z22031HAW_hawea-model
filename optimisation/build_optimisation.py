"""
created matt_dumont 
on: 11/10/22
"""

import shutil
import numpy as np
import pandas as pd
import pyemu
from pathlib import Path
from model_parameterisation.inital_parametersiation import get_race_multiplier, get_hillslope_multiplier, \
    get_initial_riv_conductance, get_inital_sy, get_inital_kh
from project_base import proj_root

base_pst_data = proj_root.joinpath('optimisation/pest_run_data')

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

    return [str(ins_file)], [str(output_file)]


def set_control_data(pst, trial):
    assert isinstance(pst, pyemu.Pst)
    # control information

    # lines 1-5
    pst.control_data.rstfle = 'restart'
    pst.control_data.pestmode = 'estimation'
    pst.control_data.precis = 'double'
    pst.control_data.phiratsuf = 0.3
    pst.control_data.obsreref = 'noobsreref'  # no observation re-referencing

    # line 5 (lambda stuff)
    pst.control_data.rlambda1 = 10
    pst.control_data.rlamfac = -3
    pst.control_data.phiratsuf = 0.3
    pst.control_data.phiredlam = 0.1
    pst.control_data.numlam = 10
    # what happens if modflow dies, no output files written
    pst.control_data.lamforgive = 'lamforgive'
    pst.control_data.derforgive = 'noderforgive'  # todo maybe consider further

    # line 6
    pst.control_data.relparmax = 10  # max 10% change
    pst.control_data.facparmax = 10  # max 10% change
    # pst.control_data.passed_options
    # pst.control_data.absparmax(1) = 0.1  # keynote hack see hack_for_absparmax, and issue

    pst.control_data.facorig = 0.001  # JD recommended default
    pst.control_data.iboundstick = 0  # do not stick parameters to paramter boundries
    pst.control_data.upvecbend = 0  # repect limits

    # line 7
    pst.control_data.phiredswh = 0.1  # switch to 3 point at 10% reduction
    pst.control_data.noptswitch = 1  # wait n itertations to switch to 3 point
    pst.control_data.doaui = 'noaui'  # no automatic user inter
    pst.control_data.dosenreuse = 'nosensereuse'  # do not use snsitivity reuse
    pst.control_data.boundscale = 'boundscale'  # treat the boundaries as confidence intervals for parameter scaling

    # splitswh  # do no supply not using spllit slope analysis

    # line 8
    if trial:
        pst.control_data.noptmax = 0  # max iterations, set to 0 for trial run!!
    else:
        pst.control_data.noptmax = 50  # max iterations

    pst.control_data.phiredstp = 0.005  # relative phi change to be 'optimised'
    pst.control_data.nphistp = 4  # min number of iterations with relative phi change before optimisation is complete
    pst.control_data.nphinored = 4  # no reduction in phi for n iterations, complete
    pst.control_data.relparstp = 0.005  # maximum parameter change to finish
    pst.control_data.nrelpar = 4  # number of iterations below maximum parameter change to finish

    # do not include
    # phistopthresh
    # lastrun
    # phiabandon

    # line 9
    pst.control_data.ires = 0
    pst.control_data.jcosave = 'jcosave'
    pst.control_data.verboserec = 'verboserec'  # todo condsider re-setting when up and running
    pst.control_data.jcosaveitn = 'jcosaveitn'
    pst.control_data.reisaveitn = 'reisaveitn'
    pst.control_data.parsaveitn = 'parsaveitn'

    # do not set
    # icov
    # icor
    # ieig
    # parsaverun


def set_parameter_data_groups(pst):
    assert isinstance(pst, pyemu.Pst)

    # set tranformation
    # sy, hill, race = none; kh, riv = log
    pst.parameter_data.loc[:, 'partrans'] = 'none'
    pst.parameter_data.loc[pst.parameter_data.index.str.contains('kh'), 'partrans'] = 'log'
    pst.parameter_data.loc[pst.parameter_data.index.str.contains('riv'), 'partrans'] = 'log'

    param_data = _get_param_data().set_index('name')
    # set inital values, lower, upper bounds
    all_params = pst.parameter_data.index
    pst.parameter_data.loc[all_params, 'parval1'] = param_data.loc[all_params, 'start']
    pst.parameter_data.loc[all_params, 'parlbnd'] = param_data.loc[all_params, 'low']
    pst.parameter_data.loc[all_params, 'parubnd'] = param_data.loc[all_params, 'up']
    pst.parameter_data.loc[all_params, 'pargp'] = all_params.str.split('_').str.get(0)
    # Not using scale and offset
    # 'dercom' # not using as only 1 model command (so far)
    # default is factor, just changing the multipliers to absolute.

    # parameter group data
    parameter_groups = pd.DataFrame(index=pd.unique(pst.parameter_data.loc[all_params, 'pargp']))
    parameter_groups.loc[:, 'pargpnme'] = parameter_groups.index.copy()
    parameter_groups.loc[:, 'inctyp'] = 'relative'
    parameter_groups.loc[:, 'derinc'] = 0.01  # the increments for calculating derivatives
    parameter_groups.loc[:, 'derinclb'] = 0.0  # parameter increment lower bound, # todo this may need changing
    parameter_groups.loc[:, 'forcen'] = 'switch'  # start with forward derivative and switch to 3 point derivatives
    parameter_groups.loc[:, 'derincmul'] = 2.0  # double parameter increments when moving to 3 point derivatives
    parameter_groups.loc[:, 'dermthd'] = 'parabolic'  # parabolic method for 3 point derivative fits
    parameter_groups.loc[:, 'splitthresh'] = 0  # dont use , fyi doerty recommended 1e-4
    parameter_groups.loc[:, 'splitreldiff'] = 0.5  # use doerty recommended
    parameter_groups.loc[:, 'splitaction'] = 'smaller'  # use doerty recommended
    pst.parameter_groups = parameter_groups


def set_obs_data(pst):
    assert isinstance(pst, pyemu.Pst)
    base_obs = _get_base_obs().set_index('name')
    all_obs = pst.observation_data.index
    pst.observation_data.loc[:, 'obgnme'] = base_obs.loc[all_obs, 'group'].str.split('_').str.get(0)
    pst.observation_data.loc[:, 'obsval'] = base_obs.loc[all_obs, 'measured']

    # keynote group weighting happens here
    pst.proportional_weights()  # make weights proportional to obs (e.g. expected * weight = 1)

    # double impact of single_3 relative to single_1
    pst.observation_data.loc[base_obs.loc[all_obs, 'group'] == 'single_3', 'weight'] *= 2

    # normalise weights by group totals  (total weight sums to 1) for each group
    weight_totals = pst.observation_data.groupby('obgnme').sum().loc[:, 'weight'].to_dict()
    for g in pst.nnz_obs_groups:
        pst.observation_data.loc[pst.observation_data.obgnme == g, 'weight'] *= 1 / weight_totals[g]

    # increase weight of specific groups
    group_wts = {
        'regular': 10,
        'riv': 8,
        'piezo': 5,
        'single': 1,
    }

    for g in pst.nnz_obs_groups:
        pst.observation_data.loc[pst.observation_data.obgnme == g, 'weight'] *= group_wts[g]

    test = pst.observation_data.groupby('obgnme').sum().loc[:, 'weight']
    assert np.isclose(test, np.array([group_wts[e] for e in test.index])).all()


def hack_for_absparmax(file):
    with open(file, 'r') as f:
        lines = f.readlines()
    lines[6] = lines[6].strip('\n') + '  absparmax(1)=0.1\n'  # keynote ABSPARMAX set here
    with open(file, 'w') as f:
        f.writelines(lines)
    pass


def raw_pest(name='opt', pst_dir=Path.home().joinpath('Downloads/raw_pst_trial'), trial=False):
    """

    :param name: name for the pest object  e.g. {name}.pst
    :param pst_dir: directory to save all pest related files (including forward_run.py)
    :param trial: bool if True then set nmaxopt to 0 (just trial of running the model)
    :return:
    """
    # todo manage env and others
    # see https://github.com/pypest/pyemu/blob/develop/examples/modflow_to_pest_like_a_boss.ipynb

    pst_dir.mkdir(exist_ok=True)
    pst_path = pst_dir.joinpath('opt.pst')

    # make parameter files
    input_files, tpl_files = make_template_and_infiles(pst_dir)

    ins_files, output_files = make_ins_and_output_files(pst_dir)

    pst = pyemu.Pst.from_io_files(tpl_files, input_files, ins_files, output_files)

    set_control_data(pst, trial)

    # do not use senestivity reuse

    # singular value decomposition
    pst.svd_data.svdmode = 1
    pst.svd_datamaxsing = 10000000  # set super high so that the eigen threshold determines cutoff
    pst.svd_dataeigthresh = 5e-7  # threshold for eigenvector cutoff, increase (up to 1e-4 max) for
    # additional numerical noise.
    pst.svd_data.eigwrite = 1  # set to 0 to only see eigen singlue values and not eigen vectors

    # No LSRQ, use SVD instead
    #  NO automatic user intervention

    # No svd assist

    # add parameter details
    set_parameter_data_groups(pst)

    # add observation details
    set_obs_data(pst)

    # No prior information, just use svd

    # No regularisation, just use svd

    # model commands
    # todo modify, need to use the right python env
    shutil.copyfile(base_pst_data.joinpath("forward_run.py"),
                    pst_dir.joinpath("forward_run.py"))
    # todo can I set a second command line for just the new parameter sections (e.g. to plot, but not plot derivetives
    # todo dbl check this behaves as I expect, e.g. separate file for each run.
    pst.model_command = ["conda run -n hawea python forward_run.py"]  # todo args ect.

    # write pest file.
    pst.write(pst_dir.joinpath(f'{name}.pst'))
    hack_for_absparmax(pst_dir.joinpath(f'{name}.pst'))

    # todo run pestcheck and others

    # todo parallell pest???
    # todo trial run


def determine_max_str_size():
    tempdir = Path.home().joinpath('temp_for_pest')
    tempdir.mkdir(exist_ok=True)
    [input_file], [tpl_file] = make_template_and_infiles(tempdir)
    [ins_file], [output_file] = make_ins_and_output_files(tempdir)
    line_len = []
    for file in [input_file, tpl_file, ins_file, output_file]:
        with open(file, 'r') as f:
            line_len.extend([len(e) for e in f.readlines()])
    print('line lengths')
    print(pd.Series(line_len).describe())
    shutil.rmtree(tempdir)


if __name__ == '__main__':
    determine_max_str_size()
    # raw_pest()
    pass
