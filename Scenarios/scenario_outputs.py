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
from model_build.project_model_tools import smt, get_low_cond_array
from pathlib import Path
from model_tools.time_discretization import TimeDis
from targets_and_sensitive_sites.model_output import plot_list_failures, modflow_converged, \
    plot_lake_moraine_smoothed_areas
from copy import deepcopy
from model_build.project_model_tools import get_2d_moraine, get_layer_pinchout_area, get_lake_array, get_lake_bar
from model_build.zones import get_model_zones
from model_build.supporting_data_analysis.all_wells import get_regular_wells
from project_base import base_scen_dir, processed_scen_dir, proj_root
from optimisation.final_opt_models.compress_uncompress_model import split_hds_npz
from scipy.stats import percentileofscore
from model_build.supporting_data_analysis import get_all_wells


def _get_indicator_wells(recalc=False):
    save_path = processed_scen_dir.joinpath('indicator_wells.csv')

    if save_path.exists() and not recalc:
        out = pd.read_csv(save_path, index_col=0)
        return out
    import geopandas as gpd
    data = gpd.read_file(base_scen_dir.joinpath('indicator_wells.shp'))

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


def get_indicator_well_locs():
    reg_wells = get_regular_wells()
    reg_wells.loc[:, 'type'] = 'monitoring'
    reg_wells.loc[:, 'group'] = 'monitoring'
    ind_wells = _get_indicator_wells()
    out = pd.concat((reg_wells, ind_wells))
    out.loc[:, 'k'] = 0
    idx = (get_2d_moraine() | get_layer_pinchout_area())[out.i, out.j]
    out.loc[idx, 'k'] = 2

    return out


def generate_scenario_outputs(model_ws, model_name, outdir, tdis, tickper=100, save_hds=True, plot_data=True,
                              save_list=True):
    assert isinstance(tdis, TimeDis)
    model_ws = Path(model_ws)
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    # save only outputs to github repo, model is run in external directory (not saved)

    # copy key input data
    shutil.copyfile(model_ws.joinpath(key_input_data_file_name), outdir.joinpath(key_input_data_file_name))
    model_ws = Path(model_ws)
    hds_file = model_ws.joinpath(f'{model_name}.hds')
    list_file = hds_file.with_suffix('.list')
    cbc_file = hds_file.with_suffix('.cbc')

    temp = flopy.utils.HeadFile(hds_file)
    hds = temp.get_alldata()
    kstpkper = temp.get_kstpkper()
    hds[hds > 1e20] = np.nan
    nper = len(hds)
    if save_hds:
        np.savez_compressed(outdir.joinpath(f'{model_name}_hds.npz'), heads=hds,
                            kstpkper=kstpkper)
        split = split_hds_npz(outdir.joinpath(f'{model_name}_hds.npz'), outdir.joinpath(f'{model_name}_hds'))
        if split:
            outdir.joinpath(f'{model_name}_hds.npz').unlink()
    conv = modflow_converged(list_file)
    if save_list:
        outpath = outdir.joinpath(list_file.name)
        outpath.unlink(missing_ok=True)
        shutil.copyfile(list_file, outpath)
    with open(outdir.joinpath('converged.txt'), 'w') as f:
        f.write(str(conv))

    # make an output dataset
    output_data = pd.DataFrame(index=tdis.pers, data=dict(date=tdis.per_middle_dates))

    # heads at:
    head_locs = get_indicator_well_locs()
    assert isinstance(head_locs, pd.DataFrame)
    for nm, k, i, j in head_locs[['k', 'i', 'j']].itertuples(name=None):
        output_data.loc[range(nper), f'hds_{nm}'] = hds[:, k, i, j]

    # river fluxes summed by area
    with flopy.utils.CellBudgetFile(cbc_file) as f:
        t = f.get_data(text='STREAM LEAKAGE', full3D=True)
    mask = t[0].mask[np.newaxis, 0]
    all_riv = np.array(t)[:, 0]
    all_riv[np.repeat(mask, all_riv.shape[0], axis=0)] = np.nan
    riv_locs = get_river_loc_data()
    for p in riv_locs.param.unique():
        temp = riv_locs.loc[riv_locs.param == p]
        output_data.loc[range(nper), f'riv_{p}_flux'] = np.nansum(all_riv[:, temp.i, temp.j], axis=1)
    input_data = pd.read_csv(model_ws.joinpath(key_input_data_file_name), index_col=0)
    _extract_zone_budget_fluxes(nper, output_data, cbc_file, outdir)
    output_data.to_csv(outdir.joinpath(key_output_data_file_name))

    out = get_all_wells()
    out = out.loc[out.ibound == 1]
    out.loc[:, 'k'] = 0
    idx = (get_2d_moraine() | get_layer_pinchout_area())[out.i, out.j]
    out.loc[idx, 'k'] = 2

    all_well_outdata = pd.DataFrame(index=tdis.pers, data=dict(date=tdis.per_middle_dates))
    for w, k, i, j in out[['k', 'i', 'j']].itertuples(True, None):
        all_well_outdata.loc[range(nper), w] = hds[:, k, i, j]
    all_well_outdata.to_csv(outdir.joinpath(key_all_well_data_file_name))

    if plot_data:
        _plot_single_model_outputs_inputs(plot_dir=outdir.joinpath('plots'), list_file=list_file, hds_array=hds,
                                          output_data=output_data,
                                          model_nm=model_name, tdis=tdis, input_data=input_data, tick_per=tickper)


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


def _plot_single_model_outputs_inputs(tdis, plot_dir, list_file, hds_array, output_data, model_nm, input_data,
                                      tick_per=100):
    plot_dir.mkdir(exist_ok=True)
    plot_list_failures(list_file, plot_dir)
    _plot_spatial_heads(all_hds=hds_array, plot_dir=plot_dir)
    all_hds = hds_array
    all_hds[all_hds < -666] = np.nan

    # steady state moraine heads
    idx = np.where(tdis.steady)[0][0]
    plot_lake_moraine_smoothed_areas(all_hds, plot_dir, index=idx,
                                     nm='Model heads at Steady state\n(1m contours)',
                                     svnm='steady_state')
    # max_lake (at g40_0415) moraine heads
    idx = output_data['hds_g40_0415'].argmax()
    plot_lake_moraine_smoothed_areas(all_hds, plot_dir, index=idx,
                                     nm='Model heads at lake max\n(1m contours)',
                                     svnm='lake_max')
    # min_lake (at g40_0415) moraine heads
    idx = output_data['hds_g40_0415'].argmin()
    plot_lake_moraine_smoothed_areas(all_hds, plot_dir, index=idx, nm='Model heads at lake min\n(1m contours)',
                                     svnm='lake_min')

    figs, axs = _plot_output_data(tdis, output_data, model_nm=model_nm, tick_per=tick_per)
    for k, fig in figs.items():
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'{k}.png'))
    plt.close('all')

    _plot_moraine_cross_sections(
        all_hds, plot_dir,
        indexs=[
            np.where(tdis.steady)[0][0],
            output_data['hds_g40_0415'].argmax(),
            output_data['hds_g40_0415'].argmin()
        ],
        nms=[
            'Model heads at Steady state',
            'Model heads at lake max',
            'Model heads at lake min'
        ],
        lss=[
            'solid',
            ':',
            '--',
        ],
        svnm='')

    # plot key input data
    figs, axs = _plot_input_data(tdis=tdis, input_data=input_data, model_nm=model_nm, tick_per=tick_per)
    for k, fig in figs.items():
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'{k}.png'))
    plt.close('all')


def _plot_moraine_cross_sections(all_hds, plot_dir, indexs, nms, lss, svnm):
    plot_dir = Path(plot_dir)
    # 3 sections
    sections = dict(
        hawea_town=([1303469.330938903, 1303500.6849574826],
                    [5053811.5626237625, 5052580.91739451]),
        cemetary=([1305366.221641333, 1305885.8342329387],
                  [5053896.7875498105, 5052653.428848469]),
        mid=([1306245.1774635299, 1307072.3634277452],
             [5054731.313333146, 5053449.757613939]),
        off=([1307268.289996199, 1305935.0975676565],
             [5055058.288127857, 5053561.239646644]),
    )
    fig, ((ax1, ax2), (ax3, loc_ax)) = plt.subplots(nrows=2, ncols=2, figsize=(14, 14))
    loc_ax.get_shared_x_axes().remove(loc_ax)
    loc_ax.get_shared_y_axes().remove(loc_ax)

    loc_cond = get_low_cond_array()
    loc_cond = loc_cond.astype(float)
    loc_cond[loc_cond == 0] = np.nan
    first = True
    from matplotlib.patches import Patch
    handles = [Patch(facecolor='saddlebrown', label='Low conductivity')]
    from matplotlib.lines import Line2D
    for idx, nm, ls in zip(indexs, nms, lss):
        handles.append(Line2D([0], [0], linestyle=ls, label=f'$H_20$ table - {nm}', linewidth=2))
        for (sect_key, ax, letter) in zip(['hawea_town', 'cemetary', 'mid'], [ax1, ax2, ax3], ['A', 'B', 'C']):
            if first:
                no_flow_layer = 0
            else:
                no_flow_layer = None
            x_coords, y_coords = sections[sect_key]
            smt.plot.plt_descrete_slice(loc_cond,
                                        names={1: 'low conductivity'}, colors={1: 'saddlebrown'}, x_coords=x_coords,
                                        y_coords=y_coords, plot_locator=False, ax=ax, alpha=0.5, plt_legend=False)
            smt.plot.plt_slice_watertable(all_hds[idx], x_coords=x_coords, y_coords=y_coords,
                                          plt_background=False, plt_layer_slice=True,
                                          plot_locator=True, ax=ax, locator_ax=loc_ax,
                                          background_alpha=0.5, no_flow_layer=no_flow_layer, locator_lim_pad=None,
                                          lay_slice_kwargs=None,
                                          slice_letter=letter, plt_basemap=first, color='b', linewidth=2, ls=ls)
            first = False
    loc_ax.legend(handles=handles)
    loc_ax.set_ylim([5.051e6, 5.058e6])
    loc_ax.set_xlim([1.301e6, 1.308e6])
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath(f'xsections_{svnm}.png'))


def _plot_input_data(tdis, input_data, model_nm, figs=None, axs=None, ls=None, tick_per=50):
    """
    to plot multiple verions pass figs, axs from perivous time
    :param input_data:
    :param model_nm:
    :param figs:
    :param axs:
    :param ls:
    :return:
    """
    if ls is None:
        ls = 'solid'
    if figs is None:
        assert axs is None
        figs, axs = _setup_input_plots()
    else:
        assert isinstance(figs, dict)
        assert isinstance(axs, dict)

    # do the plotting

    fig, use_axs = figs['lake_rch'], axs['lake_rch']
    plot_keys = ['lake', 'total_rch', 'dryland_rch', 'irr_rch']

    for ax, k in zip(use_axs, plot_keys):
        ax.plot(input_data.index, input_data[k], color='k', ls=ls, label=model_nm)
        ax.set_title(k)
        ax.legend()

    fig, use_axs = figs['hill'], axs['hill']
    plot_keys = ['hill_total', 'hill_maungawera', 'hill_flat_west', 'hill_flat_east', 'hill_terrace_east',
                 'hill_south_east']
    for ax, k in zip(use_axs, plot_keys):
        ax.plot(input_data.index, input_data[k], color='k', ls=ls, label=model_nm)
        ax.set_title(k)
        ax.legend()

    # manage ax ticks...
    for v in axs.values():
        for ax in v:
            ax.set_xticks([e for i, e in enumerate(tdis.pers) if i % tick_per == 0])
            all_labs = [f'{p}: {d.date().isoformat()}' for p, d in zip(tdis.pers, pd.Series(tdis.per_middle_dates))]
            ax.set_xticklabels([e for i, e in enumerate(all_labs) if i % tick_per == 0], rotation=-60)

    return figs, axs


def _setup_input_plots():
    figs, axs = {}, {}
    use_plots = []
    fig, use_axs = plt.subplots(2, 1, figsize=(14, 14), sharex=True)
    use_plots.extend(use_axs.flatten())
    fig2, use_axs = plt.subplots(2, 1, figsize=(14, 14), sharex=True)
    use_plots.extend(use_axs.flatten())
    figs['lake_rch'] = fig
    figs['lake_rch2'] = fig2
    axs['lake_rch'] = use_plots
    # lake	total_rch	dryland_rch	irr_rch

    use_plots = []
    fig, use_axs = plt.subplots(3, 1, figsize=(14, 14), sharex=True)
    use_plots.extend(use_axs.flatten())
    fig2, use_axs = plt.subplots(3, 1, figsize=(14, 14), sharex=True)
    use_plots.extend(use_axs.flatten())
    figs['hill'] = fig
    figs['hill2'] = fig2
    axs['hill'] = use_plots
    return figs, axs
    # hill_maungawera	hill_flat_west	hill_flat_east	hill_terrace_east	hill_south_east	hill_total


def _plot_output_data(tdis, output_data, model_nm, figs=None, axs=None, ls=None, tick_per=100, aq_pen=None):
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

    # hds groups
    for g in indicator_wells.group.unique():
        fig, use_axs = figs[f'hds_{g}'], axs[f'hds_{g}']
        temp_wells = indicator_wells.loc[indicator_wells.group == g]
        colors = smt.plot.get_colors(range(len(temp_wells)))
        for ax, nm, c in zip(use_axs, temp_wells.index, colors):
            ax.plot(output_data.index, output_data[f'hds_{nm}'], color=c, ls=ls, label=f'{nm}-{model_nm}')
            if aq_pen is not None:
                aq_pen = np.atleast_1d(aq_pen)
                for i, pen in enumerate(aq_pen):
                    labs, hands = ax.get_legend_handles_labels()
                    if f'adequate pen. from {pen}' not in labs:
                        p = get_adiquate_penetration(f'hds_{nm}', pen)
                        ax.axhline(p, label=f'adequate pen. from {pen}', ls=(0, (3, 10, 1, 10, 1, 10)),
                                   color='k', alpha=0.5)
                        # add text label
                        if i % 2 == 0:
                            idx = -1
                        else:
                            idx = 0
                        ax.text(output_data.index[idx], p, pen, color='k')
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
        ax.plot(output_data.index, output_data[key], ls=ls, label=f'{model_nm}')
        ax.set_title(print_key)
        ax.legend()

    # manage ax ticks...
    all_labs = []
    for p, d, stdy in zip(tdis.pers, pd.Series(tdis.per_middle_dates), tdis.steady):
        if stdy:
            all_labs.append(f'{p}: steady')

        else:
            all_labs.append(f'{p}: {d.date().isoformat()}')

    for k, v in axs.items():
        if 'hds' in k:
            for ax in v:
                ax.set_xticks([e for i, e in enumerate(tdis.pers) if i % tick_per == 0])
                ax.set_xticklabels([])
                ax.set_xlim(min(tdis.pers) - 1, max(tdis.pers) + 1)
            ax = v[-1]
            ax.set_xticks([e for i, e in enumerate(tdis.pers) if i % tick_per == 0])
            ax.set_xticklabels([e for i, e in enumerate(all_labs) if i % tick_per == 0], rotation=-30)

        else:
            for ax in v:
                ax.set_xticks([e for i, e in enumerate(tdis.pers) if i % tick_per == 0])
                ax.set_xticklabels([e for i, e in enumerate(all_labs) if i % tick_per == 0], rotation=-30)

    return figs, axs


def _setup_output_plots(indicator_wells, hds_only=False):
    figs, axs = {}, {}

    # indicator_hds_groups  (incl regular heads)
    for g in indicator_wells.group.unique():
        temp_wells = indicator_wells.loc[indicator_wells.group == g]
        num = len(temp_wells)
        fig = plt.Figure(figsize=(16, 14))
        fig.suptitle(f'Hds {g}')
        gs = fig.add_gridspec(nrows=num, ncols=2, width_ratios=(2, 1))
        temp_axs = []
        temp_axs.append(fig.add_subplot(gs[0, 0]))
        temp_axs.extend([fig.add_subplot(gs[i, 0]) for i in range(1, num)])
        figs[f'hds_{g}'] = fig
        axs[f'hds_{g}'] = temp_axs

        # make/ plot locator (color for well, ls for scenario)
        temp_ax = fig.add_subplot(gs[:, 1])
        smt.plot.plt_basemap(ax=temp_ax, no_flow_layer=0)
        colors = smt.plot.get_colors(range(num))
        for c, (nm, x, y) in zip(colors, temp_wells[['nztmx', 'nztmy']].itertuples(True, None)):
            temp_ax.scatter(x, y, color=c, label=nm, s=100)
        temp_ax.legend()
        smt.plot.set_plot_lims_padded(temp_wells.nztmx, temp_wells.nztmy, 1000, temp_ax)

    if hds_only:
        return figs, axs
    # river fluxes
    use_axs = []
    fig, temp_axs = plt.subplots(3, 1, sharex=True, figsize=(14, 14))
    use_axs.extend(temp_axs.flatten())
    fig2, temp_axs = plt.subplots(3, 1, sharex=True, figsize=(14, 14))
    use_axs.extend(temp_axs.flatten())
    figs['river_flux'] = fig
    figs['river_flux2'] = fig2
    axs['river_flux'] = use_axs

    # zone budget plots
    use_axs = []
    fig, temp_axs = plt.subplots(3, 1, sharex=True, figsize=(14, 14))
    use_axs.extend(temp_axs.flatten())
    fig1, temp_axs = plt.subplots(3, 1, sharex=True, figsize=(14, 14))
    use_axs.extend(temp_axs.flatten())
    fig2, temp_axs = plt.subplots(3, 1, sharex=True, figsize=(14, 14))
    use_axs.extend(temp_axs.flatten())
    figs['zone_budget'] = fig
    figs['zone_budget1'] = fig1
    figs['zone_budget2'] = fig2
    axs['zone_budget'] = use_axs
    return figs, axs


key_output_data_file_name = 'output_dataset.csv'
key_input_data_file_name = 'key_input_data.csv'
key_all_well_data_file_name = 'all_well_output_dataset.csv'


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


def _extract_zone_budget_fluxes(nper, output_data, cbc_file, outdir):
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
        output_data.loc[range(nper), f'{from_zone}_to_{to_zone}'] = tot.values


def extract_input_data(ghb_data, rch_data, well_data, tdis):
    """
    extract key into data
    :param ghb_data: ghb data stress period
    :param rch_data: rch stress period data
    :param well_data: well stress preiod data
    :param tdis: time dis object for run
    :return:
    """

    ghb_data = deepcopy(ghb_data)
    rch_data = deepcopy(rch_data)
    well_data = deepcopy(well_data)

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
        temp = smt.io.df_to_array(temp, 'i', True, duplicate_action=np.nansum)
        temp = np.isfinite(temp)
        use_data = [smt.io.select_df_from_idx_array(pd.DataFrame(well_data[p]), temp, ).flux.sum() for p in tdis.pers]
        outdata.loc[:, f'hill_{g}'] = use_data
        hill_names.append(f'hill_{g}')
    outdata.loc[:, 'hill_total'] = outdata.loc[:, hill_names].sum(axis=1)

    return outdata


def compare_scenarios(outdir, tdis, data_dirs, model_names, lss, tickper=100, usepers=None, aq_pen=None):
    """
    compare multiple models (models id by linestyle)
    must have same timedis
    :param outdir: directory to save files
    :param tdis: TimeDis
    :param data_dirs: directories with the output data and input data list like
    :param model_names: model names (for legends) list like
    :param lss: linestyles list like
    :return:
    """
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    assert isinstance(data_dirs, dict)
    assert isinstance(lss, dict)
    assert isinstance(tdis, TimeDis)
    assert set(data_dirs.keys()) == set(model_names) == set(lss.keys())
    output_figs, output_axs = None, None
    input_figs, input_axs = None, None
    if usepers is not None:
        assert set(usepers).issubset(tdis.pers)
        use_tids = tdis.get_sub_tids(usepers)
    else:
        use_tids = tdis

    for mn in model_names:
        dd, ls = data_dirs[mn], lss[mn]
        dd = Path(dd)
        input_data = pd.read_csv(dd.joinpath(key_input_data_file_name), index_col=0)
        output_data = pd.read_csv(dd.joinpath(key_output_data_file_name), index_col=0)

        if usepers is not None:
            input_data = input_data.loc[sorted(usepers)]
            input_data.index = range(len(input_data))
            output_data = output_data.loc[sorted(usepers)]
            output_data.index = range(len(output_data))

        output_figs, output_axs = _plot_output_data(use_tids, output_data=output_data, model_nm=mn, figs=output_figs,
                                                    axs=output_axs, ls=ls, tick_per=tickper, aq_pen=aq_pen)
        input_figs, input_axs = _plot_input_data(use_tids, input_data=input_data, model_nm=mn, figs=input_figs,
                                                 axs=input_axs, ls=ls, tick_per=tickper)
    # savefigs
    figs = {}
    figs.update(input_figs)
    figs.update(output_figs)
    for k, fig in figs.items():
        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{k}.png'))
    plt.close('all')


def _setup_qq_plots(indicator_wells):
    figs, axs, legend_axs = {}, {}, {}

    # indicator_hds_groups  (incl regular heads)
    for g in indicator_wells.group.unique():
        temp_wells = indicator_wells.loc[indicator_wells.group == g]
        num = len(temp_wells)
        fig = plt.Figure(figsize=(16, 14))
        fig.suptitle(f'Hds {g}')
        gs = fig.add_gridspec(nrows=num, ncols=2, width_ratios=(2, 1))
        temp_axs = []
        temp_axs.append(fig.add_subplot(gs[0, 0]))
        temp_axs.extend([fig.add_subplot(gs[i, 0]) for i in range(1, num)])
        figs[f'hds_{g}'] = fig
        axs[f'hds_{g}'] = temp_axs

        # make/ plot locator (color for well, ls for scenario)
        temp_ax = fig.add_subplot(gs[0, 1])
        temp_ax.set_xticks([])
        temp_ax.set_yticks([])
        temp_ax.spines["top"].set_visible(False)
        temp_ax.spines["right"].set_visible(False)
        temp_ax.spines["left"].set_visible(False)
        temp_ax.spines["bottom"].set_visible(False)
        legend_axs[f'hds_{g}'] = temp_ax

        temp_ax = fig.add_subplot(gs[1:, 1])
        smt.plot.plt_basemap(ax=temp_ax, no_flow_layer=0)
        colors = smt.plot.get_colors(range(num))
        for c, (nm, x, y) in zip(colors, temp_wells[['nztmx', 'nztmy']].itertuples(True, None)):
            temp_ax.scatter(x, y, color=c, label=nm, s=100)
        temp_ax.legend()
        smt.plot.set_plot_lims_padded(temp_wells.nztmx, temp_wells.nztmy, 1000, temp_ax)

    return figs, axs, legend_axs


def quantile_plots(scenarios, senario_ls, outdir, usepers=None, aq_pen=None):
    assert set(scenarios.keys()) == set(senario_ls.keys())
    indicator_wells = get_indicator_well_locs()
    figs, axs, legend_axs = _setup_qq_plots(indicator_wells)
    scens = sorted(list(scenarios.keys()))

    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)

    # setup data
    scen_data = {}
    for scen in scens:
        t = pd.read_csv(Path(scenarios[scen]).joinpath(key_output_data_file_name), index_col=0)
        if usepers is not None:
            t = t.loc[usepers]
        scen_data[scen] = t

    # hds groups
    for g in indicator_wells.group.unique():
        fig, use_axs, leg_ax = figs[f'hds_{g}'], axs[f'hds_{g}'], legend_axs[f'hds_{g}']
        temp_wells = indicator_wells.loc[indicator_wells.group == g]
        colors = smt.plot.get_colors(range(len(temp_wells)))
        for ax, nm, c in zip(use_axs, temp_wells.index, colors):

            quantiles = np.arange(1, 100)
            for scen in scens:
                data = scen_data[scen][f'hds_{nm}'].dropna()
                plt_values = [np.nanpercentile(data, p) for p in quantiles]

                ls = senario_ls[scen]
                ax.plot(quantiles, plt_values, color=c, ls=ls, label=f'{scen}')
                if aq_pen is not None:
                    aq_pen = np.atleast_1d(aq_pen)
                    for i, pen in enumerate(aq_pen):
                        hands, labs = ax.get_legend_handles_labels()
                        if f'adequate pen. from {pen}' not in labs:
                            p = get_adiquate_penetration(f'hds_{nm}', pen)
                            ax.axhline(p, label=f'adequate pen. from {pen}', ls=(0, (3, 10, 1, 10, 1, 10)),
                                       color='k', alpha=0.5)
                            # add text label
                            if i % 2 == 0:
                                idx = -1
                            else:
                                idx = 0
                            ax.text(quantiles[idx], p, pen, color='k')
                ax.legend()
    for k, fig in figs.items():
        fig.supxlabel(f'percentile')
        fig.supylabel(f'head (m)')
        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{k}.png'))
    plt.close('all')


def q_qplots(base_scen_dir, outdir, base_scen_name, other_scens: dict, other_scen_ls: dict,
             usepers=None):
    """

    :param base_scen_dir: directory for the base data
    :param base_scen_name: name of the base scenario
    :param other_scens: dict  {name: output directory for another scenario}
    :param other_scen_ls:  dict  {name: linestyle to use for plot}
    :param outdir
    :return:
    """
    assert set(other_scens.keys()) == set(other_scen_ls.keys())
    indicator_wells = get_indicator_well_locs()
    figs, axs, legend_axs = _setup_qq_plots(indicator_wells)
    scens = sorted(list(other_scens.keys()))

    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)

    # setup data
    base_data = pd.read_csv(Path(base_scen_dir).joinpath(key_output_data_file_name), index_col=0)
    scen_data = {}
    for scen in scens:
        t = pd.read_csv(Path(other_scens[scen]).joinpath(key_output_data_file_name), index_col=0)

        if usepers is not None:
            t = t.loc[usepers]
        scen_data[scen] = t

    # hds groups
    for g in indicator_wells.group.unique():
        fig, use_axs, leg_ax = figs[f'hds_{g}'], axs[f'hds_{g}'], legend_axs[f'hds_{g}']
        temp_wells = indicator_wells.loc[indicator_wells.group == g]
        colors = smt.plot.get_colors(range(len(temp_wells)))
        for ax, nm, c in zip(use_axs, temp_wells.index, colors):

            quantiles = np.arange(1, 100)
            base_values = [np.nanpercentile(base_data[f'hds_{nm}'], q) for q in quantiles]
            ax.plot(quantiles, quantiles, color='k', alpha=0.5, label='1:1')
            ax.fill_between(quantiles, np.zeros(quantiles.shape), quantiles, color='skyblue', alpha=0.3,
                            label=('scenario is less likely to have groundwater levels\n'
                                   'as low or lower than the nth percentile\n'
                                   'of the base scenario'))
            ax.fill_between(quantiles, quantiles, np.zeros(quantiles.shape) + 100, color='lightcoral', alpha=0.3,
                            label=('scenario is more likely to have groundwater levels\n'
                                   'as low or lower than the nth percentile\n'
                                   'of the base scenario'))
            for scen in scens:
                data = scen_data[scen][f'hds_{nm}'].dropna()
                plt_values = [percentileofscore(data, e) for e in base_values]
                scen_values = [np.nanpercentile(data, p) for p in plt_values]

                ls = other_scen_ls[scen]
                ax.plot(quantiles, plt_values, color=c, ls=ls, label=f'{scen}')
        leg_ax.legend(*ax.get_legend_handles_labels(), loc='upper left')
    for k, fig in figs.items():
        fig.supxlabel(f'{base_scen_name} percentile')
        fig.supylabel(f'scenario percentile of {base_scen_name} value')
        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{k}.png'))
    plt.close('all')


def get_adiquate_penetration(well, base_model, recalc=False):
    locs = get_indicator_well_locs()
    locs.index = [f'hds_{e}' for e in locs.index]
    assert well in locs.index or well == 'all', f'got weird well: {well}'
    assert base_model in ['long_current', 'long_nat', 'optimised']
    save_path = processed_scen_dir.joinpath(f'adequate_penetration_{base_model}.csv')
    if save_path.exists() and not recalc:
        data = pd.read_csv(save_path, index_col=0)['adequate_pen']
        if well == 'all':
            return data
        else:
            return data.loc[well]

    output_data = pd.read_csv(
        proj_root.joinpath('Scenarios/model_info_scen_results', base_model, key_output_data_file_name))
    output_data = output_data.drop(index=[0])
    output_data.loc[:, 'date'] = pd.to_datetime(output_data['date'])
    output_data.loc[:, 'year'] = output_data['date'].dt.year
    output_data.loc[:, 'month'] = output_data['date'].dt.month

    # remove partial years!
    drop_years = []
    for y in output_data.year.unique():
        got_months = output_data.loc[output_data.year == y, 'month']
        if set(got_months) != set(range(1, 13)):
            drop_years.append(y)
    output_data = output_data.loc[~np.in1d(output_data.year, drop_years)]
    annual_mean = output_data.groupby('year').mean()
    annual_min = output_data.groupby('year').quantile(0.10)
    annual_max = output_data.groupby('year').quantile(0.90)
    t = 3 * (annual_max.mean() - annual_min.mean())
    t[t > 15] = 15  # basically just addresses the weirdness at buterfield
    t[t < 1] = 1
    t = annual_mean.mean() - t
    data = pd.Series(index=locs.index, name='adequate_pen')
    data.loc[:] = t.loc[data.index]

    data.to_csv(save_path)
    if well == 'all':
        return data
    else:
        return data.loc[well]


def test_qqplot():
    q_qplots(
        base_scen_dir='/home/matt_dumont/PycharmProjects/Z22031HAW_hawea-model/Scenarios/model_info_scen_results/long_nat',
        outdir=Path.home().joinpath('unbacked/temp/test_plots'),
        base_scen_name='long_nat',
        other_scens={
            'long_current': '/home/matt_dumont/PycharmProjects/Z22031HAW_hawea-model/Scenarios/model_info_scen_results/long_current',
            'lake_only_var': '/home/matt_dumont/PycharmProjects/Z22031HAW_hawea-model/Scenarios/model_info_scen_results/lake_only_var'

        },
        other_scen_ls={

            'long_current': ':',
            'lake_only_var': '--',

        })


def test_with_base_model():
    outdir = Path.home().joinpath('unbacked/temp/test_outputs')
    if outdir.exists():
        shutil.rmtree(outdir)
    base_model_path = Path('/home/matt_dumont/unbacked/hawea/3d_v1d/init_3d_v1d/Optimisations/Final_opt_model/')
    use_path = Path.home().joinpath('unbacked/temp/test_model')
    if use_path.exists():
        shutil.rmtree(use_path)
    shutil.copytree(base_model_path, use_path)

    # generate input data in the use path
    print('creating key input data')
    from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
    from optimisation.optimisation_period import tdis as opt_tids
    from model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    temp = extract_input_data(ghb_data=get_ghb_data(opt_tids),
                              rch_data=get_rch_data(opt_tids, rch_param),
                              well_data=get_well_data(opt_tids, hill_param, race_param),
                              tdis=opt_tids)
    temp.to_csv(use_path.joinpath(key_input_data_file_name))

    # generate outputs
    print('generating outputs')
    generate_scenario_outputs(use_path,
                              'final_opt_model', outdir=outdir,
                              tdis=opt_tids)


def test_3d_xsections():
    all_hds = np.load('/home/matt_dumont/unbacked/temp/test_outputs/final_opt_model_hds.npz')['heads']
    _plot_moraine_cross_sections(all_hds, None, [1, 4, 8], ['1', '2', '3'], ['solid', ':', '--'], 'tst')


if __name__ == '__main__':
    get_adiquate_penetration('all', 'long_current', True)
    get_adiquate_penetration('all', 'optimised', True)
    get_adiquate_penetration('all', 'long_nat', True)

    test_qqplot()
    raise NotImplementedError
    _get_indicator_wells(True)
    tm = time.time()
    test_with_base_model()
    print(time.time() - tm, 'seconds to run')
    pass
