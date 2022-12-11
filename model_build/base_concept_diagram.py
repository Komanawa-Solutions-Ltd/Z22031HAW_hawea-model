"""
created matt_dumont 
on: 12/12/22
"""
import matplotlib.pyplot as plt
import numpy as np
from targets_and_sensitive_sites.head_targets import get_high_freq_head_targets
from model_build.project_model_tools import smt, get_lake_array, get_2d_moraine
from supporting_data_analysis import get_all_wells
from project_base import modelling_dir
from pathlib import Path


def plot_base_concent_diagram(outdir=None):
    # across moraine
    moraine_sect = ([1305740.4867037723, 1305895.0940012368], [5054567.5479282625, 5052753.69511441])

    # along moraine
    xs = [1302622.2890978227, 1303437.829817019, 1304607.5952930376, 1305283.0936665132, 1305876.214189565,
          1306477.5724976594, 1307021.2663104567, 1307729.7158241018]
    ys = [5053405.32045735, 5053397.082672307, 5053479.460522732, 5053619.502868452, 5053817.209709469,
          5054303.23902697, 5055118.779746166, 5055604.809063667]
    along_sect = (xs, ys)
    lake_array = np.isfinite(get_lake_array())
    moraine = get_2d_moraine()

    lake_levels = (338, 346)
    min_lake_levels = (327.6)

    all_wells = get_all_wells()
    all_wells = all_wells.loc[moraine[all_wells.i, all_wells.j]]
    all_wells = all_wells.loc[~all_wells.index.str.contains('hw')]
    high_freq = get_high_freq_head_targets(None, None).loc[:, 'g40_0415']
    high_freq = (high_freq.min(), high_freq.max())

    plt_array = smt.get_model_zeros(True)
    plt_array[:, lake_array] = 1
    plt_array[:, moraine] = 2
    vert_ex = 100
    bba=0.5
    figs = []
    for xsect in (moraine_sect, along_sect):
        fig, (ax, loc_ax) = plt.subplots(nrows=2, figsize=(14, 10), gridspec_kw=dict(height_ratios=(3, 2)))
        smt.plot.plt_slice(plt_array, *xsect, plt_layer_slice=False,
                           ax=ax, locator_ax=loc_ax, alpha=0.3, plt_background=False, vert_ex=vert_ex,
                           color_bar=False,
                           )
        ax2 = ax.twinx()
        loc_ax.set_ylim(5.0520E6, 5.056e6)
        loc_ax.set_xlim(1.300E6, 1.309e6)
        sig_line_width = 1.5
        for i, l in enumerate(lake_levels):
            label = None
            if i == 0:
                label = 'Lake opt. range'
            ax.axhline(l * vert_ex, color='b', label=label, ls=':', linewidth=sig_line_width)
        ax.axhline(min_lake_levels * vert_ex, color='b', label='Lake Min level', ls=(0, (1, 5)),
                   linewidth=sig_line_width)

        for i0, i in enumerate(all_wells.index):
            label = None
            if i0 == 0:
                label = 'Well depth'
            d = all_wells.loc[i, 'depth_elevation']
            ax.axhline(d * vert_ex, color='grey', label=label, ls=(0, (1, 2)), alpha=0.6)
            yoff = -100
            if i in ['g40_0368', 'g40_0345']:
                yoff = 300
            loc_ax.annotate(i, (all_wells.nztmx.loc[i], all_wells.nztmy.loc[i]+yoff),
                            bbox=dict(facecolor='w', alpha=bba))
        loc_ax.scatter(all_wells.nztmx, all_wells.nztmy, color='r', label='Wells')

        for i, d in enumerate(high_freq):
            label = None
            if i == 0:
                label = 'G40_0415 Levels'
            ax.axhline(d * vert_ex, color='r', label=label, ls='dashed', linewidth=sig_line_width)
        ax.set_ylim(270 * vert_ex, 380 * vert_ex)
        ax2.set_ylim(270 * vert_ex, 380 * vert_ex)
        ax2.set_yticks(all_wells.loc[:, 'depth_elevation'] * vert_ex)
        ax2.set_yticklabels(all_wells.index)
        ax.set_yticks(np.arange(275, 385, 10) * vert_ex)
        ax.set_yticklabels(np.arange(275, 385, 10))
        ax.legend(loc='lower right')
        loc_ax.legend(loc='lower right')
        fig.tight_layout()
        figs.append(fig)
    if outdir is None:
        plt.show()
    else:
        outdir = Path(outdir)
        outdir.mkdir(exist_ok=True)
        for i, fig in enumerate(figs):
            fig.savefig(outdir.joinpath(f'concept_diagram_{i}.svg'))

if __name__ == '__main__':
    plot_base_concent_diagram(modelling_dir.joinpath('raw_concept_figs'))
