"""
created matt_dumont 
on: 5/09/22
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from model_build.project_model_tools import smt
from model_build.utils import get_colors
from project_base import processed_model_build_data_dir, base_model_build_data_dir, modelling_dir
import rasterio

base_well_path = base_model_build_data_dir.joinpath('Hawea Wellsdata request ZEB.xlsx')
processed_well_path = processed_model_build_data_dir.joinpath('all_well_locs.csv')
dem_path = modelling_dir.joinpath('input_data/southi_15mdem_Hawea.tif')


def get_all_wells(recalc=False):
    """
    quality code refers to the quality of the ground water level data
    0: no date data for the depth to water field
    1: no elevation data present (read from DEM)
    2: no depth data for the well
    3: as good as it gets
    where multiple quality codes could apply the lowest is used.
    :param recalc:
    :return:
    """
    if processed_well_path.exists() and not recalc:
        well_data = pd.read_csv(processed_well_path, index_col=0)
        well_data.loc[:, 'drilldate'] = pd.to_datetime(well_data.loc[:, 'drilldate'])
        well_data.loc[:, 'quality_code'] = well_data.loc[:, 'quality_code'].astype(int)
        return well_data

    well_data = pd.read_excel(base_well_path, 'HaweaBox')
    well_data.dropna(subset='WellNumber')
    well_data.loc[:, 'well_name'] = well_data.loc[:, 'WellNumber'].str.replace('/', '_').str.lower()
    well_data.set_index('well_name', inplace=True)
    well_data.loc['g40_0041', 'Depth'] = 20

    well_data.dropna(subset=['Depth', 'DepthToWater'], how='all', inplace=True)
    well_data.loc[:, 'missing_elv'] = False

    # setting up quality code for elevation data
    # 1 = no elv data, 2 = elv data
    idx = well_data["Elevation"].isnull()
    well_data.loc[~idx, 'quality_code'] = 3
    well_data.loc[well_data.Depth.isna(), 'quality_code'] = 2
    well_data.loc[idx, 'quality_code'] = 1
    well_data.loc[well_data.DrillDate.isna(), 'quality_code'] = 0
    assert well_data.quality_code.notna().all()

    # getting elevation from DEM where it is missing

    # missing elevation data is where quality_code = 1, e.g same as idx
    # use rasterio and raster.sample
    raster = rasterio.open(dem_path)
    xy = zip(well_data.loc[idx, 'EastingTM'], well_data.loc[idx, 'NorthingTM'])
    t = raster.sample(xy)
    t = np.array(list(t)).flatten()
    well_data.loc[idx, 'Elevation'] = t
    well_data.loc[idx, 'missing_elv'] = True

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
    well_data["screen_from_elv"] = (well_data['Ground_RL'] + well_data['Elevation']) - well_data['ScreenFrom']
    well_data['screen_to_elv'] = (well_data['Ground_RL'] + well_data['Elevation']) - well_data['ScreenTo']

    # calculating mid screen elevation
    # taking the mean of the screen from elv and screen to elv
    well_data['midscreen_elv'] = (well_data["screen_from_elv"] + well_data["screen_to_elv"]) / 2

    # formatting depth to water as elevation
    well_data['depth_to_water_elv'] = (well_data['Ground_RL'] + well_data['Elevation']) - well_data['DepthToWater']

    # formatting drill_date as datetime
    well_data['DrillDate'] = pd.to_datetime(well_data['DrillDate'])

    mapper = {
        'EastingTM': 'nztmx',
        'NorthingTM': 'nztmy',
    }
    well_data.rename(columns=mapper, inplace=True)

    well_data.columns = [e.lower() for e in well_data.columns]
    row, col = smt.convert_coords_to_matix(well_data.nztmx, well_data.nztmy, coords_out_domain='coerce')
    well_data.loc[:, 'i'] = row
    well_data.loc[:, 'j'] = col
    well_data = well_data.loc[well_data.i >= 0]
    ibound = smt.get_no_flow(0)
    well_data.loc[:, 'ibound'] = ibound[well_data.i, well_data.j]

    well_data.to_csv(processed_well_path)


def plot_wells():
    fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, base_map=True, no_flow_layer=0)
    wells = get_all_wells()
    qcs = wells.loc[:, 'quality_code'].unique()
    colors = get_colors(qcs)
    for qc, c in zip(qcs, colors):
        temp = wells.loc[wells.quality_code == qc]
        ax.scatter(temp.nztmx, temp.nztmy, color=c, label=f'QC: {qc}')
    ax.legend()

    # plot elv exists
    fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
    temp = wells.loc[wells.missing_elv]
    ax.scatter(temp.nztmx, temp.nztmy, c='r', label='missing elevation data')
    temp = wells.loc[~wells.missing_elv]
    ax.scatter(temp.nztmx, temp.nztmy, c='b', label='has elevation data')
    ax.legend()

    smt.plot.show()

if __name__ == '__main__':
    plot_wells()
    t = get_all_wells(recalc=True)
