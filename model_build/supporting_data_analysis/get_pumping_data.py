"""
created matt_dumont 
on: 2/08/22
"""

# todo get the data and make some diagnostic plots to check the data.
import pandas as pd
from project_base import base_model_data_dir, processed_model_data_dir

default_recalc = False


def get_historical_pumping_data(start_date, end_date, frequency='D'):
    """

    :param start_date: none or date like
    :param end_date: none or date like
    :param frequency: pd freq codes
    :return:
    """
    pumping_data = pd.read_csv(base_model_data_dir.joinpath('water_permit_meter_results_2022-07-20',
                                                            'water_permit_meter_daily_data_2022-07-20.csv'))
    pumping_data.loc['datetime'] = dt = pd.to_datetime(pumping_data.loc[:, 'date'])
    pumping_data.drop(columns='date', inplace=True)
    pumping_data.set_index('datetime', inplace=True)

    if start_date is None:
        start_date = dt.min()
    if end_date is None:
        end_date = dt.max()

    idx = (dt>=start_date) and (dt <= end_date)
    keep_cols = ['permit_id', 'water_meter_no', 'gw_allo_usage_est']
    # todo I need to run a groupby here...
    use_data = pumping_data.loc[idx].resample(frequency) # todo how to run different aggs...
    raise NotImplementedError


def get_pumping_locs(recalc=default_recalc):
    raise NotImplementedError


def data_checks():
    raise NotImplementedError


if __name__ == '__main__':
    get_historical_pumping_data(None, None)
