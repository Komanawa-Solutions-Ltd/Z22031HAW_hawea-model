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
from model_tools.time_discretization import TimeDis


def run_scenario(model_name, model_ws, tdis, sy_param, kh_param, rch_data, ghb_spd, str_spd, well_spd, outdir,
                 build_run_model=True, process_results=True, stress_periods=None, tickper=100, save_hds=True,
                 plot_data=True, make_ftl=False, nwt_kwargs=None, ):
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
    :param build_run_model: bool do it or not
    :param process_results: bool do it or not
    :param stress_periods: None or a list of stress periods to run (in order)
    :param tickper: ticks every x weeks on plots
    :param save_hds: bool if true save compressed (and split) hds files.
    :return: 
    """
    if nwt_kwargs is None:
        nwt_kwargs = {'maxiterout': 1000, 'maxitinner': 100}

    exe_name = 'mfnwt'
    t = time.time()
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    model_ws = Path(model_ws)
    model_ws.mkdir(exist_ok=True)
    assert isinstance(tdis, TimeDis)

    if stress_periods is not None:  # run a subset of the stress periods
        use_tdis = TimeDis(
            name='scenario_period',
            nper=len(stress_periods),
            tsmult=1.2,
            steady=[tdis.steady[e] for e in stress_periods],
            dates=[tdis.per_dates[e] for e in stress_periods],
            nstp=[tdis.nstp[e] for e in stress_periods],
            tunit='day',
            check_dates_in_order=False
        )
        well_spd = {i: well_spd[k] for i, k in enumerate(stress_periods)}
        ghb_spd = {i: ghb_spd[k] for i, k in enumerate(stress_periods)}
        rch_data = {i: rch_data[k] for i, k in enumerate(stress_periods)}
    else:
        use_tdis = tdis

    # save input data (here yes)
    key_input_data = extract_input_data(ghb_data=ghb_spd, rch_data=rch_data, well_data=well_spd, tdis=use_tdis)
    key_input_data.to_csv(Path(model_ws).joinpath(key_input_data_file_name))

    oc_spd = {(0, 0): ['save head', 'save budget']}
    oc_spd.update({(p, 4): ['save head', 'save budget'] for p in
                   use_tdis.pers[1:]})  # keynote in future could make the oc data to save every step then mean of all
    # keynote other steps if I end up with them
    sy = interpolate_sy_pilot_points(sy_param)
    ss = set_ss_terms(sy_param)
    if build_run_model:
        out = build_model(smt=smt,
                          tdis=use_tdis,
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
                          nwt_kwargs=nwt_kwargs,
                          hani=None,
                          mfv='mfnwt',
                          run_model=True,
                          verbose=True,
                          t=t,
                          noprint=True,
                          make_ftl=make_ftl)
        print(out)
    if process_results:
        generate_scenario_outputs(model_ws=model_ws, model_name=model_name, outdir=outdir, tdis=use_tdis,
                                  tickper=tickper, save_hds=save_hds, plot_data=plot_data)
