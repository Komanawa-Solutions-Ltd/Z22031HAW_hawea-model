"""
created matt_dumont 
on: 10/08/22
"""
import numpy as np
import pandas as pd

from model_build.project_model_tools import smt, _lake_locs
from project_base import base_model_data_dir, processed_model_data_dir

default_recalc = False
lakefront_shp_path = base_model_data_dir.joinpath('lakefront.shp')
lake_shp_path = base_model_data_dir.joinpath('lake_hawea.shp')
lake_loc_path = processed_model_data_dir.joinpath('lake_hawea_loc.csv')


def get_lake_hawea_loc(recalc=default_recalc):
    if not recalc and lake_loc_path.exists():
        lake_data = pd.read_csv(lake_loc_path,dtype=int)
        return lake_data

    lake_data = _lake_locs()
    lake_data.to_csv(lake_loc_path)
    return lake_data


def get_lake_conductance(lake_loc_data, optimised):  # todo change to pass conductance,
    """
    get the river conductance values
    :param lake_loc_data: lake location data output of get_lake_hawea_loc
    :param optimised: bool if True use the optimised parameters, else use the initial parameters
    :return:
    """
    if optimised:
        raise NotImplementedError('optimisation not complete')
    else:

        raise NotImplementedError


def lake_checks():
    import matplotlib.pyplot as plt
    hawea_data = pd.read_csv(base_model_data_dir.joinpath('Lake_Hawea.csv'))
    print(hawea_data.describe())
    hawea_data.loc[:, 'datetime'] = pd.to_datetime(hawea_data.loc[:, 'DateLake'], format='%d/%m/%Y %H:%M')
    hawea_data.loc[:, 'month'] = hawea_data.loc[:, 'datetime'].dt.month
    monthly = hawea_data.groupby('month').describe(percentiles=[.05, .25, .5, .75, .95])
    fig, ax = plt.subplots()
    monthly.LakeLevel_m.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('lake level')

    smt.plot.plt_matrix(smt.io.df_to_array(get_lake_hawea_loc(),'i'),base_map=True, no_flow_layer=0,title='lake locs')
    smt.plot.show()


def get_lake_heads(start_date, end_date, frequency='D'):
    """
    get lake records from start to end dates (inclusive),
     data is available from 2012-01-01 to 2021-12-31
    :param start_date: none or dates
    :param end_date: none or dates
    :param frequency: pd frequnecy code
    :return:
    """
    hawea_data = pd.read_csv(base_model_data_dir.joinpath('Lake_Hawea.csv'))
    hawea_data.loc[:, 'datetime'] = ht = pd.to_datetime(hawea_data.loc[:, 'DateLake'], format='%d/%m/%Y %H:%M')
    if start_date is None:
        start_date = ht.min()
    if end_date is None:
        end_date = ht.max()

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    hawea_data.rename(columns={'LakeLevel_m': 'lake_stage'}, inplace=True)
    hawea_data.set_index('datetime', inplace=True)
    idx = (hawea_data.index >= start_date) & (hawea_data.index <= end_date)
    outdata = hawea_data.loc[idx, 'lake_stage'].resample(frequency).mean()

    return outdata


def build_lake_ghb_data(): # todo
    raise NotImplementedError


if __name__ == '__main__':
    lake_checks()
