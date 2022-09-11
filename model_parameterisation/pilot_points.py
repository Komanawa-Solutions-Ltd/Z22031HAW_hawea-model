"""
created matt_dumont 
on: 2/09/22
"""
import numpy as np
import pandas as pd
from scipy.interpolate import RBFInterpolator
from project_base import base_param_dir, processed_param_dir
from model_build.project_model_tools import smt, get_lake_array
from model_parameterisation.inital_parametersiation import lake_sy, lake_kh
from model_build.zones import get_param_zones
import geopandas as gpd


# todo use zones for mangawera and sandy point aquifer systems, but use pilot points for main portion of the model

def get_pilot_point_locations(recalc=False):
    data_path = base_param_dir.joinpath('pilot_points.shp')
    processed_path = processed_param_dir.joinpath('pilot_points.csv')

    if processed_path.exists() and not recalc:
        outdata = pd.read_csv(processed_path, index_col=0)
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
    assert len(outdata.id.unique()) == len(outdata)
    outdata.loc[:, 'x'] = x
    outdata.loc[:, 'y'] = y
    i, j = smt.convert_coords_to_matix(x, y)
    outdata.loc[:, 'i'] = i
    outdata.loc[:, 'j'] = j
    outdata.loc[:, 'name'] = outdata.group.astype(str) + outdata.id.astype(str)
    outdata.set_index('name', inplace=True)
    outdata.to_csv(processed_path)
    return outdata


def interpolate_kh_pilot_points(kh_data, method='rbf', return_df=False, kernal='multiquadric'):
    kh = smt.get_model_zeros() * np.nan

    # set pilot point values
    # todo interpolate on log values!

    pilot_locs = get_pilot_point_locations()
    pilot_locs.loc[:, 'value'] = [kh_data.get(n) for n in pilot_locs.index]
    for k in ['sandyhill', 'mangawera']:
        pilot_locs.loc[pilot_locs.group == k, 'value'] = kh_data[k]
    assert pilot_locs.loc[:, 'value'].notnull().all()

    # interpolate kh
    ibound = smt.get_no_flow(layer=0)
    i, j = smt.get_model_index_grid()
    idx = ibound == 1

    # todo what interpolation technique
    # I'm choosing to avoid kriging as we don't really have the data to support it.

    if method == 'rbf':
        # todo Radial basis function techniques, which kernal???
        # thinplate spline has too much possibility for radically creating extremes,
        # both multiquadric and linear do not provide too much contorition and extreme values.
        # my preference is mutiquadric as it has more curvature about the point

        rbf = RBFInterpolator(pilot_locs.loc[:, ['i', 'j']].values, pilot_locs['value'].values, kernel=kernal,
                              epsilon=1)
        kh[idx] = rbf(np.concatenate((i[idx][:, np.newaxis], j[idx][:, np.newaxis]), axis=1))

    else:
        # other options include:
        # https://docs.scipy.org/doc/scipy/tutorial/interpolate.html, look at gridded data options.
        # IDW
        # linear
        # krigging???
        # can always look into PLPROC (though I would prefer not to.)
        raise ValueError(f'unexpected method: {method}')

    # set lake values
    lake_array = get_lake_array()
    kh[np.isfinite(lake_array)] = lake_kh

    # set sandy point & mangawera zones
    zones = get_param_zones()
    # zone 1 = Sandy point, zone 2 = mangawera valley
    kh[zones == 1] = kh_data['sandyhill']
    kh[zones == 2] = kh_data['mangawera']
    kh[~idx] = 0
    assert np.isfinite(kh).all()
    kh = kh[np.newaxis]
    if return_df:
        return kh, pilot_locs
    return kh


def interpolate_sy_pilot_points():
    raise NotImplementedError


def exampine_interpolation():
    import matplotlib.pyplot as plt
    pps = get_pilot_point_locations()
    kh_data = {
        'sandyhill': np.random.choice([10, 50, 100, 200, 300, 500]),
        'mangawera': np.random.choice([10, 50, 100, 200, 300, 500]),
    }

    ncols = 3
    interpolation_techniques = ['thin_plate_spline', 'multiquadric', 'linear']
    fig1, axs1 = plt.subplots(ncols=ncols, figsize=(16, 9))
    fig2, axs2 = plt.subplots(ncols=ncols, figsize=(16, 9))
    fig3, axs3 = plt.subplots(ncols=ncols, figsize=(16, 9))
    options = [10, 50, 100, 200, 300, 500]
    randoms = np.random.choice(options, len(pps))
    for i, r in zip(pps.index, randoms):
        kh_data[i] = r

    for k, v in kh_data.items():
        kh_data[k] = np.log10(v)

    for i, kernal in enumerate(interpolation_techniques):
        kh, df = interpolate_kh_pilot_points(kh_data, return_df=True, kernal=kernal)
        smt.plot.plt_matrix(10 ** kh[0], base_map=True, no_flow_layer=0, title=f'real {kernal}', ax=axs1[i], vmin=0,
                            )
        smt.plot.plt_matrix(kh[0], base_map=True, no_flow_layer=0, title=f'log10 {kernal}', ax=axs2[i], vmin=0, vmax=3)
        smt.plot.plt_matrix(10 ** kh[0], base_map=True, no_flow_layer=0, title=f'real {kernal}', ax=axs3[i],
                            vmin=max(options))
    fig, ax = smt.plot.plt_matrix(kh[0] * np.nan, base_map=True, no_flow_layer=0, title='data', )
    ax.scatter(df.x, df.y)
    for x, y, s in df.loc[:, ['x', 'y', 'value']].itertuples(False, None):
        ax.text(x, y, str(round(s, 2)))
    fig1.tight_layout()
    fig2.tight_layout()
    fig3.tight_layout()
    smt.plot.show()


if __name__ == '__main__':
    t = get_pilot_point_locations(recalc=True)
    exampine_interpolation()
    pass
