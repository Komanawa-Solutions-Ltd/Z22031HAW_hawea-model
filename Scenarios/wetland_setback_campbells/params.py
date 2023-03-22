"""
created matt_dumont 
on: 15/03/23
"""
import numpy as np
from pathlib import Path
import tempfile

from Scenarios.wetland_setback_campbells.project_model_tools import smt
from project_base import campbells_dir, base_model_build_data_dir
from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from model_parameterisation.pilot_points import interpolate_kh_pilot_points, interpolate_sy_pilot_points


def get_hk(hk_modifer, recalc=False):
    save_path = campbells_dir.joinpath('processed_input_data/hd_data.npy')
    if not recalc and save_path.exists():
        hk_base = np.load(save_path)
    else:
        kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
        hk = interpolate_kh_pilot_points(kh_param)[0]
        from model_build.project_model_tools import smt as hawea_smt
        with tempfile.TemporaryDirectory() as tdir:
            tdir = Path(tdir)
            hawea_smt.io.array_to_raster(tdir.joinpath('temp.tif'), hk)
            hk_base = smt.io.raster_to_array(tdir.joinpath('temp.tif'), 'mean')
        np.save(save_path, hk_base)

    hk_base *= hk_modifer

    return hk_base[np.newaxis]


def get_sy(sy_modifer, recalc=False):
    save_path = campbells_dir.joinpath('processed_input_data/sy_data.npy')
    if not recalc and save_path.exists():
        sy_base = np.load(save_path)
    else:
        kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
        sy = interpolate_sy_pilot_points(sy_param)[0]
        from model_build.project_model_tools import smt as hawea_smt
        with tempfile.TemporaryDirectory() as tdir:
            tdir = Path(tdir)
            hawea_smt.io.array_to_raster(tdir.joinpath('temp.tif'), sy)
            sy_base = smt.io.raster_to_array(tdir.joinpath('temp.tif'), 'mean')
        np.save(save_path, sy_base)

    sy_base *= sy_modifer
    return sy_base[np.newaxis]


if __name__ == '__main__':
    sy = get_sy(1, True)
    hk = get_hk(1, True)

    smt.plot.plt_matrix(sy[0], base_map=True, no_flow_layer=0, title='sy')
    smt.plot.plt_matrix(hk[0], base_map=True, no_flow_layer=0, title='hk')
    smt.plot.show()
