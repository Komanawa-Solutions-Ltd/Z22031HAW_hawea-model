"""
created matt_dumont 
on: 9/02/23
"""
import pandas as pd
from model_build.utils import select_resample, fill_weekly_mean

def make_long_weekly_mean(data, start, stop, freq='W'):
    """
    make iso weekly mean dataset
    :param data: pd.series/dataframe with datetiem index
    :param start: start date
    :param stop: end date
    :param freq: pd frequecny code
    :return:
    """
    out_data = pd.DataFrame(index=pd.date_range(start, stop, freq='D'))
    out_data = pd.merge(out_data, data, 'left', right_index=True, left_index=True)
    out_data = fill_weekly_mean(out_data)
    out_data = select_resample(out_data, start, stop, freq)
    return out_data

