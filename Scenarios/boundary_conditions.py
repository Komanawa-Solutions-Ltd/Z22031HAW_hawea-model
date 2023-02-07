"""
created matt_dumont 
on: 24/11/22
"""
import pandas as pd

from project_base import processed_scen_dir, base_scen_dir
import flopy
import pickle
from model_parameterisation.pilot_points import get_spatial_temporal_rch_mult
from model_build.utils import select_resample, fill_weekly_mean
from Scenarios.supporting_data_analysis.scenario_recharge import get_weekly_plus_scenario_era5_rch
from model_build.supporting_data_analysis import get_race_locs, get_hillside_catchment_locs, get_hillside_flows, \
    get_race_well_losses, get_lake_hawea_loc, get_lake_heads, get_river_loc_data, get_river_stage_data, \
    get_river_flow_data
from model_parameterisation.static_params import lake_conduct


def _make_long_weekly_mean(data, start, stop, freq='D'):
    out_data = pd.DataFrame(index=pd.date_range(start, stop, freq='D'))
    out_data = pd.merge(out_data, data, 'left', right_index=True, left_index=True)
    out_data = fill_weekly_mean(out_data)
    out_data = select_resample(out_data, start, stop, freq)
    return out_data


def get_scen_rch(tdis, rch_param, recalc=False):
    save_path = processed_scen_dir.joinpath(f'rch_stress_period_data-{tdis.name}.p')
    if save_path.exists() and not recalc:
        out = pickle.load(open(save_path, 'rb'))
    else:
        rch_dates, rch_raw = get_weekly_plus_scenario_era5_rch(*tdis.date_limits,
                                                               frequency='d')  # todo daily might cause problems, look into this!!
        rch_raw *= 1 / 1000  # convert from mm/day to m/day
        out = tdis.map_array_to_spd(rch_dates, rch_raw)
        pickle.dump(out, open(save_path, 'wb'))

    # add rch mult
    rch_mult = get_spatial_temporal_rch_mult(rch_param, tdis)
    assert rch_mult.shape[0] == len(out.keys())
    out = {k: v * rmult for (k, v), rmult in zip(out.items(), rch_mult)}
    return out


def get_scen_pumping_data(pump_name, tdis, recalc):  # todo
    raise NotImplementedError  # todo


def get_scen_race_losses(start_date, end_date, frequency='D', recalc=False):
    hist_race_flow = get_race_well_losses(None, None)
    raise NotImplementedError  # todo I need to do something to generate race losses per year, not very regular


def get_scen_hill_race_data(tdis, recalc):
    save_path = processed_scen_dir.joinpath(f'well_stress_period_data-{tdis.name}.p')
    if save_path.exists() and not recalc:
        (race_spd, hill_spd) = pickle.load(open(save_path, 'rb'))
    else:
        # race data
        race_locs = get_race_locs()
        race_flow = get_scen_race_losses(*tdis.date_limits)

        race_spd = tdis.map_data_locations(race_locs, {'flux': race_flow},
                                           flopy.modflow.ModflowWel.get_default_dtype(),
                                           apply_to_all=True,
                                           group_cells=False,
                                           grouper='sum',
                                           manage_datatypes=False
                                           )

        # hillside data
        hillside_locs = get_hillside_catchment_locs()
        hillside_flow = get_hillside_flows(*tdis.date_limits)

        # remove flows from south of lugate tarras rd.
        hillside_flow = hillside_flow.loc[:, hillside_locs.index.unique()]
        hill_spd = tdis.map_data_locations(hillside_locs, {'flux': hillside_flow},
                                           flopy.modflow.ModflowWel.get_default_dtype(),
                                           group_cells=False,
                                           grouper='sum',
                                           manage_datatypes=False,
                                           loc_duplicate_action='apportion'
                                           )
        pickle.dump((race_spd, hill_spd), open(save_path, 'wb'))
    return race_spd, hill_spd


def get_scen_well_data(pump_name, tdis, hill_param, race_param, return_unique_spd=False, recalc=False):
    """

    :param tdis: time discritsation object
    :param hill_param: hill slope multipler
    :param race_param: race multiplier
    :param return_unique_spd: bool If False return data to go into model, if True then return dictionary of
                              different data.
    :return:
    """

    race_spd, hill_spd = get_scen_hill_race_data(tdis, recalc)
    pumping_spd = get_scen_pumping_data(pump_name, tdis, recalc)
    # manage parameters
    for p, d in race_spd.items():
        d.loc[:, 'flux'] *= race_param['all']

    for p, d in hill_spd.items():
        for k, v in hill_param.items():
            idx = d.param == k
            d.loc[idx, 'flux'] *= v

    # convert to numpy arrays (well is done before pickle)
    race_spd = tdis.manage_dtypes(race_spd, flopy.modflow.ModflowWel.get_default_dtype(),
                                  group_cells=True,
                                  grouper='sum', )
    hill_spd = tdis.manage_dtypes(hill_spd, flopy.modflow.ModflowWel.get_default_dtype(),
                                  group_cells=True,
                                  grouper='sum', )

    if return_unique_spd:
        out = {'race': race_spd, 'hill': hill_spd, 'pump': pumping_spd}
        return out
    else:
        out_spd = tdis.merge_spd((race_spd, hill_spd, pumping_spd),
                                 flopy.modflow.ModflowWel.get_default_dtype(),
                                 group_cells=True,
                                 grouper='sum')
        return out_spd


def get_scen_ghb_data(tdis, recalc=False):
    save_path = processed_scen_dir.joinpath(f'ghb_stress_period_data-{tdis.name}.p')
    if save_path.exists() and not recalc:
        out = pickle.load(open(save_path, 'rb'))
        return out
    lake_locs = get_lake_hawea_loc()
    lake_locs.loc[:, 'cond'] = lake_conduct
    lake_hds = _make_long_weekly_mean(get_lake_heads(None, None), *tdis.date_limits)

    # import lake levels
    flopy.modflow.ModflowGhb.get_default_dtype()
    # transform into GHB data
    out = tdis.map_data_locations(lake_locs, {'bhead': lake_hds},
                                  flopy.modflow.ModflowGhb.get_default_dtype(), apply_to_all=True)

    pickle.dump(out, open(save_path, 'wb'))
    return out


def get_str_stage_flow(start_date, end_date, frequency='D'):  # todo check
    riv_stage = _make_long_weekly_mean(get_river_stage_data(None, None), start_date, end_date, frequency)
    riv_flow = _make_long_weekly_mean(get_river_flow_data(None, None), start_date, end_date, frequency)
    return riv_flow, riv_stage


def get_scen_str_data(tdis, riv_params):
    riv_locs = get_river_loc_data()
    # add conductance value
    riv_locs.loc[:, 'cond'] = riv_locs.param.replace(riv_params)
    riv_locs = riv_locs.rename(columns={
        'seg': 'segment',
        'rbot': 'sbot',
        'rtop': 'stop',
    })
    riv_locs.loc[:, ['width', 'slope', 'rough']] = 1.  # Keynote dummy values as I am not calculating stage
    riv_flow, riv_stage = get_str_stage_flow(*tdis.date_limits)
    use_riv_flow = riv_stage.copy(deep=True) * 0
    for k in riv_locs.rname.unique():
        sreach = int(riv_locs.loc[riv_locs.rname == k, 'dist'].min())
        use_riv_flow.loc[:, f"{k}_{sreach:05d}"] = riv_flow.loc[:, k]

    spd_dtype, seg_dtype = flopy.modflow.ModflowStr.get_default_dtype()
    out = tdis.map_data_locations(riv_locs,
                                  {'stage': riv_stage,
                                   'flow': use_riv_flow,
                                   },
                                  spd_dtype,
                                  )
    return out
