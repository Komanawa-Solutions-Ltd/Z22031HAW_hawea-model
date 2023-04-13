"""
created matt_dumont 
on: 24/11/22
"""
import itertools

import matplotlib.pyplot as plt
import numpy as np

from project_base import processed_scen_dir
import flopy
import pickle
from model_parameterisation.pilot_points import get_spatial_temporal_rch_mult
from Scenarios.supporting_data_analysis.scenario_recharge import get_corrected_scenario_era5_rch
from model_build.supporting_data_analysis import get_race_locs, get_hillside_catchment_locs, get_hillside_flows, \
    get_race_well_losses, get_lake_hawea_loc, get_lake_heads, get_river_loc_data, get_river_stage_data, \
    get_river_flow_data
from model_parameterisation.static_params import lake_conduct
from Scenarios.supporting_data_analysis.pumping_data import accepted_pump_names, get_scen_pumping_data, \
    get_gridded_pumping
from Scenarios.supporting_data_analysis.utils import make_long_weekly_mean


def get_scen_rch(tdis, rch_param, dryland=False, recalc=False):
    extra = 'wirr'
    if dryland:
        extra = 'dryland'
    save_path = processed_scen_dir.joinpath(f'rch_stress_period_data-{tdis.name}_{extra}.npz')
    if save_path.exists() and not recalc:
        out = np.load(save_path)
        out = {int(k): v for k, v in out.items()}
    else:
        rch_dates, rch_raw = get_corrected_scenario_era5_rch(*tdis.date_limits, frequency='W', dryland=dryland)
        rch_raw *= 1 / 1000  # convert from mm/day to m/day
        out = tdis.map_array_to_spd(rch_dates, rch_raw)
        np.savez_compressed(save_path, **{str(k): v for k, v in out.items()})

    # add rch mult
    rch_mult = get_spatial_temporal_rch_mult(rch_param, tdis)
    assert rch_mult.shape[0] == len(out.keys())
    out = {k: v * rmult for (k, v), rmult in zip(out.items(), rch_mult)}
    for v in out.values():
        v[np.isnan(v)] = 0
    return out


def _get_scen_race_losses(start_date, end_date, frequency='W'):
    """
    get the scenario race losses (iso weekly mean
    :param start_date:  start date
    :param end_date:  end date
    :param frequency:  pd frequecny code
    :return:
    """
    hist_race_flow = get_race_well_losses(None, None)
    out = make_long_weekly_mean(hist_race_flow, start_date, end_date, frequency)
    return out


def _get_scen_hill_race_data(tdis, recalc):
    """
    get the raw hill inflow and race loss data (no multipliers
    :param tdis: time discritisation
    :param recalc: bool recalc from original data
    :return:
    """
    save_path_race = processed_scen_dir.joinpath(f'race_stress_period_data-{tdis.name}.p')
    save_path_hill = processed_scen_dir.joinpath(f'hill_stress_period_data-{tdis.name}.p')
    if save_path_race.exists() and save_path_hill.exists() and not recalc:
        race_spd = pickle.load(open(save_path_race, 'rb'))
        hill_spd = pickle.load(open(save_path_hill, 'rb'))
    else:
        # race data
        race_locs = get_race_locs()
        race_flow = _get_scen_race_losses(*tdis.date_limits)

        race_spd = tdis.map_data_locations(race_locs, {'flux': race_flow.flow},
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
        pickle.dump(race_spd, open(save_path_race, 'wb'))
        pickle.dump(hill_spd, open(save_path_hill, 'wb'))
    return race_spd, hill_spd


def get_scen_well_data(pump_name, tdis, hill_param, race_param, return_unique_spd=False, recalc=False):
    """
    get scenario pumping data including hillslope inflows, race data, and pumping rates
    :param pump_name:  pump names see Scenarios/supporting_data_analysis/pumping_data.py --> accepted_pump_names
    :param tdis: time discritsation object
    :param hill_param: hill slope multipler
    :param race_param: race multiplier
    :param return_unique_spd: bool If False return data to go into model, if True then return dictionary of
                              different datasets.
    :param recalc: bool recalc from base datasets
    :return:
    """
    assert pump_name in accepted_pump_names, f'unknown pump name: {pump_name}, expected on of: {accepted_pump_names}'
    race_spd, hill_spd = _get_scen_hill_race_data(tdis, recalc)
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


def get_grid_pump_scen_well_data(idx_array: np.ndarray, total_increase, tdis, hill_param, race_param,
                                 return_unique_spd=False, recalc=False):
    """
    get scenario pumping data including hillslope inflows, race data, and pumping rates
    :param idx_array: index array for the additional pumping to be applied (model_2d_grid.shape)
    :param total_increase: the total amount of abstraction to apply (spread evenly across the grid wells)
    :param tdis: time discritsation object
    :param hill_param: hill slope multipler
    :param race_param: race multiplier
    :param return_unique_spd: bool If False return data to go into model, if True then return dictionary of
                              different datasets.
    :param recalc: bool recalc from base datasets
    :return:
    """

    grid_pump = get_gridded_pumping(tdis, idx_array, total_increase)
    race_spd, hill_spd = _get_scen_hill_race_data(tdis, recalc)
    pumping_spd = get_scen_pumping_data('extended_max_allo_pc', tdis, recalc)
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
        out = {'race': race_spd, 'hill': hill_spd, 'pump': pumping_spd, 'grid': grid_pump}
        return out
    else:
        out_spd = tdis.merge_spd((race_spd, hill_spd, pumping_spd, grid_pump),
                                 flopy.modflow.ModflowWel.get_default_dtype(),
                                 group_cells=True,
                                 grouper='sum')
        return out_spd


def get_scen_ghb_data(tdis, recalc=False):
    """
    get the lake hawea GHB data,
    :param tdis: time discritsiation class
    :param recalc: bool if true recalc from the original datasets
    :return:
    """
    nfiles = 6
    save_paths = [processed_scen_dir.joinpath(f'ghb_stress_period_data-{tdis.name}-{i}.p') for i in range(nfiles)]
    if all([s.exists() for s in save_paths]) and not recalc:
        out = {}
        for s in save_paths:
            out.update(pickle.load(open(s, 'rb')))
        return out
    lake_locs = get_lake_hawea_loc()
    lake_locs.loc[:, 'cond'] = lake_conduct
    lake_hds = get_lake_heads(*tdis.date_limits)

    # import lake levels
    flopy.modflow.ModflowGhb.get_default_dtype()
    # transform into GHB data
    out = tdis.map_data_locations(lake_locs, {'bhead': lake_hds},
                                  flopy.modflow.ModflowGhb.get_default_dtype(), apply_to_all=True)
    from model_build.project_model_tools import smt
    groups = list(smt.grouper(len(out.keys()) // 6 + 1, list(out.keys()), None))
    assert len(groups) == len(save_paths)
    for g, p in zip(groups, save_paths):
        pickle.dump({k: out[k] for k in g if k is not None}, open(p, 'wb'))
    return out


def _get_str_stage_flow(start_date, end_date, frequency='W'):
    """
    get scenario stream flow and stage data, which are ISO weekly mean values.
    :param start_date: start date
    :param end_date: end date
    :param frequency: frequency (pandas frequency codes)
    :return:
    """
    riv_stage = make_long_weekly_mean(get_river_stage_data(None, None), start_date, end_date, frequency)
    org_river_flow_data = get_river_flow_data(None, None)
    riv_flow = make_long_weekly_mean(org_river_flow_data, start_date, end_date,
                                     frequency)
    # use original grandview data
    riv_flow.loc[:, 'gview'] = org_river_flow_data.loc[:, 'gview']
    riv_flow.loc[:, 'john'] = org_river_flow_data.loc[:, 'john']

    return riv_flow, riv_stage


def get_scen_str_data(tdis, riv_params, big_static=False, small_static=False, return_unique=False, recalc=False):
    """
    get stream data.  Stream flow and stage data are set from weekly averages during the inflow period
    :param tdis: time discritsiation class
    :param riv_params: optimisation riv parameters
    :param big_static: bool if true then set the big rivers (clutha/hawea) to static (e.g. steady state)
    :param small_static: bool if true then set the small rivers (grandview/john) to static (e.g. steady state)
    :return:
    """
    param_mapper = {'h1': -1, 'h2': -2, 'h3': -3, 'c1': -4, 'gview': -5, 'john': -6}
    streams = ['gview', 'john', 'hawea', 'clutha']
    pickle_paths = [processed_scen_dir.joinpath(f'stream_spd_{s}_{tdis.name}.p') for s in streams]
    spd_dtype, seg_dtype = flopy.modflow.ModflowStr.get_default_dtype()

    if all([p.exists() for p in pickle_paths]) and not recalc:
        data = {s: pickle.load(p.open('rb')) for s, p in zip(streams, pickle_paths)}
    else:
        riv_locs = get_river_loc_data()
        # add conductance value
        riv_locs.loc[:, 'cond'] = riv_locs.param.replace(param_mapper)
        riv_locs = riv_locs.rename(columns={
            'seg': 'segment',
            'rbot': 'sbot',
            'rtop': 'stop',
        })
        riv_locs.loc[:, ['width', 'slope', 'rough']] = 1.  # Keynote dummy values as I am not calculating stage
        riv_flow, riv_stage = _get_str_stage_flow(*tdis.date_limits)
        use_riv_flow = riv_stage.copy(deep=True) * 0
        for k in riv_locs.rname.unique():
            sreach = int(riv_locs.loc[riv_locs.rname == k, 'dist'].min())
            use_riv_flow.loc[:, f"{k}_{sreach:05d}"] = riv_flow.loc[:, k]

        print('mapping_clutha')
        out_clutha = tdis.map_data_locations(
            riv_locs.loc[np.in1d(riv_locs.rname, ['clutha'])],
            {'stage': riv_stage[[e for e in riv_stage.columns if 'clutha' in e]],
             'flow': use_riv_flow[[e for e in use_riv_flow.columns if 'clutha' in e]],
             },
            spd_dtype,
        )
        print('mapping_hawea')
        out_hawea = tdis.map_data_locations(
            riv_locs.loc[np.in1d(riv_locs.rname, ['hawea'])],
            {'stage': riv_stage[[e for e in riv_stage.columns if 'hawea' in e]],
             'flow': use_riv_flow[[e for e in use_riv_flow.columns if 'hawea' in e]],
             },
            spd_dtype,
        )
        print('mapping_john')
        out_john = tdis.map_data_locations(
            riv_locs.loc[np.in1d(riv_locs.rname, ['john'])],
            {'stage': riv_stage[[e for e in riv_stage.columns if 'john' in e]],
             'flow': use_riv_flow[[e for e in use_riv_flow.columns if 'john' in e]],
             },
            spd_dtype,
        )
        print('mapping_grandview')
        out_gview = tdis.map_data_locations(
            riv_locs.loc[np.in1d(riv_locs.rname, ['gview'])],
            {'stage': riv_stage[[e for e in riv_stage.columns if 'gview' in e]],
             'flow': use_riv_flow[[e for e in use_riv_flow.columns if 'gview' in e]],
             },
            spd_dtype,
        )
        data = {
            'gview': out_gview,
            'john': out_john,
            'hawea': out_hawea,
            'clutha': out_clutha,
        }
        for s, p in zip(streams, pickle_paths):
            pickle.dump(data[s], p.open('wb'))

    # manage parameter data!
    use_riv_params = {v: riv_params[k] for k, v in param_mapper.items()}
    for v in data.values():
        for spdv in v.values():
            for k, pval in use_riv_params.items():
                t = spdv['cond'].copy()
                t[np.isclose(t, k)] = pval
                spdv['cond'] = t
            pass

    if small_static:
        for k in ['gview', 'john']:
            data[k] = tdis.make_spd_steady(data[k])
    if big_static:
        for k in ['hawea', 'clutha', ]:
            data[k] = tdis.make_spd_steady(data[k])

    if return_unique:
        return data
    else:
        order = ['hawea', 'clutha', 'gview', 'john']  # order is essential!
        out = tdis.merge_spd(to_merge=[data[r] for r in order],
                             dtype=spd_dtype)
        return out


def _data_checks(save=False):
    """
    data checks for boundary conditions, exlcudes recharge and well boundary conditiosn (see
    Scenarios.supporting_data_analysis.scenario_recharge.data_checks
    Scenarios.supporting_data_analysis.pumping_data.data_checks
    :return:
    """
    from model_tools.model_plotting import plot_spd, first, last, FakePath  # keynote private repo
    from model_build.project_model_tools import smt
    from Scenarios.scen_period import scen_tdis
    from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    tickper = 50
    if save:
        outdir = processed_scen_dir.parent.joinpath('boundary_condition_plots')
        outdir.mkdir(exist_ok=True)
    else:
        outdir = FakePath()

    # stream stages and flows, statics and not statics
    print('stream flows/stages')
    for big_static, small_static in itertools.product([True, False], [True, False]):
        data = get_scen_str_data(tdis=scen_tdis, riv_params=riv_params,
                                 big_static=big_static, small_static=small_static, return_unique=True)
        for k in ['gview', 'john', 'hawea', 'clutha']:
            if k in ['gview', 'john'] and small_static:
                static_nm = 'static'
            elif k in ['hawea', 'clutha'] and big_static:
                static_nm = 'static'
            else:
                static_nm = 'variable'
            plot_spd(data[k], smt, scen_tdis,
                     func=first, key='stage', title=f'first river cell stage {k} {static_nm}', units='m msl',
                     outpath=outdir.joinpath(f'{k}_stage_{static_nm}.png'), tick_per=tickper)
            plot_spd(data[k], smt, scen_tdis,
                     func=first, key='flow', title=f'first river cell flow {k} {static_nm}', units='m3/day',
                     outpath=outdir.joinpath(f'{k}_flow_{static_nm}.png'), tick_per=tickper)

    temp = get_scen_well_data('no_pump', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                              return_unique_spd=True)
    race_spd = temp['race']
    hill_spd = temp['hill']
    get_scen_rch(scen_tdis, rch_param, True)
    get_scen_rch(scen_tdis, rch_param, False)
    # race data
    print('race data')
    plot_spd(race_spd, smt, scen_tdis, np.nansum, key='flux', title='race pump variable', tick_per=tickper,
             units='m3/day',
             outpath=outdir.joinpath('race_spd_variable.png'))
    plot_spd(scen_tdis.make_spd_steady(race_spd), smt, scen_tdis, np.nansum, key='flux', title='race pump static',
             tick_per=tickper, units='m3/day',
             outpath=outdir.joinpath('race_spd_static.png'))

    # hillslope data
    print('hillslope data')
    plot_spd(hill_spd, smt, scen_tdis, np.nansum, key='flux', title='hill slope inflows variable', tick_per=tickper,
             units='m3/day',
             outpath=outdir.joinpath('hillslope_variable.png'))
    plot_spd(scen_tdis.make_spd_steady(hill_spd), smt, scen_tdis, np.nansum, key='flux',
             title='hill slope inflows static',
             tick_per=tickper, units='m3/day',
             outpath=outdir.joinpath('hillslope_static.png'))

    # lake heads
    print('lake heads')
    lake_spd = get_scen_ghb_data(scen_tdis)
    plot_spd(lake_spd, smt, scen_tdis,
             func=np.nanmean,
             key='bhead', title='lake heads variable', outpath=outdir.joinpath(f'lake_spd_variable.png'), units='m msl',
             tick_per=tickper)
    plot_spd(scen_tdis.make_spd_steady(lake_spd), smt, scen_tdis,
             func=np.nanmean,
             key='bhead', title='lake heads static', outpath=outdir.joinpath(f'lake_spd_static.png'), units='m msl',
             tick_per=tickper)


def _check_all_in_domain():
    from model_build.project_model_tools import smt
    from Scenarios.scen_period import scen_tdis
    from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    data = dict(
        well=get_scen_well_data('no_pump', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                return_unique_spd=False),
        well2=get_scen_well_data('extended_pump', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                 return_unique_spd=False),
        well3=get_scen_well_data('static_pump', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                 return_unique_spd=False),
        lake_spd=get_scen_ghb_data(scen_tdis),
        str1=get_scen_str_data(scen_tdis, riv_params, big_static=True, small_static=True),
        str2=get_scen_str_data(scen_tdis, riv_params, big_static=True, small_static=False),
        str3=get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=True),
        str4=get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False),
    )
    iss = range(smt.rows)
    jss = range(smt.cols)
    kss = range(smt.layers)
    for k, v in data.items():
        print(k)
        is_in = np.array([np.in1d(e['i'], iss) for e in v.values()]).flatten()
        js_in = np.array([np.in1d(e['j'], jss) for e in v.values()]).flatten()
        ks_in = np.array([np.in1d(e['k'], kss) for e in v.values()]).flatten()
        assert all(is_in), f'iss out for {k}'
        assert all(js_in), f'jss out for {k}'
        assert all(ks_in), f'kss out for {k}'

    rch = get_scen_rch(scen_tdis, rch_param, False)
    assert all([e.shape == smt.model_2d_shape for e in rch.values()])
    rch2 = get_scen_rch(scen_tdis, rch_param, True)
    assert all([e.shape == smt.model_2d_shape for e in rch2.values()])


if __name__ == '__main__':
    _check_all_in_domain()
    # _data_checks(save=True)
