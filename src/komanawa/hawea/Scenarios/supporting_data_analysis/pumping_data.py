"""
created matt_dumont 
on: 9/02/23
"""
import pickle

import flopy.modflow
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import geopandas as gpd
try:
    from model_tools.time_discretization import TimeDis
except ModuleNotFoundError:
    from komanawa.hawea.dummy_packages import TimeDis
from komanawa.hawea.model_build.get_boundary_condition_data import get_well_data
from komanawa.hawea.optimisation.optimisation_period import tdis as opt_tdis
from komanawa.hawea.model_parameterisation.inital_parametersiation import get_race_multiplier, get_hillslope_multiplier
from komanawa.hawea.model_build.supporting_data_analysis.get_pumping_data import get_pumping_locs, get_historical_pumping_data, \
    get_historical_max_allo_pumping_data
from komanawa.hawea.hawea_base import processed_scen_dir, base_scen_dir
from komanawa.hawea.Scenarios.supporting_data_analysis.utils import make_long_weekly_mean
from komanawa.hawea.model_build.project_model_tools import smt, get_layer_pinchout_area, get_2d_moraine, get_lake_array, \
    get_low_cond_array
from komanawa.hawea.model_build.supporting_data_analysis.get_pumping_data import get_pump_to_l1

accepted_pump_names = (
    'extended_max_allo_pc',  # maximum allocation on the pumping curve.
    'no_pump',  # no groundwater abstraction
    'static_pump',  # static pumping (e.g. steady state for all)
    'extended_pump',  # iso week mean pumping for per-optimisation period, then known pumping for optimization period
    'extended_full_allo',  # as per extended_pump but at full allocation (temporally mapped to usage
    'extended_max_allo',  # as per extended_pump but at full allocation for every single day
)


def get_scen_pumping_data(pump_name, tdis, recalc=False):
    """
    get pumping stress period data for scenarios
    :param pump_name: defined pumping name see 'accepted_pump_names'
    :param tdis: time distritisation object
    :param recalc: bool recalc from dataset
    :return:
    """
    assert pump_name in accepted_pump_names, f'unknown pump name: {pump_name}, expected on of: {accepted_pump_names}'
    if pump_name == 'no_pump':
        return {}
    elif pump_name == 'static_pump':
        opt_data = get_well_data(opt_tdis,
                                 get_hillslope_multiplier(True), get_race_multiplier(True),  # dummy values
                                 return_unique_spd=True
                                 )
        out = {p: opt_data['pump'][0] for p in tdis.pers}
        return out
    elif pump_name == 'extended_pump':
        return _get_iso_week_normal_pumping(tdis, recalc=recalc)
    elif pump_name == 'extended_full_allo':
        return _get_iso_week_full_allo_pumping(tdis, recalc=recalc)
    elif pump_name == 'extended_max_allo':
        return _get_iso_week_max_allo_pumping(tids=tdis, recalc=recalc)
    elif pump_name == 'extended_max_allo_pc':
        return _get_iso_week_max_allo_pumping_pc(tdis, recalc)
    else:
        raise NotImplementedError(f'shouldnt get here unless {pump_name} is not fully implemented')


def _get_iso_week_max_allo_pumping_pc(tdis, recalc):
    assert isinstance(tdis, TimeDis)
    save_path = processed_scen_dir.joinpath(f'iso_week_max_allo_pc_{tdis.name}.p')
    if save_path.exists() and not recalc:
        with save_path.open('rb') as f:
            data = pickle.load(f)
        return data
    historical_data = make_long_weekly_mean(get_historical_max_allo_pumping_data(*opt_tdis.date_limits),
                                            *tdis.date_limits,
                                            only_where_na=False)
    historical_max = historical_data.max()
    pump_curve = get_pump_curve(tdis)
    historical_data = pd.DataFrame(index=pump_curve.index)
    for k, v in historical_max.to_dict().items():
        historical_data.loc[:, k] = pump_curve * v
    pumping_locs = get_pumping_locs()
    historical_data *= -1
    historical_data.fillna(0, inplace=True)
    historical_data = historical_data.loc[:, pumping_locs.index]
    outdata = tdis.map_data_locations(loc_data=pumping_locs, transient_data_dict=dict(flux=historical_data),
                                      datatype=flopy.modflow.ModflowWel.get_default_dtype(),
                                      group_cells=True, grouper=np.nansum)
    with save_path.open('wb') as f:
        pickle.dump(outdata, f)
    return outdata


def _get_iso_week_normal_pumping(tids, recalc):
    assert isinstance(tids, TimeDis)
    save_path = processed_scen_dir.joinpath(f'iso_week_pump_{tids.name}.p')
    if save_path.exists() and not recalc:
        with save_path.open('rb') as f:
            data = pickle.load(f)
        return data
    historical_data = make_long_weekly_mean(get_historical_pumping_data(*opt_tdis.date_limits), *tids.date_limits,
                                            only_where_na=False)
    pumping_locs = get_pumping_locs()
    historical_data *= -1
    historical_data.fillna(0, inplace=True)
    historical_data = historical_data.loc[:, pumping_locs.index]
    outdata = tids.map_data_locations(loc_data=pumping_locs, transient_data_dict=dict(flux=historical_data),
                                      datatype=flopy.modflow.ModflowWel.get_default_dtype(),
                                      group_cells=True, grouper=np.nansum)
    with save_path.open('wb') as f:
        pickle.dump(outdata, f)
    return outdata


def _get_iso_week_full_allo_pumping(tids, recalc):
    """
    full allo is max allo normalised to usage
    :param tids:
    :param recalc:
    :return:
    """
    assert isinstance(tids, TimeDis)
    save_path = processed_scen_dir.joinpath(f'iso_week_pump_full_allo_{tids.name}.p')
    if save_path.exists() and not recalc:
        with save_path.open('rb') as f:
            data = pickle.load(f)
        return data

    historical_data = make_long_weekly_mean(get_historical_pumping_data(*opt_tdis.date_limits),
                                            *tids.date_limits,
                                            only_where_na=False)
    allo_pumping = make_long_weekly_mean(get_historical_max_allo_pumping_data(*opt_tdis.date_limits),
                                         *tids.date_limits,
                                         only_where_na=False)
    use_data = historical_data / historical_data.max() * allo_pumping

    pumping_locs = get_pumping_locs()
    pumping_locs.loc[pumping_locs['mangawera'], 'k'] = 1  # keynote set to l1 to prevent model from failing
    use_data *= -1
    use_data.fillna(0, inplace=True)
    use_data = use_data.loc[:, pumping_locs.index]
    outdata = tids.map_data_locations(loc_data=pumping_locs, transient_data_dict=dict(flux=use_data),
                                      datatype=flopy.modflow.ModflowWel.get_default_dtype(),
                                      group_cells=True, grouper=np.nansum)
    with save_path.open('wb') as f:
        pickle.dump(outdata, f)
    return outdata


def _get_iso_week_max_allo_pumping(tids,
                                   recalc):
    """
    maximum daily allocation (mike's gw_allo field)
    :param tids:
    :param recalc:
    :return:
    """
    assert isinstance(tids, TimeDis)
    save_path = processed_scen_dir.joinpath(f'iso_week_pump_max_allo_{tids.name}.p')
    if save_path.exists() and not recalc:
        with save_path.open('rb') as f:
            data = pickle.load(f)
        return data

    historical_data = make_long_weekly_mean(get_historical_max_allo_pumping_data(*opt_tdis.date_limits),
                                            *tids.date_limits,
                                            only_where_na=False)
    pumping_locs = get_pumping_locs()
    historical_data *= -1
    historical_data.fillna(0, inplace=True)
    historical_data = historical_data.loc[:, pumping_locs.index]
    outdata = tids.map_data_locations(loc_data=pumping_locs, transient_data_dict=dict(flux=historical_data),
                                      datatype=flopy.modflow.ModflowWel.get_default_dtype(),
                                      group_cells=True, grouper=np.nansum)
    with save_path.open('wb') as f:
        pickle.dump(outdata, f)
    return outdata


def get_pump_curve(tdis):
    pump_curve = get_historical_pumping_data(None, None, frequency='W').sum(axis=1)
    pump_curve.name = 'flux'
    pump_curve = make_long_weekly_mean(pump_curve, *tdis.date_limits, only_where_na=False)
    pump_curve.loc[:, f'flux'] = pump_curve.flux.rolling(9, center=True).mean()
    pump_curve = (pump_curve - pump_curve.min()) / (pump_curve.max() - pump_curve.min())
    pump_curve = make_long_weekly_mean(pump_curve, *tdis.date_limits, only_where_na=False)
    return pump_curve


def plot_pump_curve(save=False):
    from komanawa.hawea.Scenarios.scen_period import scen_tdis
    pump = get_pump_curve(scen_tdis)
    pump = pump.iloc[1:105]
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.plot(pump.index, pump.flux)
    ax.set_xlabel('indicative date (all years are identical)')
    ax.set_ylabel('fraction of pumping applied')
    ax.set_title('pumping curve')
    fig.tight_layout()
    if save:
        outdir = processed_scen_dir.parent.joinpath('boundary_condition_plots', 'pumping')
        fig.savefig(outdir.joinpath('grid_pumping_curve.png'))
    plt.show()


def get_gridded_pumping(tdis, idx_array,
                        total_increase):
    """
    get gridded pumping spd
    :param idx_array:
    :param total_increase: float maximum daily rate to add to model, >0 = abstraction
    :return:
    """
    assert isinstance(tdis, TimeDis)
    grid_locs = get_grid_locs()
    grid_locs = smt.io.select_df_from_idx_array(grid_locs, idx_array, True)
    pump_curve = get_pump_curve(tdis)
    pump_curve = pump_curve * total_increase / len(grid_locs)
    pump_curve *= -1  # switch to abstraction

    out = tdis.map_data_locations(loc_data=grid_locs, transient_data_dict=dict(flux=pump_curve['flux']),
                                  datatype=flopy.modflow.ModflowWel.get_default_dtype(), apply_to_all=True)
    return out


def get_grid_locs(recalc=False):
    save_path = processed_scen_dir.joinpath('grid_locs.csv')
    base_data_path = base_scen_dir.joinpath('grid_well.shp')

    if save_path.exists() and not recalc:
        return pd.read_csv(save_path, index_col=0, dtype=int)

    lake_array = get_lake_array()
    data = gpd.read_file(base_data_path)
    xs = data.geometry.x
    ys = data.geometry.y
    i, j = smt.convert_coords_to_matix(xs, ys, coords_out_domain='coerce')
    i = i[i >= 0]
    j = j[j >= 0]
    data = pd.DataFrame({'i': i, 'j': j}, dtype=int)
    data.loc[:, 'k'] = 1
    special_area = np.isfinite(get_lake_array()) | get_layer_pinchout_area() | get_2d_moraine()
    data.loc[special_area[i, j], 'k'] = 2

    # move hawea flat bores to layer 1 so that they cannot go dry (reduce model instability)
    idx = get_pump_to_l1()[data.i, data.j] & (data.k == 0)
    data.loc[idx, 'k'] = 1

    data.loc[:, 'ibound'] = smt.get_no_flow()[data.k, data.i, data.j]
    data = data.loc[data.ibound == 1]
    data = data.loc[~np.isfinite(lake_array[data.i, data.j])]
    # check for bad data
    idx = get_low_cond_array()
    moraine = get_2d_moraine()
    for l in range(len(idx)):
        idx[l] = idx[l] | np.isfinite(lake_array)
    idx[0] = idx[0] | moraine
    assert not idx[data.k, data.i, data.j].any(), 'pumping in lake or low cond cells, or thin layer'
    data = smt.io.add_mxmy_to_df(data)

    data.to_csv(save_path)
    return data


def data_checks(save=True):
    from komanawa.hawea.Scenarios.scen_period import scen_tdis
    from komanawa.hawea.model_build.project_model_tools import smt
    from model_tools.model_plotting import plot_spd, first, last, FakePath # keynote private repo
    from komanawa.hawea.model_build.zones import get_model_zones
    zones = get_model_zones()
    tickper = 50
    if save:
        outdir = processed_scen_dir.parent.joinpath('boundary_condition_plots', 'pumping')
        outdir.mkdir(exist_ok=True)
    else:
        outdir = FakePath()

    for n in accepted_pump_names:
        print(f'data checks for {n}')
        if n == 'no_pump':
            continue
        data = get_scen_pumping_data(n, scen_tdis, recalc=True)

        plot_spd(data, smt, scen_tdis,
                 func=np.nansum, key='flux', title=f'total pumping rate {n}', units='m3/day',
                 outpath=outdir.joinpath(f'pumping_{n}_total.png'), tick_per=tickper)

        # zonal pumping
        plt_zones = [['mangawera', 'terrace', 'flat', 'east'], ['hawea_flat', 'hawea_town']]
        save_nms = ['model_regions', 'towns']
        for plt_z, nm in zip(plt_zones, save_nms):
            fig, axs = plt.subplots(nrows=len(plt_z), figsize=(14, 10), sharex=True)
            for z, ax in zip(plt_z, axs):
                plot_spd(data, smt, scen_tdis,
                         func=np.nansum, key='flux', title=f'{z} pumping rate {n}', units='m3/day',
                         outpath=None, tick_per=tickper,
                         area_index=np.repeat(zones[z][np.newaxis], smt.layers, axis=0),
                         ax=ax)
            outpath = outdir.joinpath(f'pumping_{n}_{nm}.png')
            if outpath is not None:
                fig.savefig(outpath)
    if not save:
        smt.plot.show()


if __name__ == '__main__':
    plot_pump_curve(True)
    data_checks()
