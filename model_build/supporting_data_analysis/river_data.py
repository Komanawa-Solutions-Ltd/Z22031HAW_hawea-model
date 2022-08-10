"""
created matt_dumont 
on: 2/08/22
"""
import numpy as np
import pandas as pd

from model_build.project_model_tools import smt, simplify_upper_clutha_dem
from project_base import base_model_data_dir, processed_model_data_dir
from model_build.supporting_data_analysis.lake_data import get_lake_hawea_loc

default_recalc = False
hawea_shp_path = base_model_data_dir.joinpath('hawea_river.shp')
clutha_shp_path = base_model_data_dir.joinpath('lower_clutha.shp')

riv_loc_data_path = processed_model_data_dir.joinpath('river_loc_data.csv')


def make_river_loc_data(recalc=default_recalc):
    if not recalc and riv_loc_data_path.exists():
        outdata = pd.read_csv(riv_loc_data_path)
        # todo manage types !!!!
        return outdata
    # read in the shapefiles and save only the data in active model
    ibound = smt.get_no_flow(0)
    hawea = smt.io.shape_file_to_model_array(hawea_shp_path, 'dist_top', alltouched=True)
    hawea[ibound < 1] = np.nan

    # make sure hawea r. not in the lake!!!
    lake_hawea = smt.io.df_to_array(get_lake_hawea_loc(), 'i')
    hawea[np.isfinite(lake_hawea)] = np.nan

    hawea = smt.io.array_to_df(hawea, 'dist')
    clutha = smt.io.shape_file_to_model_array(hawea_shp_path, 'dist_top', alltouched=True)
    clutha[ibound < 1] = np.nan
    clutha = smt.io.array_to_df(clutha, 'dist')

    # add top data
    top = simplify_upper_clutha_dem()
    hawea.loc[:, 'Rbot'] = top[hawea.loc[:, 'i'], hawea.loc[:, 'j']]
    clutha.loc[:, 'Rbot'] = top[clutha.loc[:, 'i'], clutha.loc[:, 'j']]

    # label rivers
    hawea.loc[:, 'rname'] = 'hawea'
    clutha.loc[:, 'rname'] = 'clutha'
    outdata = pd.concat((hawea, clutha))
    outdata.to_csv(riv_loc_data_path)
    return outdata


def get_river_stage_data():  # todo
    # the river stage is largely stable
    # hawea 310-313, median 311
    # along time, so hold constant in model??? # todo discuss with Jens
    # todo where is stage clutha 2200???
    # todo how do I manage the lake stage/top of the hawea river??? discuss with Jens
    # todo need to interpolate the river stage.
    raise NotImplementedError


def get_river_conductance(river_loc_data, optimised):  # todo
    """
    get the river conductance values
    :param river_loc_data: river location data output of make_river_loc_data
    :param optimised: bool if True use the optimised parameters, else use the initial parameters
    :return:
    """
    if optimised:
        raise NotImplementedError('optimisation not complete')
    else:

        raise NotImplementedError


def data_checks():
    import matplotlib.pyplot as plt
    # todo look at riv locations, make sure none of the locations are in the lake!!!

    # look at stage through time at our locations( which are???)
    hawea_data = pd.read_csv(base_model_data_dir.joinpath('Lake_Hawea.csv'))
    print(hawea_data.describe())
    hawea_data.loc[:, 'datetime'] = pd.to_datetime(hawea_data.loc[:, 'DateLake'], format='%d/%m/%Y %H:%M')
    hawea_data.loc[:, 'month'] = hawea_data.loc[:, 'datetime'].dt.month
    monthly = hawea_data.groupby('month').describe(percentiles=[.05, .25, .5, .75, .95])
    fig, ax = plt.subplots()
    monthly.LakeLevel_m.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('lake level')

    river_data = pd.read_csv(base_model_data_dir.joinpath('River_Level_Hawea.csv'))
    print(river_data.describe())
    river_data.loc[:, 'datetime'] = pd.to_datetime(river_data.loc[:, 'DateTime'], format='%d/%m/%Y')
    river_data.loc[:, 'month'] = river_data.loc[:, 'datetime'].dt.month
    monthly = river_data.groupby('month').describe(percentiles=[.05, .25, .5, .75, .95])
    fig, ax = plt.subplots()
    monthly.Level_Camphill.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('camp hill stage')
    fig, ax = plt.subplots()
    monthly.Stage_Clutha2200.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('clutha 2200 stage')
    plt.show()

    # todo look at dist vs model top, bot, riv bot along each river. include min, 5th, 25th, 50th, 75th, 95th, max temporal stage
    raise NotImplementedError


def make_river_data():
    # todo put it all togeather to drop into modflow.
    raise NotImplementedError


if __name__ == '__main__':
    data_checks()
