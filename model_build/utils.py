"""
created matt_dumont 
on: 31/08/22
"""
import pandas as pd


def select_resample(data, start_date, end_date, frequency, func='mean'):
    ht = data.index
    if start_date is None:
        start_date = ht.min()
    else:
        if pd.to_datetime(start_date) < ht.min():
            raise ValueError(f'start date {start_date} earlier than dataset start date: {ht.min()}')
    if end_date is None:
        end_date = ht.max()
    else:
        if pd.to_datetime(end_date) > ht.max():
            raise ValueError(f'end date {end_date} later than dataset start date: {ht.max()}')

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    idx = (data.index >= start_date) & (data.index <= end_date)
    outdata = data.loc[idx].resample(frequency).agg(func)

    return outdata
