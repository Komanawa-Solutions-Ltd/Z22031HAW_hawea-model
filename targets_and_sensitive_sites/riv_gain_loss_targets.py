"""
created matt_dumont 
on: 15/08/22
"""
from project_base import processed_target_dir, base_model_build_data_dir


# todo get jens to produce this data?
def get_hawea_gain_loss_targets():
    data_path = base_model_build_data_dir.joinpath('Hawea River - ORC Gaugings for Gain & Loss Estimation.xlsx')
