"""
created matt_dumont 
on: 9/12/22
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from komanawa.hawea.hawea_base import base_model_build_data_dir, processed_model_build_data_dir
from komanawa.modeltools.model_tools.plot_borelogs import plot_borelogs, plot_single_log, make_single_log_handles # keynote private repo
from komanawa.hawea.model_build.supporting_data_analysis.all_wells import get_all_wells
from komanawa.hawea.model_build.project_model_tools import smt, get_2d_moraine, get_lake_array


def read_borelogs_metadata(recalc=False):
    save_path = processed_model_build_data_dir.joinpath('borelogs_metadata.hdf')
    if save_path.exists() and not recalc:
        raise NotImplementedError

    bore_logs = pd.read_csv(base_model_build_data_dir.joinpath('ORCBores - Lithology.csv'))
    bore_logs.loc[:, 'well_id'] = bore_logs.loc[:, 'Well Number'].str.replace('/', '_').str.lower()
    bore_logs = bore_logs.dropna(subset=['well_id'])
    bore_logs.loc[:, 'bot'] = bore_logs.loc[:, 'Depth']
    bore_logs = bore_logs.sort_values(['well_id', 'bot'])
    for n in bore_logs.loc[:, 'well_id']:
        idx = bore_logs.well_id == n
        bore_logs.loc[idx, 'top'] = bore_logs.loc[idx, 'bot'].shift(1)
    bore_logs.loc[bore_logs.top.isna(), 'top'] = 0
    all_wells = get_all_wells(False)
    all_wells = all_wells.loc[all_wells.ibound == 1]
    joint_names = list(set(all_wells.index).intersection(bore_logs.well_id))

    well_metadata = all_wells.loc[joint_names]
    bore_logs = bore_logs.loc[np.isin(bore_logs.well_id, joint_names)]
    bore_logs.loc[:, 'unit'] = bore_logs.loc[:, 'Description'].str[0:20]
    # convert to elevation
    for k in ['top', 'bot']:
        bore_logs.loc[:, k] = bore_logs.well_id.replace(well_metadata.elevation.to_dict()) - bore_logs.loc[:, k]

    well_metadata.loc[:, 'x'] = well_metadata.nztmx
    well_metadata.loc[:, 'y'] = well_metadata.nztmy

    return well_metadata, bore_logs


def plot_all_borelogs():
    well_metadata, bore_logs = read_borelogs_metadata()
    fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
    plot_borelogs(ax, well_metadata, bore_logs, borelog_scale=10, log_width=50)
    plt.show()


def plot_moraine_wells():
    well_metadata, bore_logs = read_borelogs_metadata()
    moraine = get_2d_moraine()
    lake = get_lake_array()
    well_metadata = well_metadata.loc[
        moraine[well_metadata.i, well_metadata.j] | np.isfinite(lake[well_metadata.i, well_metadata.j])]
    bore_logs = bore_logs.loc[np.isin(bore_logs.well_id, well_metadata.index)]

    # manually add the QLDC water supply bore (missing in database)
    wid = 'scotts_beach'
    well_elv = 358
    top = np.array((0, 0.5, 1.5, 4, 24, 37, 42, 47, 51)) * -1 + well_elv
    bot = np.array((0.5, 1.5, 4, 24, 37, 42, 47, 51, 55)) * -1 + well_elv
    unit = [
        'top soil',
        'gravel',
        'yellow clay',
        'silt some gravel',
        'light clay bound gravel',
        'light clay bound gravel',
        'sandy gravel',
        'very sandy gravel',
        'sand',
    ]
    well_metadata.loc[wid, ['nztmx', 'nztmy']] = 1303346, 5053599
    bore_logs = pd.concat((bore_logs,
                           pd.DataFrame({'top': top, 'bot': bot, 'unit': unit, 'well_id': np.full(top.shape, wid)})))

    mapper = pd.read_csv(base_model_build_data_dir.joinpath('moraine_units.csv'), index_col=1).iloc[:, -1].to_dict()
    bore_logs.loc[:, 'label'] = bore_logs.loc[:, 'unit']
    bore_logs.loc[:, 'unit'] = bore_logs.loc[:, 'unit'].replace(mapper)
    colors = {
        'clay': 'grey', 'silt': 'tan', 'sand': 'coral', 'gravel': 'navajowhite', 'boulder': 'lightgrey',
        'topsoil': 'saddlebrown'
    }
    hatch = {
        'clay': 'X', 'silt': '-', 'sand': '.', 'gravel': 'o', 'boulder': 'O', 'topsoil': '/'
    }
    bore_logs.loc[:, 'color'] = bore_logs.loc[:, 'unit'].replace(colors)
    bore_logs.loc[:, 'hatch'] = bore_logs.loc[:, 'unit'].replace(hatch)

    fig = plt.figure(figsize=(17, 10))
    gs = fig.add_gridspec(2, 4, height_ratios=(3, 1))
    map_ax = fig.add_subplot(gs[1, :])
    smt.plot.plt_basemap(ax=map_ax)
    legend_data = {}
    wells = [
        'scotts_beach',
        'g40_0413',
        'g40_0178',
        'g40_0368',
    ]
    for i, wid in enumerate(wells):
        print(wid)
        ax = fig.add_subplot(gs[0, i])
        yoff = 200
        if wid == 'g40_0178':
            yoff *= -1
        map_ax.text(well_metadata.nztmx.loc[wid], well_metadata.nztmy.loc[wid] + yoff, wid,
                    bbox=dict(facecolor='w', alpha=0.6))
        plot_single_log(ax, bore_logs.loc[bore_logs.well_id == wid], legend_data, 'label', bba=1)
        ax.set_ylim(300, 365)
    handles = make_single_log_handles(legend_data)
    ax.legend(handles=handles)
    map_ax.scatter(well_metadata.nztmx, well_metadata.nztmy, color='r')
    map_ax.set_xlim(1.3e6, 1.308e6)
    map_ax.set_ylim(5.052e6, 5.055e6)
    fig.tight_layout()
    plt.show()


if __name__ == '__main__':
    # plot_all_borelogs()
    plot_moraine_wells()
