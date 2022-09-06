"""
created matt_dumont 
on: 15/08/22
"""
import warnings

import numpy as np
import pandas as pd
from model_build.supporting_data_analysis import get_all_wells
from model_build.project_model_tools import smt
from model_build.utils import select_resample
from project_base import processed_target_dir, base_target_dir
from model_build.utils import get_colors


# todo it may be worth comparing recharge and lake levels... at a water year level to see how to apply
# targets that occur outside of period.

def get_single_head_targets():
    # from get_all_wells
    all_wells = get_all_wells()
    all_wells = all_wells.loc[all_wells.ibound > 0]
    # todo, set indiciative times! how do I want to do this???
    warnings.warn('not finished, still need to set indicative times')
    raise NotImplementedError


def get_2011_piezo_survey():  # todo get these data
    # piezo survey conducted 21-sept-2011
    data_path = base_target_dir.joinpath('Peizo Survey 20Sept2011.xlsx')
    # todo set indicative times! how do I want to do this
    data = pd.read_excel(data_path, 'Appendix Table')
    data.rename(columns={'Easting': 'nztmx', 'Northing': 'nztmy', 'Water level elevation': 'head'}, inplace=True)
    row, col = smt.convert_coords_to_matix(data.nztmx, data.nztmy, coords_out_domain='coerce')
    data.loc[:, 'i'] = row
    data.loc[:, 'j'] = col
    data = data.loc[data.i >= 0]
    ibound = smt.get_no_flow(0)
    data.loc[:, 'ibound'] = ibound[data.i, data.j]
    data = data.loc[data.ibound > 0]

    warnings.warn('not finished, still need to set indicative times')
    return data


def get_low_freq_head_targets(start_date, end_date):
    data_path = base_target_dir.joinpath('NGMP bore fluctuations 1996 - 2019.csv')
    data = pd.read_csv(data_path)
    outdata = []
    for k in ['G40/0120', 'G40/0129']:
        temp = data.loc[:, [f'{k}_date', f'{k}_wl']].dropna()
        temp.loc[:, 'date'] = pd.to_datetime(temp.loc[:, f'{k}_date'], format='%d-%b-%Y').dt.date
        temp.rename(columns={f'{k}_wl': 'level'}, inplace=True)
        temp.loc[:, 'well'] = k.lower().replace('/', '_')
        outdata.append(temp.loc[:, ['date', 'well', 'level']])

    outdata = pd.concat(outdata)

    if start_date is None:
        start_date = outdata.loc[:, 'date'].min()
    if end_date is None:
        end_date = outdata.loc[:, 'date'].max()
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()

    idx = (outdata.loc[:, 'date'] >= start_date) & (outdata.loc[:, 'date'] <= end_date)
    return outdata[idx]


def get_high_freq_head_targets(start_date, end_date, freq='D'):
    data_path = base_target_dir.joinpath('daily_head_obs.csv')
    data = pd.read_csv(data_path, comment='#')
    data.columns = [e.replace('/', '_').replace('Groundwater Level@', '').lower() for e in data.columns]
    data.loc[:, 'datetime'] = pd.to_datetime(data.loc[:, 'timestamp'], format='%d/%m/%Y %H:%M')
    data.set_index('datetime', inplace=True)
    data.drop(columns='timestamp', inplace=True)
    return select_resample(data, start_date, end_date, freq)


def plot_head_targets(how='all'):
    alpha = 0.8
    if how == 'all':
        fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, color_bar=False,
                                      base_map=True, no_flow_layer=0)

        all_wells = get_all_wells()
        all_wells = all_wells.loc[all_wells.ibound > 0]
        qcs = all_wells.loc[:, 'quality_code'].unique()
        colors = get_colors(qcs)
        for qc, c in zip(qcs, colors):
            temp = all_wells.loc[all_wells.quality_code == qc]
            ax.scatter(temp.nztmx, temp.nztmy, color=c, label=f'drill data: {qc}', marker='d', alpha=alpha)

        # add scott piezo locs
        piezo = get_2011_piezo_survey()
        ax.scatter(piezo.nztmx, piezo.nztmy, color='orange', marker='s', alpha=alpha, label='piezo')

        # add ngmp wells
        t = get_low_freq_head_targets(None, None)
        wells = all_wells.loc[t.well.unique()]
        ax.scatter(wells.nztmx, wells.nztmy, color='b', marker='p', label='mod_freq')

        # add high frequency
        t = get_high_freq_head_targets(None, None)
        wells = all_wells.loc[t.keys()]
        ax.scatter(wells.nztmx, wells.nztmy, color='magenta', marker='*', label='high_freq')

        print('plotting all head targets')
        ax.legend()
        smt.plot.show()

    elif how == 'incl':
        # todo this is a work in progress

        print('plotting head targets included in the model')
        raise NotImplementedError
    else:
        raise NotImplementedError

# todo break the model into domains (sandy point, mangawhera, rest) so I can treat different dirfferent areas differnety for head targets.

if __name__ == '__main__':
    plot_head_targets()
