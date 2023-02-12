"""
created matt_dumont 
on: 13/02/23
"""
import time
import pandas as pd
from model_build.modflow_model import build_model
from model_build.project_model_tools import smt
from model_parameterisation.static_params import vka
from model_parameterisation.pilot_points import interpolate_kh_pilot_points, interpolate_sy_pilot_points, set_ss_terms
from Scenarios.scenario_outputs import extract_input_data, generate_scenario_outputs, key_input_data_file_name
from pathlib import Path


# todo manage both outputs and inputs.


def build_run_model(model_name, model_ws, tdis, sy_param, kh_param, rch_data, ghb_spd, str_spd, well_spd, outdir):
    """
    run the scenario model
    :param model_name: model name.
    :param model_ws: directory to run the model in
    :param tdis: time dis object
    :param sy_param: sy parameters
    :param kh_param: kh parameters
    :param rch_data: recharge stress period data
    :param ghb_spd: ghb stress period data (lake)
    :param str_spd: stream stress period data
    :param well_spd: well stress period data
    :param outdir: directory to save outputs
    :return: 
    """
    exe_name = 'mfnwt'
    run_model = True
    t = time.time()
    
    # save input data (here yes)
    key_input_data = extract_input_data(ghb_data=ghb_spd, rch_data=rch_data, well_data=well_spd, tdis=tdis)
    key_input_data.to_csv(Path(model_ws).joinpath(key_input_data_file_name))

    oc_spd = {(0, 0): ['save head', 'save budget']}
    oc_spd.update({(p, 4): ['save head', 'save budget'] for p in
                   tdis.pers[1:]})  # keynote in future could make the oc data to save every step then mean of all
    # keynote other steps if I end up with them
    sy = interpolate_sy_pilot_points(sy_param)
    ss = set_ss_terms(sy_param)
    out = build_model(smt=smt,
                      tdis=tdis,
                      oc_spd=oc_spd,
                      exe_name=exe_name,
                      model_name=model_name,
                      model_ws=model_ws,
                      hk=interpolate_kh_pilot_points(kh_param),
                      vka=vka,
                      layer_avg=0,
                      ss=ss,
                      sy=sy,
                      strt=smt.get_tops(),
                      chani=1,
                      rch=rch_data,
                      ghb_spd=ghb_spd,
                      str_spd=str_spd,
                      well_spd=well_spd,
                      options='COMPLEX',
                      nwt_kwargs={'maxiterout': 1000, 'maxitinner': 100},
                      hani=None,
                      mfv='mfnwt',
                      run_model=run_model,
                      verbose=False,
                      t=t,
                      noprint=True)
    print(out)
    
    generate_scenario_outputs(model_ws, outdir=outdir)

    # todo process model data
    return out
