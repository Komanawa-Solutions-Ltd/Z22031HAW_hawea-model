"""
created matt_dumont 
on: 5/09/22
"""
import pandas as pd
import numpy as np
from model_build.project_model_tools import smt
from project_base import processed_model_build_data_dir, base_model_build_data_dir, modelling_dir
import rasterio

base_well_path = base_model_build_data_dir.joinpath('Hawea Wellsdata request ZEB.xlsx')
processed_well_path = processed_model_build_data_dir.joinpath('all_well_locs.csv')
dem_path = modelling_dir.joinpath('input_data/southi_15mdem_Hawea.tif')


def get_all_wells(recalc=False):
    if processed_well_path.exists() and not recalc:
        raise NotImplementedError

    well_data = pd.read_excel(base_well_path, 'HaweaBox')
    well_data.loc[:, 'well_name'] = well_data.loc[:, 'WellNumber'].str.replace('/', '-')
    well_data.set_index('well_name', inplace=True)
    well_data.dropna(subset=['Depth', 'DepthToWater'], how='all', inplace=True)


    # DO NOT USE A FOR LOOP! # todo EC

    # setting up quality code for elevation data
    # 1 = no elv data, 2 = elv data
    idx = well_data["Elevation"].isnull()
    well_data.loc[:, 'quality_code'] = 2
    well_data.loc[idx, 'quality_code'] = 1


    # getting elevation from DEM where it is missing

    # missing elevation data is where quality_code = 1, e.g same as idx
    # use rasterio and raster.sample
    raster = rasterio.open(dem_path)
    xy = zip(well_data.loc[idx, 'EastingTM'], well_data.loc[idx, 'NorthingTM'])
    t = raster.sample(xy)
    t = np.array(list(t)).flatten()
    well_data.loc[idx, 'Elevation'] = t

    # changing depth to elevation
    # first filling all the NaNs in Ground_RL with zero
    well_data['Ground_RL'] = well_data['Ground_RL'].fillna(0)
    # Converting depth to elevation
    well_data['Depth_elevation'] = (well_data['Ground_RL'] + well_data['Elevation']) - well_data['Depth']

    # filling in where there are no screen values
    # first creating an index which subsets all the screen values with no value
    # using when there are no ScreenTo values, because usually both values are present or none
    # A few times there have been ScreenFrom but not ScreenTo so using
    # ScreenTo to capture all the NaNs
    screen_idx = well_data['ScreenTo'].isnull()
    # assuming the default is that the last 3 m of the well are screened
    well_data.loc[screen_idx, 'ScreenFrom'] = well_data['Depth'] - 3
    well_data.loc[screen_idx, 'ScreenTo'] = well_data['Depth']

    # changing screen data from depth to elevation
    well_data["ScreenFrom_Elv"] = (well_data['Ground_RL'] + well_data['Elevation']) - well_data['ScreenFrom']
    well_data['ScreenTo_Elv'] = (well_data['Ground_RL'] + well_data['Elevation']) - well_data['ScreenTo']

    # calculating mid screen elevation
    # taking the mean of the screen from elv and screen to elv
    well_data['MidScreen_Elv'] = (well_data["ScreenFrom_Elv"] + well_data["ScreenTo_Elv"])/2

    # formatting depth to water as elevation
    well_data['DepthToWater_Elv'] = (well_data['Ground_RL'] + well_data['Elevation']) - well_data['DepthToWater']

    # formatting drill_date as datetime
    well_data['DrillDate'] = pd.to_datetime(well_data['DrillDate'])

    print(well_data['DrillDate'])

    # todo calculate layer, row, col
    # leave this
    # smt.convert_coords_to_matix()

    well_data.to_csv(processed_well_path)

get_all_wells()