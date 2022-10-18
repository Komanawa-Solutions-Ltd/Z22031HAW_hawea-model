"""
created matt_dumont 
on: 11/10/22
"""
import sys
import time
from pathlib import Path

import pandas as pd

from model_build.modflow_model import build_model
from model_build.project_model_tools import smt, get_starting_heads
from optimisation.optimisation_period import tdis
from model_parameterisation.static_params import ss, vka
from model_parameterisation.pilot_points import interpolate_kh_pilot_points, interpolate_sy_pilot_points
from model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_riv_data
from targets_and_sensitive_sites.model_output import process_model_output
from model_parameterisation.inital_parametersiation import *


# todo I probably need to manage the python setup and environment to allow this!!!

def read_param_data(model_ws):
    parameter_file = model_ws.joinpath('parameters.dat')

    data = pd.read_csv(parameter_file, sep='\t', index_col=0, header=None).loc[:, 1].to_dict()

    kh_param = {k: data[f'kh_{k}'] for k in get_inital_kh().keys()}
    sy_param = {k: data[f'sy_{k}'] for k in get_inital_sy().keys()}
    riv_params = {k: data[f'riv_{k}'] for k in get_initial_riv_conductance().keys()}
    hill_param = {k: data[f'hill_{k}'] for k in get_hillslope_multiplier().keys()}
    race_param = {k: data[f'race_{k}'] for k in get_race_multiplier().keys()}

    return kh_param, sy_param, riv_params, hill_param, race_param


def build_run_model(model_name, model_ws, kh_param, sy_param, riv_params, hill_param, race_param):
    exe_name = 'mfnwt'
    run_model = True
    t = time.time()
    oc_spd = {(p, 0): ['save head', 'save budget'] for p in tdis.pers}
    # keynote other steps if I end up with them
    build_model(smt=smt,
                tdis=tdis,
                oc_spd=oc_spd,
                exe_name=exe_name,
                model_name=model_name,
                model_ws=model_ws,
                hk=interpolate_kh_pilot_points(kh_param),
                vka=vka,
                layer_avg=0,
                ss=ss,
                sy=interpolate_sy_pilot_points(sy_param),
                strt=get_starting_heads(),
                chani=1,
                rch=get_rch_data(tdis),
                ghb_spd=get_ghb_data(tdis),
                riv_spd=get_riv_data(tdis, riv_params=riv_params),
                well_spd=get_well_data(tdis,
                                       hill_param=hill_param,
                                       race_param=race_param),
                options='COMPLEX',
                nwt_kwargs={'maxiterout': 1000, 'maxitinner': 100},
                hani=None,
                mfv='mfnwt',
                run_model=run_model,
                verbose=True,
                t=t,
                noprint=True)


if __name__ == '__main__':
    # todo check but should be done
    name = sys.argv[1]
    plot = sys.argv[2] == 1
    model_ws = Path(__file__).parent # todo check!
    kh_param, sy_param, riv_params, hill_param, race_param = read_param_data(model_ws)
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
                         plot=plot)
