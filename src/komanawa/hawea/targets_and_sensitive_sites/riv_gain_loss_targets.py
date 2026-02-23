"""
created matt_dumont 
on: 15/08/22
"""
import pickle # todo rm pickle...

import numpy as np
import pandas as pd

from komanawa.hawea.hawea_base import processed_target_dir, base_model_build_data_dir
from komanawa.hawea.model_build.supporting_data_analysis import get_river_loc_data, get_pumping_locs, get_historical_pumping_data
from komanawa.hawea.model_build.project_model_tools import smt, exclude_near_river_pumping


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
    data.loc[:, 'target_val'] *= -1  # switch from river gain to model gain
    data.loc[:, 'target_key'] = data.shortname.str.strip('S').astype(int)
    return data.loc[:, ['target_val', 'target_key']]


def get_hawea_gain_loss_nper(tdis, recalc=False):
    save_path = processed_target_dir.joinpath(f'hawea_r_targets-{tdis.name}.hdf')

    if save_path.exists() and not recalc:
        out = pd.read_hdf(save_path, key='data')
        assert isinstance(out, pd.DataFrame)
        return out

    targets = get_hawea_gain_loss_targets()
    if exclude_near_river_pumping:
        # add pumping removal
        pump_locs = get_pumping_locs(return_raw=True)
        pump_locs = pump_locs.loc[pump_locs.near_river]
        pumping_data = get_historical_pumping_data(targets.index.min(), targets.index.max())
        riv_target_locs = get_riv_target_locs()
        for k, array in riv_target_locs.items():
            temp = smt.io.array_to_df(array, 'dummy')
            temp = temp.loc[temp.dummy]
            temp_i = temp.i.values[np.newaxis]
            temp_j = temp.j.values[np.newaxis]
            t = ((pump_locs.i.values[:, np.newaxis] - temp_i) ** 2
                 + (pump_locs.j.values[:, np.newaxis] - temp_j) ** 2
                 ) ** 0.5
            pump_locs.loc[:, f'dist_r{k}'] = t.min(axis=1) * smt.grid_space
        temp = pump_locs.loc[:, [f'dist_r{k}' for k in riv_target_locs.keys()]]
        pump_locs.loc[:, 'riv_target'] = temp.values.argmin(axis=1) + 1
        pump_locs.loc[temp.min(axis=1) > 1500, 'riv_target'] = -1

        for k in riv_target_locs.keys():
            pump_keys = pump_locs.loc[pump_locs.riv_target == k].index
            for date in targets.index.unique():
                idx = (targets.index == date) & (targets.target_key == k)
                targets.loc[idx, 'target_val'] += pumping_data.loc[pd.to_datetime(date), pump_keys].sum()

    targets = tdis.add_nstp_nper_to_df(targets, action_on_duplicates='last')
    targets.to_hdf(save_path, key='data', complib='zlib', complevel=4)
    return targets


if __name__ == '__main__':
    from komanawa.hawea.optimisation.optimisation_period import tdis

    temp = get_hawea_gain_loss_nper(tdis, True)
    loc = get_riv_target_locs()
    targ = get_hawea_gain_loss_targets()
    pass
