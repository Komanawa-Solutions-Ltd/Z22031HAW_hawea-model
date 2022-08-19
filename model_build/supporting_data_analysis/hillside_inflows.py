"""
created matt_dumont 
on: 2/08/22
"""
import pandas as pd
import numpy as np
from project_base import base_model_data_dir, processed_model_data_dir, modelling_dir, unbacked_dir
from model_build.supporting_data_analysis.recharge_model import get_met_data
from model_build.project_model_tools import smt
import geopandas as gpd
import datetime
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from copy import deepcopy

# exclude lagoon creek races instead manage as additional points of well inflow

pour_points_path = base_model_data_dir.joinpath('hillflow_inputs.shp')
catchment_area_path = processed_model_data_dir.joinpath('catchment_areas.csv')


def get_catchment_areas(show_plot=False, recalc=False):
    if catchment_area_path.exists() and not recalc:
        data = pd.read_csv(catchment_area_path)
        return data

    dem_path = modelling_dir.joinpath('input_data/southi_15mdem_Hawea.tif')
    catchment_shapefile_dir = unbacked_dir.joinpath('input_data/hillside_catchments')
    catchment_shapefile_dir.mkdir(exist_ok=True, parents=True)

    from pysheds.grid import Grid
    grid = Grid.from_raster(str(dem_path))
    dem = grid.read_raster(str(dem_path))
    # Fill pits in DEM
    pit_filled_dem = grid.fill_pits(dem)

    # Fill depressions in DEM
    flooded_dem = grid.fill_depressions(pit_filled_dem)

    # Resolve flats in DEM
    inflated_dem = grid.resolve_flats(flooded_dem)
    print('dem conditioned')

    # Compute flow directions (d8)
    dirmap = (1, 2, 3, 4, 5, 6, 7, 8)
    fdir = grid.flowdir(inflated_dem, dirmap=dirmap)

    # Calculate flow accumulation
    acc = grid.accumulation(fdir, dirmap=dirmap)
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_alpha(0)
    plt.grid('on', zorder=0)
    im = ax.imshow(acc, extent=grid.extent, zorder=2,
                   cmap='cubehelix',
                   norm=LogNorm(1, acc.max()),
                   interpolation='bilinear')

    plt.colorbar(im, ax=ax, label='Upstream Cells')
    plt.title('Flow Accumulation', size=14)
    plt.xlabel('NZTMX')
    plt.ylabel('NZTMY')
    plt.tight_layout()
    if show_plot:
        plt.show()

    pourpoints = gpd.read_file(pour_points_path)
    outdata = pd.DataFrame(index=pourpoints.River_name, columns=['raster_area', 'shp_area', 'px', 'py'])
    for i, pp in pourpoints.iterrows():
        # Delineate a catchment
        # ---------------------
        # Specify pour point
        x = pp.geometry.x
        y = pp.geometry.y
        name = pp.River_name
        print(name)
        outdata.loc[name, 'px'] = x
        outdata.loc[name, 'py'] = y

        # Snap pour point to high accumulation cell
        x_snap, y_snap = grid.snap_to_mask(acc > 1000, (x, y))

        # Delineate the catchment
        catch = grid.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap,
                               xytype='coordinate')
        # calculate area
        cell_area = 15 * 15  # m2 from 15m dem
        catch_area = catch.sum() * cell_area
        outdata.loc[name, 'raster_area'] = catch_area

        # export shapefile to check
        grid2 = deepcopy(grid)
        grid2.clip_to(catch)
        catch_view = grid2.view(catch)
        _write_shapefile(outpath=catchment_shapefile_dir.joinpath(f'{name}.shp'), grid=grid2, catch_view=catch_view)
        t = gpd.read_file(catchment_shapefile_dir.joinpath(f'{name}.shp'))
        outdata.loc[name, 'shp_area'] = t.area.sum()

    outdata.to_csv(catchment_area_path)


def _write_shapefile(outpath, grid, catch_view):
    import fiona
    shapes = grid.polygonize(catch_view.astype(np.uint8))

    # Specify schema
    schema = {
        'geometry': 'Polygon',
        'properties': {'LABEL': 'float:16'}
    }

    # Write shapefile
    with fiona.open(str(outpath), 'w',
                    driver='ESRI Shapefile',
                    crs=grid.crs.srs,
                    schema=schema) as c:
        i = 0
        for shape, value in shapes:
            rec = {}
            rec['geometry'] = shape
            rec['properties'] = {'LABEL': str(value)}
            rec['id'] = str(i)
            c.write(rec)
            i += 1


def get_historical_flows(start_date, end_date, frequency='D'):
    outdata = pd.DataFrame(index=pd.date_range('1950-01-01', '2022-01-01', freq='D') + datetime.timedelta(hours=12))
    outdata.index.name = 'datetime'
    paths = [
        'streamflow_Lindis at Lindis Peak_data.csv',
        'streamflow_Luggate Creek at SH6 Bridge_data.csv',
        'streamflow_Grandview Creek at Lake Hawea Station_data.csv',
        'streamflow_Lagoon Creek at Mount Grand Station_data.csv',
    ]
    names = [
        'Lindis',
        'Luggate',
        'Grandview',
        'Lagoon',
    ]

    for p, n in zip(paths, names):
        df = pd.read_csv(base_model_data_dir.joinpath(p), skiprows=1)
        df.loc[:, 'datetime'] = pd.to_datetime(df.time)
        df.set_index('datetime', inplace=True)
        df.rename(columns={'streamflow': n}, inplace=True)

        outdata = pd.merge(outdata, df.loc[:,[n]], how='outer', left_index=True, right_index=True)

    outdata = outdata.dropna(how='all')

    ht = outdata.index
    if start_date is None:
        start_date = ht.min()
    if end_date is None:
        end_date = ht.max()

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    idx = (outdata.index >= start_date) & (outdata.index <= end_date)
    outdata = outdata.loc[idx].resample(frequency).mean()
    return outdata

def compair_lindus_correlations():
    raise NotImplementedError # todo! start here

def get_hillside_inflows_specific_discharge():  # todo try to get from lindis at lindis peak
    raise NotImplementedError


def get_hillside_inflows_rain_pet_predict():
    metdata = get_met_data(None, None)
    # todo this might be useful for scenarios.
    raise NotImplementedError


# # todo use specific discharge of catchments?
# todo make relative to rainfall/pet/etc.?
# todo check with team

if __name__ == '__main__':
    get_historical_flows(None, None)
