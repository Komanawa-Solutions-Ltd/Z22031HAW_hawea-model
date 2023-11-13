"""
created matt_dumont 
on: 19/07/22
"""
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

try:
    from model_tools.regular_modeltools import ModelTools_RegularGrid
except ModuleNotFoundError:
    from dummy_packages import ModelTools_RegularGrid

from project_base import proj_root, modelling_dir, unbacked_dir, base_model_build_data_dir, \
    processed_model_build_data_dir
import geopandas as gpd
import numpy as np
import pandas as pd
from copy import deepcopy

default_figsize = (8, 10)
temp_file_dir = unbacked_dir.joinpath('tempfiles')
temp_file_dir.mkdir(exist_ok=True)
sdp = unbacked_dir.joinpath('sdp')
sdp.mkdir(exist_ok=True)

# keynote if this is true then the model build excludes all of the pumping in the "near_river" zone (near_river.shp)
#  note the abstraction is also added to the river targets
exclude_near_river_pumping = True

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

layers = 3
layer_type = [1, 0, 0]
bund_top = 330
l2_top = 328

temp_smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                                  model_version_name, sdp,
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


def get_2d_moraine(recalc=False):
    shp_path = base_model_build_data_dir.joinpath('moraine.shp')
    outpath = base_model_build_data_dir.joinpath('moraine.txt')
    if outpath.exists() and not recalc:
        data = np.loadtxt(outpath)
        return data == 1
    data = np.isfinite(temp_smt.io.shape_file_to_model_array(shp_path, 'id', alltouched=True))
    np.savetxt(outpath, data, '%d')
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
    assert temp_smt.layers == 3
    ibound[0][np.isfinite(active)] = 1
    ibound[0][np.isfinite(camphill)] = 0
    # remove cameron hill
    cameron = temp_smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('cameron_hill.shp'), 'id',
                                                    alltouched=True)
    ibound[0][np.isfinite(cameron)] = 0

    # remove sandy point
    sp_rm = temp_smt.io.shape_file_to_model_array(
        base_model_build_data_dir.joinpath('rm_sandy_point.shp'), 'id',
        alltouched=True)
    ibound[0][np.isfinite(sp_rm)] = 0

    # remove dam
    dam = temp_smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('dam.shp'), 'id', alltouched=True)
    ibound[0][np.isfinite(dam)] = 0

    np.savetxt(processed_model_build_data_dir.joinpath('ibound.txt'), ibound[0])
    return np.repeat(ibound, 3, axis=0)


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
    out = []
    for l in range(smt.layers):  # keynote set ghbs in all lake cells except low cond lake bar
        temp = deepcopy(lake_data)
        temp.loc[:, 'k'] = l
        out.append(temp)
    lake_data = pd.concat(out)
    low_cond = get_low_cond_array()
    lake_data = lake_data.loc[~low_cond[lake_data.k, lake_data.i, lake_data.j]]
    return lake_data


def _river_locs():
    hawea_shp_path = base_model_build_data_dir.joinpath('hawea_river.shp')
    clutha_shp_path = base_model_build_data_dir.joinpath('lower_clutha.shp')

    # read in the shapefiles and save only the data in active model
    ibound = no_flow()[0]
    hawea = temp_smt.io.shape_file_to_model_array(hawea_shp_path, 'dist_top', alltouched=True)
    hawea[ibound < 1] = np.nan

    # make sure hawea r. not in the lake!!!
    lake_hawea = get_lake_array()
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
    hawea.loc[:, 'seg'] = 1
    clutha.loc[:, 'rname'] = 'clutha'
    clutha.loc[:, 'seg'] = 2
    # fix rbot so consecutively below
    roll_size = 5
    clutha.loc[:, 'rbot'] = clutha.loc[:, 'rbot'].rolling(roll_size, min_periods=1, center=True).mean()
    hawea.loc[:, 'rbot'] = hawea.loc[:, 'rbot'].rolling(roll_size, min_periods=1, center=True).mean()
    hawea.sort_values('dist', inplace=True)
    clutha.sort_values('dist', inplace=True)
    hawea.loc[:, 'reach'] = np.arange(len(hawea))
    clutha.loc[:, 'reach'] = np.arange(len(clutha))
    outdata = pd.concat((hawea, clutha))

    # set the river river bottoms 3 m below top so that the stage is always higher than river bottom
    outdata.loc[:, 'rbot'] += -2.5

    outdata.reset_index(inplace=True, drop=True)
    return outdata


def _slope_fix_southern(bottoms):
    bottoms = deepcopy(bottoms)
    riv = _river_locs()
    fixer_path = base_model_build_data_dir.joinpath('bottoms_fixer_line.shp')
    fixer = temp_smt.io.shape_file_to_model_array(fixer_path, 'id', alltouched=True)
    ibound = no_flow()
    fixer[ibound[0] != 1] = np.nan
    idxs = smt.model_where(np.isfinite(fixer))
    start_row = {}
    stop_row = {}
    for row, col in idxs:
        start_row[col] = row
        temp = riv.loc[(riv.j == col) & (riv.i >= row)].i.min()
        stop_row[col] = temp

    for col in start_row:
        sr_row = start_row[col]
        st_row = stop_row[col]
        if np.isnan(st_row):
            continue
        top_bot = bottoms[sr_row, col]
        bot_bot = bottoms[st_row, col]
        nrows = st_row - sr_row
        if top_bot > bot_bot:
            new_bots = -1 * np.arange(nrows) * (top_bot - bot_bot) / nrows + top_bot
        else:
            new_bots = np.arange(nrows) * (top_bot - bot_bot) / nrows + bot_bot

        bottoms[sr_row:st_row, col] = new_bots
    return bottoms


def elv_calc(fix_southern=True, one_layer_version=False):
    """

    :param fix_southern: should always be True (except in debugging issues)
    :return:
    """
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
    ibound = no_flow()
    fixer = smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('bottoms_fixer_slope.shp'),
                                             'id', alltouched=True)
    fixer[np.isnan(fixer)] = -1
    fixer = fixer.astype(int)
    for v in np.unique(fixer):
        if v < 0:
            continue
        idx = fixer == v
        temp = deepcopy(bot[idx])
        diff = (temp.max() - temp.min())
        temp2 = (temp - temp.min()) / (temp.max() - temp.min())
        bot[idx] = temp2 * diff / 3 + temp.min()

    # adjust top so it is above rbot
    temp = top[river.loc[:, 'i'], river.loc[:, 'j']]
    idx = temp <= rbots
    temp[idx] = rbots[idx] + 0.5  # set model tops to above river bottom.
    top[river.loc[:, 'i'], river.loc[:, 'j']] = temp

    # adjust the bottoms near the river which are causing dry cells
    fixer = smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('bottoms_fixer_flat.shp'),
                                             'id', alltouched=True)
    fixer[np.isnan(fixer)] = -1
    fixer = fixer.astype(int)
    for v in np.unique(fixer):
        if v < 0:
            continue
        temp = deepcopy(bot[fixer == v])
        bot[fixer == v] = temp.min()

    assert np.isfinite(top).all()
    assert np.isfinite(bot).all()
    thick = top - bot
    bot[thick < 2] = top[thick < 2] - 2  # set min thickness to 2m
    if fix_southern:
        bot = _slope_fix_southern(bot)
    # adjust top so it is above rbot
    temp = top[river.loc[:, 'i'], river.loc[:, 'j']]
    idx = temp <= rbots
    temp[idx] = rbots[idx] + 0.5  # set model tops to above river bottom.
    top[river.loc[:, 'i'], river.loc[:, 'j']] = temp

    if one_layer_version:
        import warnings
        warnings.warn('one layer version')
        return np.concatenate((top[np.newaxis], bot[np.newaxis]))


    out = old_to_3d(top, bot)

    np.save(processed_model_build_data_dir.joinpath('elv_db.npy'), out)
    return out


def old_to_3d(top, bot):
    bot1 = bot
    bot2 = bot - 1
    bot3 = bot - 2

    moraine = get_2d_moraine()
    bot1[moraine | np.isfinite(get_lake_array())] = bund_top
    bot2[moraine | np.isfinite(get_lake_array())] = l2_top

    azimuth_data = temp_smt.io.azimuth_from_line(base_model_build_data_dir.joinpath('3d_smoother.shp'), 20,
                                                 return_array=False).set_index('id')
    step_points = temp_smt.io.get_new_points_from_points_azimuth(azimuth_data, 1000, 90, return_array=False)
    i, j = temp_smt.convert_coords_to_matix(step_points.new_x, step_points.new_y)
    step_points.loc[:, 'i'] = i
    step_points.loc[:, 'j'] = j
    all_points = pd.concat((azimuth_data, step_points))

    for barray in [bot1, bot2]:
        all_points.loc[:, 'val'] = barray[all_points.i, all_points.j]
        temp = all_points.groupby(['i', 'j']).mean().reset_index()
        all_i, all_j = temp_smt.get_model_index_grid()
        smooth_bot = griddata(temp.loc[:, ['i', 'j']].values, temp.loc[:, 'val'].values,
                              (all_i, all_j),
                              method='linear'
                              )
        smooth_bot[moraine | np.isfinite(get_lake_array())] = np.nan
        barray[np.isfinite(smooth_bot)] = smooth_bot[np.isfinite(smooth_bot)]
    np.savetxt(processed_model_build_data_dir.joinpath('smoothed_array'), np.isfinite(smooth_bot), '%d')
    thick2 = bot2 - bot3
    bot3[thick2 < 1] += -1 + thick2[thick2 < 1]
    return np.concatenate([e[np.newaxis] for e in [top, bot1, bot2, bot3]])


def get_layer_pinchout_area(recalc=False):
    if recalc:
        elv_calc()
    return np.loadtxt(processed_model_build_data_dir.joinpath('smoothed_array'), int) == 1


def get_elv_db(recalc=False):
    if recalc:
        elv_calc()
    return np.load(processed_model_build_data_dir.joinpath('elv_db.npy'))


def get_ibound(recalc=False):
    if recalc:
        no_flow()
    out = np.loadtxt(processed_model_build_data_dir.joinpath('ibound.txt'))
    return np.repeat(out[np.newaxis], 3, axis=0)


smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                             model_version_name, sdp,
                             rotation=0, layer_type=layer_type,
                             no_flow_calc=get_ibound, elv_calculator=get_elv_db,
                             base_map_path=base_map_path, default_figsize=default_figsize, epsg_num=2193)


def get_starting_heads(recalc=False):
    raise NotImplementedError('depreciated')
    save_path = processed_model_build_data_dir.joinpath('start_heads.txt')
    if save_path.exists() and not recalc:
        return np.repeat(np.loadtxt(save_path)[np.newaxis], smt.layers, axis=0)
    strt_hds = smt.get_tops()[0]
    scott_hds = smt.io.raster_to_array(proj_root.joinpath('scott_model/scott_model_files/scott_hds.tif'),
                                       'average')
    idx = scott_hds < strt_hds
    strt_hds[idx] = scott_hds[idx]
    np.savetxt(save_path, strt_hds)
    return np.repeat(strt_hds[np.newaxis], smt.layers, axis=0)


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


def get_xsection_points(recalc=False):
    num_plots = 10
    save_path = processed_model_build_data_dir.joinpath('xsection_points')

    if save_path.exists() and not recalc:
        step_points = pd.read_csv(save_path)
        return step_points

    azimuth_data = smt.io.azimuth_from_line(base_model_build_data_dir.joinpath('3d_examiner.shp'), 20,
                                            return_array=False).set_index('id')
    step_points = smt.io.get_new_points_from_points_azimuth(azimuth_data, 2000, 90, return_array=False)
    idxs = np.arange(num_plots + 1) * len(step_points) // num_plots
    idxs[-1] = step_points.index[-1]
    (x_min, x_max), (y_min, y_max) = smt.get_xlim_ylim()
    step_points[step_points.new_x > x_max] = x_max
    step_points = step_points.loc[idxs, ['old_x', 'old_y', 'new_x', 'new_y']].reset_index()
    xs = [
        (1302335.8300223248, 1303305.152166307),
        (1302197.3554303276, 1303486.9000683036),
        (1302257.9380643263, 1303512.864054303),
        (1302231.974078327, 1304014.8344502938)
    ]
    ys = [
        (5053140.726263654, 5053227.272883653),
        (5052552.2092476655, 5052604.137219664),
        (5051652.124399682, 5051755.98034368),
        (5050803.967523698, 5050829.931509697),
    ]

    for i, (x, y) in enumerate(zip(xs, ys)):
        step_points.loc[100 + i, ['old_x', 'new_x', ]] = x
        step_points.loc[100 + i, ['old_y', 'new_y']] = y

    step_points.to_csv(save_path)
    return step_points


def get_lake_bar():
    lake = get_lake_array()
    ibound = smt.get_no_flow(0)
    rows, cols = smt.get_model_index_grid()
    rows = rows[np.isfinite(lake) & (ibound == 1)]
    cols = cols[np.isfinite(lake) & (ibound == 1)]

    out_array = np.full(smt.model_2d_shape, False)
    for col in np.unique(cols):
        row = rows[cols == col].max()
        out_array[row, col] = True
    for row in np.unique(rows):
        if out_array[row, :].sum() > 0:
            continue
        col = cols[rows == row].max()
        out_array[row, col] = True
    return out_array


def get_low_cond_array():
    # make a low conductiviyt array for the area, how to handle the interface between layer 3 and the lake, lake bar?
    data = np.full(smt.model_shape, False)
    data[1, get_2d_moraine()] = True
    lake_bar = get_lake_bar()
    data[1, lake_bar] = True
    data[2, lake_bar] = True
    return data


def examine_3d(num_plots=10, show=True, save=False):
    rt_figs = []
    rt_names = []
    elv_calc()
    get_ibound(True)
    lake = get_lake_array(True)
    moraine = get_2d_moraine(True)
    smooth = get_layer_pinchout_area(True)
    smt.plot.plt_matrix((moraine | np.isfinite(lake)), base_map=True, no_flow_layer=0)
    azimuth_data = smt.io.azimuth_from_line(base_model_build_data_dir.joinpath('3d_examiner.shp'), 20,
                                            return_array=False).set_index('id')
    step_points = smt.io.get_new_points_from_points_azimuth(azimuth_data, 2000, 90, return_array=False)
    idxs = np.arange(num_plots + 1) * len(step_points) // num_plots
    idxs[-1] = step_points.index[-1]
    (x_min, x_max), (y_min, y_max) = smt.get_xlim_ylim()
    step_points[step_points.new_x > x_max] = x_max
    plt_array = smt.get_model_zeros(True) * np.nan
    plt_array[:, np.isfinite(lake)] = 1
    plt_array[1:, get_lake_bar()] = 3
    plt_array[:, moraine] = 2
    plt_array[1, moraine] = 3
    plt_array[:, smooth] = 4
    names = {
        1: 'Lake',
        2: 'Moraine (permeable)',
        3: 'Moraine (impermeable)',
        4: 'Pinchout Area',
    }
    colors = {
        1: 'blue',
        2: 'sandybrown',
        3: 'saddlebrown',
        4: 'lightcoral',
    }
    for l in range(smt.layers):
        fig, ax = plt.subplots(figsize=(10, 8))
        smt.plot.plt_discrete_matrix(plt_array[l], names=names, colors=colors, base_map=True, no_flow_layer=l,
                                     alpha=0.6,
                                     ax=ax, legend_loc='lower right', title=f'layer: {l}')
        ax.set_ylim(5.051e6, smt.get_xlim_ylim(False)[-1])
        ax.set_xlim(1.3e6, 1.31e6)
        fig.tight_layout()
        rt_figs.append(fig)
        rt_names.append(f'spatiall{l}')

    l_slice_kwargs = dict(c='k', lw=1, alpha=1, ls='--')
    i = 0
    for ox, oy, nx, ny in step_points.loc[idxs, ['old_x', 'old_y', 'new_x', 'new_y']].itertuples(False, None):
        fig, (ax, locator_ax) = plt.subplots(nrows=2, gridspec_kw=dict(height_ratios=(3, 1)), figsize=(14, 9))
        fig, ax = smt.plot.plt_descrete_slice(plt_array, names=names, colors=colors, x_coords=[ox, nx],
                                              y_coords=[oy, ny], ax=ax,
                                              locator_ax=locator_ax, alpha=0.4, color_bar=False, no_flow_layer=0,
                                              locator_lim_pad=1000, lay_slice_kwargs=l_slice_kwargs)
        locator_ax.set_ylim([5.0520e6, max(locator_ax.get_ylim())])
        fig.tight_layout()
        rt_figs.append(fig)
        rt_names.append(f'cross_section_{i:02d}')
        i += 1
    xs = [
        (1302335.8300223248, 1303305.152166307),
        (1302197.3554303276, 1303486.9000683036),
        (1302257.9380643263, 1303512.864054303),
        (1302231.974078327, 1304014.8344502938)
    ]
    ys = [
        (5053140.726263654, 5053227.272883653),
        (5052552.2092476655, 5052604.137219664),
        (5051652.124399682, 5051755.98034368),
        (5050803.967523698, 5050829.931509697),
    ]

    for i, (x, y) in enumerate(zip(xs, ys)):
        fig, (ax, locator_ax) = plt.subplots(nrows=2, gridspec_kw=dict(height_ratios=(3, 1)), figsize=(14, 9))
        fig, ax = smt.plot.plt_descrete_slice(plt_array, names=names, colors=colors,
                                              x_coords=x, y_coords=y, ax=ax,
                                              locator_ax=locator_ax, alpha=0.4, color_bar=False, no_flow_layer=0,
                                              locator_lim_pad=1000, lay_slice_kwargs=l_slice_kwargs)
        locator_ax.set_ylim([5.0450e6, max(locator_ax.get_ylim())])
        fig.tight_layout()
        rt_figs.append(fig)
        rt_names.append(f'river_slice_{i:02d}')

    smt.plot.plt_layer_slices(smt.get_thickness(), base_map=True, contour_levels=10, contour=True, title='thick')
    thick = smt.get_thickness()
    thick[thick > 10] = np.nan
    smt.plot.plt_layer_slices(thick, base_map=True, contour_levels=1, contour=True, title='thick')
    if save:
        outdir = proj_root.joinpath('support_figures','3d_xsect')
        outdir.mkdir( exist_ok=True)
        for name, fig in zip(rt_names, rt_figs):
            fig.savefig(outdir.joinpath(f'{name}.png'))

    if show:
        smt.plot.show()

    return rt_names, rt_figs


def plot_3d_structure_spatial():
    lake = np.isfinite(get_lake_array())
    lake_bar = get_lake_bar()
    moraine = get_2d_moraine()
    pinch = get_layer_pinchout_area()

    mapper = {
        1: 'Lake',
        2: 'Lake bar (layers 1 & 2)',
        3: 'Moraine zone',
        4: 'Layer pinch out area',
    }
    plt_layer = smt.get_model_zeros() * np.nan
    plt_layer[lake] = 1
    plt_layer[moraine] = 3
    plt_layer[pinch] = 4
    plt_layer[lake_bar] = 2
    fig, ax = plt.subplots(figsize=(10, 6))
    smt.plot.plt_discrete_matrix(plt_layer, names=mapper, base_map=True, no_flow_layer=0, cmap='tab10', alpha=0.6,
                                 ax=ax, legend_loc='lower right', title='3D structure zones')
    ax.set_ylim(5.051e6, smt.get_xlim_ylim(False)[-1])
    ax.set_xlim(1.3e6, 1.31e6)
    fig.tight_layout()
    plt.show()
    fig.savefig(proj_root.joinpath('support_figures', '3d_spatial.png'))
    return fig, ax


if __name__ == '__main__':
    examine_3d(save=True)
    plot_3d_structure_spatial()
    bots = smt.get_bottoms()
    smt.plot.plt_layer_slices(bots, 'bottom', contour=True, contour_levels=5, label_contours=True, base_map=True)
    smt.plot.show()
    examine_3d()
    smt.plot.show()
    t = get_xsection_points()
    temp = get_low_cond_array()
    smt.plot.plt_layer_slices(temp, base_map=True)
    smt.plot.show()
    from pathlib import Path

    get_lake_array(True)
    get_2d_moraine(True)
    save_old = False
    old_path = Path.home().joinpath('Downloads/previous_bot.txt')
    if save_old:
        old = get_elv_db()[1]
        np.savetxt(old_path, old)

    old_bot = np.loadtxt(old_path)
    top = get_elv_db()[0]
    old_to_3d(top, old_bot)
    new_bot = elv_calc()[1]
    temp = np.concatenate((old_bot, new_bot))
    vmax = np.nanmax(temp)
    vmin = np.nanmin(temp)
    contour_levels = 2
    fig, (ax1, ax2) = plt.subplots(ncols=2, sharex=True, sharey=True, figsize=(16, 9.5))
    smt.plot.plt_matrix(old_bot, base_map=True, contour=True, contour_levels=contour_levels,
                        label_contours=True, no_flow_layer=0, title='old_bot', ax=ax1,
                        vmin=vmin, vmax=vmax)
    smt.plot.plt_matrix(new_bot, base_map=True, contour=True, contour_levels=contour_levels,
                        label_contours=True, no_flow_layer=0, title='new_bot', ax=ax2,
                        vmin=vmin, vmax=vmax)
    fig.tight_layout()
    smt.plot.plt_matrix(old_bot - new_bot, base_map=True, contour=True, contour_levels=2,
                        label_contours=True, no_flow_layer=0, title='dif (old-new)')

    smt.plot.show()
    raise NotImplementedError
    data_checks()
    get_starting_heads(True)
    export_model_boundary()
    smt.plot.plt_matrix(smt.get_model_zeros(), base_map=True)
    smt.plot.show()
