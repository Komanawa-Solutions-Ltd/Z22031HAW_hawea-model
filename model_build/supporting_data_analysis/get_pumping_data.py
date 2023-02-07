"""
created matt_dumont 
on: 2/08/22
"""

import pandas as pd
import numpy as np
from project_base import base_model_build_data_dir, processed_model_build_data_dir
from model_build.utils import select_resample, get_colors
from model_build.supporting_data_analysis.map_flowmeter_to_wells import get_well_flowmeter_mapper
from model_build.zones import get_model_zones
from model_build.project_model_tools import exclude_near_river_pumping, get_low_cond_array, get_lake_array, \
    get_2d_moraine, smt

default_recalc = False


# keynote why is it so hard to link well numbers to flow meter number...

def _load_usage_data():
    data_path = base_model_build_data_dir.joinpath(
        'water_permit_meter_results_2022-07-20/water_permit_meter_daily_data_2022-07-20.csv')
    data = pd.read_csv(data_path, low_memory=False)
    data.loc[:, 'date'] = pd.to_datetime(data.loc[:, 'date'])
    return data


def get_historical_pumping_data(start_date, end_date, frequency='D', recalc=False, func='mean'):
    """

    :param start_date: none or date like
    :param end_date: none or date like
    :param frequency: pd freq codes
    :return:
    """
    processed_path = processed_model_build_data_dir.joinpath('historical_pumping.csv')
    if processed_path.exists() and not recalc:
        data = pd.read_csv(processed_path)
        data.loc[:, 'date'] = pd.to_datetime(data.loc[:, 'date'])
        data.set_index('date', inplace=True)
        return select_resample(data, start_date, end_date, frequency, func=func)

    pumping_key = 'gw_allo_usage_est'
    pumping_data = _load_usage_data()
    pumping_data.loc[:, 'uname'] = pumping_data.loc[:, 'permit_id'] + '_' + pumping_data.loc[:, 'water_meter_no']
    well_names = get_well_flowmeter_mapper()
    well_names.loc[:, 'uname'] = well_names.loc[:, 'permit_id'] + '_' + well_names.loc[:, 'water_meter_no']

    outdata = pd.DataFrame(index=pd.unique(pumping_data.loc[:, 'date']), columns=well_names.index)
    outdata.index.name = 'date'
    duplicated = well_names.index[well_names.loc[:, ['permit_id', 'water_meter_no']].duplicated(keep=False)]
    unique_names = well_names.index[~well_names.loc[:, ['permit_id', 'water_meter_no']].duplicated(keep=False)]

    for n in unique_names:
        idx = np.in1d(pumping_data.loc[:, 'uname'], well_names.loc[n, 'uname'])
        temp = pumping_data.loc[idx, ['date', pumping_key]].set_index('date')
        outdata.loc[temp.index, n] = temp.values[:, 0]

    for uname in pd.unique(well_names.loc[duplicated, 'uname']):
        use_well_names = well_names.index[np.in1d(well_names.uname, uname)]
        assert not np.in1d(use_well_names, unique_names).any()
        temp = pumping_data.loc[pumping_data.uname == uname]
        temp = temp.groupby('date').sum().loc[:, pumping_key]
        for n in use_well_names:
            outdata.loc[temp.index, n] = temp.values / len(use_well_names)

    assert np.isclose(pumping_data.groupby('date').sum().loc[:, pumping_key], outdata.sum(axis=1)).all()
    outdata = outdata.loc[:, well_names.loc[well_names.ibound == 1].index]
    outdata.drop(columns=['w_068', 'w_025'], inplace=True)
    outdata.to_csv(processed_path)
    return select_resample(outdata, start_date, end_date, frequency, func=func)


def get_pump_to_l1(recalc=False):
    save_path = processed_model_build_data_dir.joinpath('pump_mover.txt')
    if save_path.exists() and not recalc:
        out = np.loadtxt(save_path).astype(int) == 1
    else:
        out = np.isfinite(
            smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('pump_to_layer_2.shp'), 'id',
                                             alltouched=True))
        np.savetxt(save_path, out.astype(int), '%d')
    return out


def get_pumping_locs(return_raw=False):
    data = get_well_flowmeter_mapper()
    idx = get_low_cond_array()
    moraine = get_2d_moraine()
    lake_array = get_lake_array()
    for l in range(len(idx)):
        idx[l] = idx[l] | np.isfinite(lake_array)
    idx[0] = idx[0] | moraine
    data = data.loc[:, ['ibound', 'use_x', 'use_y', 'i', 'j', 'k']]
    data = data.loc[data.ibound == 1]
    data.drop(['w_068', 'w_025'], inplace=True)
    assert not idx[data.k, data.i, data.j].any(), 'pumping in lake or low cond cells, or thin layer'

    zones = get_model_zones()
    for k, v in zones.items():
        data.loc[:, k] = v[data.i, data.j]

    # move hawea flat bores to layer 1 so that they cannot go dry (reduce model instability)
    idx = get_pump_to_l1()[data.i, data.j] & (data.k == 0)
    data.loc[idx, 'k'] = 1
    if return_raw:
        return data
    if exclude_near_river_pumping:
        data = data.loc[~data.near_river]
    return data


def data_checks():
    import matplotlib.pyplot as plt
    from model_build.project_model_tools import smt
    pumping_y = get_historical_pumping_data(None, None, 'Y')
    locs = get_pumping_locs()
    zones = get_model_zones()
    locs.loc[:, 'near_river'] = zones['near_river'][locs.i, locs.j]
    fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, base_map=True, no_flow_layer=0, color_bar=False)
    for t, x, y in locs.loc[:, ['use_x', 'use_y']].itertuples(True, None):
        i = np.random.randint(-50, 50)
        ax.scatter(x + i, y + i)
        ax.text(x + i, y + i, t)

    fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, base_map=True, no_flow_layer=0, color_bar=False)
    cb = ax.scatter(locs.use_x, locs.use_y, c=pumping_y.mean().loc[locs.index], cmap='magma',
                    s=pumping_y.mean().loc[locs.index])
    ax.set_title('pumping in model domain')
    fig.colorbar(cb)

    use_locs = locs.loc[locs.near_river]
    fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, base_map=True, no_flow_layer=0, color_bar=False)
    cb = ax.scatter(use_locs.use_x, use_locs.use_y, c=pumping_y.mean().loc[use_locs.index], cmap='magma',
                    s=pumping_y.mean().loc[use_locs.index])
    ax.set_title('pumping in "near_river" zone')
    fig.colorbar(cb)

    use_locs = locs.loc[~locs.near_river]
    fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, base_map=True, no_flow_layer=0, color_bar=False)
    cb = ax.scatter(use_locs.use_x, use_locs.use_y, c=pumping_y.mean().loc[use_locs.index], cmap='magma',
                    s=pumping_y.mean().loc[use_locs.index])
    ax.set_title('pumping out of "near_river" zone')
    fig.colorbar(cb)

    # plot pumping over time
    pumping_m = get_historical_pumping_data(None, None, 'M')
    zones = get_model_zones()
    for z in zones:
        fig, (ax, ax2) = plt.subplots(nrows=2, sharex=True)
        ax.set_title(z)

        temp = pumping_m.loc[:, locs.index[locs[z]]]
        ax.plot(temp.sum(axis=1).index, temp.sum(axis=1).values)

        ax2.set_title(z + ' individual wells')
        keys = temp.keys()
        colors = get_colors(keys)
        for k, c in zip(keys, colors):
            ax2.plot(temp.index, temp[k], c=c, label=k)
        ax2.legend()

    fig, (ax, ax2) = plt.subplots(nrows=2, sharex=True)
    z = 'full domain'
    ax.set_title(z)

    temp = pumping_m
    ax.plot(temp.sum(axis=1).index, temp.sum(axis=1).values)

    ax2.set_title(z + ' individual wells')
    keys = temp.keys()
    colors = get_colors(keys)
    for k, c in zip(keys, colors):
        ax2.plot(temp.index, temp[k], c=c, label=k)
    ax2.legend()

    fig, (ax, ax2) = plt.subplots(nrows=2, sharex=True)
    z = 'exclude near river and sandy point'
    ax.set_title(z)

    temp = pumping_m.loc[:, locs.index[~locs['near_river'] & ~locs['sandypoint']]]
    ax.plot(temp.sum(axis=1).index, temp.sum(axis=1).values)

    ax2.set_title(z + ' individual wells')
    keys = temp.keys()
    colors = get_colors(keys)
    for k, c in zip(keys, colors):
        ax2.plot(temp.index, temp[k], c=c, label=k)
    ax2.legend()

    smt.plot.show()


if __name__ == '__main__':
    locs = get_pumping_locs()
    get_model_zones(True)
    data_checks()
    flow_mapper = get_well_flowmeter_mapper(recalc=True)
    flow = get_historical_pumping_data(None, None, recalc=True)
