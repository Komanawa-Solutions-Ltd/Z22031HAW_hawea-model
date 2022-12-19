"""
created matt_dumont 
on: 4/10/22
"""
import pandas as pd
from model_build.supporting_data_analysis import get_all_wells
from model_build.zones import get_param_zones
from model_build.utils import select_resample
from project_base import base_target_dir


def get_single_target_data():
    # from get_all_wells
    all_wells = get_all_wells()
    all_wells = all_wells.loc[all_wells.ibound > 0]
    param_zone = get_param_zones()
    all_wells.loc[:, 'param_zone'] = param_zone[all_wells.i, all_wells.j]

    idx = (all_wells.param_zone < 0) & (all_wells.quality_code < 3)
    all_wells = all_wells.loc[~idx]
    all_wells = all_wells.loc[all_wells.quality_code > 0]
    return all_wells


def get_high_freq_head_targets(start_date, end_date, freq='D'):
    data_path = base_target_dir.joinpath('daily_head_obs.csv')
    data = pd.read_csv(data_path, comment='#')
    data.columns = [e.replace('/', '_').replace('Groundwater Level@', '').lower() for e in data.columns]
    data.loc[:, 'datetime'] = pd.to_datetime(data.loc[:, 'timestamp'], format='%d/%m/%Y %H:%M')
    data.set_index('datetime', inplace=True)
    data.drop(columns='timestamp', inplace=True)
    return select_resample(data, start_date, end_date, freq)
