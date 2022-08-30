"""
created matt_dumont 
on: 2/08/22
"""
import warnings

import geopandas as gpd
# todo use https://github.com/mullenkamp/lsrm-archive
# todo that LSR model is really set up for Ecan's context..., perhaps program in rushton...
import numpy as np
import pandas as pd
import netCDF4 as nc
from project_base import base_model_data_dir, processed_model_data_dir, modelling_dir
from model_build.project_model_tools import smt

irrigated_area_dir = base_model_data_dir.joinpath('irrigated_area')
irrigated_area_dir.mkdir(exist_ok=True)

irrigated_area_codes = {
    0: 'Gun', 1: 'Borderdyke', 2: 'Pivot', 3: 'Solid-set', 4: 'K-line/Long lateral',
    5: 'Unknown', 6: 'Drip/micro', 7: 'Rotorainer', 8: 'Wild flooding', 9: 'Linear boom'}

irrigation_effciency = {}  # todo!!

irrigation_record_dir = processed_model_data_dir.joinpath('rch_historical_record')
irrigation_record_dir.mkdir(exist_ok=True)


def get_met_data(start_date, end_date, frequency='D'):
    data = pd.read_csv(base_model_data_dir.joinpath('Rainfall_Hawea.csv'))
    data.loc[:, 'datetime'] = dt = pd.to_datetime(data.loc[:, 'Date'], format='%d/%m/%Y')
    data.drop(columns='Date', inplace=True)
    data.set_index('datetime', inplace=True)

    if start_date is None:
        start_date = dt.min()
    if end_date is None:
        end_date = dt.max()

    idx = ((dt >= start_date) & (dt <= end_date)).values
    use_data = data.loc[idx].resample(frequency).sum()
    return use_data


def _process_irrigated_area():
    # Keynote irrigated area is additive (e.g. no/minial overlap)
    data = gpd.read_file(modelling_dir.joinpath('input_data/otago_irrigated_area_26oct2021_model_extent.shp'))
    data.loc[:, 'itype_code'] = data.loc[:, 'type'].replace({v: k for k, v in irrigated_area_codes.items()})
    data.to_file(irrigated_area_dir.joinpath(f'otago_irrigated_area_26oct2021_model_extent.shp'))
    for y in data.loc[:, 'year_irr'].unique():
        temp = data.loc[data.year_irr == y]
        temp.to_file(irrigated_area_dir.joinpath(f'ia_{y}.shp'))


def data_checks():
    import matplotlib.pyplot as plt
    # plot met data
    fig, (ax1, ax2) = plt.subplots(2, sharex=True)
    data = get_met_data(None, None, 'M')
    ax1.plot(data.index, data.Rainfall)
    ax1.set_title('Rainfall')
    ax2.plot(data.index, data.PET)
    ax2.set_title('PET')
    # make annual maps of irrigated area...
    files = list(irrigated_area_dir.glob('*.shp'))
    for f in files:
        temp = smt.io.shape_file_to_model_array(f, 'itype_code', alltouched=True)
        smt.plot.plt_matrix(temp, base_map=True, title=f.name)

    # plot soil paw
    soil_paw = get_soil_paw_taw(fix_nan=False)
    smt.plot.plt_matrix(soil_paw, title='PAW', base_map=True)
    print('number of soil PAWs', len(np.unique(soil_paw)))
    print('soil paws', np.unique(soil_paw))
    ibound = smt.get_no_flow(0)
    print('number of nan soils', np.isnan(soil_paw[ibound >= 1]).sum())
    smt.plot.plt_matrix(np.isnan(soil_paw), title='PAW is nan', base_map=True)

    smt.plot.plt_matrix(soil_paw == 0, title='soil paw 0', base_map=True)

    smt.plot.show()

    # todo more....


def get_soil_paw_taw(fix_nan=True):
    soil_paw = smt.io.shape_file_to_model_array(base_model_data_dir.joinpath('soils_with_paw.shp'),
                                                'PAW', alltouched=True)
    if fix_nan:
        soil_paw[np.isnan(soil_paw)] = np.nanmin(soil_paw)

    # todo the soil PAW has null values that are being burned as 0...
    # todo I may need ather soil data...
    return soil_paw


def _map_from_code(irrig_codes, key):  # todo
    raise NotImplementedError


def get_historical_rch_model_results(recalc=False):
    # get met data
    data = get_met_data('2012-07-01', None)
    data.loc[:, 'water_year'] = (data.index + pd.DateOffset(months=-6)).year
    water_years = data.water_year.unique()

    files = [irrigation_record_dir.joinpath(f'{y}.nc') for y in water_years]

    if all([e.exists() for e in files]) and not recalc:
        data = []
        dates = []
        for f in files:
            # todo add dates!!!
            with nc.Dataset(f, mode='r') as ncd:
                t = nc.num2date(np.array(ncd.variables['time']), ncd.variables['time'].units,
                                only_use_python_datetimes=True, only_use_cftime_datetimes=False)
                dates.append(pd.to_datetime(t).to_pydatetime())
                data.append(np.array(ncd.variables['recharge']))
        data = np.concatenate(data, axis=0)
        dates = np.concatenate(dates, axis=0)

        return dates, data

    from rushton_model.rushton import Rushton
    dates, data = [], []

    # todo make static datasets
    irrig_max_store = 50  # todo how much storage per area!!!, might be iterative to set

    static_taw = get_soil_paw_taw(True)  # todo, not finished
    warnings.warn('TAW is not finished!!!!!!')
    fracstore = None  # todo 2d
    raw_p = None  # todo 2d

    # make semi static data, reset after each model run
    init_near_surface_storage = smt.get_model_zeros()
    initial_smd = smt.get_model_zeros()
    irrig_init_store = smt.get_model_zeros()

    for y in water_years:
        temp_data = data.loc[data.water_year == y]

        # get irrigation codes (note the shapefiles are additive/overwrite)
        irrig_codes = smt.get_model_zeros().astype(int) - 1
        if y < 2020:
            irrig_path = base_model_data_dir.joinpath('irrigated_area/ia_2015.shp')
            temp = smt.io.shape_file_to_model_array(irrig_path, 'type_code', alltouched=True)
            irrig_codes[np.isfinite(temp)] = temp[np.isfinite(temp)]

        if y == 2020:
            irrig_path = base_model_data_dir.joinpath('irrigated_area/ia_2020.shp')
            temp = smt.io.shape_file_to_model_array(irrig_path, 'type_code', alltouched=True)
            irrig_codes[np.isfinite(temp)] = temp[np.isfinite(temp)]

        if y >= 2021:
            irrig_path = base_model_data_dir.joinpath('irrigated_area/ia_2021.shp')
            temp = smt.io.shape_file_to_model_array(irrig_path, 'type_code', alltouched=True)
            irrig_codes[np.isfinite(temp)] = temp[np.isfinite(temp)]

        max_irrig_apply = _map_from_code(irrig_codes, 'max_irrig_apply')  # todo 2d, map from codes!
        min_irrig_return = _map_from_code(irrig_codes, 'min_irrig_return')  # todo 2d
        irrig_effic = _map_from_code(irrig_codes, 'irrig_effic')  # todo 2d

        # todo tricky ones (3d)
        irrig_aval = None  # todo 3d, pull from pumping and irrigation race data!, pumping by zones?
        irrig_trig = None  # todo 3d, static or variable?
        irrig_targ = None  # todo 3d, static or variable?

        rush = Rushton(
            dates=temp_data.index,
            # 3d arrays in
            rainfall=np.repeat(temp_data.Rainfall.values[:, np.newaxis], np.prod(smt.model_array_shape[1:]),
                               axis=1).reshape((len(temp_data), *smt.model_array_shape[1:])),
            pet=np.repeat(temp_data.PET.values[:, np.newaxis], np.prod(smt.model_array_shape[1:]),
                          axis=1).reshape((len(temp_data), *smt.model_array_shape[1:])),
            taw=np.repeat(static_taw[np.newaxis, :, :], len(temp_data), axis=0),

            # 2d arrays in
            init_near_surface_storage=init_near_surface_storage,
            fracstore=fracstore,
            raw_p=raw_p,
            initial_smd=initial_smd,

            # single parameters
            runoff_method=None,
            irrigate=True,
            allow_irrigation_to_runoff=False,
            irrig_start_date='01-sep',
            irrig_stop_date='30-apr',

            # irrigation paramters
            # 3d array or None
            irrig_aval=irrig_aval,
            irrig_trig=irrig_trig,
            irrig_targ=irrig_targ,

            # 2d array or None
            max_irrig_apply=max_irrig_apply,
            min_irrig_return=min_irrig_return,
            irrig_max_store=np.full((len(temp_data), *smt.model_array_shape[1:]), irrig_max_store),
            irrig_init_store=irrig_init_store,
            irrig_effic=irrig_effic
        )

        xs, ys = smt.get_model_x_y(grid=False)
        rush.to_netcdf(irrigation_record_dir.joinpath(f'{y}.nc'),
                       description=f'best estimate recharge for Hawea model made with {__file__}',
                       xs=xs, ys=ys, proj_attrs=rush.get_nztm_nc_coords())
        init_near_surface_storage = rush.near_surface_storage[-1]
        irrig_init_store = rush.irrig_store[-1]

        dates.append(rush.dates)
        data.append(rush.recharge)

    data = np.concatenate(data, axis=0)
    dates = np.concatenate(dates, axis=0)
    return dates, data


def get_rch(start_date, end_date, frequency='D'):
    raise NotImplementedError  # todo from above


if __name__ == '__main__':
    get_historical_rch_model_results()
    data_checks()
