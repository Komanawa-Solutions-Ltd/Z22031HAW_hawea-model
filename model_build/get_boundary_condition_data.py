"""
created matt_dumont 
on: 1/08/22
"""
import pickle
import time

from model_build.supporting_data_analysis import get_rch, get_hillside_catchment_locs, get_hillside_flows, \
    get_pumping_locs, get_historical_pumping_data, get_race_locs, get_race_well_losses, get_river_stage_data, \
    get_river_loc_data, get_lake_hawea_loc, get_lake_heads
from model_parameterisation.pilot_points import interpolate_rch_pilot_points
from model_parameterisation.static_params import lake_conduct
import flopy
from project_base import processed_model_build_data_dir


def get_well_data(tdis, hill_param, race_param, return_unique_spd=False, recalc=False):
    """

    :param tdis: time discritsation object
    :param hill_param: hill slope multipler
    :param race_param: race multiplier
    :param return_unique_spd: bool If False return data to go into model, if True then return dictionary of
                              different data.
    :return:
    """
    save_path = processed_model_build_data_dir.joinpath(f'well_stress_period_data-{tdis.name}.p')
    if save_path.exists() and not recalc:
        (race_spd, hill_spd, pumping_spd) = pickle.load(open(save_path, 'rb'))
    else:
        # race data
        race_locs = get_race_locs()
        race_flow = get_race_well_losses(*tdis.date_limits)

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
        # add parameter
        for k, v in hill_param.items():
            use_keys = hillside_locs.loc[hillside_locs.param == k].index.unique()
            hillside_flow.loc[:, use_keys] *= v
            assert set(hill_param.keys()) == set(hillside_locs.param)
        hill_spd = tdis.map_data_locations(hillside_locs, {'flux': hillside_flow},
                                           flopy.modflow.ModflowWel.get_default_dtype(),
                                           group_cells=False,
                                           grouper='sum',
                                           manage_datatypes=False,
                                           loc_duplicate_action='apportion'
                                           )

        # pumping data
        pumping_locs = get_pumping_locs()
        pumping_flow = get_historical_pumping_data(*tdis.date_limits)
        pumping_flow *= -1
        pumping_flow.fillna(0, inplace=True)
        pumping_flow = pumping_flow.loc[:, pumping_locs.index]
        pumping_spd = tdis.map_data_locations(pumping_locs, {'flux': pumping_flow},
                                              flopy.modflow.ModflowWel.get_default_dtype(),
                                              group_cells=True,
                                              grouper='sum',
                                              manage_datatypes=True
                                              )
        pickle.dump((race_spd, hill_spd, pumping_spd), open(save_path, 'wb'))

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


def get_rch_data(tdis, rch_param, recalc=False):
    save_path = processed_model_build_data_dir.joinpath(f'rch_stress_period_data-{tdis.name}.p')
    if save_path.exists() and not recalc:
        out = pickle.load(open(save_path, 'rb'))
    else:
        rch_dates, rch_raw = get_rch(*tdis.date_limits, frequency='d')  # tdis manges this
        rch_raw *= 1 / 1000  # convert from mm/day to m/day
        out = tdis.map_array_to_spd(rch_dates, rch_raw)
        pickle.dump(out, open(save_path, 'wb'))

    # add rch mult
    rch_mult = interpolate_rch_pilot_points(rch_param)
    out = {k: v * rch_mult for k, v in out.items()}
    return out


def get_ghb_data(tdis, recalc=False):
    save_path = processed_model_build_data_dir.joinpath(f'ghb_stress_period_data-{tdis.name}.p')
    if save_path.exists() and not recalc:
        out = pickle.load(open(save_path, 'rb'))
        return out
    lake_locs = get_lake_hawea_loc()
    lake_locs.loc[:, 'cond'] = lake_conduct
    lake_hds = get_lake_heads(*tdis.date_limits)

    # import lake levels
    flopy.modflow.ModflowGhb.get_default_dtype()
    # transform into GHB data
    out = tdis.map_data_locations(lake_locs, {'bhead': lake_hds},
                                  flopy.modflow.ModflowGhb.get_default_dtype(), apply_to_all=True)

    pickle.dump(out, open(save_path, 'wb'))
    return out


def get_riv_data(tdis, riv_params):
    riv_locs = get_river_loc_data()
    # add conductance value
    riv_locs.loc[:, 'cond'] = riv_locs.param.replace(riv_params)

    riv_stage = get_river_stage_data(*tdis.date_limits)

    out = tdis.map_data_locations(riv_locs,
                                  {'stage': riv_stage},
                                  flopy.modflow.ModflowRiv.get_default_dtype(),
                                  )
    return out


if __name__ == '__main__':
    from optimisation.optimisation_period import tdis
    from model_parameterisation.inital_parametersiation import get_initial_riv_conductance, get_hillslope_multiplier

    b = get_well_data(tdis, hill_param=get_hillslope_multiplier(True)
                      , race_param={'all': 1}, recalc=True)
    get_riv_data(tdis, get_initial_riv_conductance(return_just_start=True))
    get_ghb_data(tdis)
