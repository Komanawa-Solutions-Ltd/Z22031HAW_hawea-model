"""
created matt_dumont 
on: 19/07/22
"""
from model_tools.regular_modeltools import ModelTools_RegularGrid
from project_base import modelling_dir, unbacked_dir, base_model_data_dir  # from project_base.py file in the project
import geopandas as gpd
import numpy as np

# todo clone the 'modflow_tools' repo and make a new branch for this model, don't forget to merge
# when finished
default_figsize = (8, 10)
temp_file_dir = unbacked_dir.joinpath('tempfiles')
temp_file_dir.mkdir(exist_ok=True)
sdp = unbacked_dir.joinpath('sdp')
sdp.mkdir(exist_ok=True)

boundary_path = base_model_data_dir.joinpath('model_boundary.shp')
temp = gpd.read_file(boundary_path)
ulx = np.floor(temp.bounds.loc[0, 'minx'])
uly = np.ceil(temp.bounds.loc[0, 'maxy'])

lrx = np.ceil(temp.bounds.loc[0, 'maxx'])
lry = np.floor(temp.bounds.loc[0, 'miny'])
base_map_path = base_model_data_dir.joinpath('nz-topo50-maps.tif')
model_version_name = 'v1'

grid_space = 100  #
cols = int(abs(ulx - lrx) // grid_space) + 1
rows = int(abs(uly - lry) // grid_space) + 1

layers = 1
nper = 1  # todo dummy
steady = np.repeat([False], (nper,))  # todo dbl check
# todo other period data
layer_type = [1]

temp_smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                                  model_version_name, sdp, temp_file_dir,
                                  rotation=0, nper=nper, layer_type=layer_type, steady=steady,
                                  no_flow_calc=None, elv_calculator=None,
                                  base_map_path=base_map_path, default_figsize=default_figsize, epsg_num=2193)


def simplify_hawea_dem(recalc=False):
    """
    take the mean of the soutisland 15 m dem provided by Lincoln agritech
    run once from project filestore
    :return:
    """
    dem_path = modelling_dir.joinpath('input_data/southi_15mdem_Hawea.tif')
    outpath = base_model_data_dir.joinpath('raw_mean_dem_top.txt')
    if outpath.exists() and not recalc:
        data = np.loadtxt(outpath)
        return data
    data = temp_smt.io.raster_to_array(dem_path, 'average')
    np.savetxt(outpath, data)
    return data


def simplify_upper_clutha_dem(recalc=False):  # todo need to run on tuke... ran out of memory
    """
    take the min of the upper clutha dem to use for the model
    run once from project filestore
    :return:
    """
    dem_path = modelling_dir.joinpath('input_data/UpperClutha_DEM_1m.tif')
    outpath = base_model_data_dir.joinpath('raw_min_dem.txt')
    if outpath.exists() and not recalc:
        data = np.loadtxt(outpath)
        return data
    from osgeo import gdal, osr
    temp_file = '{}/temp2.tif'.format(temp_file_dir)
    f = gdal.Open(str(dem_path))
    geotransform = f.GetGeoTransform()
    f2 = f.GetRasterBand(1)
    no_data = f2.GetNoDataValue()
    temp_data = f2.ReadAsArray()
    f = None

    if no_data is not None:
        temp_data[np.isclose(temp_data, no_data)] = np.nan
    temp_data[temp_data < 220] = np.nan  # manage weird artifacts in the dem
    null_val = -999999

    output_raster = gdal.GetDriverByName('GTiff').Create(temp_file, temp_data.shape[1], temp_data.shape[0], 1,
                                                         gdal.GDT_Float32)  # Open the file
    output_raster.SetGeoTransform(geotransform)  # Specify its coordinates
    srs = osr.SpatialReference()  # Establish its coordinate encoding
    srs.ImportFromEPSG(temp_smt.epsg)  # set the georefernce
    output_raster.SetProjection(srs.ExportToWkt())  # Exports the coordinate system
    # to the file
    band = output_raster.GetRasterBand(1)
    band.WriteArray(temp_data)  # Writes my array to the raster
    band.FlushCache()
    band.SetNoDataValue(null_val)

    data = temp_smt.io.raster_to_array(temp_file, 'min')
    np.savetxt(outpath, data)
    return data


def no_flow():
    ibound = temp_smt.get_model_zeros(_3d=True)
    active = temp_smt.io.shape_file_to_model_array(boundary_path, 'fid', alltouched=True)
    assert temp_smt.layers == 1
    ibound[0][np.isfinite(active)] = 1
    return ibound


def elv_calc():
    bot_path = base_model_data_dir.joinpath('Model_bot.tif')
    top = simplify_hawea_dem()
    bot = temp_smt.io.raster_to_array(bot_path, 'average')
    thick = top - bot
    bot[thick < 2] = top[thick < 2] - 2  # set min thickness to 2m

    return np.concatenate((top[np.newaxis], bot[np.newaxis]))


smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                             model_version_name, sdp, temp_file_dir,
                             rotation=0, nper=nper, layer_type=layer_type, steady=steady,
                             no_flow_calc=no_flow, elv_calculator=elv_calc,
                             base_map_path=base_map_path, default_figsize=default_figsize, epsg_num=2193)

if __name__ == '__main__':
    temp_smt.plot.plt_matrix(simplify_upper_clutha_dem(recalc=True), title='upperc', base_map=True) # todo need to run on dicke... more memory

    temp_smt.plot.show()
