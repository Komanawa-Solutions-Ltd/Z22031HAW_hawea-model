"""
created matt_dumont 
on: 13/11/23
"""
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import pandas as pd
from project_base import historical_figure_dir, historical_data_dir
from historical_investigation.get_historical_data import get_historical_well_heads, get_lake_heads, \
    historical_time_start, historical_time_end
from historical_investigation.plot_historical_data import add_locator_to_ax, historical_well_colors
from historical_investigation.current_model_prediction import get_hist_nat_data

outdir = historical_figure_dir.joinpath('3d_v1d_historical')
outdir.mkdir(exist_ok=True)


def plot_historical_well_heads_vmodelled():
    for well, color in historical_well_colors.items():
        measured = get_historical_well_heads(well, freq='D')
        modelled = get_hist_nat_data(well, freq='D')
        fig = plt.figure(figsize=(14, 9))
        gs = GridSpec(2, 2, width_ratios=(2, 1), height_ratios=(3, 1))
        ax = fig.add_subplot(gs[0, 0])
        ax.plot(measured.index, measured, label='measured', color=color)
        ax.plot(modelled.index, modelled, label='modelled', color=color, ls='--')

        ax_lake = fig.add_subplot(gs[1, 0])
        ax_loc = fig.add_subplot(gs[:, 1])
        add_locator_to_ax(ax_loc, [well], False)
        lake = get_lake_heads(historical_time_start, historical_time_end)
        ax_lake.plot(lake.index, lake, label='lake heads')
        ax_lake.set_ylabel('lake heads (m)')
        ax_lake.set_xlim(historical_time_start, historical_time_end)
        ax.set_xlim(historical_time_start, historical_time_end)
        ax.set_xticks([])
        ax.set_xticklabels([])
        ax.set_xlabel('')
        ax.set_xlabel('Date')
        ax.set_ylabel('Weekly mean Head (m)')
        ax.legend()
        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{well}_modelled.png'))


def plot_histoical_with_modified_lake():
    for well, color in historical_well_colors.items():
        measured = get_historical_well_heads(well, freq='D')
        modelled = get_hist_nat_data(well, freq='D')
        fig = plt.figure(figsize=(14, 9))
        gs = GridSpec(1, 2, width_ratios=(2, 1))
        ax = fig.add_subplot(gs[0])
        ax.plot(measured.index, measured, label='measured', color=color)
        ax.plot(modelled.index, modelled, label='modelled', color=color, ls='--')

        ax_loc = fig.add_subplot(gs[1])
        add_locator_to_ax(ax_loc, [well], False)
        lake = get_lake_heads(historical_time_start, historical_time_end)
        diff = (lake - measured).mean()
        ax.plot(lake.index, lake - diff, label=f'lake heads - {round(diff, 2)} m', color='b', ls=':')
        ax.set_xlim(historical_time_start, historical_time_end)
        ax.set_xticks([])
        ax.set_xticklabels([])
        ax.set_xlabel('')
        ax.set_xlabel('Date')
        ax.set_ylabel('Weekly mean Head (m)')
        ax.legend()
        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{well}_modelled_lake_mod.png'))
def plot_regular_v10a():
    from optimisation.optimisation_period import tdis as opt_tdis
    from historical_investigation.plot_historical_data import get_regular_hds_colors

    all_out = pd.read_csv(
        '/home/matt_dumont/Hawea_model_unbacked/historical_investigation/results/long_nat_v10a/output_dataset.csv',
        index_col=1)
    all_out.index = pd.to_datetime(all_out.index)
    all_out = all_out.loc[all_out.index>pd.to_datetime(opt_tdis.date_limits[0])]
    reg_colors = get_regular_hds_colors()
    use_outdir = outdir.joinpath('reg_opt_period')
    use_outdir.mkdir(exist_ok=True)
    from optimisation.optimisation_period import tdis as tdis_opt
    from targets_and_sensitive_sites.get_raw_target_data import get_high_freq_head_targets
    from targets_and_sensitive_sites.head_targets import plot_hds_regular_locator
    for well, c in reg_colors.items():
        if f'hds_{well}' not in all_out:
            print(f'skipping: {well}')
            continue
        fig = plt.figure(figsize=(14, 9))
        gs =GridSpec(2, 2, width_ratios=(2, 1), height_ratios=(3, 1))
        ax = fig.add_subplot(gs[0, 0])
        ax_lake = fig.add_subplot(gs[1, 0])
        ax_loc = fig.add_subplot(gs[0, 1])
        temp2 = get_high_freq_head_targets(*tdis_opt.date_limits)[well]
        ax.scatter(temp2.index, temp2, color=c, label=f'{well.capitalize()} measured')
        ax.plot(all_out.index, all_out[f'hds_{well}'], color=c, label=f'{well.capitalize()} modelled')
        plot_hds_regular_locator(ax_loc, {well: c})
        lake = get_lake_heads(temp2.index.min(), temp2.index.max())
        ax_lake.plot(lake.index, lake, label='lake heads')
        ax_lake.set_ylabel('lake heads (m)')
        ax_lake.set_xlim(ax.get_xlim())
        ax.set_xticks([])
        ax.set_xticklabels([])
        ax.set_xlabel('')
        ax.set_title(f'{well.capitalize()} hds')
        ax.set_xlabel('Date')
        ax.set_ylabel('Weekly mean Head (m)')
        ax.legend()
        fig.tight_layout()
        fig.savefig(use_outdir.joinpath(f'hds_closeup_{well}.png'))
        plt.close(fig)


if __name__ == '__main__':
    #plot_historical_well_heads_vmodelled()
    #plot_histoical_with_modified_lake()
    plot_regular_v10a()