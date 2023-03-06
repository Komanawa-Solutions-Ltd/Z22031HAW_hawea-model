"""
created matt_dumont 
on: 1/03/23
"""
# todo plot the locs in the allocation system.
from Scenarios.run_flow_scenario import run_scenario
from Scenarios.boundary_conditions import get_scen_ghb_data, get_scen_well_data, get_scen_str_data, get_scen_rch, \
    get_grid_pump_scen_well_data
from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from Scenarios.scen_period import scen_tdis
from project_base import unbacked_dir, proj_root
import inspect

base_run_dir = unbacked_dir.joinpath('allocation_scenarios')
base_run_dir.mkdir(exist_ok=True)
base_outdir = proj_root.joinpath('Scenarios/allocation_scenarios')
base_outdir.mkdir(exist_ok=True)


def print_myself(name):
    print(f'{inspect.stack()[1][3]}: {name}')


def get_allocation_zone(zone):  # todo make these zones!! use both scotts and my zones (maybe small zones as well)
    raise NotImplementedError

def plot_pumping_in_zones():
    # todo for each zone plot current, full allo, and max allo across normal year.
    raise NotImplementedError


def run_grid_allocation_scenario(zone, total_increase):  # todo
    model_name = f'{zone}_{int(total_increase):06d}'  # todo max value???,
    # todo what are increased pumping values to use, should I make this more standartised (look at pumping in the zone)
    model_ws = base_run_dir.joinpath(model_name)
    print_myself(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    idx_array = get_allocation_zone(zone)
    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    wel_data = get_grid_pump_scen_well_data(idx_array=idx_array,
                                            total_increase=total_increase,
                                            tdis=scen_tdis, hill_param=hill_param, race_param=race_param, )
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
                 plot_data=plot_data, save_hds=save_hds,
                 )


def full_allocation():
    model_name = 'full_allocation'
    print_myself(model_name)
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    wel_data = get_scen_well_data('extended_full_allo', scen_tdis, hill_param, race_param, False)
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
                 plot_data=plot_data, save_hds=save_hds,
                 )


def max_allocation():
    model_name = 'max_allocation'
    print_myself(model_name)
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    wel_data = get_scen_well_data('extended_max_allo', scen_tdis, hill_param, race_param, False)
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
                 plot_data=plot_data, save_hds=save_hds,
                 )


plot_data = False
save_hds = False
process_results = True
run_modflow = True
