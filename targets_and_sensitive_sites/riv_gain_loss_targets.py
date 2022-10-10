"""
created matt_dumont 
on: 15/08/22
"""
import numpy as np
import pandas as pd

from project_base import processed_target_dir, base_model_build_data_dir
from model_build.supporting_data_analysis import get_river_loc_data
from model_build.project_model_tools import smt


def get_riv_target_locs(recalc=False):
    river_targets = range(1, 4)
    river_target_path = processed_target_dir.joinpath(f'river_target_locs.txt')

    if river_target_path.exists() and not recalc:
        out = {}
        temp = np.loadtxt(river_target_path).astype(int)
        for n in river_targets:
            out[n] = temp == n
        return out

    river_loc_data = get_river_loc_data(False)
    river_loc_data = smt.io.df_to_array(river_loc_data, 'gage')
    river_loc_data[np.isnan(river_loc_data)] = -1
    river_loc_data = river_loc_data.astype(int)
    out = {}
    save_out = smt.get_model_zeros()
    for n in river_targets:
        temp = river_loc_data == n
        save_out[temp] = n
        out[n] = temp
    np.savetxt(river_target_path, save_out.astype(int), fmt='%d')

    return out


def get_hawea_gain_loss_targets():
    # jens produced this data from the two concurrent gageings of the hawea river
    data_path = base_model_build_data_dir.joinpath('Hawea River - ORC Gaugings for Gain & Loss Estimation.xlsx')
    data = pd.read_excel(data_path, 'comp_read', comment='#')
    data.loc[:, 'datetime'] = pd.to_datetime(data.loc[:, 'date'], '%Y-%m-%d').dt.date
    data.set_index('datetime', inplace=True)
    data.loc[:, 'target_val'] = data.loc[:, 'gain_loss'] * 60 * 60 * 24  # convert from m3/s to m3/day
    data.loc[:, 'target_key'] = data.shortname.str.strip('S').astype(int)
    return data.loc[:, ['target_val', 'target_key']]

#TODO add NSTP AND NPER

if __name__ == '__main__':
    loc = get_riv_target_locs()
    targ = get_hawea_gain_loss_targets()
    pass
