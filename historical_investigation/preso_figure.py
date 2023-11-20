"""
created matt_dumont 
on: 21/11/23
"""
import matplotlib.pyplot as plt
import datetime
from historical_investigation.lake_drop_scenarios import *
from historical_investigation.plot_historical_natualised_model import get_hist_nat_data
from historical_investigation.simple_smoothing_model import brute_min, simple_smoothing_model, bounds

def plot_hist_plus_lake_drop(scen, well):
    assert scen in scenarios
    assert well in historical_well_names
    measured = get_historical_well_heads(well)
    modelled = get_extract_historical(scen)[well]
    modelled_nat = get_hist_nat_data(well)
    hist_lake = get_historical_lake_heads()

    params = brute_min(well, recalc=False)
    temp = simple_smoothing_model(hist_lake, *params[0], clip=False, center=True)

    xs, modelled_lake = get_lake_hds(scen)
    fig = plt.figure(figsize=(14, 9))
    gs = plt.GridSpec(2, 2, height_ratios=(1, 1), width_ratios=(1, 0.3))
    ax = fig.add_subplot(gs[0, 0])
    ax_lake = fig.add_subplot(gs[1, 0], sharex=ax)
    ax_loc = fig.add_subplot(gs[:, 1])
    add_locator_to_ax(ax_loc, [well], False)
    ax.plot(measured.index, measured, label='Measured: historical', color=historical_well_colors[well])
    ax.plot(np.array(low_lake_tdis.per_middle_dates[1:]) + tdis_to_lake_date, modelled[1:], label='Modelled: lake drop',
            color=historical_well_colors[well], ls=':')
    ax.plot(modelled_nat.index, modelled_nat, label='Modelled: historical', color=historical_well_colors[well], ls='--')
    ax.plot(hist_lake.index, temp.values, label='Simple Smoothing Model', color='fuchsia', ls='--', alpha=0.5)
    ax_lake.plot(hist_lake.index, hist_lake, label='Measured: historical', c='b')
    ax_lake.plot(np.array(low_lake_tdis.per_middle_dates[1:]) + tdis_to_lake_date, modelled_lake[1:],
                 label='Modelled: lake drop', c='b', ls=':')
    ax_lake.legend()
    ax.legend()
    ax.set_xlim(temp.index.min() - datetime.timedelta(days=50), measured.index.max())
    fig.supxlabel('Date')
    fig.supylabel('Head (m)')
    fig.suptitle(f'{well} - {scen}')
    fig.tight_layout()
    return fig

if __name__ == '__main__':
    for bore in bounds:
        fig = plot_hist_plus_lake_drop('lake_drop_320', bore)
        outdir = historical_figure_dir.joinpath('ssm_lake_drop_models')
        outdir.mkdir(exist_ok=True)
        fig.savefig(outdir.joinpath(f'{bore}_lake_drop_320.png'))
    plt.show()