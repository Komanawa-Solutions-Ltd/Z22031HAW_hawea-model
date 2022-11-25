"""
created matt_dumont 
on: 25/11/22
"""
from pathlib import Path
import numpy as np
import shutil
from targets_and_sensitive_sites.model_output import process_model_output
from optimisation.model_utils_for_forward_run import read_param_data, build_run_model
from model_tools.run_multiprocess import run_multiprocess, make_mp_function
from model_parameterisation.inital_parametersiation import *


def _run_model_mp(kwargs):
    try:
        manual_opt(**kwargs)
        success = True
        error = 'None'
    except Exception as val:
        success = False
        error = val
    return kwargs, success, error


def manual_opt(mod_params, model_ws, name, plot=True):
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = mod_params
    build_run_model(
        model_name=name, model_ws=model_ws,
        kh_param=kh_param,
        sy_param=sy_param,
        riv_params=riv_params,
        hill_param=hill_param,
        race_param=race_param,
        rch_param=rch_param
    )
    process_model_output(model_ws=model_ws,
                         hds_file=model_ws.joinpath(f'{name}.hds'),
                         plot=plot, savelist=False, save_param=False, run_if_unconverged=True)

def run_manal_opt(mod_params):  # todo need to play with manual optimisation, start here if v11 doesn't magically work~
    kh_param = get_inital_kh(True)
    sy_param = get_inital_sy(True)
    riv_params = get_initial_riv_conductance(True)
    hill_param = get_hillslope_multiplier(True)
    race_param = get_race_multiplier(True)
    rch_param = get_initial_rch_mult(True)

    kh_param = {k: data[f'kh_{k}'] for k in get_inital_kh().keys()}
    sy_param = {k: data[f'sy_{k}'] for k in get_inital_sy().keys()}
    riv_params = {k: data[f'riv_{k}'] for k in get_initial_riv_conductance().keys()}
    hill_param = {k: data[f'hill_{k}'] for k in get_hillslope_multiplier().keys()}
    race_param = {k: data[f'race_{k}'] for k in get_race_multiplier().keys()}
    rch_param = {k: data[f'rch_{k}'] for k in get_initial_rch_mult().keys()}

