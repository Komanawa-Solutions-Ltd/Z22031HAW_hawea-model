"""
created matt_dumont 
on: 27/09/22
"""
import time
from pathlib import Path

import numpy as np

from model_build.modflow_example import build_model
from model_build.project_model_tools import smt, get_top
from optimisation.optimisation_period import tdis
from model_parameterisation.static_params import ss, vka
from model_parameterisation.pilot_points import interpolate_kh_pilot_points, interpolate_sy_pilot_points
from model_parameterisation.inital_parametersiation import get_inital_sy, get_inital_kh, get_inital_lake_conductance, \
    get_initial_riv_conductance, get_race_multiplier, get_hillslope_multiplier
from model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_riv_data


# todo build the model including all packages

def build_initial_model(model_name, model_ws,
                        exe_name='mfnwt', run_model=False):
    t = time.time()
    build_model(smt=smt,
                tdis=tdis,
                exe_name=exe_name,
                model_name=model_name,
                model_ws=model_ws,
                hk=interpolate_kh_pilot_points(get_inital_kh(return_just_start=True)),
                vka=vka,
                layer_avg=0,
                ss=ss,
                sy=interpolate_sy_pilot_points(get_inital_sy(return_just_start=True)),
                chani=1,
                constant_heads=get_top()[np.newaxis],
                rch=get_rch_data(tdis),
                ghb_spd=get_ghb_data(tdis, lake_params=get_inital_lake_conductance(True)),
                riv_spd=get_riv_data(tdis, riv_params=get_initial_riv_conductance(True)),
                well_spd=get_well_data(tdis,
                                       hill_param=get_hillslope_multiplier(True),
                                       race_param=get_race_multiplier(True)),
                options='COMPLEX',
                nwt_kwargs={'maxiterout': 1000, 'maxitinner': 1000}, # todo just playing
                hani=None,
                mfv='mfnwt',
                run_model=run_model,
                verbose=True,
                t=t)


if __name__ == '__main__':
    # todo this is running, but it's not converging START HERE
    build_initial_model(model_name='test', model_ws=Path.home().joinpath('Downloads/test_model'),
                        run_model=True)
