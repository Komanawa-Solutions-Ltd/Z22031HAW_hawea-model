"""
created matt_dumont 
on: 20/03/23
"""

from komanawa.hawea.model_build.project_model_tools import smt
import matplotlib.pyplot as plt
from komanawa.hawea.hawea_base import proj_root
import numpy as np

outdir = proj_root.joinpath('Scenarios', 'figs_for_writeup')
outdir.mkdir(exist_ok=True)


def mt3d_plot():
    names = ['Recharge and Hill inflows', 'Lake', 'Stream package']
    paths = [
        'Scenarios/mt3d_indicator_scenarios/ucn_data/hill_rch_indicator.npz',
        'Scenarios/mt3d_indicator_scenarios/ucn_data/lake_con_indicator.npz',
        'Scenarios/mt3d_indicator_scenarios/ucn_data/all_str.npz']
    tfig, tax = plt.subplots()
    m = tax.imshow(smt.get_model_zeros(),cmap='plasma', vmin=0, vmax=1)
    fig = plt.Figure(figsize=(14, 8))
    gs = fig.add_gridspec(2, 3, height_ratios=(10, 1))
    axs = [fig.add_subplot(gs[0, i]) for i in range(len(names))]
    cbar_ax = fig.add_subplot(gs[1, :])
    for i, (p, n, ax) in enumerate(zip(paths, names, axs)):
        if i>0:
            ax.set_yticks([])
        data = np.load(proj_root.joinpath(p))['id_conc']
        smt.plot.plt_matrix(data[2], vmin=0, vmax=1, title=n, no_flow_layer=0, base_map=True, ax=ax, color_bar=False)
    fig.colorbar(m, cax=cbar_ax, orientation='horizontal')
    fig.tight_layout()
    fig.suptitle('Fraction water from:')
    fig.savefig(outdir.joinpath('mt3d_results.png'))
if __name__ == '__main__':
    mt3d_plot()