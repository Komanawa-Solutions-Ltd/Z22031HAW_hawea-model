"""
created matt_dumont 
on: 1/11/22
"""

# this allows testing multiple paramters sets/structures quickly, use git branches for some of this.
from pathlib import Path


def recalc_model_build(rerun_rushton=False):
    from model_build.project_model_tools import smt, no_flow, elv_calc, \
        get_lake_array, get_starting_heads
    from model_build.supporting_data_analysis.river_data import get_river_stage_data, get_river_loc_data
    from model_build.supporting_data_analysis.recharge_model import get_historical_rch_model_results, get_soil_classes, \
        get_era5_land, get_corrected_historical_era5_rch
    from model_build.supporting_data_analysis.lake_data import get_lake_hawea_loc
    from model_build.supporting_data_analysis.irrigation_race_losses import get_race_locs
    from model_build.supporting_data_analysis.hillside_inflows import get_hillside_catchment_locs, get_catchment_areas, \
        get_luggate_catchment_area, get_hillside_flows
    from model_build.supporting_data_analysis.get_pumping_data import get_historical_pumping_data
    from model_build.supporting_data_analysis.map_flowmeter_to_wells import get_well_flowmeter_mapper
    from model_build.supporting_data_analysis.all_wells import get_all_wells
    from model_build.zones import get_param_zones, get_model_zones
    from model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_riv_data
    from optimisation.optimisation_period import tdis

    no_flow()
    elv_calc()
    smt.recalc_all_pickles()
    get_starting_heads(recalc=True)

    get_param_zones(recalc=True)
    get_lake_array(recalc=True)
    get_model_zones(recalc=True)

    get_river_loc_data(recalc=True)
    get_river_stage_data(None, None, recalc=True)
    get_all_wells(recalc=True)
    get_lake_hawea_loc(recalc=True)
    get_race_locs(recalc=True)
    get_hillside_catchment_locs(recalc=True)
    get_catchment_areas(recalc=True)
    get_luggate_catchment_area(recalc=True)
    get_hillside_flows(None, None, recalc=True)
    get_well_flowmeter_mapper(recalc=True)
    get_historical_pumping_data(None, None, recalc=True)
    get_soil_classes(recalc=True)
    get_rch_data(tdis, recalc=True)
    get_ghb_data(tdis, recalc=True)
    get_well_data(tdis, hill_param={'south_east': 1, 'main': 1, 'maungawera': 1, }, race_param={'all': 1}, recalc=True)
    if rerun_rushton:
        for k in [True, False]:
            get_era5_land(correct=True, recalc=True)
            get_historical_rch_model_results(data_source='historical', limited_irrigation=k, recalc=True)
            get_historical_rch_model_results(data_source='era5', limited_irrigation=k, recalc=True)
            get_corrected_historical_era5_rch(None, None, recalc=True, limited_irrigation=k)


def recalc_param_targets():
    from model_parameterisation.pilot_points import get_pilot_point_locations
    from targets_and_sensitive_sites.riv_gain_loss_targets import get_riv_target_locs
    from targets_and_sensitive_sites.head_targets import get_2011_piezo_survey, get_all_hds_targets
    from targets_and_sensitive_sites.senstive_sites import get_wetlands
    from targets_and_sensitive_sites.get_indicative_times import get_indicative_times_v2
    from optimisation.optimisation_period import tdis

    get_riv_target_locs(recalc=True)
    get_2011_piezo_survey(recalc=True)
    get_wetlands(recalc=True)
    get_indicative_times_v2(recalc=True)
    get_all_hds_targets(tdis, recalc=True)
    get_pilot_point_locations(recalc=True)


def build_test_model(model_ws, notes):
    from targets_and_sensitive_sites.model_output import process_model_output
    from optimisation.model_utils_for_forward_run import read_param_data, build_run_model

    recalc_param_targets()
    recalc_model_build()

    plot = True
    name = 'opt_model'
    with open(model_ws.joinpath('0_new_model_notes'), 'w') as f:
        f.write(notes)
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


# todo version here to run pest and base model
mversion = ''
test_notes = ''
test_path = Path().home().joinpath('Downloads').joinpath(mversion)
if __name__ == '__main__':
    build_test_model(model_ws=test_path, notes=test_notes)
