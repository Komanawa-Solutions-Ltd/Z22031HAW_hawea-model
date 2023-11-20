"""
created matt_dumont 
on: 2/11/23
"""
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

import pandas as pd

from project_base import proj_root, historical_data_dir, processed_historical_data_dir, historical_figure_dir
from targets_and_sensitive_sites.head_targets import plot_hds_regular_locator, get_all_hds_targets
from optimisation.optimisation_period import tdis as tdis_opt
from targets_and_sensitive_sites.get_raw_target_data import get_high_freq_head_targets
from model_build.utils import get_colors
from historical_investigation.get_historical_data import get_historical_well_heads, get_historical_data_locs, \
    get_historical_lake_heads, historical_well_names, historical_well_colors, get_model_period_hds, \
    historical_time_start, historical_time_end
from model_build.project_model_tools import smt
from model_build.supporting_data_analysis import get_lake_heads


def get_regular_hds_colors():
    reg_colormap = 'tab10'
    regular_wells = sorted([
        'g40_0041',
        'g40_0120',
        'g40_0129',
        'g40_0366',
        'g40_0367',
        'g40_0415',
        'g40_0416',
    ])
    regular_colors = get_colors(regular_wells, reg_colormap)
    return {n: nc for n, nc in zip(regular_wells, regular_colors)}


def add_locator_to_ax(ax, sites, label=True):
    reg_colors = get_regular_hds_colors()

    reg_dict = {s: reg_colors[s] for s in sites if s in reg_colors}
    hist_dict = {s: historical_well_colors[s] for s in sites if s in historical_well_names}

    plot_hds_regular_locator(ax=ax, label=False, colors_dict=reg_dict)
    historical_locs = get_historical_data_locs()
    for w in hist_dict:
        x, y = historical_locs.loc[w, ['x', 'y']]
        c = hist_dict[w]
        ax.scatter(x, y, color=c, label='Hist. ' + w, s=80, marker='^')
    ax.legend()


def plot_head_locs():
    fig, ax = plt.subplots(figsize=smt.default_figsize)
    plot_hds_regular_locator(ax=ax, label=False, colors_dict=get_regular_hds_colors())
    historical_locs = get_historical_data_locs()
    for w in historical_well_names:
        x, y = historical_locs.loc[w, ['x', 'y']]
        c = historical_well_colors[w]
        ax.scatter(x, y, color=c, label='Hist. ' + w, s=80, marker='^')
    ax.legend()
    ax.set_title('Historical and Modern Head Locations')
    fig.tight_layout()
    fig.savefig(historical_figure_dir.joinpath('historical_head_locs.png'))


def creater_well_hds_figure(sites, date_limits):
    fig = plt.figure(figsize=(14, 9))
    gs = gridspec.GridSpec(2, 2, width_ratios=(2, 1), height_ratios=(3, 1))
    ax = fig.add_subplot(gs[0, 0])
    ax_lake = fig.add_subplot(gs[1, 0])
    ax_loc = fig.add_subplot(gs[0, 1])
    add_locator_to_ax(ax_loc, sites, False)
    lake = get_lake_heads(*date_limits)
    ax_lake.plot(lake.index, lake, label='lake heads')
    ax_lake.set_ylabel('lake heads (m)')
    ax_lake.set_xlim(*date_limits)
    ax.set_xlim(*date_limits)
    ax.set_xticks([])
    ax.set_xticklabels([])
    ax.set_xlabel('')
    ax.set_xlabel('Date')
    ax.set_ylabel('Weekly mean Head (m)')
    ax.legend()
    return fig, ax


def plot_model_period_hds():
    well_groups = {
        'NE': ['g40_0415', 'bore_315'],
        'NW': ['g40_0416', 'g40_0041', 'bore_513', 'bore_13', 'bore_515', ],
        'MID': ['g40_0367', 'bore_butterfields', ],
        'S': ['g40_0366']
    }

    regular_colors = get_regular_hds_colors()
    all_colors = {**regular_colors, **historical_well_colors}
    for nm, sites in well_groups.items():
        fig, ax = creater_well_hds_figure(sites, tdis_opt.date_limits)
        for site in sites:
            c = all_colors[site]
            if site in historical_well_names:
                hds = get_model_period_hds(site).iloc[1:]
                ax.plot(hds.index, hds, color=c, label='Mod. ' + site)
            else:
                hds = get_high_freq_head_targets(*tdis_opt.date_limits)[site]
                ax.plot(hds.index, hds, color=c, label='Meas. ' + site)
        ax.legend()
        fig.tight_layout()
        useoutdir = historical_figure_dir.joinpath('model_period_hds')
        useoutdir.mkdir(exist_ok=True)
        fig.savefig(useoutdir.joinpath(f'{nm}_hds.png'))
        plt.close(fig)


def plot_raw_historic():
    for site in historical_well_names:
        fig, ax = creater_well_hds_figure([site], [historical_time_start, historical_time_end])
        c = historical_well_colors[site]
        if site in historical_well_names:
            hds = get_historical_well_heads(site, freq='W')
            ax.plot(hds.index, hds, color=c, label='Measured ' + site)
        ax.legend()
        fig.tight_layout()
        useoutdir = historical_figure_dir.joinpath('historic_period_hds')
        useoutdir.mkdir(exist_ok=True)
        fig.savefig(useoutdir.joinpath(f'{site}_hds.png'))


def plot_lake_v_hds_nearest_modern():
    from historical_investigation.shift_diff import use_shifts
    outdir = historical_figure_dir.joinpath('lake_v_hds_nearest_modern')
    outdir.mkdir(exist_ok=True)
    nearest_well = {
        'bore_315': 'g40_0415',
        'bore_13': 'g40_0041',
        'bore_513': 'g40_0041',
        'bore_515': 'g40_0041',
        'bore_butterfields': 'g40_0367',
    }
    lake_org = get_lake_heads('1976-01-01', tdis_opt.date_limits[-1])
    for site in historical_well_names:
        lake = lake_org.copy()
        lake.index = lake.index + pd.Timedelta(days=use_shifts[site])
        near_site = nearest_well[site]
        fig, (ax, axloc) = plt.subplots(ncols=2, figsize=(14, 10))
        add_locator_to_ax(axloc, [site, near_site], False)
        historical = pd.DataFrame(get_historical_well_heads(site))
        historical['lake'] = lake.loc[historical.index]
        modern = pd.DataFrame(get_high_freq_head_targets(*tdis_opt.date_limits)[near_site])
        modern['lake'] = lake.loc[modern.index]
        min_lake = modern.lake.min()

        num_days = 30
        historical = historical.rolling(num_days).mean()
        modern = modern.rolling(num_days).mean()
        modern = modern.resample(f'{num_days}D').mean()
        historical = historical.resample(f'{num_days}D').mean()

        modern['increasing'] = (modern['lake'].diff(1) > 0)
        historical['increasing'] = (historical['lake'].diff(1) > 0)
        ax.scatter(historical.loc[historical.increasing, 'lake'], historical.loc[historical.increasing, 'head'],
                   color='orange', label=f'increasing low lake period: {site}', marker='^')
        ax.scatter(historical.loc[~historical.increasing, 'lake'], historical.loc[~historical.increasing, 'head'],
                   color='red', label=f'decreasing low lake period: {site}', marker='v')
        ax.scatter(modern.loc[modern.increasing, 'lake'], modern.loc[modern.increasing, near_site], color='blue',
                   label=f'increasing modern: {near_site}', marker='^')
        ax.scatter(modern.loc[~modern.increasing, 'lake'], modern.loc[~modern.increasing, near_site], color='purple',
                   label=f'decreasing modern: {near_site}', marker='v')
        ax.axvline(min_lake, ls=':', label='minium lake level during optimisation')
        ax.legend()
        ax.set_xlabel('Lake Head (m)')
        ax.set_ylabel('Well Head (m)')
        ax.set_title(f'Lake vs Well Heads: {site}')
        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{site}_lake_v_hds.png'))
        plt.close(fig)


def plot_lake_v_hds_modelled():
    outdir = historical_figure_dir.joinpath('lake_v_hds_modelled')
    outdir.mkdir(exist_ok=True)
    lake_org = get_lake_heads('1976-01-01', tdis_opt.date_limits[-1])
    from historical_investigation.shift_diff import use_shifts
    for site in historical_well_names:
        lake = lake_org.copy()
        lake.index = lake.index + pd.Timedelta(days=use_shifts[site])
        fig, (ax, axloc) = plt.subplots(ncols=2, figsize=(14, 10))
        add_locator_to_ax(axloc, [site], False)
        historical = pd.DataFrame(get_historical_well_heads(site))
        historical['lake'] = lake.loc[historical.index]
        modern = pd.DataFrame(get_model_period_hds(site).iloc[1:])
        modern['lake'] = lake.loc[modern.index]
        min_lake = modern.lake.min()

        num_days = 30
        historical = historical.rolling(num_days).mean()
        modern = modern.rolling(num_days).mean()
        modern = modern.resample(f'{num_days}D').mean()
        historical = historical.resample(f'{num_days}D').mean()

        modern['increasing'] = (modern['lake'].diff(1) > 0)
        historical['increasing'] = (historical['lake'].diff(1) > 0)
        ax.scatter(historical.loc[historical.increasing, 'lake'], historical.loc[historical.increasing, 'head'],
                   color='orange', label=f'increasing low lake period: {site}', marker='^')
        ax.scatter(historical.loc[~historical.increasing, 'lake'], historical.loc[~historical.increasing, 'head'],
                   color='red', label=f'decreasing low lake period: {site}', marker='v')
        ax.scatter(modern.loc[modern.increasing, 'lake'], modern.loc[modern.increasing, site], color='blue',
                   label=f'increasing modern modelled', marker='^')
        ax.scatter(modern.loc[~modern.increasing, 'lake'], modern.loc[~modern.increasing, site], color='purple',
                   label=f'decreasing modern modelled', marker='v')
        ax.axvline(min_lake, ls=':', label='minium lake level during optimisation')
        ax.legend()
        ax.set_xlabel('Lake Head (m)')
        ax.set_ylabel('Well Head (m)')
        ax.set_title(f'Lake vs Well Heads: {site}')
        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{site}_lake_v_hds.png'))
        plt.close(fig)


def plot_lake_v_hds_historic():
    outdir = historical_figure_dir.joinpath('lake_v_hds_historic_only')
    outdir.mkdir(exist_ok=True)
    lake_org = get_lake_heads('1976-01-01', tdis_opt.date_limits[-1])
    from historical_investigation.shift_diff import use_shifts
    for site in historical_well_names:
        lake = lake_org.copy()
        lake.index = lake.index + pd.Timedelta(days=use_shifts[site])
        fig = plt.figure(figsize=(14, 9))
        gs = gridspec.GridSpec(2, 2, width_ratios=(1.5, 1), height_ratios=(1, 2))
        ax_loc = fig.add_subplot(gs[1, 1])
        ax_lake = fig.add_subplot(gs[0, 1])
        ax_first = fig.add_subplot(gs[0, 0])
        ax_second = fig.add_subplot(gs[1, 0])
        add_locator_to_ax(ax_loc, [site], False)
        historical = pd.DataFrame(get_historical_well_heads(site))
        historical['lake'] = lake.loc[historical.index]
        historical = historical.loc[historical.lake <= 338]
        modern = pd.DataFrame(get_model_period_hds(site).iloc[1:])
        modern['lake'] = lake.loc[modern.index]
        min_lake = modern.lake.min()

        num_days = 1
        historical = historical.rolling(num_days).mean()
        historical = historical.resample(f'{num_days}D').mean()

        historical['increasing'] = (historical['head'].diff(1) > 0)
        datelimits = [
            pd.to_datetime(['1976-11-01', '1977-07-20']) + pd.Timedelta(days=use_shifts[site]),
            pd.to_datetime(['1977-09-01', '1979-01-01']) + pd.Timedelta(days=use_shifts[site]),
        ]
        labels = ['First recovery', 'Second recovery']
        for ax, datlim, lab in zip([ax_first, ax_second], datelimits, labels):
            ax_lake.axvspan(*datlim, color='k', alpha=0.1)
            ax_lake.text(pd.Series(datlim).mean(), 345, lab, rotation=0, va='bottom', ha='center')
            idx = (historical.index >= datlim[0]) & (historical.index <= datlim[1]) & historical.increasing
            ax.plot(historical.loc[idx, 'lake'], historical.loc[idx, 'head'],
                    color='orange', label=f'increasing low lake period: {site}')
            ax.axvline(min_lake, ls=':', label='minimum lake level during optimisation')
            ax.legend()
            ax.set_xlabel(f'Lake Head (m) shifted forward by {use_shifts[site]} days')
            ax.set_ylabel('Well Head (m)')
            ax.set_title(lab)

        # lake axis
        lake = lake.loc[lake.index <= datelimits[-1][1]]
        ax_lake.plot(lake.index, lake, label='lake')
        historical = get_historical_well_heads(site)
        historical = historical.loc[historical.index <= datelimits[-1][1]]
        ax_lake.plot(historical.index, historical, label='well', color=historical_well_colors[site])
        ax_lake.set_ylabel(' Head (m)')
        ax_lake.set_xlabel('Date')
        ax_lake.legend()
        ax_lake.set_xticks([2191., 2312., 2435., 2557., 2677., 2800., 2922., 3042., 3165.,
                            3287.])

        labs = ['1976-01', '1976-05', '1976-09', '1977-01', '1977-05', '1977-09', '1978-01', '1978-05', '1978-09',
                '1979-01']
        ax_lake.set_xticklabels(labs, rotation=-45)
        fig.suptitle(f'Lake vs Well Heads: {site}')
        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{site}_lake_v_hds.png'))
        plt.close(fig)


def plot_lake_hds():
    t = get_historical_lake_heads()
    fig, ax = plt.subplots()
    ax.plot(t.index, t)
    ax.set_title('Lake Hawea level')
    ax.set_ylabel('Lake level (m)')
    ax.set_xlabel('Date')
    fig.tight_layout()
    plt.show()
    fig.savefig(historical_figure_dir.joinpath('lake_heads.png'))


if __name__ == '__main__':
    re_run = False
    plot_lake_hds()
    plot_lake_v_hds_historic()
    if re_run:
        plot_lake_v_hds_modelled()
        plot_lake_v_hds_nearest_modern()
        plot_raw_historic()
        plot_head_locs()
        plot_model_period_hds()
