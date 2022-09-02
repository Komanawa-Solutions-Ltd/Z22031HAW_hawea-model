"""
created matt_dumont 
on: 15/08/22
"""
import pandas as pd
from project_base import base_model_build_data_dir, processed_model_build_data_dir
from model_build.project_model_tools import smt
from model_build.utils import select_resample

default_recalc = False
race_shp_path = base_model_build_data_dir.joinpath('races.shp')
inflow_path = base_model_build_data_dir.joinpath('Hawea Irrigation Co - Lake Hawea Takes (daily).csv')
race_loc_data_path = processed_model_build_data_dir.joinpath('race_loc_data.csv')


def get_race_locs(recalc=default_recalc):
    # do I need to manage luggate-tarras road races, nope
    # exclude lagoon creek races instead manage as additional points of well inflow
    if not recalc and race_loc_data_path.exists():
        outdata = pd.read_csv(race_loc_data_path)
        dtypes = {
            'i': 'int64',
            'j': 'int64',
        }

        for k, v in dtypes.items():
            outdata.loc[:, k] = outdata.loc[:, k].astype(v)
        return outdata

    outdata = smt.io.array_to_df(smt.io.shape_file_to_model_array(race_shp_path, 'OBJECTID', alltouched=True),
                                 'dummy')
    outdata.loc[:, 'param'] = 'all'
    outdata.drop(columns='dummy', inplace=True)
    outdata.to_csv(race_loc_data_path)

    return outdata


def get_race_inflows(start_date, end_date, frequency='D'):
    """
    get race inflows from start to end dates (inclusive),
     data is available from 2012-01-01 to 2021-12-31
    :param start_date: none or dates
    :param end_date: none or dates
    :param frequency: pd frequnecy code
    :return:
    """
    data = pd.read_csv(inflow_path)
    data.loc[:, 'datetime'] = ht = pd.to_datetime(data.loc[:, 'Date'], format='%d/%m/%Y')
    data.rename(columns={'Combined': 'flow'}, inplace=True)  # in m3/day
    data.set_index('datetime', inplace=True)
    return select_resample(data, start_date, end_date, frequency, 'mean')


def get_race_well_losses(start_date, end_date, frequency='D'):
    race_locs = get_race_locs()
    data = get_race_inflows(start_date, end_date, frequency).flow * 0.1 / len(race_locs)
    return data


if __name__ == '__main__':
    t = get_race_locs(recalc=True)
    t = get_race_inflows(None, None, 'M')
    pass
