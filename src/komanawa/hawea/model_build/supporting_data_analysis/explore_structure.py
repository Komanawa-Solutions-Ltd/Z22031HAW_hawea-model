"""
created matt_dumont 
on: 15/12/22
"""
import matplotlib.pyplot as plt
import numpy as np
from komanawa.hawea.targets_and_sensitive_sites import get_high_freq_head_targets
from komanawa.hawea.model_build.project_model_tools import smt, get_lake_array, get_2d_moraine
from komanawa.hawea.model_build.supporting_data_analysis import get_all_wells


def define_cutoffs(poss_elvs):
    poss_elvs = np.atleast_1d(poss_elvs)
    _plot_xsection(poss_elvs)
    fig, axs = plt.subplots(ncols=3, figsize=(14, 9))
    smt.plot.plt_matrix(smt.get_tops()[0], base_map=True, no_flow_layer=0, title='model top', ax=axs[0])
    smt.plot.plt_matrix(smt.get_bottoms()[-1], base_map=True, no_flow_layer=0, title='model bot', ax=axs[1])
    smt.plot.plt_matrix(smt.get_thickness().sum(axis=0), base_map=True, no_flow_layer=0, title='model thick', ax=axs[2])
    fig.tight_layout()


    for elv in poss_elvs:
        _plot_layer_surface_intersect(elv)
    plt.show()


def _plot_layer_surface_intersect(elv):
    fig, axs = plt.subplots(ncols=3, figsize=(14, 9))

    plt_arrays = {
        f'{elv} above surface': (smt.get_tops()[0] < elv, 1),
        f'thickness above {elv}': (smt.get_tops()[0] - elv, 30),
        f'thickness below {elv}': (elv - smt.get_bottoms()[-1], 30),
    }
    for ax, (k, v) in zip(axs, plt_arrays.items()):
        smt.plot.plt_matrix(v[0], base_map=True, no_flow_layer=1, ax=ax,
                            title=k, vmax=v[1])
    fig.tight_layout()


def _plot_xsection(poss_elvs):
    moraine_sect = ([1305740.4867037723, 1305895.0940012368], [5054567.5479282625, 5052753.69511441])
    lake_array = np.isfinite(get_lake_array())
    moraine = get_2d_moraine()
    all_wells = get_all_wells()
    all_wells = all_wells.loc[moraine[all_wells.i, all_wells.j]]
    all_wells = all_wells.loc[~all_wells.index.str.contains('hw')]
    high_freq = get_high_freq_head_targets(None, None).loc[:, 'g40_0415']
    high_freq = (high_freq.min(), high_freq.max())

    lake_levels = (338, 346)
    min_lake_levels = (327.6)
    plt_array = smt.get_model_zeros(True)
    plt_array[:, lake_array] = 1
    plt_array[:, moraine] = 2
    vert_ex = 100
    bba = 0.5
    printout = {
        'lake_levels': (327.6, 338, 346),
        'g40_0415': (high_freq)

    }
    fig, (ax, loc_ax) = plt.subplots(nrows=2, figsize=(14, 10), gridspec_kw=dict(height_ratios=(3, 2)))
    smt.plot.plt_slice(plt_array, *moraine_sect, plt_layer_slice=False,
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
        if i in ['g40_0178', 'g40_0368']:
            alpha = 1
        else:
            alpha = 0.6
        d = all_wells.loc[i, 'depth_elevation']
        printout[i] = d
        ax.axhline(d * vert_ex, color='grey', label=label, ls=(0, (1, 2)), alpha=alpha)
        yoff = -100
        if i in ['g40_0368', 'g40_0345']:
            yoff = 300
        loc_ax.annotate(i, (all_wells.nztmx.loc[i], all_wells.nztmy.loc[i] + yoff),
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
    for elv in poss_elvs:
        ax.axhline(elv * vert_ex, color='pink', label=f'elv: {elv}')
    ax.legend(loc='lower right')
    loc_ax.legend(loc='lower right')
    fig.tight_layout()
    print(printout)
    return fig, ax, loc_ax


if __name__ == '__main__':
    t = {
        'lake_levels': (327.6, 338, 346),
        'g40_0415': (326.0940868, 334.1174253),
        'g40_0016': 304.3712158203125,
        'g40_0026': 322.01910400390625,
        'g40_0104': 312.888427734375,
        'g40_0178': 316.17,
        'g40_0345': 328.5882897949219,
        'g40_0368': 318.58349609375,
        'g40_0413': 313.8}
    define_cutoffs([328, 335])


    # 328 as bottom of confining
    # paramaterise top?, start 335
    # does the elevation of the head cutoff matter???
