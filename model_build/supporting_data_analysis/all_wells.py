"""
created matt_dumont 
on: 5/09/22
"""
import pandas as pd
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
    well_data.dropna(subset='Depth', inplace=True)

    # DO NOT USE A FOR LOOP! # todo EC

    # todo set qual code 1 for no elv data, 2 for with elv data

    # todo get elevation from DEM where missing
    # use rasterio and raster.sample
    raster = rasterio.open(dem_path)
    raster.sample()

    # todo convert depth to elevation (use ground RL if present)

    # todo fill missing screen data

    # todo calculate mid screen elv

    # todo translate screen date from depth to elv

    # todo correctly format depth to water and drill_date

    # todo calculate layer, row, col
    smt.convert_coords_to_matix()

    # todo save to:  as csv
    processed_well_path
