"""
created matt_dumont 
on: 7/09/22
"""
import numpy as np

from project_base import processed_model_build_data_dir, base_model_build_data_dir
from model_build.project_model_tools import smt


def get_param_zones(recalc=False):
    """
    zone 1 = Sandy point, zone 2 = mangawera valley
    rest of the model = -1
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
    np.savetxt(processed_path, data, fmt='%d')
    return data


if __name__ == '__main__':
    smt.plot.plt_matrix(get_param_zones(True), base_map=True, no_flow_layer=0)
    smt.plot.show()