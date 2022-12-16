"""
created matt_dumont 
on: 9/12/22
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from project_base import base_model_build_data_dir, processed_model_build_data_dir
from model_tools.plot_borelogs import plot_borelogs, plot_single_log
from model_build.supporting_data_analysis.all_wells import get_all_wells
from model_build.project_model_tools import smt


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
    all_wells = all_wells.loc[all_wells.ibound==1]
    joint_names = list(set(all_wells.index).intersection(bore_logs.well_id))

    well_metadata = all_wells.loc[joint_names]
    bore_logs = bore_logs.loc[np.in1d(bore_logs.well_id, joint_names)]
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


if __name__ == '__main__':
    plot_all_borelogs()
