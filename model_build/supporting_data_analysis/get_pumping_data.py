"""
created matt_dumont 
on: 2/08/22
"""

# todo get the data and make some diagnostic plots to check the data.
import pandas as pd
import numpy as np
from project_base import base_model_build_data_dir, processed_model_build_data_dir
from model_build.utils import select_resample
from model_build.project_model_tools import smt
from model_build.supporting_data_analysis.map_flowmeter_to_wells import get_well_flowmeter_mapper

default_recalc = False

# keynote why is it so hard to link well numbers to flow meter number...

def _load_usage_data():
    data_path = base_model_build_data_dir.joinpath(
        'water_permit_meter_results_2022-07-20/water_permit_meter_daily_data_2022-07-20.csv')
    data = pd.read_csv(data_path, low_memory=False)
    data.loc[:, 'date'] = pd.to_datetime(data.loc[:, 'date'])
    return data


def get_historical_pumping_data(start_date, end_date, frequency='D', recalc=False):
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
        return data

    pumping_key = 'gw_allo_usage_est'  # todo correct key???
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
    outdata.to_csv(processed_path)
    return outdata


def get_pumping_locs():
    data = get_well_flowmeter_mapper()
    data = data.loc[:, ['use_x', 'use_y', 'i', 'j', 'k']]
    return data


def data_checks(): # TODO start here need to get some of these
    raise NotImplementedError


if __name__ == '__main__':
    get_pumping_locs()
    get_historical_pumping_data(None, None, recalc=False)
