"""
created matt_dumont 
on: 19/07/22
"""
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
try:
    from komanawa.modeltools import RectangularModelTools as ModelTools_RegularGrid
    from komanawa.modeltools import TimeDis
    dummy_modeltools = False
except ModuleNotFoundError:
    from komanawa.hawea.dummy_packages import ModelTools_RegularGrid, TimeDis
    dummy_modeltools = True
from komanawa.hawea.hawea_base import unbacked_dir, base_model_build_data_dir, modelling_dir, butterfield_dir
import geopandas as gpd

temp_file_dir = unbacked_dir.joinpath('tempfiles')
temp_file_dir.mkdir(exist_ok=True)
sdp = unbacked_dir.joinpath('sdp_but')
sdp.mkdir(exist_ok=True)

extent = gpd.read_file(butterfield_dir.joinpath('base_input_data',
                                                'domain.shp'))
ebounds = extent.geometry.bounds.loc[0]
ulx = ebounds.loc['minx']
uly = ebounds.loc['maxy']
lrx = ebounds.loc['maxx']
lry = ebounds.loc['miny']
base_map_path = base_model_build_data_dir.joinpath('nz-topo50-maps.jpg')
model_version_name = 'v1'

grid_space = 50
cols = int((lrx - ulx) // grid_space) + 1
rows = int((uly - lry) // grid_space) + 1

layers = 1
layer_type = 1

if dummy_modeltools:
    temp_smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                                  model_version_name, sdp,
                                  rotation=0, layer_type=None,
                                  no_flow_calc=None, elv_calculator=None,
                                  base_map_path=base_map_path, default_figsize=(8, 7), epsg_num=2193)
else:
    temp_smt = ModelTools_RegularGrid(llx=ulx, lly=uly-(grid_space*rows), layers=layers, rows=rows, cols=cols, delr=grid_space,
                                      delc=grid_space,
                                      model_version_name=model_version_name, sdp=sdp,
                                      rotation=0, layer_type=layer_type,
                                      no_flow_calc=None, elv_calculator=None,
                                      base_map_path=base_map_path, default_figsize=(8, 7), epsg_num=2193)

def no_flow(recalc=False):
    save_path = butterfield_dir.joinpath('processed_input_data', 'ibound.npy')
    if save_path.exists() and not recalc:
        return np.load(save_path)[np.newaxis]

    from komanawa.hawea.model_build.project_model_tools import smt as hawea_smt
    ibound = hawea_smt.get_no_flow(0)
    with tempfile.TemporaryDirectory() as tdir:
        tdir = Path(tdir)
        hawea_smt.io.array_to_raster(tdir.joinpath('temp.tif'), ibound)
        outibound = smt.io.raster_to_array(tdir.joinpath('temp.tif'), 'mean').astype(int)
    np.save(save_path, outibound)
    return outibound[np.newaxis]


def simplify_hawea_dem(recalc=False):
    """
    take the mean of the soutisland 15 m dem provided by Lincoln agritech
    run once from project filestore
    :return:
    """
    dem_path = modelling_dir.joinpath('input_data/southi_15mdem_Hawea.tif')
    outpath = butterfield_dir.joinpath('processed_input_data', 'raw_mean_dem_top.txt')
    if outpath.exists() and not recalc:
        data = np.loadtxt(outpath)
        return data
    data = temp_smt.io.raster_to_array(dem_path, 'mean')
    np.savetxt(outpath, data)
    return data


def simplify_upper_clutha_dem(recalc=False):
    """
    take the min of the upper clutha dem to use for the model
    run once from project filestore
    :return:
    """
    dem_path = modelling_dir.joinpath('input_data/UpperClutha_DEM_1m.tif')
    outpath = butterfield_dir.joinpath('processed_input_data', 'raw_min_dem.txt')
    if outpath.exists() and not recalc:
        data = np.loadtxt(outpath)
        return data
    from osgeo import gdal, osr
    temp_file = '{}/temp2.tif'.format(temp_file_dir)
    f = gdal.Open(str(dem_path))
    geotransform = f.GetGeoTransform()
    f2 = f.GetRasterBand(1)
    no_data = f2.GetNoDataValue()
    temp_data = f2.ReadAsArray().astype(np.float32)

    f = None
    print('read data')
    if no_data is not None:
        temp_data[np.isclose(temp_data, no_data)] = np.nan
    rows = temp_data.shape[1]
    t = temp_data[0:rows // 4]
    t[t < 260] = np.nan
    t = temp_data[0:rows // 2]
    t[t < 230] = np.nan
    t = temp_data[rows // 2:]
    t[t < 220] = np.nan
    null_val = -999999
    print('fixed data')
    output_raster = gdal.GetDriverByName('GTiff').Create(temp_file, temp_data.shape[1], temp_data.shape[0], 1,
                                                         gdal.GDT_Float32)  # Open the file
    output_raster.SetGeoTransform(geotransform)  # Specify its coordinates
    srs = osr.SpatialReference()  # Establish its coordinate encoding
    srs.ImportFromEPSG(temp_smt.epsg)  # set the georefernce
    output_raster.SetProjection(srs.ExportToWkt())  # Exports the coordinate system
    # to the file
    band = output_raster.GetRasterBand(1)
    print('set up array')
    band.WriteArray(temp_data)  # Writes my array to the raster
    band.FlushCache()
    band.SetNoDataValue(null_val)
    output_raster = None

    data = temp_smt.io.raster_to_array(temp_file, 'min')
    data[~np.isfinite(data)] = np.nan
    np.savetxt(outpath, data)
    return data


def _get_top_array(retun_idx=False, recalc=False):
    save_path = butterfield_dir.joinpath('processed_input_data', 'model_top.npy')
    if save_path.exists() and not recalc:
        return np.load(save_path)

    clutha_dem = simplify_upper_clutha_dem()
    all_dem = simplify_hawea_dem()
    use_dem = all_dem.copy()
    idx = smt.get_model_zeros() + 1
    np.save(save_path, use_dem)
    if retun_idx:
        return use_dem, idx
    return use_dem


def elv_calc():
    return np.concatenate((
        _get_top_array()[np.newaxis],
        smt.get_model_zeros(True) + 255  # loosely based on hawea model bottom.
    ), axis=0)

if dummy_modeltools:
    smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                             model_version_name, sdp,
                             rotation=0, layer_type=layer_type,
                             no_flow_calc=no_flow, elv_calculator=elv_calc,
                             base_map_path=base_map_path, default_figsize=(8, 7), epsg_num=2193)
else:
    smt = ModelTools_RegularGrid(llx=ulx, lly=uly - (grid_space * rows), layers=layers, rows=rows, cols=cols, delr=grid_space,
                           delc=grid_space,
                           model_version_name=model_version_name, sdp=sdp,
                           rotation=0, layer_type=layer_type,
                           no_flow_calc=no_flow, elv_calculator=elv_calc,
                           base_map_path=base_map_path, default_figsize=(8, 7), epsg_num=2193)

ss_dates = ('2001-07-01', '2002-06-30')
trans_dates = pd.date_range('2002-07-01', '2003-06-30', freq='W')

use_dates = [ss_dates]
use_dates.extend([e for e in zip(trans_dates, trans_dates + pd.Timedelta(days=6))])
steady = [True] + [False for d in trans_dates]
nstp = [1] + [7 for d in trans_dates]
nper = len(use_dates)
tdis = TimeDis(
    name='butterfield', nper=nper, tsmult=1., steady=steady,
    dates=use_dates,
    nstp=nstp
)

def check_old_new_smt():
    if dummy_modeltools:
        raise ModuleNotFoundError('requires internal package komanawa-modeltools')
    from komanawa.hawea.dummy_packages.regular_modeltools import DummyModelTools_RegularGrid
    from komanawa.modeltools import RectangularModelTools
    old_smt =  DummyModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                             model_version_name, sdp,
                             rotation=0, layer_type=layer_type,
                             no_flow_calc=no_flow, elv_calculator=elv_calc,
                             base_map_path=base_map_path, default_figsize=(8, 7), epsg_num=2193)
    new_smt = RectangularModelTools(llx=ulx, lly=uly - (grid_space * rows), layers=layers, rows=rows, cols=cols, delr=grid_space,
                           delc=grid_space,
                           model_version_name=model_version_name, sdp=sdp,
                           rotation=0, layer_type=layer_type,
                           no_flow_calc=no_flow, elv_calculator=elv_calc,
                           base_map_path=base_map_path, default_figsize=(8, 7), epsg_num=2193)
    assert old_smt.model_shape == new_smt.model_shape
    xs, ys = old_smt.get_model_x_y()
    new_x, new_y = new_smt.get_model_x_y()
    assert np.allclose(xs, new_x)
    assert np.allclose(ys, new_y)

if __name__ == '__main__':
    check_old_new_smt()
    raise NotImplementedError # this is just to stop the other code from running
    top, idx = _get_top_array(True, True)
    smt.plot.plt_matrix(top, title='top', base_map=True)
    smt.plot.plt_matrix(idx, title='idx', base_map=True)
    t = smt.get_elv_db()
    smt.plot.plt_matrix(t[0] - t[1], vmax=1)

    smt.plot.show()
    pass
