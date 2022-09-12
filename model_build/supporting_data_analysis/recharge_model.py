"""
created matt_dumont 
on: 2/08/22
"""
import warnings
import geopandas as gpd
import numpy as np
import pandas as pd
import netCDF4 as nc
from project_base import base_model_build_data_dir, processed_model_build_data_dir, modelling_dir
from model_build.project_model_tools import smt
from model_build.utils import select_resample

irrigated_area_dir = base_model_build_data_dir.joinpath('irrigated_area')
irrigated_area_dir.mkdir(exist_ok=True)

irrigated_area_codes = {
    0: 'Gun', 1: 'Borderdyke', 2: 'Pivot', 3: 'Solid-set', 4: 'K-line/Long lateral',
    5: 'Unknown', 6: 'Drip/micro', 7: 'Rotorainer', 8: 'Wild flooding', 9: 'Linear boom'}

irrig_max_store = 50  # todo how much storage per area!!!, might be iterative to set, discuss with Jens

irrig_targets = {
    'Borderdyke': 1.,
    'Wild flooding': 1.,  # once every 8 days

    'Rotorainer': 1.,  # once every 3 days
    'K-line/Long lateral': 1.,
    'Gun': 1.,
    'Unknown': 1.,

    'Solid-set': 0.90,
    'Linear boom': 0.90,
    'Pivot': 0.90,
    'Drip/micro': 0.90,

}

irrig_trigs = {
    'Borderdyke': 0.50,
    'Wild flooding': 0.50,

    'Rotorainer': 0.75,
    'Gun': 0.75,
    'Unknown': 0.75,

    'Solid-set': 0.75,
    'K-line/Long lateral': 0.75,
    'Linear boom': 0.75,
    'Pivot': 0.75,

    'Drip/micro': 0.80,

}

irrig_eff = {
    'Borderdyke': 0.50,
    'Wild flooding': 0.50,

    'Rotorainer': 0.75,
    'Gun': 0.75,
    'Unknown': 0.75,

    'Solid-set': 0.85,
    'K-line/Long lateral': 0.85,
    'Linear boom': 0.85,
    'Pivot': 0.85,

    'Drip/micro': 0.90,
}

irrig_max_irrig_apply = {
    'Borderdyke': 80,
    'Wild flooding': 80,

    'Rotorainer': 15,
    'Gun': 15,
    'K-line/Long lateral': 15,
    'Unknown': 15,

    'Solid-set': 8,
    'Linear boom': 8,
    'Pivot': 8,

    'Drip/micro': 5,
}

irrig_min_irrig_return = {
    'Borderdyke': 7,
    'Wild flooding': 7,  # once every 8 days

    'Rotorainer': 2,  # once every 3 days
    'K-line/Long lateral': 2,
    'Gun': 2,
    'Unknown': 2,

    'Solid-set': 0,
    'Linear boom': 0,
    'Pivot': 0,

    'Drip/micro': 0,
}

irrigation_record_dir = processed_model_build_data_dir.joinpath('rch_historical_record')
irrigation_record_dir.mkdir(exist_ok=True)


def get_met_data(start_date, end_date, frequency='D'):  # todo get a longer record either from ORC or ERA5-land
    data = pd.read_csv(base_model_build_data_dir.joinpath('Rainfall_Hawea.csv'))
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
    soil_paw = get_soil_classes(fix_nan=False)
    smt.plot.plt_matrix(soil_paw, title='soil_clases', base_map=True)
    for k in ['scs_curve', 'frac_store', 'paw', 'raw_p', 'soil_retention']:
        smt.plot.plt_matrix(_map_from_soil_class(soil_paw, k), title=k, base_map=True)

    print('number of soil PAWs', len(np.unique(soil_paw)))
    print('soil paws', np.unique(soil_paw))
    ibound = smt.get_no_flow(0)
    print('number of nan soils', np.isnan(soil_paw[ibound >= 1]).sum())
    smt.plot.plt_matrix(np.isnan(soil_paw), title='PAW is nan', base_map=True)

    smt.plot.plt_matrix(soil_paw == 0, title='soil paw 0', base_map=True)

    smt.plot.show()

    # todo look at recharge stats.....


def get_soil_classes(recalc=False):
    soil_classes_path = processed_model_build_data_dir.joinpath('soil_classes.txt')
    if soil_classes_path.exists() and not recalc:
        return np.loadtxt(soil_classes_path)

    soil_classes = smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('soils_with_paw.shp'),
                                                    'Jens_soil', alltouched=True)

    # todo the soil PAW has null values that are being burned as 0...
    # todo I may need ather soil data...
    raise NotImplementedError
    np.savetxt(soil_classes_path, soil_classes)
    return soil_classes


def _map_from_irrig_code(irrig_codes, key):
    out = np.zeros(irrig_codes.shape) * np.nan
    gen_dicts = {
        'max_irrig_apply': irrig_max_irrig_apply,
        'min_irrig_return': irrig_min_irrig_return,
        'irrig_effic': irrig_eff,
        'irrig_trig': irrig_trigs,
        'irrig_targ': irrig_targets,
    }
    nan_values = {
        'max_irrig_apply': 0.,
        'min_irrig_return': 0,
        'irrig_effic': 0.0,
        'irrig_trig': 0.0,
        'irrig_targ': 1.,
    }
    dict_to_use = gen_dicts[key]

    for v in np.unique(irrig_codes):
        if np.isnan(v):
            continue
        map_value = dict_to_use[irrigated_area_codes[v]]
        out[np.isclose(irrig_codes, v)] = map_value

    out[np.isnan(out)] = nan_values[key]

    if key == 'min_irrig_return':
        out = out.astype(int)

    return out


def _map_from_soil_class(soil_classes: np.ndarray, key: str, type=float):
    # data from Jens Rekker soil classes and his analysis.
    out = np.zeros(soil_classes.shape).astype(type)
    assert np.issubdtype(soil_classes.dtype, np.integer)
    data = {
        'scs_curve': {
            0: 57,
            1: 45,
            2: 49,
            3: 57,
            4: 60,
        },
        'frac_store': {
            0: 0.3,
            1: 0.2,
            2: 0.35,
            3: 0.3,
            4: 0.3,
        },
        'paw': {
            0: 100,  # default set high as this increases holding and reduces recharge
            1: 55.,
            2: 90.,
            3: 120.,
            4: 160.,
        },
        'raw_p': {
            0: 0.58,
            1: 0.87,
            2: 0.56,
            3: 0.58,
            4: 0.6,
        },
        'soil_retention': {
            0: 200,
            1: 310.4,
            2: 264.4,
            3: 195.6,
            4: 169.3,
        },

    }
    use_mapper = data[key]
    for k, v in use_mapper.items():
        if np.isnan(v):
            raise NotImplementedError(f'default value for {k} not set')
        out[soil_classes == k] = v

    return out


def get_irrig_avaliblity(dates):
    # keynote storage is reset each water year
    # todo 3d, pull from pumping and irrigation race data!, pumping by zones?
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

    # make static datasets
    soil_classes = get_soil_classes()
    static_taw = _map_from_soil_class(soil_classes, 'taw')
    fracstore = _map_from_soil_class(soil_classes, 'fracstore')
    raw_p = _map_from_soil_class(soil_classes, 'raw_p')

    # make semi static data, reset after each model run
    init_near_surface_storage = smt.get_model_zeros()
    initial_smd = smt.get_model_zeros()
    irrig_init_store = smt.get_model_zeros()

    for y in water_years:
        temp_data = data.loc[data.water_year == y]

        # get irrigation codes (note the shapefiles are additive/overwrite)
        irrig_codes = smt.get_model_zeros().astype(int) - 1
        if y < 2020:
            irrig_path = base_model_build_data_dir.joinpath('irrigated_area/ia_2015.shp')
            temp = smt.io.shape_file_to_model_array(irrig_path, 'type_code', alltouched=True)
            irrig_codes[np.isfinite(temp)] = temp[np.isfinite(temp)]

        if y == 2020:
            irrig_path = base_model_build_data_dir.joinpath('irrigated_area/ia_2020.shp')
            temp = smt.io.shape_file_to_model_array(irrig_path, 'type_code', alltouched=True)
            irrig_codes[np.isfinite(temp)] = temp[np.isfinite(temp)]

        if y >= 2021:
            irrig_path = base_model_build_data_dir.joinpath('irrigated_area/ia_2021.shp')
            temp = smt.io.shape_file_to_model_array(irrig_path, 'type_code', alltouched=True)
            irrig_codes[np.isfinite(temp)] = temp[np.isfinite(temp)]

        max_irrig_apply = _map_from_irrig_code(irrig_codes, 'max_irrig_apply')
        min_irrig_return = _map_from_irrig_code(irrig_codes, 'min_irrig_return')
        irrig_effic = _map_from_irrig_code(irrig_codes, 'irrig_effic')

        irrig_aval = get_irrig_avaliblity(dates=temp_data.index)

        irrig_trig = np.repeat(_map_from_irrig_code(irrig_codes, 'irrig_trig')[np.newaxis:, ],
                               len(temp_data), axis=0)  # 3d, static
        irrig_targ = np.repeat(_map_from_irrig_code(irrig_codes, 'irrig_targ')[np.newaxis:, ],
                               len(temp_data), axis=0)

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

        # explicitly reset irrigation storage 0 at the water year break.
        irrig_init_store = np.zeros(smt.model_array_shape[1:])

        dates.append(rush.dates)
        data.append(rush.recharge)

    data = np.concatenate(data, axis=0)
    dates = np.concatenate(dates, axis=0)
    return dates, data


def get_rch(start_date, end_date, frequency='D', recalc=False):
    dates, rch = get_historical_rch_model_results(recalc=recalc)

    temp = pd.DataFrame(index=dates,
                        data=rch.reshape(rch.shape[0], np.prod(rch.shape[1:]))
                        )

    temp = select_resample(temp, start_date, end_date, frequency, 'mean')
    out_rch = temp.values.reshape(rch.shape)
    assert np.isclose(out_rch.mean(axis=0), rch.mean(axis=0)).all()
    return dates, out_rch


# todo compare histoical recharge to lysimiter:
#  "G:\Shared drives\YMULT_small_projects\Z22031HAW_hawea-model\Data\Hawea lysimeter data processing - June 2014.xlsx"

if __name__ == '__main__':
    get_historical_rch_model_results()
    data_checks()
