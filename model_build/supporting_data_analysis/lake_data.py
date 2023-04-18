"""
created matt_dumont 
on: 10/08/22
"""
import numpy as np
import pandas as pd

from model_build.project_model_tools import smt, _lake_locs
from model_build.utils import select_resample
from project_base import base_model_build_data_dir, processed_model_build_data_dir

default_recalc = False
lakefront_shp_path = base_model_build_data_dir.joinpath('lakefront.shp')
lake_shp_path = base_model_build_data_dir.joinpath('lake_hawea.shp')
lake_loc_path = processed_model_build_data_dir.joinpath('lake_hawea_loc.csv')


def get_lake_hawea_loc(recalc=default_recalc):
    if not recalc and lake_loc_path.exists():
        lake_data = pd.read_csv(lake_loc_path, dtype=int)
        return lake_data

    lake_data = _lake_locs()
    lake_data.to_csv(lake_loc_path)
    return lake_data


def lake_checks():
    import matplotlib.pyplot as plt
    hawea_data = _read_lake_level()
    hawea_data.plot()
    hawea_data.loc[:, 'month'] = hawea_data.index.month
    monthly = hawea_data.groupby('month').describe(percentiles=[.05, .25, .5, .75, .95])
    fig, ax = plt.subplots()
    monthly.lake_stage.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('lake level')

    smt.plot.show()
    smt.plot.plt_matrix(smt.io.df_to_array(get_lake_hawea_loc(), 'i'), base_map=True, no_flow_layer=0,
                        title='lake locs')
    smt.plot.show()


def _read_lake_level():
    hawea_data = pd.read_csv(base_model_build_data_dir.joinpath('Amalgamated Lake Hawea Levels (weekly & daily).csv'))
    hawea_data.loc[0:864, 'datetime'] = pd.to_datetime(hawea_data.loc[0:864, 'date'], format='%d/%m/%y')
    hawea_data.loc[865:, 'datetime'] = pd.to_datetime(hawea_data.loc[865:, 'date'], format='%d/%m/%Y')
    hawea_data.rename(columns={'Lake Hawea Elevation (m AMSL)': 'lake_stage'}, inplace=True)
    hawea_data.set_index('datetime', inplace=True)
    return hawea_data


def get_lake_heads(start_date, end_date, frequency='D'):
    """
    get lake records from start to end dates (inclusive),
     data is available from 2012-01-01 to 2021-12-31
    :param start_date: none or dates
    :param end_date: none or dates
    :param frequency: pd frequnecy code
    :return:
    """
    hawea_data = _read_lake_level()
    hawea_data = hawea_data.resample('D').interpolate()

    # keynote convert lake levels from  Dunedin 1958 (from NZVD2016) to New Zealand Vertical Datum 2016
    #  conversion by https://www.geodesy.linz.govt.nz/concord/
    hawea_data.loc[:, 'lake_stage'] = hawea_data.loc[:, 'lake_stage'] - 1 / 3

    return select_resample(hawea_data.loc[:, 'lake_stage'], start_date, end_date, frequency, 'mean')


if __name__ == '__main__':
    lake_checks()
    get_lake_hawea_loc(True)
    t = get_lake_heads(None, None)
