"""
created matt_dumont 
on: 7/09/22
"""
import numpy as np

from project_base import processed_model_build_data_dir, base_model_build_data_dir
from model_build.project_model_tools import smt, get_lake_array


def get_param_zones(recalc=False):
    """
    zone 1 = Sandy point, zone 2 = mangawera valley,  rest of the model = -1
    :param recalc:
    :return:
    """
    data_path = base_model_build_data_dir.joinpath('special_zones.shp')
    processed_path = processed_model_build_data_dir.joinpath('param_zones.txt')

    if processed_path.exists() and not recalc:
        data = np.loadtxt(processed_path).astype(int)
        return data

    data = smt.io.shape_file_to_model_array(data_path, 'id', alltouched=True)
    data[np.isnan(data)] = -1
    data = data.astype(int)
    ibound = smt.get_no_flow(0)
    data[ibound < 1] = -1
    np.savetxt(processed_path, data, fmt='%d')
    return data


zone_keys = {'terrace': 'terrace.shp',
             'flat': 'flat.shp',
             'east': 'east.shp',
             'near_river': 'near_river.shp',
             'hawea_flat': 'hawea_flat.shp',
             'hawea_town': 'hawea_town.shp',
             'main': 'None',  # made from ibound or other zones
             'active': 'None',  # made from ibound or other zones
             }


def _get_other_zones(name, recalc=False):
    if name not in zone_keys:
        raise NotImplementedError(f'{name} not in created expected one of: {zone_keys.keys()}')
    base_path = base_model_build_data_dir.joinpath('zones', zone_keys[name])
    processed_path = processed_model_build_data_dir.joinpath(f'zone_{name}.txt')
    if processed_path.exists() and not recalc:
        out = np.loadtxt(processed_path) == 1
        return out
    if name == 'main':
        pzones = get_param_zones()
        ibound = smt.get_no_flow(0)
        out = (pzones < 0) & (ibound > 0)
    elif name == 'active':
        out = smt.get_no_flow(0) > 0
    else:
        out = np.isfinite(smt.io.shape_file_to_model_array(base_path, 'id', True))
        ibound = smt.get_no_flow(0)
        out[ibound < 1] = False
        pzones = get_param_zones()
        out[pzones > 0] = False
        lake = get_lake_array()
        out[np.isfinite(lake)] = False
    np.savetxt(processed_path, out.astype(int), fmt='%d')
    return out


def get_model_zones(recalc=False):
    out = {}
    param_zones = get_param_zones(recalc=recalc)
    out['mangawera'] = param_zones == 2
    out['sandypoint'] = param_zones == 1
    out['lake'] = np.isfinite(get_lake_array(recalc=recalc))
    for k in zone_keys.keys():
        out[k] = _get_other_zones(k, recalc=recalc)
    return out


if __name__ == '__main__':
    t = get_model_zones()
    for k,v in t.items():
        smt.plot.plt_matrix(v, title=k, base_map=True, no_flow_layer=0)
    smt.plot.show()
    smt.plot.plt_matrix(get_param_zones(True), base_map=True, no_flow_layer=0)
    for k in zone_keys:
        smt.plot.plt_matrix(_get_other_zones(k, recalc=True), no_flow_layer=0, title=k, base_map=True)
    smt.plot.show()
