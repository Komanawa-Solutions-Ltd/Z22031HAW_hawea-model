"""
created matt_dumont 
on: 31/08/22
"""
import warnings

import pandas as pd
from matplotlib.cm import get_cmap


def select_resample(data, start_date, end_date, frequency, func='mean', start_ends_out_bounds='raise'):
    assert start_ends_out_bounds in ['raise', 'warn', 'pass']
    ht = data.index
    if start_date is None:
        start_date = ht.min()
    else:
        if pd.to_datetime(start_date) < ht.min():
            if start_ends_out_bounds =='raise':
                raise ValueError(f'start date {start_date} earlier than dataset start date: {ht.min()}')
            elif start_ends_out_bounds =='warn':
                warnings.warn(f'start date {start_date} earlier than dataset start date: {ht.min()}')
            elif start_ends_out_bounds =='pass':
                pass
            else:
                raise ValueError('cant get here')

    if end_date is None:
        end_date = ht.max()
    else:
        if pd.to_datetime(end_date) > ht.max():
            if start_ends_out_bounds =='raise':
                raise ValueError(f'end date {end_date} earlier than dataset start date: {ht.max()}')
            elif start_ends_out_bounds =='warn':
                warnings.warn(f'end date {end_date} earlier than dataset start date: {ht.max()}')
            elif start_ends_out_bounds =='pass':
                pass
            else:
                raise ValueError('cant get here')

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


def plot_1_to_1(ax, **kwargs):
    xs = ax.get_xlim()
    ys = ax.get_ylim()
    limits = []
    limits.extend(xs)
    limits.extend(ys)
    use_limits = (min(limits), max(limits))
    ax.plot(limits, limits, **kwargs)



int_season_mapper = {
    12: 2,
    1: 2,
    2: 2,
    3: 3,
    4: 3,
    5: 3,
    6: 4,
    7: 4,
    8: 4,
    9: 1,
    10: 1,
    11: 1,

}
season_mapper = {
    12: 'summer',
    1: 'summer',
    2: 'summer',
    3: 'autumn',
    4: 'autumn',
    5: 'autumn',
    6: 'winter',
    7: 'winter',
    8: 'winter',
    9: 'spring',
    10: 'spring',
    11: 'spring',
}
