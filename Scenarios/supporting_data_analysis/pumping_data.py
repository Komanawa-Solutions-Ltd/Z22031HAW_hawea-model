"""
created matt_dumont 
on: 9/02/23
"""
import pickle

import flopy.modflow
import matplotlib.pyplot as plt
import numpy as np

from model_tools.time_discretization import TimeDis
from model_build.get_boundary_condition_data import get_well_data
from optimisation.optimisation_period import tdis as opt_tdis
from model_parameterisation.inital_parametersiation import get_race_multiplier, get_hillslope_multiplier
from model_build.supporting_data_analysis.get_pumping_data import get_pumping_locs, get_historical_pumping_data
from project_base import processed_scen_dir
from Scenarios.supporting_data_analysis.utils import make_long_weekly_mean

accepted_pump_names = (  # todo more pumping scenarios??
    'no_pump',  # no groundwater abstraction
    'static_pump',  # static pumping (e.g. steady state for all)
    'extended_pump',  # iso week mean pumping for per-optimisation period, then known pumping for optimization period
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
    else:
        raise NotImplementedError(f'shouldnt get here unless {pump_name} is not fully implemented')


def _get_iso_week_normal_pumping(tids, recalc):
    assert isinstance(tids, TimeDis)
    save_path = processed_scen_dir.joinpath(f'iso_week_pump_{tids.name}.p')
    if save_path.exists() and not recalc:
        with save_path.open('rb') as f:
            data = pickle.load(f)
        return data
    historical_data = make_long_weekly_mean(get_historical_pumping_data(None, None), *tids.date_limits)
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


def data_checks(save=True):  # todo check, re-run on new pumping names
    from Scenarios.scen_period import scen_tdis
    from model_build.project_model_tools import smt
    from model_tools.model_plotting import plot_spd, first, last, FakePath
    from model_build.zones import get_model_zones
    zones = get_model_zones()
    tickper = 50
    if save:
        outdir = processed_scen_dir.parent.joinpath('boundary_condition_plots', 'pumping')
        outdir.mkdir(exist_ok=True)
    else:
        outdir = FakePath()

    for n in accepted_pump_names:
        if n == 'no_pump':
            continue
        data = get_scen_pumping_data(n, scen_tdis)

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
    data_checks()
