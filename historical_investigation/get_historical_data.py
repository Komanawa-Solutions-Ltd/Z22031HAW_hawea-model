"""
created matt_dumont 
on: 2/11/23
"""
import tempfile

import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from scipy.interpolate import interp1d
import numpy as np
import geopandas as gpd
from model_build.supporting_data_analysis import get_lake_heads
from project_base import historical_data_dir, processed_historical_data_dir, proj_root
from optimisation.final_opt_models.compress_uncompress_model import uncompress_model
from model_build.utils import select_resample

historical_well_names = (
    'bore_13',
    'bore_315',
    'bore_513',
    'bore_515',
    'bore_butterfields',
)

historical_well_colors = {
    'bore_13':'purple',
    'bore_315':'navy',
    'bore_513':'darkred',
    'bore_515':'darkgreen',
    'bore_butterfields': 'goldenrod',
}

_historical_data_paths = {
    'bore_13': historical_data_dir.joinpath('Bore 13/Bore_13_graph.csv'),
    'bore_315': historical_data_dir.joinpath('Bore 315/Bore_315.csv'),
    'bore_513': historical_data_dir.joinpath('Bore 513/Bore_513.csv'),
    'bore_515': historical_data_dir.joinpath('Bore 515/Bore_515.csv'),
    'bore_butterfields': historical_data_dir.joinpath('Butterfield bore/Butterfield_bore.csv'),
    'lake': historical_data_dir.joinpath('lake_plot.csv'),
}

historical_time_start = pd.to_datetime('1976-01-01')
historical_time_end = pd.to_datetime('1983-01-01')

historical_data_savepath = processed_historical_data_dir.joinpath('historical_data.hdf')


def get_historical_lake_heads():
    """
    get the lake heads for the historical period
    :return:
    """
    lake_hds = get_lake_heads(historical_time_start, historical_time_end)
    return lake_hds


def get_historical_well_heads(site, freq='D', recalc=False):
    """
    get the well heads for the historical period as read from the pdf
    :param site:
    :return:
    """
    t = None
    assert site in historical_well_names
    if not recalc and historical_data_savepath.exists():
        try:
            t = pd.read_hdf(historical_data_savepath, key=site)
            assert isinstance(t, pd.Series)
        except KeyError:
            pass
    if t is None:
        well_hds = _read_sampled_data(_historical_data_paths[site])

        well_hds.to_hdf(historical_data_savepath, key=site, complib='zlib', complevel=9)
        t = well_hds
    t = select_resample(t, t.index.min(), t.index.max(), frequency=freq, interpolate=True)
    return t


def _get_lake_hds_from_hist_document(recalc=False):
    """
    get the lake heads from the historical document used to confirm reading method
    :return:
    """
    if not recalc and historical_data_savepath.exists():
        try:
            t = pd.read_hdf(historical_data_savepath, key='lake')
            assert isinstance(t, pd.Series)
            return t
        except KeyError:
            pass
    lake_hds = _read_sampled_data(_historical_data_paths['lake'])
    lake_hds.to_hdf(historical_data_savepath, key='lake', complib='zlib', complevel=9)
    return lake_hds


def check_historic_document_lake_heads():
    hist = _get_lake_hds_from_hist_document()
    true = get_historical_lake_heads()
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.plot(hist.index, hist.values, label='hist', marker='o', alpha=0.5)
    ax.plot(true.index, true.values, label='true', marker='o', alpha=0.5)
    ax.legend()
    ax.set_title('lake heads from historical document vs true')
    ax.set_ylabel('head (m)')
    ax.set_xlabel('time')
    plt.show()


def _read_sampled_data(path):
    path = Path(path)
    series_start = 0
    x_start = 0
    y_start = 0
    with path.open('r') as f:
        for i, l in enumerate(f.readlines()):
            if 'Series' in l:
                series_start = i
            elif 'X' in l and 'axis' in l:
                x_start = i
            elif 'Y' in l and 'axis' in l:
                y_start = i
    series = pd.read_csv(path, skiprows=series_start + 1, nrows=x_start - series_start - 2).dropna(how='all')
    x_axis = pd.read_csv(path, skiprows=x_start + 1, nrows=y_start - x_start - 2).dropna()
    y_axis = pd.read_csv(path, skiprows=y_start + 1).dropna()

    x_axis['actual'] = x_axis['Actual (yy/mm)'].astype(int).astype(str)
    x_axis['datetime'] = pd.to_datetime([f'19{e[:2]}-{e[2:]}-01' for e in x_axis['actual']])
    base_time = pd.to_datetime('1970-01-01')
    x_axis['days'] = (x_axis['datetime'] - base_time).dt.days
    hist_time_int = interp1d(x_axis['X'], x_axis['days'], fill_value='extrapolate')
    series['days'] = hist_time_int(series['X'])
    series['datetime'] = pd.to_datetime(series['days'], unit='D', origin='1970-01-01')
    series.set_index('datetime', inplace=True)

    # interpolate y axis
    y_axis['actual'] = y_axis['Actual (cm)'].astype(float) / 100  # convert to m
    y_interp = interp1d(y_axis['Y'], y_axis['actual'], fill_value='extrapolate')
    # keynote convert lake levels from  Dunedin 1958 (from NZVD2016) to New Zealand Vertical Datum 2016
    #  conversion by https://www.geodesy.linz.govt.nz/concord/
    series['head'] = y_interp(series['Y']) - 1 / 3

    return series['head']


def get_model_period_hds(site, freq='D', recalc=False):
    """
    get the model period heads for the given site
    :param site:
    :return:
    """
    t = None
    assert site in historical_well_names
    key = f'all_modelled_period_hds'
    if not recalc and historical_data_savepath.exists():
        try:
            t = pd.read_hdf(historical_data_savepath, key=key)[site]
            assert isinstance(t, pd.Series)
        except KeyError:
            pass
    if t is None:
        with tempfile.TemporaryDirectory() as tdir:
            tdir = Path(tdir)
            compressed_path = proj_root.joinpath('optimisation/final_opt_models/3d_v1d')  # path to the model in the repo
            uncompress_model(compressed_path, tdir)
            import flopy
            from model_build.project_model_tools import smt
            from optimisation.optimisation_period import tdis as opt_tdis
            hds_path = tdir.joinpath('final_opt_model.hds')
            all_hds = flopy.utils.HeadFile(hds_path).get_alldata()
            all_hds[all_hds > 1e20] = np.nan
            assert all_hds.shape[0] == opt_tdis.nper
            head_locs = get_historical_data_locs()

            out_hds = pd.DataFrame(index=opt_tdis.per_middle_dates, columns=historical_well_names)
            for site in historical_well_names:
                k = head_locs.loc[site, 'k']
                i = head_locs.loc[site, 'i']
                j = head_locs.loc[site, 'j']
                out_hds.loc[:, site] = all_hds[:, k, i, j]

        out_hds.to_hdf(historical_data_savepath, key=key, complib='zlib', complevel=9)
        t = out_hds[site]
    t = select_resample(t, t.index.min(), t.index.max(), frequency=freq, interpolate=True)
    return t


def get_historical_data_locs(recalc=False):
    """
    get the locations of the historical data
    :return:
    """
    if not recalc and historical_data_savepath.exists():
        try:
            t = pd.read_hdf(historical_data_savepath, key='locs')
            assert isinstance(t, pd.DataFrame)
            return t
        except KeyError:
            pass

    raw_data = gpd.read_file(historical_data_dir.joinpath('georeferenced/boreholes_georef.shp'))
    raw_data['x'] = raw_data.geometry.x
    raw_data['y'] = raw_data.geometry.y
    name_mapper = {
        'Bore 13': 'bore_13',
        'Bore 315': 'bore_315',
        'Bore 513': 'bore_513',
        'Bore 515': 'bore_515',
        'Butterfields Bore': 'bore_butterfields',

    }
    raw_data['name'] = raw_data['Name'].replace(name_mapper)
    raw_data.set_index('name', inplace=True)
    raw_data = raw_data.loc[list(historical_well_names)]
    from model_build.project_model_tools import smt
    row, col = smt.convert_coords_to_matix(raw_data['x'], raw_data['y'])
    raw_data['i'] = row
    raw_data['j'] = col
    raw_data['k'] = 2
    raw_data = raw_data.loc[:, ['k', 'i', 'j', 'x', 'y']]
    raw_data.to_hdf(historical_data_savepath, key='locs', complib='zlib', complevel=9)
    return raw_data


if __name__ == '__main__':
    get_historical_data_locs()
    get_model_period_hds(historical_well_names[0])
    for site in historical_well_names:
        get_historical_well_heads(site)
    check_historic_document_lake_heads()
