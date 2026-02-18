"""
created matt_dumont 
on: 13/03/23
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from komanawa.hawea.hawea_base import proj_root
from komanawa.hawea.Scenarios.allocation_zones import get_allo_zones
from komanawa.hawea.model_build.supporting_data_analysis import get_hillside_catchment_locs, get_hillside_flows, get_rch
from komanawa.hawea.Scenarios.supporting_data_analysis.scenario_recharge import get_corrected_scenario_era5_rch
from komanawa.hawea.model_build.project_model_tools import smt


def get_allo_zone_rch_hillside(recalc=False):
    allo_zone, zone_mapper = get_allo_zones('all')
    outdir = proj_root.joinpath('Scenarios/allocation_results', 'allo_zone_rch')
    outdir.mkdir(exist_ok=True)
    savepaths = [outdir.joinpath(f'allo_zone_rch_hillslope_{z}.csv') for z in zone_mapper.values()]
    save_paths_exist = [e.exists() for e in savepaths]
    if all(save_paths_exist) and not recalc:
        out = {z: pd.read_csv(outdir.joinpath(f'allo_zone_rch_hillslope_{z}.csv'), index_col=0) for z in
               zone_mapper.values()}
        return out
    start = '1981-01-01'
    end = '2020-12-31'

    hillside_locs = get_hillside_catchment_locs()
    hillside_flow = get_hillside_flows(start, end, include_hill_str=True, frequency='A', func='mean') * 365
    scen_dates, scen_rch = get_corrected_scenario_era5_rch(start, end, frequency='Y', fun='mean')
    scen_rch *= 365
    opt_dates, opt_rch = get_rch('2016-01-01', end, frequency='Y', fun='mean')
    opt_rch *= 365
    opt_rch *= smt.grid_space ** 2 / 1000
    scen_rch *= smt.grid_space ** 2 / 1000
    out = {}
    for id_num, zone in zone_mapper.items():
        outdata = pd.DataFrame(index=range(1981, 2021))
        # scen period
        temp_scen_rch = pd.Series(index=scen_dates.year, data=np.nansum(scen_rch[:, allo_zone == id_num], axis=1))
        outdata.loc[:, f'scen_rch'] = temp_scen_rch

        temp_locs = smt.io.select_df_from_idx_array(hillside_locs, allo_zone == id_num, d2_only=True)
        temp_flows = hillside_flow.loc[:, temp_locs.index].sum(axis=1)
        temp_flows.index = temp_flows.index.year
        outdata.loc[:, f'hill'] = temp_flows

        # opt_period
        outdata.loc[:, f'opt_rch'] = pd.Series(np.nansum(opt_rch[:, allo_zone == id_num], axis=1),
                                               index=pd.Series(opt_dates).dt.year)
        out[zone] = outdata
        outdata.to_csv(outdir.joinpath(f'allo_zone_rch_hillslope_{zone}.csv'))

    return out


if __name__ == '__main__':
    all_rch = get_allo_zone_rch_hillside(False)
    for k, v in all_rch.items():
        fig, ax = plt.subplots(figsize=(10, 8))
        colors = smt.plot.get_colors(v.keys())
        for k0, c in zip(v.keys(), colors):
            ax.plot(v.index, v[k0], color=c, label=k0)
        ax.set_title(k)
        ax.set_yscale('log')
        ax.legend()
    plt.show()
