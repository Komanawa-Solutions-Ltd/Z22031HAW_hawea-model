"""
created matt_dumont 
on: 9/02/23
"""
import shutil
import time
import flopy.utils
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from model_build.supporting_data_analysis.recharge_model import get_irrigation_code
from model_build.supporting_data_analysis.hillside_inflows import get_hillside_catchment_locs
from model_build.supporting_data_analysis.river_data import get_river_loc_data
from model_build.project_model_tools import smt
from pathlib import Path
from model_tools.time_discretization import TimeDis
from targets_and_sensitive_sites.model_output import plot_list_failures, modflow_converged, \
    plot_lake_moraine_smoothed_areas
from copy import deepcopy
from model_build.project_model_tools import get_2d_moraine, get_layer_pinchout_area, get_lake_array, get_lake_bar
from model_build.zones import get_model_zones
from model_build.supporting_data_analysis.all_wells import get_regular_wells
from project_base import base_scen_dir, processed_scen_dir


def _get_indicator_wells(recalc=False):
    save_path = processed_scen_dir.joinpath('indicator_wells.csv')

    if save_path.exists() and not recalc:
        out = pd.read_csv(save_path, index_col=0)
        return out
    import geopandas as gpd
    data = gpd.read_file(base_scen_dir.joinpath('indicator_wells.shp'))
    # todo decide names and groups (for plotting togeather after interigating base data)

    out = pd.DataFrame(index=data.loc[:, 'name'])
    out.index.name = 'well_name'
    x, y = data.geometry.x, data.geometry.y
    i, j = smt.convert_coords_to_matix(x, y)
    out.loc[:, 'nztmx'] = x.values
    out.loc[:, 'nztmy'] = y.values
    out.loc[:, 'group'] = data.loc[:, 'group'].values
    out.loc[:, 'type'] = 'indicator'
    out.loc[:, 'i'] = i
    out.loc[:, 'j'] = j
    out.to_csv(save_path)
    return out


def get_indicator_well_locs(plot=False):
    reg_wells = get_regular_wells()
    reg_wells.loc[:, 'type'] = 'monitoring'
    reg_wells.loc[:, 'group'] = reg_wells.index
    ind_wells = _get_indicator_wells()
    out = pd.concat((reg_wells, ind_wells))
    out.loc[:, 'k'] = 0
    idx = (get_2d_moraine() | get_layer_pinchout_area())[out.i, out.j]
    out.loc[idx, 'k'] = 2

    return out


def generate_scenario_outputs(model_ws, model_name, outdir, tdis):
    assert isinstance(tdis, TimeDis)
    model_ws = Path(model_ws)
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    # save only outputs to github repo, model is run in external directory (not saved)

    # copy key input data
    # todo after debug shutil.copyfile(model_ws.joinpath(key_input_data_file_name), outdir.joinpath(key_input_data_file_name))
    model_ws = Path(model_ws)
    hds_file = model_ws.joinpath(f'{model_name}.hds')
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
    for nm, k, i, j in head_locs[['k', 'i', 'j']].itertuples(name=None):
        output_data.loc[:, f'hds_{nm}'] = hds[:, k, i, j]

    # river fluxes summed by area
    with flopy.utils.CellBudgetFile(cbc_file) as f:
        t = f.get_data(text='STREAM LEAKAGE', full3D=True)
    mask = t[0].mask[np.newaxis, 0]
    all_riv = np.array(t)[:, 0]
    all_riv[np.repeat(mask, all_riv.shape[0], axis=0)] = np.nan
    riv_locs = get_river_loc_data()
    for p in riv_locs.param.unique():
        temp = riv_locs.loc[riv_locs.param == p]
        output_data.loc[:, f'riv_{p}_flux'] = np.nansum(all_riv[:, temp.i, temp.j], axis=1)

    _extract_zone_budget_fluxes(output_data, cbc_file, outdir)
    output_data.to_csv(outdir.joinpath('output_dataset.csv'))
    _plot_outputs(plot_dir=outdir.joinpath('plots'), list_file=list_file, hds_array=hds, output_data=output_data,
                  model_nm=model_name, tdis=tdis)


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
        plt_hds[ibound[0] != 1] = np.nan
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


def _plot_outputs(tdis, plot_dir, list_file, hds_array, output_data, model_nm):
    plot_dir.mkdir(exist_ok=True)
    figs, axs = _plot_output_data(tdis, output_data, model_nm=model_nm)
    plot_list_failures(list_file, plot_dir)
    _plot_spatial_heads(all_hds=hds_array, plot_dir=plot_dir)
    all_hds = hds_array
    all_hds[all_hds < -666] = np.nan
    # todo plot key input data

    # todo steady state moraine heads
    plot_lake_moraine_smoothed_areas(all_hds, plot_dir, index=None, nm=None) # todo only the steady state?? or include the max/min lake heads, todo set index and nm
    # todo max_lake (at g40_0415) moraine heads
    # todo min_lake (at g40_0415) moraine heads

    for k, fig in figs.items():
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'{k}.png'))
    plt.close('all')


def _plot_output_data(tdis, output_data, model_nm, figs=None, axs=None, ls=None, tick_per=50):
    """
    to plot multiple verions pass figs, axs from perivous time
    :param output_data:
    :param model_nm:
    :param figs:
    :param axs:
    :param ls:
    :return:
    """
    if ls is None:
        ls = 'solid'
    indicator_wells = get_indicator_well_locs()
    if figs is None:
        assert axs is None
        figs, axs = _setup_output_plots(indicator_wells)
    else:
        assert isinstance(figs, dict)
        assert isinstance(axs, dict)

    # todo plot data

    # hds groups
    for g in indicator_wells.group.unique():
        fig, use_axs = figs[f'hds_{g}'], axs[f'hds_{g}']
        temp_wells = indicator_wells.loc[indicator_wells.group == g]
        colors = smt.plot.get_colors(range(len(temp_wells)))
        for ax, nm, c in zip(use_axs, temp_wells.index, colors):
            ax.plot(output_data.index, output_data[f'hds_{nm}'], color=c, ls=ls, label=f'{nm}-{model_nm}')
            ax.legend()

    # river fluxes
    fig, use_axs = figs['river_flux'], axs['river_flux']
    rivers = ['riv_h1_flux', 'riv_h2_flux', 'riv_h3_flux', 'riv_c1_flux', 'riv_gview_flux', 'riv_john_flux']
    for riv, ax in zip(rivers, use_axs):
        use_riv = riv.replace('_h', '_hawea').replace('_c', '_clutha').replace('riv_', '').replace('_', ' ')
        use_riv = use_riv.capitalize()
        ax.plot(output_data.index, output_data[riv], c='k', ls=ls, label=f'{use_riv}-{model_nm}')
        ax.set_title(use_riv)
        ax.legend()

    # zone budget plots
    fig, use_axs = figs['zone_budget'], axs['zone_budget']
    for ax, (from_zone, to_zone) in zip(use_axs, z_bud_to_from):
        key = f'{from_zone}_to_{to_zone}'
        print_key = f'{from_zone.capitalize()} to {to_zone.capitalize()}'
        ax.plot(output_data.index, output_data[key], ls=ls, label=f'{print_key}-{model_nm}')
        ax.set_title(print_key)

    # manage ax ticks...
    for v in axs.values():
        for ax in v:
            ax.set_xticks([e for i, e in enumerate(tdis.pers) if i % tick_per == 0])
            all_labs = [f'{p}: {d.date().isoformat()}' for p, d in zip(tdis.pers, pd.Series(tdis.per_middle_dates))]
            ax.set_xticklabels([e for i, e in enumerate(all_labs) if i % tick_per == 0], rotation=-60)

    return figs, axs


def _setup_output_plots(indicator_wells):
    figs, axs = {}, {}

    # indicator_hds_groups  (incl regular heads)
    for g in indicator_wells.group.unique():
        temp_wells = indicator_wells.loc[indicator_wells.group == g]
        num = len(temp_wells)
        fig = plt.Figure(figsize=(14, 14))
        fig.suptitle(f'Hds {g}')
        gs = fig.add_gridspec(nrows=num, ncols=2, width_ratios=(2, 1))
        temp_axs = []
        temp_axs.append(fig.add_subplot(gs[0, 0]))
        temp_axs.extend([fig.add_subplot(gs[i, 0], sharex=temp_axs[0]) for i in range(1, num)])
        figs[f'hds_{g}'] = fig
        axs[f'hds_{g}'] = temp_axs

        # make/ plot locator (color for well, ls for scenario)
        temp_ax = fig.add_subplot(gs[:, 1])
        smt.plot.plt_basemap(ax=temp_ax, no_flow_layer=0)
        colors = smt.plot.get_colors(range(num))
        for c, (nm, x, y) in zip(colors, temp_wells[['nztmx', 'nztmy']].itertuples(True, None)):
            temp_ax.scatter(x, y, color=c, label=nm)
        temp_ax.legend()
        smt.plot.set_plot_lims_padded(temp_wells.nztmx, temp_wells.nztmy, 500, temp_ax)

    # river fluxes
    fig, temp_axs = plt.subplots(3, 2, sharex=True, figsize=(14, 14))
    figs['river_flux'] = fig
    axs['river_flux'] = temp_axs.flatten()

    # zone budget plots
    fig, temp_axs = plt.subplots(3, 3, sharex=True, figsize=(14, 14))
    figs['zone_budget'] = fig
    axs['zone_budget'] = temp_axs.flatten()
    return figs, axs


key_input_data_file_name = 'key_input_data.csv'


def get_zone_budget_array(plot=False):
    mappers = {
        0: 'noflow',
        1: 'haweaflat',
        2: 'moraine_top',
        3: 'river_zone',
        4: 'main_terrace',
        5: 'sandy_point',
        6: 'clutha',
        7: 'sub_terrace',
        8: 'mangawera',
    }
    established_zones = get_model_zones()
    keys = list(mappers.keys())
    active = smt.get_no_flow() == 1
    zones = smt.get_model_zeros(True)

    zones[:, established_zones['flat']] = 1
    zones[:, np.isfinite(get_lake_array())] = 2
    zones[0, get_2d_moraine()] = 2
    zones[1:, get_lake_bar()] = 2
    zones[:, established_zones['mangawera']] = 8
    zones[:, established_zones['sandypoint']] = 5
    zones[:, established_zones['east'] | established_zones['near_river']] = 3
    zones[:, established_zones['terrace']] = 4
    zones[:, established_zones['clutha']] = 6
    zones[:, established_zones['sub_terrace']] = 7
    zones[~active] = 0

    if plot:
        from model_build.utils import get_colors
        colors = {k: c for k, c in zip(keys, get_colors(keys))}
        for l in range(smt.layers):
            smt.plot.plt_discrete_matrix(zones[l], colors, names=mappers, title=f'layer: {l}', base_map=True)
        smt.plot.show()

    return zones.astype(int), mappers


z_bud_to_from = (
    # (from zone, to zone)
    ('moraine_top', 'haweaflat'),
    ('mangawera', 'river_zone'),
    ('haweaflat', 'main_terrace'),
    ('haweaflat', 'river_zone'),
    ('river_zone', 'main_terrace'),
    ('river_zone', 'sub_terrace'),
    ('main_terrace', 'sub_terrace'),
    ('main_terrace', 'clutha'),
    ('main_terrace', 'sandy_point'),
)


def _extract_zone_budget_fluxes(output_data, cbc_file, outdir):
    zones, mapper = get_zone_budget_array()
    t = flopy.utils.ZoneBudget(str(cbc_file), zones, kstpkper=None,
                               aliases=mapper)
    dfs = t.get_dataframes(index_key='kstpkper').reset_index()
    dfs = dfs.set_index(['name', 'stress_period'])
    dfs.to_csv(outdir.joinpath('zone_budget.csv'))

    for from_zone, to_zone in z_bud_to_from:
        fr = dfs.loc[f'FROM_{from_zone}', to_zone]
        to = dfs.loc[f'TO_{from_zone}', to_zone]
        tot = fr - to
        output_data.loc[:, f'{from_zone}_to_{to_zone}'] = tot.values


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
    from optimisation.optimisation_period import tdis as opt_tids

    _get_indicator_wells(True)
    get_indicator_wells = get_indicator_well_locs()
    generate_scenario_outputs('/home/matt_dumont/unbacked/hawea/3d_v1d/init_3d_v1d/Optimisations/Final_opt_model/',
                              'final_opt_model', outdir=Path.home().joinpath('unbacked/temp/test_outputs'),
                              tdis=opt_tids)
    raise NotImplementedError
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
