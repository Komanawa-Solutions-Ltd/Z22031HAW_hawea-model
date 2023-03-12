"""
created matt_dumont 
on: 13/03/23
"""
import pandas as pd
from project_base import proj_root
from Scenarios.allocation_zones import get_allo_zones
from model_build.supporting_data_analysis import get_hillside_catchment_locs, get_hillside_flows, get_rch
from Scenarios.supporting_data_analysis.scenario_recharge import get_corrected_scenario_era5_rch
from model_build.project_model_tools import smt


def get_allo_zone_rch_hillside(recalc=False):
    allo_zone, zone_mapper = get_allo_zones('all')
    outdir = proj_root.joinpath('Scenarios/allocation_results', 'allo_zone_rch')
    outdir.mkdir(exist_ok=True)
    savepaths = [outdir.joinpath(f'allo_zone_rch_hillslope_{z}.csv') for z in zone_mapper.values()]
    save_paths_exist = [e.exists() for e in savepaths]
    if all(save_paths_exist) and not recalc:
        out = {z: pd.read_csv(processed_scen_dir.joinpath(f'allo_zone_rch_hillslope_{z}.csv')) for z in
               zone_mapper.values()}
        return out
    percentiles = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, ]
    start = '1981-01-01'
    end = '2020-12-31'

    hillside_locs = get_hillside_catchment_locs()
    hillside_flow = get_hillside_flows(start, end, include_hill_str=True, frequency='A', func='sum')
    scen_dates, scen_rch = get_corrected_scenario_era5_rch(start, end, frequency='Y', fun='sum')
    opt_dates, opt_rch = get_rch('2016-01-01', end, frequency='Y', fun='sum')
    opt_rch *= smt.grid_space**2 / 1000
    scen_rch *= smt.grid_space**2 / 1000
    out = {}
    for id_num, zone in zone_mapper.items():
        outdata = pd.DataFrame(index=pd.Series([1]).describe(percentiles=percentiles).index)
        # scen period
        temp_scen_rch = pd.Series(index=scen_dates, data=scen_rch[:, allo_zone == id_num].sum(axis=1))
        outdata.loc[:, f'scen_rch_full'] = temp_scen_rch.describe(percentiles)

        temp_locs = smt.io.select_df_from_idx_array(hillside_locs, allo_zone == id_num, d2_only=True)
        temp_flows = hillside_flow.loc[:, temp_locs.index].sum(axis=1)
        outdata.loc[:, f'hill_full'] = temp_flows.describe(percentiles)

        # opt_period
        outdata.loc[:, f'scen_rch_opt'] = temp_scen_rch.loc[temp_scen_rch.index.year >= 2016].describe(
            percentiles)
        outdata.loc[:, f'hill_opt'] = temp_flows.loc[temp_flows.index.year >= 2016].describe(percentiles)
        outdata.loc[:, f'opt_rch_opt'] = pd.Series(opt_rch[:, allo_zone == id_num].sum(axis=1)).describe(percentiles)
        pass
        out[zone] = outdata
        outdata.to_csv(outdir.joinpath(f'allo_zone_rch_hillslope_{zone}.csv'))

    return out


if __name__ == '__main__':
    get_allo_zone_rch_hillside(True)
