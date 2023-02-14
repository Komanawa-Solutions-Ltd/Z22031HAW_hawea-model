"""
created matt_dumont 
on: 9/02/23
"""
import shutil
import time
import flopy.utils
import pandas as pd
import numpy as np
from model_build.supporting_data_analysis.recharge_model import get_irrigation_code
from model_build.supporting_data_analysis.hillside_inflows import get_hillside_catchment_locs
from model_build.supporting_data_analysis.river_data import get_river_loc_data
from model_build.project_model_tools import smt
from pathlib import Path
from model_tools.time_discretization import TimeDis
from targets_and_sensitive_sites.model_output import plot_list_failures, modflow_converged
from copy import deepcopy
from model_build.project_model_tools import get_2d_moraine, get_layer_pinchout_area, get_lake_array


def get_indicator_well_locs():
    # todo locations for indicator wells, and also regular head locations
    raise NotImplementedError


def generate_scenario_outputs(model_ws, model_name, outdir, tdis):
    assert isinstance(tdis, TimeDis)
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

    temp = flopy.utils.HeadFile(hds_file)
    hds = temp.get_alldata()
    kstpkper = temp.get_kstpkper()
    hds[hds > 1e20] = np.nan
    np.savez_compressed(outdir.joinpath(f'{model_name}_hds.npz'), heads=hds, kstpkper=kstpkper)
    conv = modflow_converged(list_file)
    with open(outdir.joinpath('converged.txt'), 'w') as f:
        f.write(str(conv))

    # make an output dataset
    output_data = pd.DataFrame(index=tdis.pers, data=dict(date=tdis.per_middle_dates))

    # heads at:
    head_locs = get_indicator_well_locs()
    assert isinstance(head_locs, pd.DataFrame)
    for nm, k, i, j in head_locs.itertuples(name=None):
        output_data.loc[:, f'hds_{nm}'] = hds[:, k, i, j]

    # todo zone budget fluxes(??), probably
    #   moraine to main aquifer
    #   mangawera to river zone
    #   hawea flat to main terrace
    #   hawea flat to river zone
    #   river zone to main terrace
    #   river zone to sub terrace
    #   main terrace to sub terrace
    #   main terrace to clutha
    #   main terrace to sandy point


    # river fluxes summed by area
    t = flopy.utils.CellBudgetFile(cbc_file).get_data(text='STREAM LEAKAGE', full3D=True)
    mask = t[0].mask[np.newaxis, 0]
    all_riv = np.array(t)[:, 0]
    all_riv[np.repeat(mask, all_riv.shape[0], axis=0)] = np.nan
    riv_locs = get_river_loc_data()
    for p in riv_locs.param.unique():
        temp = riv_locs.loc[riv_locs.param == p]
        output_data.loc[:, f'riv_{p}_flux'] = np.nansum(all_riv[:, 0, temp.i, temp.j], axis=1)

    output_data.to_csv(outdir.joinpath('output_dataset.csv'))
    _plot_outputs(outdir.joinpath('plots'), list_file=list_file, hds_array=hds, output_data=output_data)


def _plot_spatial_heads(all_hds, plot_dir):
    tops = smt.get_tops()
    ibound = smt.get_no_flow()
    # dry cells at non-target data points
    dry_hds = (all_hds < -666) & (ibound == 1)

    # flooded cells
    flooded_cells = (all_hds > tops) & (ibound == 1)

    # plot hds (ss, min, max, range)
    use_hds = deepcopy(all_hds[:, 0])
    idx = get_2d_moraine() | get_layer_pinchout_area() | np.isfinite(get_lake_array())
    use_hds[:, idx] = all_hds[:, 2, idx]
    use_hds[use_hds < -666] = np.nan
    # keynote plotting layer 2 in lake, moraine, pinchout area
    all_plt_hds = {
        'Steady state heads (Hawea aquifer)': use_hds[0],
        'Min heads (Hawea aquifer)': np.nanmin(use_hds[1:], axis=0),
        'Max heads (Hawea aquifer)': np.nanmax(use_hds[1:], axis=0),
        'Range of Heads (Hawea aquifer)': np.nanmax(use_hds[1:], axis=0) - np.nanmin(use_hds[1:], axis=0)
    }
    for key, plt_hds in all_plt_hds.items():
        plt_hds[ibound != 1] = np.nan
        clevels = np.arange((np.nanmin(plt_hds) // 5) * 5, np.nanmax(plt_hds) // 5 * 5 + 5, 10)
        fig, ax = smt.plot.plt_matrix(plt_hds, no_flow_layer=0, base_map=True, title=key,
                                      contour=True, label_contours=True, contour_levels=clevels)
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'{key.replace(" ", "_")}.png'))
        smt.plot.close(fig)

    dry_hds = dry_hds.astype(float)
    dry_hds[np.isclose(dry_hds, 0)] = np.nan
    dry_hds = np.nansum(dry_hds, axis=0)
    flooded_cells = flooded_cells.astype(float)
    flooded_cells[np.isclose(flooded_cells, 0)] = np.nan
    flooded_cells = np.nansum(flooded_cells, axis=0)
    for l in range(smt.layers):
        # plot dry hds
        fig, ax = smt.plot.plt_matrix(dry_hds[l], base_map=True, no_flow_layer=0,
                                      title=f'Dry cells layer {l} (# of steps)')
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'dry_cells_l{l}.png'))
        smt.plot.close(fig)

        # plot flooded cells
        fig, ax = smt.plot.plt_matrix(flooded_cells[l], base_map=True, no_flow_layer=0,
                                      title=f'flooded cells layer {l}  (# of steps)')
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'flooded_cells_l{l}.png'))
        smt.plot.close(fig)


def _plot_outputs(plot_dir, list_file, hds_array, output_data):
    plot_dir.mkdir(exist_ok=True)
    plot_list_failures(list_file, plot_dir)
    _plot_spatial_heads(all_hds=hds_array, plot_dir=plot_dir)

    # todo plot output datasets

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


def compare_scenarios():  # todo
    # compare multiple results

    raise NotImplementedError


if __name__ == '__main__':
    from Scenarios.scen_period import scen_tdis
    from Scenarios.boundary_conditions import get_scen_well_data, get_scen_rch, get_scen_ghb_data
    from model_parameterisation.optimised_parameterisation import get_3d_v1d_params

    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    ghb_data = get_scen_ghb_data(tdis=scen_tdis)
    rch_data = get_scen_rch(scen_tdis, rch_param=rch_param, dryland=False)
    rch_data2 = get_scen_rch(scen_tdis, rch_param=rch_param, dryland=False, recalc=True)
    assert all([np.isclose(rch_data[k], rch_data2[k], equal_nan=True).all() for k in rch_data.keys()])
    well_data = get_scen_well_data('no_pump', scen_tdis, hill_param, race_param)
    t = time.time()
    extract_input_data(ghb_data=ghb_data,
                       rch_data=rch_data,
                       well_data=well_data,
                       tdis=scen_tdis)

    print(time.time() - t, 'seconds to run')
    pass
