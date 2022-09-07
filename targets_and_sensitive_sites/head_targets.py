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
from model_build.zones import get_param_zones
from project_base import processed_target_dir, base_target_dir
from model_build.utils import get_colors


# todo it may be worth comparing recharge and lake levels... at a water year level to see how to apply
# targets that occur outside of period.

def get_single_head_targets():
    # from get_all_wells
    all_wells = get_all_wells()
    all_wells = all_wells.loc[all_wells.ibound > 0]
    param_zone = get_param_zones()
    all_wells.loc[:, 'param_zone'] = param_zone[all_wells.i, all_wells.j]

    idx = (all_wells.param_zone < 0) & (all_wells.quality_code < 3)
    all_wells = all_wells.loc[~idx]
    all_wells = all_wells.loc[all_wells.quality_code > 0]

    # todo, set indiciative times! how do I want to do this???
    warnings.warn('not finished, still need to set indicative times')

    return all_wells


def get_2011_piezo_survey(recalc=False):
    # piezo survey conducted 21-sept-2011
    data_path = base_target_dir.joinpath('Peizo Survey 20Sept2011.xlsx')
    processed_path = processed_target_dir.joinpath('piezo_targets.csv')

    if processed_path.exists() and not recalc:
        data = pd.read_csv(processed_path)
        # todo manage types
        raise NotImplementedError
        return data

    data = pd.read_excel(data_path, 'Appendix Table')
    data.rename(columns={'Easting': 'nztmx', 'Northing': 'nztmy', 'Water level elevation': 'head'}, inplace=True)
    row, col = smt.convert_coords_to_matix(data.nztmx, data.nztmy, coords_out_domain='coerce')
    data.loc[:, 'i'] = row
    data.loc[:, 'j'] = col
    data = data.loc[data.i >= 0]
    ibound = smt.get_no_flow(0)
    data.loc[:, 'ibound'] = ibound[data.i, data.j]
    data = data.loc[data.ibound > 0]

    # todo set indicative times! how do I want to do this
    warnings.warn('not finished, still need to set indicative times')
    data.to_csv(processed_path)
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
            ax.scatter(temp.nztmx, temp.nztmy, color=c, label=f'single targets qc: {qc}', marker='d', alpha=alpha)

        # add scott piezo locs
        piezo = get_2011_piezo_survey(recalc=True)
        ax.scatter(piezo.nztmx, piezo.nztmy, color='orange', marker='s', alpha=alpha, label='piezo 2011')

        # add ngmp wells
        t = get_low_freq_head_targets(None, None)
        wells = all_wells.loc[t.well.unique()]
        ax.scatter(wells.nztmx, wells.nztmy, color='b', marker='p', label='mod_freq')

        # add high frequency
        t = get_high_freq_head_targets(None, None)
        wells = all_wells.loc[t.keys()]
        ax.scatter(wells.nztmx, wells.nztmy, color='magenta', marker='*', label='high_freq')

        print('plotting all head targets')
        ax.set_title('all head targets')
        ax.legend()


    elif how == 'incl':
        fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, color_bar=False,
                                      base_map=True, no_flow_layer=0)

        all_wells = get_all_wells()
        single_targets = get_single_head_targets()
        all_wells = all_wells.loc[all_wells.ibound > 0]
        qcs = all_wells.loc[:, 'quality_code'].unique()
        colors = get_colors(qcs)
        for qc, c in zip(qcs, colors):
            temp = single_targets.loc[single_targets.quality_code == qc]
            ax.scatter(temp.nztmx, temp.nztmy, color=c, label=f'single targets qc: {qc}', marker='d', alpha=alpha)

        # add scott piezo locs
        piezo = get_2011_piezo_survey(recalc=True)
        ax.scatter(piezo.nztmx, piezo.nztmy, color='orange', marker='s', alpha=alpha, label='piezo 2011')

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
        ax.set_title('included head targets')

        print('plotting head targets included in the model')
    else:
        raise NotImplementedError


def export_incl_head_target_locs():
    outdata = []

    all_wells = get_all_wells()
    single_targets = get_single_head_targets()
    all_wells = all_wells.loc[all_wells.ibound > 0]
    qcs = single_targets.loc[:, 'quality_code'].unique()
    colors = get_colors(qcs)
    for qc, c in zip(qcs, colors):
        temp = single_targets.loc[single_targets.quality_code == qc]
        temp_out = {'nztmx': temp.nztmx.values, 'nztmy': temp.nztmy.values}
        temp_out = pd.DataFrame(temp_out)
        temp_out.loc[:, 'type'] = f'single_qc{qc}'
        outdata.append(temp_out)

    # add scott piezo locs
    piezo = get_2011_piezo_survey(recalc=True)
    temp_out = {'nztmx': piezo.nztmx.values, 'nztmy': piezo.nztmy.values}
    temp_out = pd.DataFrame(temp_out)
    temp_out.loc[:, 'type'] = 'piezo_2011'
    outdata.append(temp_out)


    # add ngmp wells
    t = get_low_freq_head_targets(None, None)
    wells = all_wells.loc[t.well.unique()]
    temp_out = {'nztmx': wells.nztmx.values, 'nztmy': wells.nztmy.values}
    temp_out = pd.DataFrame(temp_out)
    temp_out.loc[:, 'type'] = 'mod_freq'
    outdata.append(temp_out)

    # add high frequency
    t = get_high_freq_head_targets(None, None)
    wells = all_wells.loc[t.keys()]
    temp_out = {'nztmx': wells.nztmx.values, 'nztmy': wells.nztmy.values}
    temp_out = pd.DataFrame(temp_out)
    temp_out.loc[:, 'type'] = 'high_freq'
    outdata.append(temp_out)

    outdata = pd.concat(outdata)
    outdata.to_csv(processed_target_dir.joinpath('head_target_locations.csv'))

if __name__ == '__main__':
    plot_head_targets()
    plot_head_targets(how='incl')
    export_incl_head_target_locs()
    smt.plot.show()
