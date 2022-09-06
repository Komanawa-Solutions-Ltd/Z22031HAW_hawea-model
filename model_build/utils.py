"""
created matt_dumont 
on: 31/08/22
"""
import pandas as pd
from matplotlib.cm import get_cmap


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


def get_colors(vals, cmap_name='tab10'):
    n_scens = len(vals)
    if n_scens < 20:
        cmap = get_cmap(cmap_name)
        colors = [cmap(e / (n_scens + 1)) for e in range(n_scens)]
    else:
        colors = []
        i = 0
        cmap = get_cmap(cmap_name)
        for v in vals:
            colors.append(cmap(i / 20))
            i += 1
            if i == 20:
                i = 0
    return colors
