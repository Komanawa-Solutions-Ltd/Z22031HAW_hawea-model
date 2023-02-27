"""
created matt_dumont 
on: 27/02/23
"""
from Scenarios.run_flow_scenario import run_scenario
from Scenarios.boundary_conditions import get_scen_ghb_data, get_scen_well_data, get_scen_str_data, get_scen_rch
from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from Scenarios.scen_period import scen_tdis
from project_base import unbacked_dir, proj_root
from optimisation.model_utils_for_forward_run import read_param_data, build_run_model
import inspect

base_run_dir = unbacked_dir.joinpath('model_info_scenarios')
base_run_dir.mkdir(exist_ok=True)
base_outdir = proj_root.joinpath('Scenarios/model_info_scen_results')
base_outdir.mkdir(exist_ok=True)


def print_myself():
    print(inspect.stack()[1][3])


def optimised_model():
    # to check if I cna still run it!
    print_myself()
    model_name = 'optimised'

    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    build_run_model(model_name, model_ws, kh_param, sy_param, riv_params, hill_param, race_param, rch_param)


def mixed_optimised():
    # for depbugging purposes only
    #  could not run trying:  ulimit -s unlimited, did not fix.. cant be memory, smaller model failed
    #  checking boundary condition ijk and shape
    #  checking periods... unlikely
    #  removed nan values in rch array
    #  not bas, dis, nam, nwt, oc, upw
    #  not saving key inputdata
    from optimisation.optimisation_period import tdis as opt_tdis
    print_myself()
    model_name = 'old_str'
    from model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_str_data

    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    opt_ghb_spd = get_ghb_data(opt_tdis)
    opt_rch = get_rch_data(opt_tdis, rch_param)
    opt_str_spd = get_str_data(opt_tdis, riv_params=riv_params)
    opt_well_spd = get_well_data(opt_tdis,
                                 hill_param=hill_param,
                                 race_param=race_param)

    scen_str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False,
                                      small_static=False)  # problem with stream seg order

    # this worked scen_nat_rch = get_scen_rch(scen_tdis, rch_param, dryland=True)
    # this worked scen_lake = get_scen_ghb_data(scen_tdis)
    # this ran scen_wel_data = get_scen_well_data('no_pump', scen_tdis, hill_param, race_param, False)

    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=opt_rch,
                 ghb_spd=opt_ghb_spd,
                 str_spd=opt_str_spd,
                 well_spd=opt_well_spd,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=True, process_results=False,
                 stress_periods=[0])


def long_naturalised():
    print_myself()
    model_name = 'long_nat'
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    nat_rch = get_scen_rch(scen_tdis, rch_param, dryland=True)
    lake = get_scen_ghb_data(scen_tdis)
    wel_data = get_scen_well_data('no_pump', scen_tdis, hill_param, race_param, False)
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=nat_rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=True, process_results=True)


def long_current_state():
    print_myself()
    model_name = 'long_current'
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    wel_data = get_scen_well_data('extended_pump', scen_tdis, hill_param, race_param, False)
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=True, process_results=True,
                 )


def lake_only_var():
    print_myself()
    model_name = 'lake_only_var'
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = scen_tdis.make_spd_steady(get_scen_rch(scen_tdis, rch_param, dryland=False))
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=True, small_static=True)
    wel_data = scen_tdis.make_spd_steady(get_scen_well_data('static_pump', scen_tdis, hill_param, race_param, False))
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=True, process_results=True)


def rch_only_var():
    print_myself()
    model_name = 'rch_only_var'
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = scen_tdis.make_spd_steady(get_scen_ghb_data(scen_tdis))
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=True, small_static=True)
    wel_data = scen_tdis.make_spd_steady(get_scen_well_data('static_pump', scen_tdis, hill_param, race_param, False))
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=True, process_results=True)


def hillslope_only_var():
    print_myself()
    model_name = 'hillslope_only_var'
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = scen_tdis.make_spd_steady(get_scen_rch(scen_tdis, rch_param, dryland=False))
    lake = scen_tdis.make_spd_steady(get_scen_ghb_data(scen_tdis))
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=True, small_static=False)
    wel_data = get_scen_well_data('static_pump', scen_tdis, hill_param, race_param, False)
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=True, process_results=True)


def low_lake_scenario_1():  # todo need to make lake data
    print_myself()

    raise NotImplementedError


if __name__ == '__main__':
    long_current_state()
    long_naturalised()
    lake_only_var()
    rch_only_var()
    hillslope_only_var()
