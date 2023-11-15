"""
created matt_dumont 
on: 14/11/23
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from historical_investigation.get_historical_data import get_historical_lake_heads, get_historical_well_heads, \
    historical_well_colors, historical_well_names, get_historical_data_locs
from historical_investigation.plot_historical_data import add_locator_to_ax

from Scenarios.low_lake_scenarios import run_low_lake_scenario, get_lake_hds, low_lake_tdis
from project_base import unbacked_dir, processed_historical_data_dir, historical_figure_dir

scenarios = ['lake_drop_320', 'lake_drop_333']

run_dir = unbacked_dir.joinpath('historical_investigation', 'lake_drop_scenarios', 'runs')
outdir = unbacked_dir.joinpath('historical_investigation', 'lake_drop_scenarios', 'results')
outdir.mkdir(exist_ok=True, parents=True)
run_dir.mkdir(exist_ok=True, parents=True)

plot_dir = historical_figure_dir.joinpath('lake_drop_scenarios')
plot_dir.mkdir(exist_ok=True)


def run_all():
    for k in scenarios:
        run_low_lake_scenario(key=k, base_run_dir=run_dir, base_outdir=outdir,
                              build_run_model=True, process_results=False,
                              plot=False, rerun=False)


def get_extract_historical(scen, recalc=False):
    assert scen in scenarios
    save_path = processed_historical_data_dir.joinpath('lake_drop_results.hdf')
    if not recalc and save_path.exists():
        try:
            return pd.read_hdf(save_path, key=scen)
        except KeyError:
            pass

    import flopy
    hds_path = run_dir.joinpath(f'{scen}/{scen}.hds')
    hds = flopy.utils.HeadFile(hds_path).get_alldata()
    outdata = pd.DataFrame(index=np.arange(len(hds)), columns=historical_well_names)
    head_locs = get_historical_data_locs()
    for site in historical_well_names:
        k = head_locs.loc[site, 'k']
        i = head_locs.loc[site, 'i']
        j = head_locs.loc[site, 'j']
        outdata.loc[:, site] = hds[:, k, i, j]
    outdata.to_hdf(outdir.joinpath(f'{scen}_hds.hdf'), key=scen, complib='zlib', complevel=9)
    return outdata


def plot_hist_plus_lake_drop(scen, well):
    assert scen in scenarios
    assert well in historical_well_names
    measured = get_historical_well_heads(well)
    modelled = get_extract_historical(scen)[well]
    hist_lake = get_historical_lake_heads()
    xs, modelled_lake = get_lake_hds(scen)
    fig = plt.figure(figsize=(14, 9))
    gs = plt.GridSpec(2, 2, height_ratios=(1, 1), width_ratios=(1, 0.3))
    ax = fig.add_subplot(gs[0, 0])
    ax_lake = fig.add_subplot(gs[1, 0], sharex=ax)
    ax_loc = fig.add_subplot(gs[:, 1])
    add_locator_to_ax(ax_loc, [well], False)
    ax.plot(measured.index, measured, label='Measured: historical', color=historical_well_colors[well])
    ax.plot(np.array(low_lake_tdis.per_middle_dates[1:]) + tdis_to_lake_date, modelled[1:], label='Modelled: lake drop',
            color=historical_well_colors[well], ls='--')
    ax_lake.plot(hist_lake.index, hist_lake, label='Measured: historical', c='b')
    ax_lake.plot(np.array(low_lake_tdis.per_middle_dates[1:]) + tdis_to_lake_date, modelled_lake[1:],
                 label='Modelled: lake drop', c='b', ls='--')
    ax_lake.legend()
    ax.legend()
    fig.supxlabel('Date')
    fig.supylabel('Head (m)')
    fig.suptitle(f'{well} - {scen}')
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath(f'{well}_{scen}.png'))


tdis_to_lake_date = pd.to_datetime('1976-06-02') - pd.to_datetime('2001-05-15') + pd.to_timedelta('7D')


def plot_lake_v_lakedrop():
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 9))
    hist_lake = get_historical_lake_heads()
    xs, modelled_lake = get_lake_hds('lake_drop_320')
    ax1.plot(np.array(low_lake_tdis.per_middle_dates[1:]) + tdis_to_lake_date, modelled_lake[1:], label='modelled')
    ax2.plot(hist_lake.index, hist_lake, label='historical')
    ax3.plot(np.array(low_lake_tdis.per_middle_dates[1:]) + tdis_to_lake_date, modelled_lake[1:], label='modelled')
    ax3.plot(hist_lake.index, hist_lake, label='historical')
    ax2.legend()

    plt.show()


if __name__ == '__main__':
    rerun = False
    if rerun:
        run_all()
    for s in scenarios:
        for w in historical_well_names:
            plot_hist_plus_lake_drop(s, w)
