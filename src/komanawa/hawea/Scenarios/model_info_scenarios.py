"""
created matt_dumont 
on: 27/02/23
"""
import shutil

import pandas as pd

from komanawa.hawea.Scenarios.run_flow_scenario import run_scenario
from komanawa.hawea.Scenarios.boundary_conditions import get_scen_ghb_data, get_scen_well_data, get_scen_str_data, get_scen_rch
from komanawa.hawea.model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from komanawa.hawea.Scenarios.scen_period import scen_tdis
from komanawa.hawea.hawea_base import unbacked_dir, proj_root
import inspect

base_run_dir = unbacked_dir.joinpath('model_info_scenarios')
base_run_dir.mkdir(exist_ok=True)
base_outdir = proj_root.joinpath('Scenarios/model_info_scen_results')
base_outdir.mkdir(exist_ok=True)


def print_myself():
    print(inspect.stack()[1][3])


def opt_on_long_timescale():
    from komanawa.hawea.optimisation.optimisation_period import tdis as opt_tdis
    print_myself()
    model_name = 'optimised'
    from komanawa.hawea.model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_str_data

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
                 tdis=opt_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=opt_rch,
                 ghb_spd=opt_ghb_spd,
                 str_spd=opt_str_spd,
                 well_spd=opt_well_spd,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=run_modflow, process_results=True,
                 stress_periods=None, save_hds=False, plot_data=False)

    # re-format results
    temp = pd.DataFrame(index=opt_tdis.pers, data={'date': opt_tdis.per_middle_dates})
    temp = scen_tdis.add_nstp_nper_to_df(temp, 'date', action_on_duplicates='last')
    temp.loc[0, 'nper'] = 0
    mapper = temp.loc[:, 'nper'].to_dict()

    from komanawa.hawea.Scenarios.scenario_outputs import key_output_data_file_name, key_input_data_file_name, \
        key_all_well_data_file_name
    outdir = base_outdir.joinpath(model_name)

    for n in [key_output_data_file_name, key_input_data_file_name, key_all_well_data_file_name]:
        org_input_path = outdir.joinpath(f'org_{n}')
        org_input_path.unlink(True)
        shutil.copyfile(outdir.joinpath(n), org_input_path)
        use_input_path = outdir.joinpath(n)
        input_data = pd.read_csv(org_input_path, index_col=0)
        input_data.index = [mapper[e] for e in input_data.index]
        input_data.to_csv(use_input_path)


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
                 build_run_model=run_modflow, process_results=process_results)


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
                 build_run_model=run_modflow, process_results=process_results,
                 )
def no_pumping():
    print_myself()
    model_name = 'no_pumping'
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    wel_data = get_scen_well_data('no_pump', scen_tdis, hill_param, race_param, False)
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=run_modflow, process_results=process_results,
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
                 build_run_model=run_modflow, process_results=process_results, save_hds=False, plot_data=False)


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
                 build_run_model=run_modflow, process_results=process_results, save_hds=False, plot_data=False,
                 )


def static_pumping():
    print_myself()
    model_name = 'static_pumping'
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
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
                 build_run_model=run_modflow, process_results=process_results, save_hds=False, plot_data=False
                 )


def pump_only_var():
    import flopy
    print_myself()
    model_name = 'pump_only_var'
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = scen_tdis.make_spd_steady(get_scen_rch(scen_tdis, rch_param, dryland=False))
    lake = scen_tdis.make_spd_steady(get_scen_ghb_data(scen_tdis))
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=True, small_static=True)
    temp = get_scen_well_data('extended_pump', scen_tdis, hill_param, race_param, return_unique_spd=True)
    race = scen_tdis.make_spd_steady(temp['race'])
    hill = scen_tdis.make_spd_steady(temp['hill'])
    pump = temp['pump']
    wel_data = scen_tdis.merge_spd((race, hill, pump),
                                   flopy.modflow.ModflowWel.get_default_dtype(),
                                   group_cells=True,
                                   grouper='sum')
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=run_modflow, process_results=process_results,
                 save_hds=False, plot_data=False)


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
                 build_run_model=run_modflow, process_results=process_results,
                 save_hds=False, plot_data=False)


process_results = True
run_modflow = True
if __name__ == '__main__':
    rerun = False
    no_pumping()
    if rerun:
        long_naturalised()
        opt_on_long_timescale()
        long_current_state()
        lake_only_var()
        rch_only_var()
        hillslope_only_var()
        static_pumping()
        pump_only_var()
