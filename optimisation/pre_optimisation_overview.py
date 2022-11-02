"""
created matt_dumont 
on: 19/09/22
"""
import kslcore
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from pathlib import Path
from model_build.project_model_tools import smt, get_starting_heads
from model_build.utils import get_colors
from model_parameterisation.pilot_points import get_pilot_point_locations, interpolate_kh_pilot_points, \
    interpolate_kh_pilot_points, get_param_zones, get_lake_array
from model_parameterisation.static_params import *
from model_tools.model_plotting import plot_spd, first, last, FakePath
from model_build.get_boundary_condition_data import get_well_data, get_rch_data, get_ghb_data, get_riv_data
from model_parameterisation.inital_parametersiation import *
from optimisation.optimisation_period import tdis
from project_base import proj_root, base_model_build_data_dir
from model_build.supporting_data_analysis import *
from model_build.zones import get_model_zones
from targets_and_sensitive_sites.head_targets import plot_head_targets, get_high_freq_head_targets, \
    get_low_freq_head_targets, get_2011_piezo_survey, get_single_head_targets, get_all_hds_targets
from targets_and_sensitive_sites.riv_gain_loss_targets import get_riv_target_locs, get_hawea_gain_loss_targets
from optimisation.determine_opt_start import get_opt_start_stop

extension = '.pdf'
if extension == '.png':
    save_path = proj_root.joinpath('optimisation/pre_optimisation_plots_png')
elif extension == '.pdf':
    save_path = proj_root.joinpath('optimisation/pre_optimisation_plots_pdf')
else:
    raise ValueError('nope')

save_path.mkdir(exist_ok=True)


def plot_parameterisation(save=False):
    outdir = save_path.joinpath('parameterisation')
    outdir.mkdir(exist_ok=True)
    # parameter overview
    parameters = {
        'Hillside inflow multiplier': ('Wel', get_hillslope_multiplier()),
        'Race loss multiplier': ('Wel', get_race_multiplier()),
        'River Conductance': ('Riv', get_initial_riv_conductance()),
        'Specific Yeild': ('Upw', get_inital_sy()),
        'Conductivity': ('Upw', get_inital_kh()),
        'Recharge Multiplier': ('Rch', get_initial_rch_mult())
    }
    static_params = {
        'Lake Sy': lake_sy,
        'SS': ss,
        'VKA': vka,
        'Lake Conductance': lake_conduct
    }
    param_out = pd.DataFrame(columns=['Parameter type', 'Static', 'Package', 'Name', 'Initial', 'Min', 'Max'])
    out = []
    for k, v in static_params.items():
        temp = param_out.copy()
        val = (k, 'True', 'Upw', 'all', v, 'na', 'na')
        temp.loc[1, ['Parameter type', 'Static', 'Package', 'Name', 'Initial', 'Min', 'Max']] = val
        out.append(temp)
    for k, (pkg, (params)) in parameters.items():
        num = len(params)
        temp = pd.DataFrame(index=range(num),
                            columns=['Parameter type', 'Static', 'Package', 'Name', 'Initial', 'Min', 'Max'])
        names = params.keys()
        print(k)
        init, minn, maxx = np.array([[i, n, x] for n, (i, x) in params.values()]).transpose()
        temp.loc[range(num), 'Parameter type'] = k
        temp.loc[range(num), 'Static'] = False
        temp.loc[range(num), 'Package'] = pkg
        temp.loc[range(num), ['Name', 'Initial', 'Min', 'Max']] = list(zip(names, init, minn, maxx))
        out.append(temp)
    out = pd.concat(out).reset_index(drop=True)
    if save:
        if extension == '.pdf':
            import pdfkit as pdf
            tempf = Path.home().joinpath('Downloads/temp.html')
            out.to_html(tempf)
            new = outdir.joinpath('parameter_overview.pdf')
            pdf.from_file(str(tempf), str(new))
        if extension == '.png':
            out.to_csv(outdir.joinpath('parameter_overview.csv'))

    # river conductance
    riv_data = get_river_loc_data()
    base_names = riv_data.param.unique()
    riv_data.loc[:, 'map_param'] = riv_data.param.replace({k: i for i, k in enumerate(base_names)})
    zone_colors = get_colors(base_names)
    cmap = ListedColormap(zone_colors)
    fig, (ax1, legendax) = plt.subplots(ncols=2, gridspec_kw={'width_ratios': [5, 1], },
                                        figsize=(10, 9))
    smt.plot.plt_matrix(smt.io.df_to_array(riv_data, 'map_param'), no_flow_layer=0, base_map=True,
                        title='River conductance Zones', cmap=cmap, color_bar=False, ax=ax1, alpha=1)
    handles, labels = [Patch(facecolor='w')], ['name: (initial, (min, max)']
    riv = get_initial_riv_conductance()
    for c, n in zip(zone_colors, base_names):
        handles.append(Patch(facecolor=c))
        labels.append(f'{n.capitalize()} River Cond.: {riv[n]}')
    legendax.legend(handles, labels)
    legendax.set_xticks([])
    legendax.set_yticks([])
    legendax.spines["top"].set_visible(False)
    legendax.spines["right"].set_visible(False)
    legendax.spines["left"].set_visible(False)
    legendax.spines["bottom"].set_visible(False)
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'river_conductance{extension}'))

    # plot_example_rbf_interp
    pps = get_pilot_point_locations()
    options = [10, 50, 100, 200, 300, 500]
    np.random.seed(1656)
    a = np.random.choice(options)
    np.random.seed(155683)
    b = np.random.choice(options)
    np.random.seed(165653)
    c = np.random.choice(options)
    kh_data = {
        'sandy': a,
        'mang': b,
        'lake_conductance': c,
    }

    ncols = 3
    fig1, axs1 = plt.subplots(ncols=ncols, figsize=(16, 9))
    np.random.seed(35873)
    randoms = np.random.choice(options, len(pps))
    for i, r in zip(pps.index, randoms):
        kh_data[i] = r

    kh, df = interpolate_kh_pilot_points(kh_data, return_df=True)
    smt.plot.plt_matrix(kh[0], base_map=True, no_flow_layer=0, title=f'real kh', ax=axs1[0], vmin=0,
                        )
    smt.plot.plt_matrix(np.log10(kh[0]), base_map=True, no_flow_layer=0, title=f'log10 kh', ax=axs1[1], vmin=0, vmax=3)
    smt.plot.plt_matrix(kh[0] * np.nan, base_map=True, no_flow_layer=0, title='data', ax=axs1[2], color_bar=False)
    ax = axs1[2]
    ax.scatter(df.x, df.y)
    for x, y, s in df.loc[:, ['x', 'y', 'value']].itertuples(False, None):
        ax.text(x, y, str(round(s, 2)))
    fig1.suptitle('example RBF multiquadric interpolation')
    fig1.tight_layout()
    if save:
        fig1.savefig(outdir.joinpath(f'example_rbf{extension}'))

    # inital transmisivity
    khs = get_inital_kh()
    lake = get_lake_array()
    thick = get_starting_heads()[0] - smt.get_bottoms()[0]
    kh = np.full(smt.model_shape[1:], khs['sandy'][0])
    kh[np.isfinite(lake)] = khs['lake_conductance'][0]

    thick[smt.get_no_flow(0) != 1] = np.nan
    fig, ax = smt.plot.plt_matrix(thick, title='Initial Transmissivity', base_map=True,
                                  no_flow_layer=0, contour=True, label_contours=True,
                                  contour_levels=[0, 10, 20, 30, 40, 50, 60, 80, 100])
    fig.tight_layout()

    if save:
        fig.savefig(outdir.joinpath(f'inital_trans{extension}'))

    # parameter zones
    pilot_locs = get_pilot_point_locations()
    zone_plotter = smt.get_model_zeros() * np.nan
    zone_plotter[np.isfinite(get_lake_array())] = 0
    param_zones = get_param_zones()
    zone_plotter[param_zones == 1] = 1
    zone_plotter[param_zones == 2] = 2

    # plot zones
    zone_colors = ['b', 'tan', 'thistle']
    zone_names = ['lake_conductance', 'sandy', 'mang']
    cmap = ListedColormap(zone_colors)

    fig, (ax1, legendax) = plt.subplots(ncols=2, gridspec_kw={'width_ratios': [5, 1], },
                                        figsize=(10, 9))
    fig, ax = smt.plot.plt_matrix(zone_plotter, title='Kh / sy zones and pilot points', ax=ax1, base_map=True,
                                  cmap=cmap, color_bar=False, no_flow_layer=0)
    handles, labels = [Patch(facecolor='w')], ['name: (initial, (min, max)']
    for c, n in zip(zone_colors, zone_names):
        handles.append(Patch(facecolor=c))
        labels.append(f'{n.capitalize()} zone: {khs[n]}')

    # plot pilot points
    groups = pilot_locs.group.unique()
    markersize = 3
    marker = 'o'
    for group, c in zip(groups, get_colors(groups)):
        temp = pilot_locs.loc[pilot_locs.group == group]
        ax.scatter(temp.x, temp.y, color=c, marker='o')
        handles.append(Line2D([0], [0], marker=marker, color='w',
                              markerfacecolor=c, markersize=markersize * 5))
        labels.append(f'PP Group: {group.capitalize()}')

    legendax.legend(handles, labels)
    legendax.set_xticks([])
    legendax.set_yticks([])
    legendax.spines["top"].set_visible(False)
    legendax.spines["right"].set_visible(False)
    legendax.spines["left"].set_visible(False)
    legendax.spines["bottom"].set_visible(False)
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'kh_sy_params{extension}'))

    # plot rch mult pilot points
    rch_pilots = get_rch_pilot_point_locations()
    fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
    ax.scatter(rch_pilots.x, rch_pilots.y, color='r', marker='o')
    ax.set_title('Rch multiplier points (linear interpolation)')
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'kh_sy_params{extension}'))



def plot_thickness_top_bot(save=False):
    data = {'Model tops': smt.get_tops()[0],
            'Model bottoms': smt.get_bottoms()[0],
            'Model thickness': smt.get_thickness()[0]}

    for k, v in data.items():
        dist = 20
        ibound = smt.get_no_flow(0)
        v[ibound != 1] = np.nan
        contours = range(int(np.nanmin(v) // dist * dist), int(np.nanmax(v) // dist * dist), dist)
        fig, ax = smt.plot.plt_matrix(v, title=k, no_flow_layer=0,
                                      base_map=True, contour=True, label_contours=True,
                                      contour_levels=contours)
        if save:
            outpath = save_path.joinpath('model_structure', f'{k}{extension}')
            outpath.parent.mkdir(exist_ok=True)
            fig.savefig(outpath)


def plot_all_spd(save=False):
    if save:
        outdir = save_path.joinpath('stress_period_data')
        outdir.mkdir(exist_ok=True)
    else:
        outdir = FakePath()
    # well boundary conditions
    well_data = get_well_data(tdis, hill_param=get_hillslope_multiplier(True), race_param=get_race_multiplier(True),
                              return_unique_spd=True)
    for k, v in well_data.items():
        plot_spd(v, smt, tdis, is_array=False, key='flux', func=np.nansum, title=f'wel: {k}',
                 outpath=outdir.joinpath(f'well_{k}_time{extension}'))

    # recharge
    plot_spd(get_rch_data(tdis, rch_param=get_initial_rch_mult(True)),
             smt, tdis, is_array=True, key='total LSR',
             func=np.nansum, mult_by_area=True, title='recharge',
             outpath=outdir.joinpath(f'rch_time{extension}'))

    # lake
    plot_spd(get_ghb_data(tdis), smt, tdis,
             func=np.nanmean,
             key='bhead', title='lake heads', outpath=outdir.joinpath(f'lake_time{extension}'))

    # river
    plot_spd(get_riv_data(tdis, get_initial_riv_conductance(True)), smt, tdis,
             func=first, key='stage', title='first river cell stage',
             outpath=outdir.joinpath(f'riv_first_cell_time{extension}'))
    plot_spd(get_riv_data(tdis, get_initial_riv_conductance(True)), smt, tdis,
             func=last, key='stage', title='last river cell stage',
             outpath=outdir.joinpath(f'riv_last_cell_time{extension}'))

    # river height and stage data
    plt_stg_data = get_river_stage_data(None, None).dropna().describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95])
    k_cs = ['min', '5%', '25%', '50%', '75%', '95%', 'max', ]
    colors = get_colors(k_cs, cmap_name='winter')
    temp_data = get_river_loc_data()
    tops = smt.get_tops()[0]
    bottoms = smt.get_bottoms()[0]
    temp_data.loc[:, 'model_top'] = tops[temp_data.loc[:, 'i'], temp_data.loc[:, 'j']]
    temp_data.loc[:, 'model_bot'] = bottoms[temp_data.loc[:, 'i'], temp_data.loc[:, 'j']]
    hawea_clutha_divide = temp_data.loc[temp_data.rname == 'hawea', 'dist'].max()
    temp_data.loc[temp_data.rname == 'clutha', 'dist'] += hawea_clutha_divide
    temp_data.sort_values('dist', inplace=True)
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_title('River Profile')
    ax.plot(temp_data.dist, temp_data.rbot, c='y', label='river_bottom_fixed')
    ax.plot(temp_data.dist, temp_data.model_bot, c='firebrick', label='model_bottom')
    ax.plot(temp_data.dist, temp_data.model_top, c='r', label='model_top')
    for k, c in zip(k_cs, colors):
        ax.plot(temp_data.dist, plt_stg_data.loc[k].values.transpose(), c=c, label=f'River Stage: {k}')
    ax.axvline(hawea_clutha_divide, ls=':', c='k', label='Hawea-Clutha Divide')
    ax.set_ylabel('Elevation')
    ax.set_xlabel('Distance from top of river')
    ax.legend()
    if save:
        fig.savefig(outdir.joinpath(f'River_profile{extension}'))

    # monthly stage data
    # look at stage through time at our locations( which are???)
    hawea_data = pd.read_csv(base_model_build_data_dir.joinpath('Lake_Hawea.csv'))
    print(hawea_data.describe())
    hawea_data.loc[:, 'datetime'] = pd.to_datetime(hawea_data.loc[:, 'DateLake'], format='%d/%m/%Y %H:%M')
    hawea_data.loc[:, 'Month'] = hawea_data.loc[:, 'datetime'].dt.month
    monthly = hawea_data.groupby('Month').describe(percentiles=[.05, .25, .5, .75, .95])
    fig, ax = plt.subplots(figsize=(10, 8))
    monthly.LakeLevel_m.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('Monthly lake level')
    ax.set_ylabel('Stage (m)')
    if save:
        fig.savefig(outdir.joinpath(f'Monthly_mean_lake_levels{extension}'))

    river_data = pd.read_csv(base_model_build_data_dir.joinpath('River_Level_Hawea.csv'))
    print(river_data.describe())
    river_data.loc[:, 'datetime'] = pd.to_datetime(river_data.loc[:, 'DateTime'], format='%d/%m/%Y')
    river_data.loc[:, 'Month'] = river_data.loc[:, 'datetime'].dt.month
    monthly = river_data.groupby('Month').describe(percentiles=[.05, .25, .5, .75, .95])

    fig, ax = plt.subplots(figsize=(10, 8))
    monthly.Level_Camphill.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('Hawea at Camp Hill stage')
    ax.set_ylabel('Stage (m)')
    if save:
        fig.savefig(outdir.joinpath(f'Monthly_mean_camphill_levels{extension}'))

    fig, ax = plt.subplots(figsize=(10, 8))
    monthly.Stage_Clutha2200.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('Clutha at Luggate stage')
    ax.set_ylabel('Stage (m)')
    if save:
        fig.savefig(outdir.joinpath(f'Monthly_mean_clutha_levels{extension}'))


def plot_boundary_locs(save=False):
    outdir = save_path.joinpath('boundary_condition_locations')
    outdir.mkdir(exist_ok=True)
    datasets = {'Abstraction': get_pumping_locs(),
                'Race Losses': get_race_locs(),
                'River cells': get_river_loc_data(),
                'Lake cells': get_lake_hawea_loc(),
                'Hillside Inflows': get_hillside_catchment_locs()}
    for k, data in datasets.items():
        fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() + np.nan, title=k, no_flow_layer=0, color_bar=False,
                                      base_map=True)
        data = smt.io.add_mxmy_to_df(data)
        ax.scatter(data.mx, data.my, color='r')
        fig.tight_layout()
        if save:
            fig.savefig(outdir.joinpath(f'{k.replace(" ", "_")}{extension}'))


def plot_steady_state_water_budget(save=False):
    outdir = save_path.joinpath('steady_state_water_budget')
    outdir.mkdir(exist_ok=True)
    rch = get_rch_data(tdis, rch_param=get_initial_rch_mult(True))
    rch = rch[0]
    wel = get_well_data(tdis, get_hillslope_multiplier(True), get_race_multiplier(True), return_unique_spd=True)
    wel = {k: v[0] for k, v in wel.items()}
    zones = get_model_zones()
    labels = []
    data = {k: [] for k in wel}
    data['recharge'] = []

    for k, z in zones.items():
        labels.append(k)
        data['recharge'].append(np.nansum(rch[z]) * smt.grid_space ** 2)
        for w, wdata in wel.items():
            wdata = pd.DataFrame(wdata)
            wdata = wdata.loc[z[wdata.i, wdata.j]]
            data[w].append(wdata.flux.sum())

    # get max and min
    modifer = 1 / 24 / 60 / 60
    modifer = 1
    maxv = np.array(list(data.values())).max() * modifer
    minv = np.array(list(data.values())).min() * modifer
    x = np.arange(len(labels) * len(data), step=len(data))
    colors = get_colors(data)
    fig, ax = plt.subplots(figsize=(10, 8))
    for i, (c, (k, v)) in enumerate(zip(colors, data.items())):
        ax.bar(x + i, np.array(v) * modifer, color=c, label=k)
        if i == 0:
            ax.vlines(x + i + 0.5, minv, maxv, ls=':', color='k')
            ax.set_ylabel(f'flux (m3/day)')

    ax.axhline(0, ls='-', color='k')
    ax.set_xticks(x + len(data) / 2)
    ax.set_xticklabels(labels, rotation=-45)
    ax.set_xlabel('model zone')
    ax.set_xlim(x.min(), x.max() + len(data) + 0.5)
    ax.legend()
    fig.suptitle('fixed water budget for model zones')
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'water_budget{extension}'))


def plot_steady_state_water_bud_locs(save):
    outdir = save_path.joinpath('steady_state_water_budget')
    outdir.mkdir(exist_ok=True)
    ibound = smt.get_no_flow(0)
    rch = get_rch_data(tdis, rch_param=get_initial_rch_mult(True))
    rch = rch[0]
    rch[ibound != 1] = np.nan
    wel = get_well_data(tdis, get_hillslope_multiplier(True), get_race_multiplier(True), return_unique_spd=True)
    wel = {k: v[0] for k, v in wel.items()}
    start = get_starting_heads()[0]
    start[ibound != 1] = np.nan
    # plot mean recharge
    fig, ax = smt.plot.plt_matrix(rch * 1000, no_flow_layer=0, base_map=True, title='Mean Recharge (mm)')
    if save:
        fig.savefig(outdir.joinpath(f'spatial_mean_recharge{extension}'))

    # plot starting heads
    fig, ax = smt.plot.plt_matrix(start, no_flow_layer=0, base_map=True, title='Starting Heads (m)', contour=True,
                                  contour_levels=np.arange(np.nanmin(start), np.nanmax(start), 20),
                                  label_contours=True)
    if save:
        fig.savefig(outdir.joinpath(f'spatial_start_heads{extension}'))

    for k, v in wel.items():
        fig, ax = smt.plot.plt_matrix(rch * np.nan, no_flow_layer=0, base_map=True,
                                      title=f'Wel: {k} flux by color', color_bar=False)
        v = pd.DataFrame(v)
        if k == 'pump':
            v.loc[:, 'flux'] *= -1
        v = smt.io.add_mxmy_to_df(v)
        from matplotlib.colors import LogNorm
        sc = ax.scatter(v.mx, v.my, c=v.flux, cmap='magma', norm=LogNorm())
        cbar = fig.colorbar(sc)
        if save:
            fig.savefig(outdir.joinpath(f'spatial_start_heads{extension}'))


def plot_targets(save):
    outdir = save_path.joinpath('targets')
    outdir.mkdir(exist_ok=True)

    # spatially
    # head targets
    fig, ax = plot_head_targets('incl')
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'spatial_head_targets{extension}'))

    # river targets
    riv_loc = get_riv_target_locs()
    use_riv_targets = smt.get_model_zeros() * np.nan
    for k, v in riv_loc.items():
        use_riv_targets[v] = k

    base_names = [f'Hawea Target: {int(e)}' for e in riv_loc.keys()]
    zone_colors = get_colors(base_names)
    cmap = ListedColormap(zone_colors)
    fig, ax1 = plt.subplots(figsize=smt.default_figsize)
    smt.plot.plt_matrix(use_riv_targets, no_flow_layer=0, base_map=True,
                        title='River target zones', cmap=cmap, color_bar=False, ax=ax1, alpha=1)
    handles, labels = [], []
    for c, n in zip(zone_colors, base_names):
        handles.append(Patch(facecolor=c))
        labels.append(n.capitalize())
    ax1.legend(handles, labels, loc='lower left')
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'river_conductance{extension}'))

    # temporally (high frequency)
    high = get_high_freq_head_targets(*tdis.date_limits, freq='W')
    low = get_low_freq_head_targets(*tdis.date_limits, freq='W')
    all_targs = pd.merge(high, low, how='outer', right_index=True, left_index=True)
    all_targs = all_targs.loc[(all_targs.index >= tdis.date_limits[0]) & (all_targs.index <= tdis.date_limits[1])]
    targ_names = all_targs.keys()

    fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(8, 10), gridspec_kw=dict(height_ratios=(1, 2)))
    colors = get_colors(targ_names)
    colors[-1] = 'gold'
    for i, (k, c) in enumerate(zip(targ_names, colors)):
        temp = all_targs.loc[:, k].dropna()
        ax1.axhline(i, color='k', alpha=.30)
        ax1.scatter(temp.index, np.repeat(i, len(temp)), color=c)
    ax1.set_yticks(range(len(targ_names)))
    ax1.set_yticklabels(targ_names)
    ax1.set_ylabel('Well name')

    all_wells = get_all_wells().loc[targ_names]
    smt.plot.plt_basemap(ax=ax2, no_flow_layer=0)

    for k, c in zip(targ_names, colors):
        x, y = all_wells.loc[k, ['nztmx', 'nztmy']]
        ax2.scatter(x, y, color=c, label=k, s=80)
    ax2.legend(loc='lower left')

    fig.suptitle('High Frequency targets')
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'high_freq_temporal_targets{extension}'))

    # temporally by zones (low frequency) incl riv targets
    riv_targ = get_hawea_gain_loss_targets()
    low_heads = pd.concat([
        get_2011_piezo_survey(),
        get_single_head_targets()

    ])
    low_heads.loc[:, 'use_datetime'] = pd.to_datetime('15-' + low_heads.model_time, format='%d-%m-%Y')
    low_heads.drop_duplicates(['use_datetime', 'i', 'j'], inplace=True)
    zones = get_model_zones()
    use_zones = [
        'sandypoint',
        'flat',
        'east',
        'mangawera',
        'terrace',
        'river targets'
    ]
    fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(8, 10), gridspec_kw=dict(height_ratios=(1, 2)))
    colors = get_colors(use_zones)

    zone_plot = smt.get_model_zeros() * np.nan
    zone_plot[zones['active']] = 2
    for i, z in enumerate(use_zones[:-1]):
        zone_plot[zones[z]] = i

    # plot low freq heads
    for i, (z, c) in enumerate(zip(use_zones[:-1], colors[:-1])):
        idx = zone_plot[low_heads.i, low_heads.j] == i
        temp = low_heads.loc[idx]
        np.random.seed(13658 + i)
        adders = np.random.uniform(0.1, 0.9, len(temp))
        ax1.scatter(temp.use_datetime, i + adders, color=c)
        ax1.axhline(i + 1, color='k', ls=':')

    # plot river targets
    ax1.scatter(riv_targ.index, len(use_zones) - 1 + riv_targ.target_key / 4, color=colors[-1])

    ax1.set_yticks(np.arange(len(use_zones)) + 0.5)
    ax1.set_yticklabels(use_zones)

    # plot zones
    cmap = ListedColormap(colors[:-1])
    smt.plot.plt_matrix(zone_plot, no_flow_layer=0, base_map=True,
                        cmap=cmap, color_bar=False, ax=ax2, alpha=0.5)
    handles, labels = [], []
    for c, n in zip(colors[:-1], use_zones[:-1]):
        handles.append(Patch(facecolor=c))
        labels.append(n.capitalize())
    ax2.legend(handles, labels, loc='lower left')
    fig.suptitle('Low frequency targets')
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'low_freq_temporal_targets{extension}'))

    # plot targets from get targets
    all_hds = get_all_hds_targets(tdis)
    all_hds = smt.io.add_mxmy_to_df(all_hds)
    groups = all_hds.group.unique()
    colors = get_colors(groups)
    # temporally

    fig, ax = plt.subplots(figsize=(10, 8))
    for i, (g, c) in enumerate(zip(groups, colors)):
        temp = all_hds.loc[all_hds.group == g]
        np.random.seed(56548 + i)
        mapper = np.random.uniform(0.1, 0.9, len(temp))
        ax.scatter(temp.nper, mapper + i, color=c, label=g)
        ax.axhline(i + 1, color='k', ls=':')
    ax.set_title('Targets after formatting for model input')
    ax.set_yticks(np.arange(len(groups)) + 1)
    ax.set_yticklabels(groups)
    if save:
        fig.savefig(outdir.joinpath(f'temporal_post_formatting{extension}'))

    #  from get all head targest spatially
    fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
    for g, c in zip(groups, colors):
        temp = all_hds.loc[all_hds.group == g]
        ax.scatter(temp.mx, temp.my, color=c, label=g)
    ax.set_title('Targets after formatting for model input')
    ax.legend()
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'spatial_post_formatting{extension}'))


def plot_deciding_time_period(save):
    outdir = save_path.joinpath('determine_opt_period')
    outdir.mkdir(exist_ok=True)
    figs, names = get_opt_start_stop()
    if save:
        for f, n in zip(figs, names):
            f.savefig(outdir.joinpath(f'{n}{extension}'))


def indicative_target_times(save):
    outdir = save_path.joinpath('indicative_target_times')
    outdir.mkdir(exist_ok=True)
    figs, names = [], []
    from targets_and_sensitive_sites.get_indicative_times import get_indicative_times_v2, predictive_power_hill_rch
    i, (ifigs, inames) = get_indicative_times_v2(True, True)
    figs.extend(ifigs)
    names.extend(inames)
    i, (ifigs, inames) = predictive_power_hill_rch()
    figs.extend(ifigs)
    names.extend(inames)
    if save:
        for f, n in zip(figs, names):
            f.savefig(outdir.joinpath(f'{n}{extension}'))


def plot_zone_maps(save):
    outdir = save_path
    zones = get_model_zones()
    use_zones1 = [
        'lake',
        'sandypoint',
        'flat',
        'east',
        'mangawera',
        'terrace',
    ]
    use_zones2 = [
        'near_river',
        'hawea_flat',
        'hawea_town',
    ]
    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10, 8))
    colors1 = {i: c for i, c in enumerate(get_colors(use_zones1, 'Set1'))}
    colors2 = {i: c for i, c in enumerate(get_colors(use_zones2, 'Set2'))}
    for colors, use_zones, ax, ttl, a in zip([colors1, colors2],
                                             [use_zones1, use_zones2],
                                             [ax1, ax2],
                                             ['Large zones', 'Detailed zones'],
                                             [0.5, 0.7]):

        # plot zones
        zone_plot = smt.get_model_zeros() * np.nan
        for i, z in enumerate(use_zones):
            zone_plot[zones[z]] = i
        smt.plot.plt_discrete_matrix(zone_plot, colors=colors, names={i: n for i, n in enumerate(use_zones)},
                                     legend_loc='lower left', no_flow_layer=0, base_map=True,
                                     ax=ax, alpha=a,
                                     title=ttl)
    fig.suptitle('Model zones')
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'zones{extension}'))


def plot_indicative_cross_sections(save):
    outdir = save_path.joinpath('cross_sections')
    outdir.mkdir(exist_ok=True)
    rows = [50, 100, 170]
    cols = [80, 100]
    # mangawera points
    xs = [1296620.8105173516, 1302218.1332765596, 1307002.4370875028, 1308347.0453480945]
    ys = [5052176.357249308, 5047110.623802427, 5043326.958697041, 5038636.464764744]

    figs, names = [], []

    title = f'Bespoke cross section'
    fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(10, 8), gridspec_kw=dict(height_ratios=(1, 2)))
    smt.plot.plt_slice(np.zeros(smt.model_shape) * np.nan, x_coords=xs, y_coords=ys,
                       coords_in_row_col=False,
                       plot_locator=True, title=title, color_bar=False, ax=ax1, locator_ax=ax2,
                       no_flow_layer=0
                       )
    fig.set_size_inches(10, 8)
    fig.tight_layout()
    figs.append(fig)
    names.append(title.replace(' ', '_'))

    for r in rows:
        title = f'Cross section Row {r}'
        fig, ax = smt.plot.plt_slice(np.zeros(smt.model_shape) * np.nan, x_coords=None, y_coords=r,
                                     coords_in_row_col=True,
                                     plot_locator=True, title=title, color_bar=False, no_flow_layer=0)
        fig.tight_layout()
        figs.append(fig)
        names.append(title.replace(' ', '_'))

    for c in cols:
        title = f'Cross section column {c}'
        fig, ax = smt.plot.plt_slice(np.zeros(smt.model_shape) * np.nan, x_coords=c, y_coords=None,
                                     coords_in_row_col=True,
                                     plot_locator=True, title=title, color_bar=False, no_flow_layer=0)
        fig.tight_layout()
        figs.append(fig)
        names.append(title.replace(' ', '_'))

    if save:
        for f, n in zip(figs, names):
            f.savefig(outdir.joinpath(f'{n}{extension}'))


def plot_era5_correction_process(save):
    outdir = save_path.joinpath('era5_correction')
    outdir.mkdir(exist_ok=True)
    from model_build.supporting_data_analysis.recharge_model import get_era5_land, get_corrected_historical_era5_rch
    era5, era_data_fig = get_era5_land(True, True, True)

    temp, out_rch, rch_fig = get_corrected_historical_era5_rch(None, None, recalc=True, return_fig=True)

    if save:
        era_data_fig.savefig(outdir.joinpath(f'era5_data_correction{extension}'))
        rch_fig.savefig(outdir.joinpath(f'era5_rch_correction{extension}'))


def plot_hillslope_inflow_process(save):
    from model_build.supporting_data_analysis.hillside_inflows import lindis_correlation_with_malf
    outdir = save_path.joinpath('hillslope_inflow_correction')
    outdir.mkdir(exist_ok=True)
    outdata, (figs, names) = lindis_correlation_with_malf(return_figs=True)
    if save:
        for f, n in zip(figs, names):
            f.savefig(outdir.joinpath(f'{n}{extension}'))


def draft_objective_function_thoughts(save):
    data = pd.DataFrame(index=range(1, 6),
                        columns=['Target Group', 'intragroup weight', 'Relative intergroup weight', 'Function'],
                        data=[
                            ['High frequency head targets', 'None', 'High', 'RSME'],
                            ['Low frequency head targets', 'None', 'high', 'RSME'],
                            ['Scott 2011 piezo survey', 'None', 'moderate', 'RSME'],
                            ['Drill date data', 'By quality code', 'low', 'RSME'],
                            ['River targets', 'None', 'high', 'RSME'],
                        ])
    if save:
        if extension == '.pdf':
            import pdfkit as pdf
            tempf = Path.home().joinpath('Downloads/temp.html')
            data.to_html(tempf)
            new = save_path.joinpath('obj_function.pdf')
            pdf.from_file(str(tempf), str(new))
        if extension == '.png':
            data.to_csv(save_path.joinpath('obj_function.csv'))

    model_stats = pd.DataFrame(
        index=range(1, 4), columns=['Step', 'Run time', 'File size'],
        data=[['python model build', '3.7s', ' NA'],
              ['writing model', '7.5s', '148MB'],
              ['Running Model (259 periods)', '30.8s, 28.04s in ramdisk', '240MB (minimum(80MB))'], ]
    )
    if save:
        if extension == '.pdf':
            import pdfkit as pdf
            tempf = Path.home().joinpath('Downloads/temp.html')
            model_stats.to_html(tempf)
            new = save_path.joinpath('model_stats.pdf')
            pdf.from_file(str(tempf), str(new))
        if extension == '.png':
            model_stats.to_csv(save_path.joinpath('model_stats.csv'))


def make_all_preopt(save):
    funcs = [
        draft_objective_function_thoughts,
        plot_thickness_top_bot,
        plot_hillslope_inflow_process,
        plot_era5_correction_process,
        plot_indicative_cross_sections,
        plot_zone_maps,
        plot_targets,
        indicative_target_times,
        plot_deciding_time_period,
        plot_steady_state_water_bud_locs,
        plot_steady_state_water_budget,
        plot_boundary_locs,
        plot_all_spd,
        plot_parameterisation,
    ]
    for f in funcs:
        print(f.__name__)
        f(save)
        if save:
            plt.close()
        else:
            plt.show()
    print('Done with everything!!!')


if __name__ == '__main__':
    save = True
    # checked and finished, but not saved
    make_all_preopt(save)
