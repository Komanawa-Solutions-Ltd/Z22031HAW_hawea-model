"""
created matt_dumont 
on: 2/09/22
"""
from pathlib import Path

import pandas as pd

from project_base import unbacked_dir, base_model_build_data_dir
from model_tools.regular_modeltools import ModelTools_RegularGrid
import flopy
import numpy as np

base_scott_dir = Path(__file__).parent.joinpath('scott_model_files')
default_figsize = (8, 10)
temp_file_dir = unbacked_dir.joinpath('tempfiles')
temp_file_dir.mkdir(exist_ok=True)
sdp = unbacked_dir.joinpath('sdp_scott')
sdp.mkdir(exist_ok=True)

base_map_path = base_model_build_data_dir.joinpath('nz-topo50-maps.jpg')
model_version_name = 'v1'

grid_space = 250  #
cols = 60 - 8
rows = 92 - 20
#  lower left corner 1296250mE 5032250mN, Upper right corner 1312670mE 5059750mN
ulx = 1296250 + np.sum([500., 500., 660., 490., 350., ])
uly = 5059750 - np.sum([500., 500., 500., 500., 500., 500., 660., 490., 350.])  # todo get from Jens

layers = 1
layer_type = [1]


def ibound_calc():
    m = get_full_scott_model()
    ibnd = convert_scott_array_to_reg_grid(m.bas6.ibound.array[0])
    return ibnd[np.newaxis].astype(float)


smt_scott = ModelTools_RegularGrid(ulx, uly, layers, rows, cols, grid_space,
                                   model_version_name, sdp, temp_file_dir,
                                   rotation=0, layer_type=layer_type,
                                   no_flow_calc=ibound_calc, elv_calculator=None,
                                   base_map_path=base_map_path, default_figsize=default_figsize, epsg_num=2193)


def get_full_scott_model():
    t = flopy.modflow.Modflow.load(base_scott_dir.joinpath('gv10.nam'))
    return t


def convert_scott_array_to_reg_grid(array):
    assert array.shape == (92, 60)
    return array[9:rows + 9, 5:cols + 5]


def covert_scott_df_to_reg(data: pd.DataFrame):
    data = data.copy(deep=True)
    data.loc[:, 'i'] += -9
    data.loc[:, 'j'] += -5
    idx = (data.i < rows) & (data.i >= 0) & (data.j >= 0) & (data.j < cols)
    return data.loc[idx]


def plot_ibound():
    m = get_full_scott_model()
    smt_scott.plot.plt_matrix(convert_scott_array_to_reg_grid(m.bas6.ibound.array[0]), base_map=True)
    smt_scott.plot.show()


def plot_hk():
    m = get_full_scott_model()
    smt_scott.plot.plt_matrix(convert_scott_array_to_reg_grid(m.upw.hk.array[0]), base_map=True,
                              title='hk')
    smt_scott.plot.plt_matrix(np.log10(convert_scott_array_to_reg_grid(m.upw.hk.array[0])), base_map=True,
                              title='log hk')


def plot_riv_conductances():
    m = get_full_scott_model()
    riv_data = smt_scott.io.df_to_array(covert_scott_df_to_reg(pd.DataFrame(m.riv.stress_period_data[0])), 'cond')
    smt_scott.plot.plt_matrix(riv_data, base_map=True, title='river conductance')
    smt_scott.plot.plt_matrix(np.log10(riv_data), base_map=True, title='log river conductance')
    print(np.unique(riv_data))


if __name__ == '__main__':
    smt_scott.get_no_flow(recalc=True)
    plot_hk()
    plot_riv_conductances()
    smt_scott.plot.show()
