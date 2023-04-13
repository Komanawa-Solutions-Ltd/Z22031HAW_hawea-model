"""
created matt_dumont 
on: 19/07/22
"""
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd

try:
    from model_tools.regular_modeltools import ModelTools_RegularGrid
    from model_tools.time_discretization import TimeDis
except ModuleNotFoundError:
    from dummy_packages import ModelTools_RegularGrid, TimeDis
from project_base import unbacked_dir, base_model_build_data_dir, modelling_dir, campbells_dir
import geopandas as gpd

temp_file_dir = unbacked_dir.joinpath('tempfiles')
temp_file_dir.mkdir(exist_ok=True)
sdp = unbacked_dir.joinpath('sdp_campbells')
sdp.mkdir(exist_ok=True)

extent = gpd.read_file(campbells_dir.joinpath('base_input_data',
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

temp_smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                                  model_version_name, sdp,
                                  rotation=0, layer_type=None,
                                  no_flow_calc=None, elv_calculator=None,
                                  base_map_path=base_map_path, default_figsize=(8, 7), epsg_num=2193)


def no_flow(recalc=False):
    save_path = campbells_dir.joinpath('processed_input_data', 'ibound.npy')
    if save_path.exists() and not recalc:
        return np.load(save_path)[np.newaxis]

    from model_build.project_model_tools import smt as hawea_smt
    ibound = hawea_smt.get_no_flow(0)
    with tempfile.TemporaryDirectory() as tdir:
        tdir = Path(tdir)
        hawea_smt.io.array_to_raster(tdir.joinpath('temp.tif'), ibound)
        outibound = smt.io.raster_to_array(tdir.joinpath('temp.tif'), 'mean').astype(int)
    temp = outibound == 0
    outibound[0, :] = -1
    outibound[:, 0] = -1
    outibound[:, -1] = -1
    outibound[temp] = 0

    np.save(save_path, outibound)
    return outibound[np.newaxis]


def simplify_hawea_dem(recalc=False):
    """
    take the mean of the soutisland 15 m dem provided by Lincoln agritech
    run once from project filestore
    :return:
    """
    dem_path = modelling_dir.joinpath('input_data/southi_15mdem_Hawea.tif')
    outpath = campbells_dir.joinpath('processed_input_data', 'raw_mean_dem_top.txt')
    if outpath.exists() and not recalc:
        data = np.loadtxt(outpath)
        return data
    data = temp_smt.io.raster_to_array(dem_path, 'mean')
    np.savetxt(outpath, data)
    return data


def _get_top_array(retun_idx=False, recalc=False):
    save_path = campbells_dir.joinpath('processed_input_data', 'model_top.npy')
    if save_path.exists() and not recalc:
        return np.load(save_path)

    all_dem = simplify_hawea_dem()
    use_dem = all_dem.copy()
    idx = smt.get_model_zeros() + 1
    np.save(save_path, use_dem)
    if retun_idx:
        return use_dem, idx
    return use_dem


def _get_bot_array(retun_idx=False, recalc=False):
    save_path = campbells_dir.joinpath('processed_input_data', 'model_bot.npy')
    if save_path.exists() and not recalc:
        return np.load(save_path)

    from model_build.project_model_tools import smt as hawea_smt
    ibound = hawea_smt.get_bottoms()[0]
    with tempfile.TemporaryDirectory() as tdir:
        tdir = Path(tdir)
        hawea_smt.io.array_to_raster(tdir.joinpath('temp.tif'), ibound)
        model_bot = smt.io.raster_to_array(tdir.joinpath('temp.tif'), 'mean').astype(int)
    np.save(save_path, model_bot)
    return model_bot


def elv_calc():
    return np.concatenate((
        _get_top_array()[np.newaxis],
        _get_bot_array()[np.newaxis]
    ), axis=0)


smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                             model_version_name, sdp,
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
    name='campbells', nper=nper, tsmult=1., steady=steady,
    dates=use_dates,
    nstp=nstp
)
if __name__ == '__main__':
    nf = no_flow(True)[0]
    smt.plot.plt_matrix(nf, title='no flow', base_map=True)
    top, idx = _get_top_array(True, True)
    t = smt.get_elv_db()
    smt.plot.plt_matrix(top, title='top', base_map=True, no_flow_layer=0)
    smt.plot.plt_matrix(idx, title='idx', base_map=True, no_flow_layer=0)
    smt.plot.plt_matrix(t[1], title='bottom', base_map=True, no_flow_layer=0)
    smt.plot.plt_matrix(t[0] - t[1], title='thickness', base_map=True, no_flow_layer=0)

    smt.plot.show()
    pass
