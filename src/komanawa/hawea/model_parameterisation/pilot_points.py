"""
created matt_dumont 
on: 2/09/22
"""
import numpy as np
import pandas as pd
from scipy.interpolate import RBFInterpolator
from komanawa.hawea.hawea_base import base_param_dir, processed_param_dir
from komanawa.hawea.model_build.zones import get_model_zones
from komanawa.hawea.model_build.project_model_tools import smt, get_lake_array, get_low_cond_array, get_2d_moraine
from komanawa.hawea.model_build.supporting_data_analysis import get_irrigation_code
try:
    from komanawa.modeltools import TimeDis
except ModuleNotFoundError:
    from komanawa.hawea.dummy_packages import TimeDis
from komanawa.hawea.model_parameterisation.static_params import lake_sy
import geopandas as gpd


# keynote use zones for mangawera and sandy point aquifer systems, but use pilot points for main portion of the model

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
    else:
        data = gpd.read_file(data_path)
        x, y = data.geometry.x, data.geometry.y

        data.loc[:, 'group'] = data.loc[:, 'group'].replace({
            'rivergroup': 'riv_g',
            'terrace': 'ter',
            'haweaflat': 'h_flat',
            'sandyhill': 'sandy',
            'mangawera': 'mang',
            'hillside': 'hill',
        })

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
    # keynote remove some v12 parameterisation
    outdata = outdata.drop(['h_flat40', 'h_flat41', 'h_flat42', 'h_flat43', 'h_flat44'])

    return outdata


def interpolate_kh_pilot_points(kh_data, method='rbf', return_df=False, kernal='multiquadric'):
    """

    :param kh_data: real values, it will be logged then unlogged
    :param method:
    :param return_df:
    :param kernal:
    :return:
    """
    kh = smt.get_model_zeros() * np.nan

    # set pilot point values

    pilot_locs = get_pilot_point_locations()
    pilot_locs.loc[:, 'value'] = [kh_data.get(n) for n in pilot_locs.index]
    assert pilot_locs.loc[:, 'value'].notnull().all()
    # keynote interpolate on log values!
    pilot_locs.loc[:, 'value'] = np.log10(pilot_locs.loc[:, 'value'])
    # interpolate kh
    ibound = smt.get_no_flow(layer=0)
    i, j = smt.get_model_index_grid()
    idx = ibound == 1

    if method == 'rbf':
        # Radial basis function techniques, which kernal
        # thinplate spline has too much possibility for radically creating extremes,
        # both multiquadric and linear do not provide too much contorition and extreme values.
        # my preference is mutiquadric as it has more curvature about the point
        terrace_points = pilot_locs.loc[pilot_locs.group == 'ter']
        other_points = pilot_locs.loc[~(pilot_locs.group == 'ter')]
        rbf_other = RBFInterpolator(other_points.loc[:, ['i', 'j']].values, other_points['value'].values, kernel=kernal,
                                    epsilon=1)
        kh[idx] = rbf_other(np.concatenate((i[idx][:, np.newaxis], j[idx][:, np.newaxis]), axis=1))

        rbf_ter = RBFInterpolator(terrace_points.loc[:, ['i', 'j']].values, terrace_points['value'].values,
                                  kernel=kernal, epsilon=1)
        idx = idx & get_model_zones()['terrace']
        kh[idx] = rbf_ter(np.concatenate((i[idx][:, np.newaxis], j[idx][:, np.newaxis]), axis=1))

    else:
        # other options include:
        # https://docs.scipy.org/doc/scipy/tutorial/interpolate.html, look at gridded data options.
        # IDW
        # linear
        # krigging???
        # can always look into PLPROC (though I would prefer not to.)
        # I chose to simply use RBF methods
        raise ValueError(f'unexpected method: {method}')

    # undo the log
    kh = 10 ** kh
    pilot_locs.loc[:, 'value'] = 10 ** (pilot_locs.loc[:, 'value'])

    kh[~(ibound == 1)] = 0
    assert np.isfinite(kh).all()
    # set lake values
    lake_array = get_lake_array()

    kh[np.isfinite(lake_array)] = kh_data['lake']
    kh = np.repeat(kh[np.newaxis], smt.layers, axis=0)

    kh[get_low_cond_array()] = kh_data['mor_l1']
    kh[0, get_2d_moraine()] = kh_data['mor_l0']

    if return_df:
        return kh, pilot_locs
    return kh


def interpolate_sy_pilot_points(sy_data, method='rbf', return_df=False,
                                kernal='multiquadric'):
    # keynote interpolate on log values
    sy = smt.get_model_zeros() * np.nan

    # set pilot point values

    pilot_locs = get_pilot_point_locations()
    pilot_locs.loc[:, 'value'] = [sy_data.get(n) for n in pilot_locs.index]
    assert pilot_locs.loc[:, 'value'].notnull().all()

    # interpolate sy
    ibound = smt.get_no_flow(layer=0)
    i, j = smt.get_model_index_grid()
    idx = ibound == 1
    pilot_locs.loc[:, 'value'] = np.log10(pilot_locs.loc[:, 'value'])

    if method == 'rbf':
        # Radial basis function techniques, which kernal
        # thinplate spline has too much possibility for radically creating extremes,
        # both multiquadric and linear do not provide too much contorition and extreme values.
        # my preference is mutiquadric as it has more curvature about the point
        terrace_points = pilot_locs.loc[pilot_locs.group == 'ter']
        other_points = pilot_locs.loc[~(pilot_locs.group == 'ter')]
        rbf_other = RBFInterpolator(other_points.loc[:, ['i', 'j']].values, other_points['value'].values, kernel=kernal,
                                    epsilon=1)
        sy[idx] = rbf_other(np.concatenate((i[idx][:, np.newaxis], j[idx][:, np.newaxis]), axis=1))

        rbf_ter = RBFInterpolator(terrace_points.loc[:, ['i', 'j']].values, terrace_points['value'].values,
                                  kernel=kernal, epsilon=1)
        idx = idx & get_model_zones()['terrace']
        sy[idx] = rbf_ter(np.concatenate((i[idx][:, np.newaxis], j[idx][:, np.newaxis]), axis=1))


    else:
        # other options include:
        # https://docs.scipy.org/doc/scipy/tutorial/interpolate.html, look at gridded data options.
        # IDW
        # linear
        # krigging???
        # can always look into PLPROC (though I would prefer not to.)
        # I chose to simply use RBF methods
        raise ValueError(f'unexpected method: {method}')

    # undo the log
    sy = 10 ** sy
    pilot_locs.loc[:, 'value'] = 10 ** (pilot_locs.loc[:, 'value'])

    # set lake values
    lake_array = get_lake_array()
    sy[np.isfinite(lake_array)] = lake_sy

    sy[~(ibound == 1)] = 0
    assert np.isfinite(sy).all()
    min_v = min(sy_data.values())
    sy[sy < min_v] = min_v
    sy[~(ibound == 1)] = 0
    sy = np.repeat(sy[np.newaxis], smt.layers, axis=0)

    sy[get_low_cond_array()] = sy_data['sy_mor_l1']
    sy[0, get_2d_moraine()] = sy_data['sy_mor_l0']

    if return_df:
        return sy, pilot_locs
    return sy


def set_ss_terms(sy_data):
    """
    make the array for the ss data, ss parameters are being added to the sy_data for easy handling
    :param sy_data:
    :return:
    """
    ss = smt.get_model_zeros(True) + sy_data['ss_rest']
    ss[0, get_2d_moraine()] = sy_data['ss_mor_l0']
    ss[get_low_cond_array()] = sy_data['ss_mor_l1']

    return ss


def exampine_kh_interpolation():
    import matplotlib.pyplot as plt
    pps = get_pilot_point_locations()
    options = np.linspace(0.5, 3.5, 10)
    kh_data = {
        'sandy': np.random.choice(options),
        'mang': np.random.choice(options),
        'lake': 1
    }

    ncols = 3
    interpolation_techniques = ['thin_plate_spline', 'multiquadric', 'linear']
    fig1, axs1 = plt.subplots(ncols=ncols, figsize=(16, 9))
    fig2, axs2 = plt.subplots(ncols=ncols, figsize=(16, 9))
    fig3, axs3 = plt.subplots(ncols=ncols, figsize=(16, 9))
    randoms = np.random.choice(options, len(pps))
    for i, r in zip(pps.index, randoms):
        kh_data[i] = r

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


def examine_sy_interpolation(log_before=False):
    import matplotlib.pyplot as plt
    choices = [0.02, 0.05, 0.1, 0.2, 0.3]
    pps = get_pilot_point_locations()
    sy_data = {
        'sandy': np.random.choice(choices),
        'mang': np.random.choice(choices),
    }

    ncols = 1
    interpolation_techniques = ['multiquadric']
    fig1, axs1 = plt.subplots(ncols=ncols, figsize=(16, 9))
    fig3, axs3 = plt.subplots(ncols=ncols, figsize=(16, 9))
    randoms = np.random.choice(choices, len(pps))
    for i, r in zip(pps.index, randoms):
        sy_data[i] = r

    if log_before:
        for k, v in sy_data.items():
            sy_data[k] = np.log10(v)

    for i, kernal in enumerate(interpolation_techniques):
        sy, df = interpolate_kh_pilot_points(sy_data, return_df=True, kernal=kernal)
        if log_before:
            smt.plot.plt_matrix(10 ** sy[0], base_map=True, no_flow_layer=0, title=f'real {kernal}', ax=axs1, )
            smt.plot.plt_matrix(10 ** sy[0], base_map=True, no_flow_layer=0, title=f'real {kernal}', ax=axs3,
                                vmin=max(choices))
            fig2, axs2 = plt.subplots(ncols=ncols, figsize=(16, 9))
            smt.plot.plt_matrix(sy[0], base_map=True, no_flow_layer=0, title=f'log10 {kernal}', ax=axs2)

        else:
            smt.plot.plt_matrix(sy[0], base_map=True, no_flow_layer=0, title=f'real {kernal}', ax=axs1, )
            smt.plot.plt_matrix(sy[0], base_map=True, no_flow_layer=0, title=f'real {kernal}', ax=axs3,
                                vmin=max(choices))

    fig, ax = smt.plot.plt_matrix(sy[0] * np.nan, base_map=True, no_flow_layer=0, title='data', )
    ax.scatter(df.x, df.y)
    for x, y, s in df.loc[:, ['x', 'y', 'value']].itertuples(False, None):
        ax.text(x, y, str(round(s, 2)))
    fig1.tight_layout()
    if log_before:
        fig2.tight_layout()
    fig3.tight_layout()
    smt.plot.show()


def get_spatial_temporal_rch_mult(rch_data, tdis, recalc=False):
    assert isinstance(tdis, TimeDis)
    assert isinstance(rch_data, dict)
    save_path = processed_param_dir.joinpath(f'irrigated_area_{tdis.name}.npz') # transformed to npz 2026
    if save_path.exists() and not recalc:
        out = np.load(save_path)['data'].astype(bool)
    else:
        out = np.concatenate(
            [get_irrigation_code(y)[np.newaxis] >= 0 for y in pd.to_datetime(tdis.per_middle_dates).year], axis=0)
        np.savez_compressed(save_path, data=out)
    rch_mult = np.full(out.shape, rch_data['all'])

    return rch_mult


def check_kh_sy_ss():
    from komanawa.hawea.model_parameterisation.inital_parametersiation import get_inital_sy, get_inital_kh
    vas = get_inital_kh(True)
    vas['lake'] = 20
    vas['mor_l0'] = 7
    vas['mor_l1'] = 5
    kh = interpolate_kh_pilot_points(vas)
    ss_sy = get_inital_sy(True)
    ss_sy['sy_mor_l0'] = 0.02
    ss_sy['sy_mor_l1'] = 0.03
    ss_sy['ss_rest'] = 0.1
    ss_sy['ss_mor_l0'] = 0.2
    ss_sy['ss_mor_l1'] = 0.3

    sy = interpolate_sy_pilot_points(ss_sy)

    ss = set_ss_terms(ss_sy)

    for k in ['kh', 'sy', 'ss']:
        smt.plot.plt_layer_slices(eval(k), base_map=True, no_flow_layer=0, title=k)
    smt.plot.show()


if __name__ == '__main__':
    check_kh_sy_ss()

    t = get_pilot_point_locations(recalc=True)
    exampine_kh_interpolation()
    pass
