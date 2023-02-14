"""
created matt_dumont 
on: 9/02/23
"""
import shutil
import time

import pandas as pd
import numpy as np
from model_build.supporting_data_analysis.recharge_model import get_irrigation_code
from model_build.supporting_data_analysis.hillside_inflows import get_hillside_catchment_locs
from model_build.project_model_tools import smt
from pathlib import Path
from model_tools.time_discretization import TimeDis
from targets_and_sensitive_sites.model_output import plot_list_failures


# todo make standard set of scenario outputs!

def generate_scenario_outputs(model_ws, model_name, outdir):
    model_ws = Path(model_ws)
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    # save only outputs to github repo, model is run in external directory (not saved)

    # copy key input data
    shutil.copyfile(model_ws.joinpath(key_input_data_file_name), outdir.joinpath(key_input_data_file_name))
    model_ws = Path(model_ws)
    hds_file = model_ws.joinpath(f'{model_name}.hds')  # todo check
    list_file = hds_file.with_suffix('.list')
    cbc_file = hds_file.with_suffix('.cbc')

    # todo copy and expand from: targets_and_sensitive_sites.model_output.process_model_output

    # single model outputs

    # make an output dataset
    # heads at:
    #   high frequency wells
    #   architype locations (e.g. example wells)
    #   zone budget fluxes(??), probably
    #

    # river fluxes

    # passed/failed


    raise NotImplementedError


def _plot_outputs(plot_dir, list_file, hds_array, output_data):
    plot_dir.mkdir(exist_ok=True)
    plot_list_failures(list_file, plot_dir)
    # plots of:
    # heads min, mean, max, range, steady state (exclude dry cells)
    # as above but for the 3d area
    # dry cells
    # head data???
    raise NotImplementedError


key_input_data_file_name = 'key_input_data.csv'


def extract_input_data(ghb_data, rch_data, well_data, tdis):
    """
    extract key into data
    :param ghb_data: ghb data stress period
    :param rch_data: rch stress period data
    :param well_data: well stress preiod data
    :param tdis: time dis object for run
    :return:
    """
    assert isinstance(tdis, TimeDis)
    outdata = pd.DataFrame(index=tdis.pers, data={'datetime': tdis.per_middle_dates})

    # heads of lake
    outdata.loc[:, 'lake'] = [np.mean(ghb_data[per]['bhead']) for per in tdis.pers]

    # recharge at irrigated (mean), dryland, full active
    all_rch = np.concatenate([rch_data[per][np.newaxis] for per in tdis.pers], axis=0)
    irr = get_irrigation_code(2021) >= 0
    active = smt.get_no_flow(0) != 0
    outdata.loc[:, 'total_rch'] = np.nanmean(all_rch[:, active], axis=(1))
    outdata.loc[:, 'dryland_rch'] = np.nanmean(all_rch[:, ~irr & active], axis=(1))
    outdata.loc[:, 'irr_rch'] = np.nanmean(all_rch[:, irr & active], axis=(1))

    # hillslope inflows (ex. john/grandview) total and by group.
    hill_locs = get_hillside_catchment_locs()
    hill_names = []
    for g in hill_locs.group.unique():
        temp = hill_locs.loc[hill_locs.group == g]
        temp = smt.io.df_to_array(temp, 'i', True, duplicate_action=None)
        temp = np.isfinite(temp)
        use_data = [smt.io.select_df_from_idx_array(pd.DataFrame(well_data[p]), temp, ) for p in tdis.pers]
        outdata.loc[:, f'hill_{g}'] = use_data
        hill_names.append(f'hill_{g}')
    outdata.loc[:, 'hill_total'] = outdata.loc[:, hill_names].sum(axis=1)

    return outdata


def compare_scenarios():
    # compare multiple results

    raise NotImplementedError


if __name__ == '__main__':
    from Scenarios.scen_period import scen_tdis
    from Scenarios.boundary_conditions import get_scen_well_data, get_scen_rch, get_scen_ghb_data
    from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
    # todo some of these are too big for github!!! break up!!!
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    ghb_data = get_scen_ghb_data(tdis=scen_tdis)
    rch_data = get_scen_rch(scen_tdis, rch_param=rch_param, dryland=False)
    rch_data2 = get_scen_rch(scen_tdis, rch_param=rch_param, dryland=False, recalc=True)
    assert all([np.isclose(rch_data[k], rch_data2[k],equal_nan=True).all() for k in rch_data.keys()])
    well_data = get_scen_well_data('no_pump', scen_tdis, hill_param, race_param)
    t = time.time()
    extract_input_data(ghb_data=ghb_data,
                       rch_data=rch_data,
                       well_data=well_data,
                       tdis=scen_tdis)

    print(time.time() - t, 'seconds to run')
    pass
