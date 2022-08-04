"""
created matt_dumont 
on: 19/07/22
"""
from model_tools.regular_modeltools import ModelTools_RegularGrid
from project_base import modelling_dir, unbacked_dir  # from project_base.py file in the project
import geopandas as gpd
import numpy as np

# todo clone the 'modflow_tools' repo and make a new branch for this model, don't forget to merge
# when finished

temp_file_dir = unbacked_dir.joinpath('tempfiles')
temp_file_dir.mkdir(exist_ok=True)
sdp = unbacked_dir.joinpath('sdp')
sdp.mkdir(exist_ok=True)

boundary_path = modelling_dir.joinpath('input_data/model_boundary.shp')
temp = gpd.read_file(boundary_path)
ulx = np.floor(temp.bounds.loc[0, 'minx'])
uly = np.ciel(temp.bounds.loc[0, 'maxy'])

lrx = np.ciel(temp.bounds.loc[0, 'maxx'])
lry = np.floor(temp.bounds.loc[0, 'miny'])
base_map_path = None  # todo
model_version_name = 'v1'

grid_space = 250  #
cols = (ulx - lrx // grid_space) + 1
rows = (uly - lry // grid_space) + 1

layers = 1  # todo
nper = None  # todo
# todo other period data
layer_type = None  # todo
steady = None  # todo

temp_smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                                  model_version_name, sdp, temp_file_dir,
                                  rotation=0, nper=None, layer_type=None, steady=None,
                                  no_flow_calc=None, elv_calculator=None,
                                  base_map_path=base_map_path, default_figsize=(14, 7), epsg_num=2193)


def no_flow():
    ibound = temp_smt.get_model_zeros(_3d=True)
    active = temp_smt.io.shape_file_to_model_array(boundary_path, 'fid', alltouched=True)  # todo attribute
    assert temp_smt.layers == 1
    ibound[0][np.isfinite(active)] = 1
    return ibound

def elv_calc():
    top_path = None  # todo
    bot_path = None  # todo
    top = temp_smt.io.raster_to_array(top_path, 'average')
    bot = temp_smt.io.raster_to_array(bot_path, 'average')

    return np.concatenate((top[np.newaxis], bot[np.newaxis]))


smt = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                             model_version_name, sdp, temp_file_dir,
                             rotation=0, nper=nper, layer_type=layer_type, steady=steady,
                             no_flow_calc=no_flow, elv_calculator=elv_calc,
                             base_map_path=base_map_path, default_figsize=(14, 7), epsg_num=2193)
