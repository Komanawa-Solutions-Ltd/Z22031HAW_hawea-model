"""
created matt_dumont 
on: 15/03/23
"""
import numpy as np
from pathlib import Path
import tempfile

from komanawa.hawea.Scenarios.wetland_setback_butterfield.project_model_tools import smt
from komanawa.hawea.hawea_base import butterfield_dir, base_model_build_data_dir
from komanawa.hawea.model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from komanawa.hawea.model_parameterisation.pilot_points import interpolate_kh_pilot_points, interpolate_sy_pilot_points


def get_terrace_zone(recalc=False):
    shp_path = base_model_build_data_dir.joinpath('zones/terrace.shp')
    save_path = butterfield_dir.joinpath('processed_input_data/terrace_zone.npy')

    if not recalc and save_path.exists():
        return np.load(save_path)
    out = smt.io.shape_file_to_model_array(shp_path, 'id', alltouched=True)
    out = np.isfinite(out)
    np.save(save_path, out)
    return out


def get_hk(terrace_hk, flat_hk, recalc=False):
    save_path = butterfield_dir.joinpath('processed_input_data/hd_data.npy')
    if not recalc and save_path.exists():
        hk_base = np.load(save_path)
    else:
        kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
        hk = interpolate_kh_pilot_points(kh_param)[0]
        from komanawa.hawea.model_build.project_model_tools import smt as hawea_smt
        with tempfile.TemporaryDirectory() as tdir:
            tdir = Path(tdir)
            hawea_smt.io.array_to_raster(tdir.joinpath('temp.tif'), hk)
            hk_base = smt.io.raster_to_array(tdir.joinpath('temp.tif'), 'mean')
        np.save(save_path, hk_base)

    hk_base[get_terrace_zone()] *= terrace_hk
    hk_base[~get_terrace_zone()] *= flat_hk

    return hk_base[np.newaxis]


def get_sy(terrace_sy, flat_sy, recalc=False):
    save_path = butterfield_dir.joinpath('processed_input_data/sy_data.npy')
    if not recalc and save_path.exists():
        sy_base = np.load(save_path)
    else:
        kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
        sy = interpolate_sy_pilot_points(sy_param)[0]
        from komanawa.hawea.model_build.project_model_tools import smt as hawea_smt
        with tempfile.TemporaryDirectory() as tdir:
            tdir = Path(tdir)
            hawea_smt.io.array_to_raster(tdir.joinpath('temp.tif'), sy)
            sy_base = smt.io.raster_to_array(tdir.joinpath('temp.tif'), 'mean')
        np.save(save_path, sy_base)

    sy_base[get_terrace_zone()] *= terrace_sy
    sy_base[~get_terrace_zone()] *= flat_sy
    return sy_base[np.newaxis]

if __name__ == '__main__':
    sy = get_sy(1, 1, True)
    hk = get_hk(1,1, True)

    smt.plot.plt_matrix(sy[0], base_map=True, no_flow_layer=0, title='sy')
    smt.plot.plt_matrix(hk[0], base_map=True, no_flow_layer=0, title='hk')
    smt.plot.show()