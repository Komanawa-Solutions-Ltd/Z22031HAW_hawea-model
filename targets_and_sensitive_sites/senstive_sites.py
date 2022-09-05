"""
created matt_dumont 
on: 1/09/22
"""
import numpy as np

from project_base import processed_target_dir, base_target_dir
from model_build.project_model_tools import smt
import geopandas as gpd


# todo wetland and water supply bores, anything else?

def get_wetlands(recalc=False):
    wetland_path = base_target_dir.joinpath('Hawea_Updated_RSWetlands.shp')
    processed_path = processed_target_dir.joinpath('wetlands.txt')
    all_keys = [1, 2]

    shp_data = {18: 'Butterfield Wetland', 20: 'Campbells Reserve Pond Margins'}
    key = {1: 'Butterfield_Wetland', 2: 'Campbells_Reserve_Pond_Margins'}
    shp_key = {1: 18, 2: 20}

    if processed_path.exists() and not recalc:
        temp = np.loadtxt(processed_path).astype(int)
        out = {}
        for i in all_keys:
            out[i] = temp == i
        return out

    temp = smt.io.shape_file_to_model_array(wetland_path, 'ID', alltouched=True)
    out = {}
    save_out = smt.get_model_zeros()
    for k in all_keys:
        out[k] = t = np.isclose(temp, shp_key[k])
        save_out[t] = k
    np.savetxt(processed_path, save_out, fmt='%d')
    return out


if __name__ == '__main__':
    t = get_wetlands(recalc=True)
    for k, v in t.items():
        smt.plot.plt_matrix(v, title=k, base_map=True)
    smt.plot.show()
