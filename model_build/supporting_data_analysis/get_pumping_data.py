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
# keynote why is it so hard to link well numbers to flow meter number...

# todo how does MNwell handle 2 feature in the same cell.

def _load_usage_data():
    data_path = base_model_build_data_dir.joinpath(
        'water_permit_meter_results_2022-07-20/water_permit_meter_daily_data_2022-07-20.csv')
    data = pd.read_csv(data_path, low_memory=False)
    data.loc[:, 'date'] = pd.to_datetime(data.loc[:, 'date'])
    return data


def get_historical_pumping_data(start_date, end_date, frequency='D'):
    """

    :param start_date: none or date like
    :param end_date: none or date like
    :param frequency: pd freq codes
    :return:
    """
    pumping_data = _load_usage_data()
    # todo make wide format, but need to see if any of the gallaries are classed as sw?, I need locations for this.

    raise NotImplementedError


def get_pumping_locs(recalc=default_recalc):
    # todo
    # * PumpsHawea seems to be the site name to consent ID, to easting, northing.  This looks like Watermeter data
    # * todo no Z info, does not seem to have well information, talk to Jens
    # *

    raise NotImplementedError


def data_checks():
    raise NotImplementedError


def get_well_flows(start_date, end_date, frequency='D'):
    raise NotImplementedError


if __name__ == '__main__':
    get_pumping_locs()
    get_historical_pumping_data(None, None)
