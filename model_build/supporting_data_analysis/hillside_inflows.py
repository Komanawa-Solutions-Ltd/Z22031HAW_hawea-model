"""
created matt_dumont 
on: 2/08/22
"""
import pandas as pd
import numpy as np
from project_base import base_model_data_dir, processed_model_data_dir, modelling_dir,unbacked_dir
from model_build.project_model_tools import smt
import geopandas as gpd
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


def get_historical_flows():
    raise NotImplementedError

def get_hillside_inflows_specific_discharge():
    raise NotImplementedError

def get_hillside_inflows_rain_pet_predict():
    # todo this might be useful for scenarios.
    raise NotImplementedError

# todo check the shapefiles and areas!!... also check overlaps, I think I have sorted most of these, but need to check v2
# # todo use specific discharge of catchments?
# todo make relative to rainfall/pet/etc.?
# todo check with team

if __name__ == '__main__':
    get_catchment_areas(show_plot=False, recalc=True)
