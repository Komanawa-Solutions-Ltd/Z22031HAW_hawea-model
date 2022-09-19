"""
created matt_dumont 
on: 31/08/22
"""
from model_build.project_model_tools import smt, simplify_hawea_dem, simplify_upper_clutha_dem, no_flow, elv_calc, \
    get_lake_array
from model_build.supporting_data_analysis.river_data import get_river_stage_data, get_river_loc_data
from model_build.supporting_data_analysis.recharge_model import get_historical_rch_model_results, get_soil_classes, \
    get_era5_land
from model_build.supporting_data_analysis.lake_data import get_lake_hawea_loc
from model_build.supporting_data_analysis.irrigation_race_losses import get_race_locs
from model_build.supporting_data_analysis.hillside_inflows import get_hillside_catchment_locs, get_catchment_areas, \
    get_luggate_catchment_area, get_hillside_flows
from model_build.supporting_data_analysis.get_pumping_data import get_historical_pumping_data
from model_build.supporting_data_analysis.map_flowmeter_to_wells import get_well_flowmeter_mapper
from model_build.supporting_data_analysis.all_wells import get_all_wells
from model_build.zones import get_param_zones, get_model_zones

if __name__ == '__main__':
    # recalculate all saved data in model_build
    t = input('are you sure you want to recalculate everything? y/n')
    if t.upper() != 'Y':
        raise ValueError('stopped to avoid recalc')
    run_dem_simps = False  # needs lots of memory
    if run_dem_simps:
        t = input('are you sure you want to recalculate DEM DATA?  This takes atleast 32 GB ram y/n')
        if t.upper() != 'Y':
            raise ValueError('stopped to avoid recalc of DEM data')
        simplify_upper_clutha_dem(True)
        simplify_hawea_dem(True)

    no_flow()
    elv_calc()
    smt.recalc_all_pickles()

    get_param_zones(recalc=True)
    get_lake_array(recalc=True)
    get_model_zones(recalc=True)

    get_river_loc_data(True)
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
    get_era5_land(correct_pet=True, recalc=True)
    for k in [True, False]:
        get_historical_rch_model_results(data_source='historical', limited_irrigation=k, recalc=True)
        for startyear in range(1949, 2020, 10):
            get_historical_rch_model_results(data_source='era5', limited_irrigation=k,
                                             from_year=startyear, to_year=startyear + 10, recalc=True)
