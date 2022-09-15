"""
created matt_dumont 
on: 2/08/22
"""
import warnings
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import netCDF4 as nc
from project_base import base_model_build_data_dir, processed_model_build_data_dir, modelling_dir
from model_build.project_model_tools import smt, grid_space
from model_build.utils import select_resample, get_colors
from model_build.supporting_data_analysis.map_flowmeter_to_wells import get_well_flowmeter_mapper
from model_build.supporting_data_analysis.get_pumping_data import _load_usage_data
from model_build.zones import get_model_zones
from copy import deepcopy
import gc

irrigated_area_dir = base_model_build_data_dir.joinpath('irrigated_area')
irrigated_area_dir.mkdir(exist_ok=True)

irrigated_area_codes = {
    -1: 'no_irrig',
    0: 'Gun', 1: 'Borderdyke', 2: 'Pivot', 3: 'Solid-set', 4: 'K-line/Long lateral',
    5: 'Unknown', 6: 'Drip/micro', 7: 'Rotorainer', 8: 'Wild flooding', 9: 'Linear boom'}

irrig_max_store = 50.  # storage is not really used as I am allowing an infinite avalibility.

irrig_targets = {
    'no_irrig': 1.,
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
    'no_irrig': 1.,
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
    'no_irrig': 1.,
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
    'no_irrig': 0,
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
    'no_irrig': 999999,
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


def get_era5_land():
    file_paths = ['era5_potential_et.nc',
                  'era5_precipitation.nc',
                  'era5_reference_et.nc', ]
    base_dir = base_model_build_data_dir.joinpath('era5_data')
    outdata = {}
    for f in file_paths:
        var = f.replace('era5_', '').replace('.nc', '')
        with nc.Dataset(base_dir.joinpath(f)) as ncd:
            t = np.array(
                nc.num2date(ncd.variables['time'][:], ncd.variables['time'].units, only_use_cftime_datetimes=False,
                            only_use_python_datetimes=True))
            t = pd.to_datetime(t)
            data = np.array(ncd.variables[var]).mean(axis=(1, 2))
            outdata[var] = pd.Series(data=data, index=t)

    outdata = pd.DataFrame(outdata)
    return outdata


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
        return np.loadtxt(soil_classes_path).astype(int)

    soil_classes = smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('soils_with_paw.shp'),
                                                    'Jens_soil', alltouched=True)
    soil_classes[np.isnan(soil_classes)] = 0
    smt.plot.plt_matrix(soil_classes, base_map=True, no_flow_layer=0, cmap='tab10')
    smt.plot.show()
    np.savetxt(soil_classes_path, soil_classes, fmt='%d')
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
        'fracstore': {
            0: 0.3,
            1: 0.2,
            2: 0.35,
            3: 0.3,
            4: 0.3,
        },
        'taw': {
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


def get_irrig_avaliblity(dates, plot=False):
    # todo below keynotes are not correct

    # keynote storage is reset each water year
    # keynote looking at the data we miss many consents, so that's tricky, but we see on average
    #  10 mm a day/m2, which mostly exceeds the water limits and return period limits that are specified for
    #  irrigation systems.  Therefore we will not limit irrigation avaliblity, and instead use an infinite avaliblity.
    locations = get_well_flowmeter_mapper(incl_surface_water=True)

    use_zones = get_model_zones()
    zone_keys = ['main', 'sandypoint', 'mangawera', 'all']
    for k in zone_keys:
        if k == 'all':
            continue
        locations.loc[use_zones[k][locations.i, locations.j], 'zone'] = k
    locations.loc[:, 'uid'] = locations.permit_id + '_' + locations.water_meter_no.astype(str)

    useage_data = _load_usage_data()
    useage_data.loc[:, 'uid'] = useage_data.permit_id + '_' + useage_data.water_meter_no.astype(str)

    irrig_area = {}
    for k in zone_keys:
        if k == 'all':
            use_k = 'active'
        else:
            use_k = k
        irrig_area[k] = {}
        for y in [2015, 2020, 2021]:
            temp = get_irrigation_code(y)
            irrig_area[k][y] = ((temp > 0) & use_zones[use_k]).sum() * grid_space ** 2
    data_1d = {}
    if plot:
        fig, axs = plt.subplots(4, sharex=True)
    colors = get_colors(zone_keys)
    for i, (c, k) in enumerate(zip(colors, zone_keys)):
        if k == 'all':
            temp = useage_data.loc[np.in1d(useage_data.uid, locations.loc[locations.zone.notna(), 'uid'])]
        else:
            temp = useage_data.loc[np.in1d(useage_data.uid, locations.loc[locations.zone == k, 'uid'])]
        total = temp.groupby('date').sum().loc[:, 'total_allo']
        total *= 1000  # convert from m3/day to mm*m2/day
        total.loc[total.index.year < 2020] *= 1 / irrig_area[k][2015]
        total.loc[total.index.year == 2020] *= 1 / irrig_area[k][2020]
        total.loc[total.index.year > 2020] *= 1 / irrig_area[k][2021]
        data_1d[k] = total

        if plot:
            axs[i].plot(total.index, total.values, c=c, label=k)
            axs[i].legend()
        pass

    if plot:
        plt.show()
    raise NotImplementedError


def get_irrigation_code(y, recalc=False):
    if y < 2020:
        processed_path = processed_model_build_data_dir.joinpath('irrig_code_pre_2020.txt')
    elif y == 2020:
        processed_path = processed_model_build_data_dir.joinpath('irrig_code_2020.txt')
    else:
        processed_path = processed_model_build_data_dir.joinpath('irrig_code_2021_on.txt')

    if processed_path.exists() and not recalc:
        out = np.loadtxt(processed_path)
        return out.astype(int)

    irrig_codes = smt.get_model_zeros().astype(int) - 1

    irrig_path = base_model_build_data_dir.joinpath('irrigated_area/ia_2015.shp')
    temp = smt.io.shape_file_to_model_array(irrig_path, 'itype_code', alltouched=True)
    irrig_codes[np.isfinite(temp)] = temp[np.isfinite(temp)]

    if y >= 2020:
        irrig_path = base_model_build_data_dir.joinpath('irrigated_area/ia_2020.shp')
        temp = smt.io.shape_file_to_model_array(irrig_path, 'itype_code', alltouched=True)
        irrig_codes[np.isfinite(temp)] = temp[np.isfinite(temp)]

    if y >= 2021:
        irrig_path = base_model_build_data_dir.joinpath('irrigated_area/ia_2021.shp')
        temp = smt.io.shape_file_to_model_array(irrig_path, 'itype_code', alltouched=True)
        irrig_codes[np.isfinite(temp)] = temp[np.isfinite(temp)]
    np.savetxt(processed_path, irrig_codes, fmt='%d')
    return irrig_codes # todo check I think this is WRONG!!!!!


def get_historical_rch_model_results(limited_irrigation, recalc=False):
    if limited_irrigation:
        irrigation_record_dir = processed_model_build_data_dir.joinpath('rch_historical_record_limited')
    else:
        irrigation_record_dir = processed_model_build_data_dir.joinpath('rch_historical_record_unlimited')
    irrigation_record_dir.mkdir(exist_ok=True)

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
    dates, outdata = [], []

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
        print(f'starting to run year: {y}')
        temp_data = data.loc[data.water_year == y]

        # get irrigation codes (note the shapefiles are additive/overwrite)
        irrig_codes = get_irrigation_code(y)

        max_irrig_apply = _map_from_irrig_code(irrig_codes, 'max_irrig_apply')
        min_irrig_return = _map_from_irrig_code(irrig_codes, 'min_irrig_return')
        irrig_effic = _map_from_irrig_code(irrig_codes, 'irrig_effic')

        if limited_irrigation:
            irrig_aval = get_irrig_avaliblity(dates=temp_data.index)
        else:
            irrig_aval = np.full((len(temp_data), *smt.model_array_shape[1:]), np.inf)

        irrig_trig = np.repeat(_map_from_irrig_code(irrig_codes, 'irrig_trig')[np.newaxis, :],
                               len(temp_data), axis=0)  # 3d, static
        irrig_targ = np.repeat(_map_from_irrig_code(irrig_codes, 'irrig_targ')[np.newaxis, :],
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
            irrig_max_store=np.full(smt.model_array_shape[1:], irrig_max_store),
            irrig_init_store=irrig_init_store,
            irrig_effic=irrig_effic
        )

        xs, ys = smt.get_model_x_y(grid=True)
        print('saving rushton')
        rush.to_netcdf(irrigation_record_dir.joinpath(f'{y}.nc'),
                       description=f'best estimate recharge for Hawea model made with {__file__}',
                       xs=xs, ys=ys, proj_attrs=rush.get_nztm_nc_coords(),
                       keys=['recharge', 'nat_irrigation_demand', 'remain_irrigation_demand', 'irrigation_applied',
                             'irrig_store'],
                       mask=smt.get_no_flow(0) != 1,
                       invert_x_y_order=True,
                       compression='zlib',
                       complevel=4
                       )
        init_near_surface_storage = deepcopy(rush.near_surface_storage[-1])

        # explicitly reset irrigation storage 0 at the water year break.
        irrig_init_store = np.zeros(smt.model_array_shape[1:])

        dates.append(deepcopy(rush.dates))
        outdata.append(deepcopy(rush.recharge))
        rush = None
        gc.collect()

    outdata = np.concatenate(outdata, axis=0)
    dates = np.concatenate(outdata, axis=0)
    return dates, outdata


def get_rch(start_date, end_date, frequency='D', limited_irrigation=True, recalc=False):
    dates, rch = get_historical_rch_model_results(limited_irrigation=limited_irrigation)

    temp = pd.DataFrame(index=dates,
                        data=rch.reshape(rch.shape[0], np.prod(rch.shape[1:]))
                        )

    temp = select_resample(temp, start_date, end_date, frequency, 'mean')
    out_rch = temp.values.reshape(rch.shape)
    assert np.isclose(out_rch.mean(axis=0), rch.mean(axis=0)).all()
    return dates, out_rch


# todo compare histoical recharge to lysimiter and look at the data incl zonally
#  "G:\Shared drives\YMULT_small_projects\Z22031HAW_hawea-model\Data\Hawea lysimeter data processing - June 2014.xlsx"

if __name__ == '__main__':
    # for y in [2015, 2020, 2021]:
    #     t = get_irrigation_code(y, recalc=True)
    #     smt.plot.plt_matrix(t,title=y)
    # smt.plot.show()
    get_irrig_avaliblity(1, plot=True)
    get_historical_rch_model_results(limited_irrigation=False, recalc=False)
    data_checks()
