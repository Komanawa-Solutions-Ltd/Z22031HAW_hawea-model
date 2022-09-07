"""
created matt_dumont 
on: 2/09/22
"""
import pandas as pd

from project_base import base_param_dir, processed_param_dir
from model_build.project_model_tools import smt
import geopandas as gpd


# todo use zones for mangawera and sandy point aquifer systems, but use pilot points for main portion of the model

def get_pilot_point_locations(recalc=False):
    data_path = base_param_dir.joinpath('pilot_points.shp')
    processed_path = processed_param_dir.joinpath('pilot_points.csv')

    if processed_path.exists() and not recalc:
        outdata = pd.read_csv(processed_path)
        dtypes = {
            'i': 'int64',
            'j': 'int64',
        }

        for k, v in dtypes.items():
            outdata.loc[:, k] = outdata.loc[:, k].astype(v)
        return outdata

    data = gpd.read_file(data_path)
    x, y = data.geometry.x, data.geometry.y
    outdata = data.loc[:, ['id', 'group']]
    outdata.loc[:, 'x'] = x
    outdata.loc[:, 'y'] = y
    i, j = smt.convert_coords_to_matix(x, y)
    outdata.loc['i'] = i
    outdata.loc['j'] = j

    outdata.to_csv(processed_path)
    return outdata

def interpolate_pilot_points():
    # todo what interpolation technique
    # I'm choosing to avoid kriging as we don't really have the data to support it.
    # todo Radial basis function spline techniques
    # inverse distance weighting ( my preference)
    # todo does IDW beyond boundry
    # interpolation in the log space or not???
    # todo see PLPROC



    raise NotImplementedError


if __name__ == '__main__':
    get_pilot_point_locations()
