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

default_recalc = False


# todo how does MNwell handle 2 feature in the same cell.

def get_historical_pumping_data(start_date, end_date, frequency='D'):
    """

    :param start_date: none or date like
    :param end_date: none or date like
    :param frequency: pd freq codes
    :return:
    """
    pumping_data = pd.read_csv(base_model_build_data_dir.joinpath('water_permit_meter_results_2022-07-20',
                                                            'water_permit_meter_daily_data_2022-07-20.csv'),
                               low_memory=False)
    pumping_data.loc[:, 'datetime'] = dt = pd.to_datetime(pumping_data.loc[:, 'date'])
    pumping_data.drop(columns='date', inplace=True)
    pumping_data.set_index('datetime', inplace=True)

    if start_date is None:
        start_date = dt.min()
    if end_date is None:
        end_date = dt.max()

    idx = (dt >= start_date) & (dt <= end_date)
    keep_cols = ['permit_id', 'water_meter_no', 'gw_allo_usage_est']
    # todo I need to run a groupby here...
    use_data = pumping_data.loc[idx].resample(frequency)  # todo how to run different aggs...
    # todo select_resample(outdata, start_date, end_date, frequency, 'mean')
    raise NotImplementedError


def get_pumping_locs(recalc=default_recalc):
    # todo
    # * PumpsHawea seems to be the site name to consent ID, to easting, northing.  This looks like Watermeter data
    # * todo no Z info, does not seem to have well information, talk to Jens
    # *

    raise NotImplementedError


def data_checks():
    pumping_data = pd.read_csv(base_model_build_data_dir.joinpath('water_permit_meter_results_2022-07-20',
                                                            'water_permit_meter_daily_data_2022-07-20.csv'),
                               low_memory=False)
    pumping_data.loc[:, 'datetime'] = dt = pd.to_datetime(pumping_data.loc[:, 'date'])
    pumping_data.drop(columns='date', inplace=True)
    pumping_data.set_index('datetime', inplace=True)

    metadata = pd.read_csv(base_model_build_data_dir.joinpath('PumpsHawea.csv'), encoding='ISO-8859-1')
    # water meters are unique in this dataset

    # todo do we have all of the location data???, nope missing 72 of 119 in the pumping data...
    # I dont really trust the metadata (PumpsHawea.csv) # todo discuss with Jens
    wms = ['WM' + str(e) for e in pumping_data.water_meter_no.unique()]
    idx = ~ np.in1d(wms, metadata.SiteName)
    print(np.array(wms)[idx])
    pass
    raise NotImplementedError


def get_well_flows(start_date, end_date, frequency='D'):
    raise NotImplementedError


if __name__ == '__main__':
    data_checks()
