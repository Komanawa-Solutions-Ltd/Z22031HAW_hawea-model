"""
created matt_dumont 
on: 15/08/22
"""
from project_base import processed_target_dir, base_target_dir

def get_single_head_targets():
    raise NotImplementedError

def get_low_freq_head_targets():
    raise NotImplementedError

def get_high_freq_head_targets():
    data_path = base_target_dir.joinpath('daily_head_obs.csv')
    raise NotImplementedError