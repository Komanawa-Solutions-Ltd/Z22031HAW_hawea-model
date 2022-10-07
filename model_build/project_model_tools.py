"""
created matt_dumont 
on: 19/07/22
"""
from model_tools.regular_modeltools import ModelTools_RegularGrid
from project_base import proj_root, modelling_dir, unbacked_dir, base_model_build_data_dir, \
    processed_model_build_data_dir
import geopandas as gpd
import numpy as np
import pandas as pd
from copy import deepcopy

# todo clone the 'modflow_tools' repo and make a new branch for this model, don't forget to merge
# when finished
default_figsize = (8, 10)
temp_file_dir = unbacked_dir.joinpath('tempfiles')
temp_file_dir.mkdir(exist_ok=True)
sdp = unbacked_dir.joinpath('sdp')
sdp.mkdir(exist_ok=True)

boundary_path = base_model_build_data_dir.joinpath('model_boundary.shp')
temp = gpd.read_file(boundary_path)
ulx = np.floor(temp.bounds.loc[0, 'minx'])
uly = np.ceil(temp.bounds.loc[0, 'maxy'])

lrx = np.ceil(temp.bounds.loc[0, 'maxx'])
lry = np.floor(temp.bounds.loc[0, 'miny'])
base_map_path = base_model_build_data_dir.joinpath('nz-topo50-maps.jpg')
model_version_name = 'v1'

grid_space = 100  #
cols = int(abs(ulx - lrx) // grid_space) + 1
rows = int(abs(uly - lry) // grid_space) + 1

layers = 1
layer_type = [1]

temp_smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                                  model_version_name, sdp, temp_file_dir,
                                  rotation=0, layer_type=layer_type,
                                  no_flow_calc=None, elv_calculator=None,
                                  base_map_path=base_map_path, default_figsize=default_figsize, epsg_num=2193)


def simplify_hawea_dem(recalc=False):
    """
    take the mean of the soutisland 15 m dem provided by Lincoln agritech
    run once from project filestore
    :return:
    """
    dem_path = modelling_dir.joinpath('input_data/southi_15mdem_Hawea.tif')
    outpath = base_model_build_data_dir.joinpath('raw_mean_dem_top.txt')
    if outpath.exists() and not recalc:
        data = np.loadtxt(outpath)
        return data
    data = temp_smt.io.raster_to_array(dem_path, 'med')
    np.savetxt(outpath, data)
    return data


def simplify_upper_clutha_dem(recalc=False):
    """
    take the min of the upper clutha dem to use for the model
    run once from project filestore
    :return:
    """
    dem_path = modelling_dir.joinpath('input_data/UpperClutha_DEM_1m.tif')
    outpath = base_model_build_data_dir.joinpath('raw_min_dem.txt')
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


def no_flow():
    ibound = temp_smt.get_model_zeros(_3d=True)
    active = temp_smt.io.shape_file_to_model_array(boundary_path, 'fid', alltouched=True)
    # remove camphill and the camphill moraine from the model
    camphill = temp_smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('camp_hill_moraine.shp'), 'id',
                                                     alltouched=True)
    assert temp_smt.layers == 1
    ibound[0][np.isfinite(active)] = 1
    ibound[0][np.isfinite(camphill)] = 0
    # remove cameron hill
    cameron = temp_smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('cameron_hill.shp'), 'id',
                                                    alltouched=True)
    ibound[0][np.isfinite(cameron)] = 0
    np.savetxt(processed_model_build_data_dir.joinpath('ibound.txt'), ibound[0])
    return ibound


def get_lake_array(recalc=False):
    save_path = processed_model_build_data_dir.joinpath('lake_array.txt')
    if save_path.exists() and not recalc:
        lake = np.loadtxt(save_path)
        lake = lake.astype(float)
        lake[lake < 0] = np.nan
        return lake

    lakefront_shp_path = base_model_build_data_dir.joinpath('lakefront.shp')
    lake_shp_path = base_model_build_data_dir.joinpath('lake_hawea.shp')
    lake = temp_smt.io.shape_file_to_model_array(lake_shp_path, 'id', alltouched=True)
    lake_front = temp_smt.io.shape_file_to_model_array(lakefront_shp_path, 'id', alltouched=True)
    lake[np.isfinite(lake_front)] = -1
    lake = lake.astype(int)
    np.savetxt(save_path, lake, fmt='%d')
    lake = lake.astype(float)
    lake[lake < 0] = np.nan

    return lake


def _lake_locs():
    lake = get_lake_array(True)
    lake_data = temp_smt.io.array_to_df(lake, 'drop')
    lake_data.drop(columns='drop', inplace=True)
    lake_data.loc[:, 'k'] = 0
    return lake_data


def _river_locs():
    hawea_shp_path = base_model_build_data_dir.joinpath('hawea_river.shp')
    clutha_shp_path = base_model_build_data_dir.joinpath('lower_clutha.shp')

    # read in the shapefiles and save only the data in active model
    ibound = no_flow()[0]
    hawea = temp_smt.io.shape_file_to_model_array(hawea_shp_path, 'dist_top', alltouched=True)
    hawea[ibound < 1] = np.nan

    # make sure hawea r. not in the lake!!!
    lake_hawea = temp_smt.io.df_to_array(_lake_locs(), 'i')
    hawea[np.isfinite(lake_hawea)] = np.nan

    hawea = temp_smt.io.array_to_df(hawea, 'dist').sort_values('dist')

    clutha = temp_smt.io.shape_file_to_model_array(clutha_shp_path, 'dist_top', alltouched=True)
    clutha[ibound < 1] = np.nan
    clutha = temp_smt.io.array_to_df(clutha, 'dist').sort_values('dist')

    # add top data
    top = simplify_upper_clutha_dem()
    hawea.loc[:, 'rbot'] = top[hawea.loc[:, 'i'], hawea.loc[:, 'j']]
    hawea.loc[0, 'rbot'] = hawea.loc[1, 'rbot']  # first segment dem is nan, so set first to second
    hawea.loc[:, 'rbot_raw'] = hawea.loc[:, 'rbot']
    clutha.loc[:, 'rbot'] = top[clutha.loc[:, 'i'], clutha.loc[:, 'j']]
    clutha.loc[0, 'rbot'] = hawea.loc[:, 'rbot'].iloc[-1]
    clutha.loc[:, 'rbot_raw'] = clutha.loc[:, 'rbot']

    # fix weird things in the DEM
    val = -1
    idx = hawea.rbot.diff(-1) <= val
    for d in [-2]:
        idx = idx | (hawea.rbot.diff(d) <= val)
    hawea.loc[idx, 'rbot'] = np.nan

    hawea.loc[idx, 'rbot'] = hawea.loc[:, 'rbot'].rolling(5, min_periods=1, center=True).mean().loc[idx]

    val = -1
    idx = clutha.rbot.diff(-1) <= val
    for d in [-2]:
        idx = idx | (clutha.rbot.diff(d) <= val)
    clutha.loc[idx, 'rbot'] = np.nan

    clutha.loc[idx, 'rbot'] = clutha.loc[:, 'rbot'].rolling(5, min_periods=1, center=True).mean().loc[idx]

    # label rivers
    hawea.loc[:, 'rname'] = 'hawea'
    clutha.loc[:, 'rname'] = 'clutha'
    hawea.sort_values('dist', inplace=True)
    clutha.sort_values('dist', inplace=True)
    outdata = pd.concat((hawea, clutha))

    # set the river river bottoms 3 m below top so that the stage is always higher than river bottom
    outdata.loc[:, 'rbot'] += -2.5

    outdata.reset_index(inplace=True, drop=True)
    return outdata


def elv_calc():
    bot_path = base_model_build_data_dir.joinpath('Model_bot.tif')
    top = simplify_hawea_dem()
    top[top > 600] = 600  # for easy viewing of noflow area
    bot = temp_smt.io.raster_to_array(bot_path, 'min')
    # fill missing bottoms with neibours
    assert np.isnan(bot[:, 0]).all()
    assert np.isnan(bot[:, -7:]).all()
    bot[:, 0] = bot[:, 1]
    bot[:, -7:] = bot[:, -8][:, np.newaxis]

    # adjust bottom so that the clutha is not below bottom
    river = _river_locs()
    temp = bot[river.loc[:, 'i'], river.loc[:, 'j']]
    rbots = river.loc[:, 'rbot'].values
    idx = temp >= rbots
    temp[idx] = rbots[idx] - 0.5  # set model bottoms to below river level.
    bot[river.loc[:, 'i'], river.loc[:, 'j']] = temp

    # fix bottom area which is causing dry cells by reducing the gradient
    fixer = np.isfinite(smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('bottoms_fixer.shp'),
                                             'id', alltouched=True))
    temp = deepcopy(bot[fixer])
    diff = (temp.max()-temp.min())
    temp2 = (temp-temp.min())/(temp.max()-temp.min())

    bot[fixer] = temp3 = temp2 * diff/3 + temp.min()

    # adjust top so it is above rbot
    temp = top[river.loc[:, 'i'], river.loc[:, 'j']]
    idx = temp <= rbots
    temp[idx] = rbots[idx] + 0.5  # set model tops to above river bottom.
    top[river.loc[:, 'i'], river.loc[:, 'j']] = temp

    assert np.isfinite(top).all()
    assert np.isfinite(bot).all()
    thick = top - bot
    bot[thick < 2] = top[thick < 2] - 2  # set min thickness to 2m

    out = np.concatenate((top[np.newaxis], bot[np.newaxis]))
    np.save(processed_model_build_data_dir.joinpath('elv_db.npy'), out)
    np.savetxt(processed_model_build_data_dir.joinpath('elv_db_top.txt'), out[0])
    np.savetxt(processed_model_build_data_dir.joinpath('elv_db_bot.txt'), out[1])

    return out


def get_top(recalc=False):
    if recalc:
        elv_calc()
    out = np.loadtxt(processed_model_build_data_dir.joinpath('elv_db_top.txt'))
    return out


def get_bottom(recalc=False):
    if recalc:
        elv_calc()
    out = np.loadtxt(processed_model_build_data_dir.joinpath('elv_db_bot.txt'))
    return out


smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                             model_version_name, sdp, temp_file_dir,
                             rotation=0, layer_type=layer_type,
                             no_flow_calc=no_flow, elv_calculator=elv_calc,
                             base_map_path=base_map_path, default_figsize=default_figsize, epsg_num=2193)


def get_starting_heads(recalc=False):
    save_path = processed_model_build_data_dir.joinpath('start_heads.txt')
    if save_path.exists() and not recalc:
        return np.loadtxt(save_path)[np.newaxis]
    strt_hds = smt.get_tops()[0]
    scott_hds = smt.io.raster_to_array(proj_root.joinpath('scott_model/scott_model_files/scott_hds.tif'),
                                       'average')
    idx = scott_hds < strt_hds
    strt_hds[idx] = scott_hds[idx]
    np.savetxt(save_path, strt_hds)
    return strt_hds[np.newaxis]


def data_checks():
    contour_levels = range(200, 460, 10)
    smt.recalc_all_pickles()
    tops = smt.get_tops()[0]
    bots = smt.get_bottoms()[0]
    ibound = smt.get_no_flow(0)
    smt.plot.plt_matrix(bots, base_map=True, title='bottom_raw', contour=True, label_contours=True,
                        contour_levels=contour_levels)
    tops[ibound < 1] = np.nan
    bots[ibound < 1] = np.nan
    smt.plot.plt_matrix(tops, base_map=True, title='top', contour=True, label_contours=True,
                        contour_levels=contour_levels, no_flow_layer=0)
    smt.plot.plt_matrix(bots, base_map=True, title='bottom', contour=True, label_contours=True,
                        contour_levels=contour_levels, no_flow_layer=0)

    # N-S cross sections
    cols = range(0, smt.cols, 20)
    for c in cols:
        smt.plot.plt_slice(np.zeros(smt.model_shape) * np.nan, x_coords=c, y_coords=None, coords_in_row_col=True,
                           plot_locator=True, title=f'col{c}')

    # E-W cross sections
    rows = range(0, smt.rows, 20)
    for r in rows:
        smt.plot.plt_slice(np.zeros(smt.model_shape) * np.nan, x_coords=None, y_coords=r, coords_in_row_col=True,
                           plot_locator=True, title=f'row{r}')
    smt.plot.show()

    # happy with this setup


def export_model_boundary():
    outpath = processed_model_build_data_dir.joinpath('model_boundary.shp')
    ibound = smt.get_no_flow(0)
    ibound[ibound <= 0] = np.nan
    smt.io.polygonize_array(outpath,
                            ibound, None)


if __name__ == '__main__':
    elv_calc()
    get_bottom(True)
    smt.recalc_all_pickles()
    raise NotImplementedError
    data_checks()
    get_starting_heads(True)
    export_model_boundary()
    smt.plot.plt_matrix(smt.get_model_zeros(), base_map=True)
    smt.plot.show()
