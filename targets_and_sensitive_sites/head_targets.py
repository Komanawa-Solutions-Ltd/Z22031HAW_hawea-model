"""
created matt_dumont 
on: 15/08/22
"""
import pandas as pd
from model_build.supporting_data_analysis import get_all_wells
from model_build.utils import select_resample
from project_base import processed_target_dir, base_target_dir


def get_single_head_targets():
    # from get_all_wells
    # todo, set indiciative times! how do I want to do this???
    raise NotImplementedError


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
    return outdata[outdata.loc[idx, 'date']]


def get_high_freq_head_targets(start_date, end_date, freq='D'):
    data_path = base_target_dir.joinpath('daily_head_obs.csv')
    data = pd.read_csv(data_path, comment='#')
    data.columns = [e.replace('/', '_').replace('Groundwater Level@', '').lower() for e in data.columns]
    data.loc[:, 'datetime'] = pd.to_datetime(data.loc[:, 'timestamp'], format='%d/%m/%Y %H:%M')
    data.set_index('datetime', inplace=True)
    data.drop(columns='timestamp', inplace=True)
    return select_resample(data, start_date, end_date, freq)



if __name__ == '__main__':
    t = get_high_freq_head_targets(None, None)
    get_low_freq_head_targets(None, None)
