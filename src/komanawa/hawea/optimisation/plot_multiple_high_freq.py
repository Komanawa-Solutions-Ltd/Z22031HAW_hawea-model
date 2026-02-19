"""
created matt_dumont 
on: 24/01/23
"""
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
from komanawa.hawea.model_build.utils import get_colors
from komanawa.modeltools.model_tools.plot_optimisation import plot_optimisation_and_extract_info  # keynote private repo
from komanawa.modeltools.model_tools.util_functions.list_file_utils import ListSolverInfo  # keynote private repo
from komanawa.hawea.targets_and_sensitive_sites import plot_hds_regular_locator, base_regular_groupnames
from komanawa.hawea.optimisation.optimisation_period import tdis


def plot_mult_high_freq_heads(obs_files, plot_dir):
    """
    plot multiple obs files
    :param obs_files: dict name: obs file path
    :param plot_dir: directory to plot stuff
    :return:
    """
    plot_dir.mkdir(exist_ok=True)
    regular_hds = {}
    # read in all of the regualr heads
    for n, f in obs_files.items():
        hds_obs = pd.read_fwf(f, skiprows=4)
        hds_obs.rename(columns={e: e.lower() for e in hds_obs.keys()}, inplace=True)
        hds_obs.loc[:, 'weight'] = pd.to_numeric(hds_obs.loc[:, 'weight'], 'coerce')
        hds_obs.loc[:, 'residual'] = pd.to_numeric(hds_obs.loc[:, 'residual'], 'coerce')
        hds_obs.loc[:, 'modelled'] = pd.to_numeric(hds_obs.loc[:, 'modelled'], 'coerce')
        hds_obs.loc[:, 'measured'] = pd.to_numeric(hds_obs.loc[:, 'measured'], 'coerce')
        hds_obs.loc[:, 'iphi'] = (hds_obs.loc[:, 'residual'] * hds_obs.loc[:, 'weight']) ** 2
        mapper = {'h_piezo': 'h_piezo',
                  'h_single_3': 'h_single_3',
                  'h_single_1': 'h_single_1'}
        mapper.update({k: 'regular' for k in base_regular_groupnames})
        hds_obs.loc[:, 'group'] = hds_obs.loc[:, 'group'].replace(mapper)
        hds_obs.loc[:, 'well_name'] = [f'{"_".join(e.split("_")[:-1])}' for e in hds_obs.loc[:, 'name']]
        hds_obs = hds_obs.loc[hds_obs.loc[:, 'group'] == 'regular']
        hds_obs.loc[:, 'nper'] = hds_obs.name.str.split('_').str.get(-1).astype(int)
        hds_obs.loc[:, 'date'] = tdis.get_date(hds_obs.loc[:, 'nper'])
        hds_obs.loc[:, 'week'] = hds_obs.date.dt.isocalendar().loc[:, 'week']

        regular_hds[n] = hds_obs

    opt_steps = sorted(list(regular_hds.keys()))
    colors = get_colors(regular_hds, 'tab20')
    reg_colormap = 'tab10'
    regular_wells = sorted(regular_hds[opt_steps[0]].well_name.unique())
    regular_colors = get_colors(regular_wells, reg_colormap)

    for n, nc in zip(regular_wells, regular_colors):
        # full dataset
        fig, axs = plt.subplots(ncols=2, figsize=(14, 9),
                                gridspec_kw=dict(width_ratios=(2, 1)))
        ax = axs[0]
        ax_loc = axs[1]
        for k, c in zip(opt_steps, colors):
            temp2 = regular_hds[k].loc[regular_hds[k].well_name == n].sort_values('date')
            ax.plot(temp2.date, temp2.modelled, color=c, label=k)

        ax.scatter(temp2.date, temp2.measured, color=nc, label=f'{n.capitalize()} measured')
        plot_hds_regular_locator(ax_loc, {n: nc})
        ax.set_title(f'{n.capitalize()} hds')
        ax.set_xlabel('Date')
        ax.set_ylabel('Weekly mean Head (m)')
        ax.legend()
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'hds_closeup_{n}.png'))
        plt.close(fig)


if __name__ == '__main__':
    obs_files = {}
    temp = '/home/matt_dumont/unbacked/hawea/3d_v1b/init_3d_v1b/Optimisations/opt.rei.'
    for i in [12, 20, 21, 22, 23, 24, 25, 26]:
        obs_files[f'b_{i:02d}'] = temp + str(i)

    temp = '/home/matt_dumont/unbacked/hawea/3d_v1a/init2_3d_v1a/Optimisations/opt.rei.'
    obs_files2 = {}
    for i in [13, 14, 16, 17, 18]:
        obs_files2[f'a_{i:02d}'] = temp + str(i)

    plot_dir = Path('/home/matt_dumont/unbacked/hawea/3d_v1a-b_comp/just_b')
    plot_mult_high_freq_heads(obs_files, plot_dir)
    plot_dir = Path('/home/matt_dumont/unbacked/hawea/3d_v1a-b_comp/just_a')
    plot_mult_high_freq_heads(obs_files2, plot_dir)

    obs_files.update(obs_files2)
    plot_dir = Path('/home/matt_dumont/unbacked/hawea/3d_v1a-b_comp/both')
    plot_mult_high_freq_heads(obs_files, plot_dir)
