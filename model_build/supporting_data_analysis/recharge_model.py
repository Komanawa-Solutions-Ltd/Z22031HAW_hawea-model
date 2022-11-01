"""
created matt_dumont 
on: 2/08/22
"""
import datetime
import warnings
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import netCDF4 as nc
from project_base import base_model_build_data_dir, processed_model_build_data_dir, modelling_dir
from model_build.project_model_tools import smt, grid_space
from model_build.utils import select_resample, get_colors, season_mapper, int_season_mapper
from model_build.supporting_data_analysis.map_flowmeter_to_wells import get_well_flowmeter_mapper
from model_build.supporting_data_analysis.get_pumping_data import _load_usage_data
from model_build.zones import get_model_zones
from copy import deepcopy
import gc
from scipy.stats import linregress

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


def get_met_data(start_date, end_date, frequency='D'):
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


def _get_raw_era5_land():
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
            data[data < 0] = 0
            outdata[var] = pd.Series(data=data, index=t)
    outdata = pd.DataFrame(outdata)
    return outdata


def get_era5_land(correct=True, recalc=False, return_figs=False):
    if return_figs:
        assert recalc and correct

    if correct:
        processed_path = processed_model_build_data_dir.joinpath('corrected_era5_data.csv')
        if processed_path.exists() and not recalc:
            data = pd.read_csv(processed_path, index_col=0)
            data.index = pd.to_datetime(data.index)
            return data

        from sklearn.linear_model import LinearRegression
        fig, (rainax, petax) = plt.subplots(2, figsize=(10, 8))
        era5 = _get_raw_era5_land()
        era5.loc[:, 'season'] = [int_season_mapper[m] for m in era5.index.month]
        era5.index = pd.to_datetime(era5.index).date
        met_data = get_met_data(None, None)
        met_data.index = pd.to_datetime(met_data.index).date
        use_dates = sorted(list(set(era5.index).intersection(met_data.index)))
        regr = LinearRegression()
        x = era5.loc[use_dates, ['potential_et', 'season']]
        y = met_data.loc[use_dates, 'PET']
        regr.fit(x, y)
        print('r2 for pet conversion')
        rscore = regr.score(x, y)
        print(regr.score(x, y))
        era5.loc[:, 'uncor_potential_et'] = era5.loc[:, 'potential_et']
        xall = era5.loc[:, ['potential_et', 'season']]
        era5.loc[:, 'potential_et'] = regr.predict(xall)
        y_pred = regr.predict(x)
        era5.loc[era5.potential_et < 0, 'potential_et'] = 0
        petax.scatter(x.values[:, 0], y, color='k', label='Original data')
        petax.scatter(x.values[:, 0], y_pred, color='r', label='Predicted data')
        petax.set_title(f'PET prediction\nFunction of PET and season\nR2:{round(rscore, 2)}')
        petax.set_xlabel('ERA5-Land PET')
        petax.set_ylabel('Measured PET')
        petax.legend()

        # correct rainfall
        met_data.rename(columns={'Rainfall': 'precipitation'}, inplace=True)
        for df in [era5, met_data]:
            df.loc[:, 'month'] = [e.month for e in df.index]
            df.loc[:, 'year'] = [e.year for e in df.index]

        met_data = met_data.loc[use_dates]
        era5_temp = era5.loc[use_dates]
        era5_temp.index = pd.to_datetime(era5_temp.index)
        met_data.index = pd.to_datetime(met_data.index)
        weekly_era = era5_temp.resample('W').mean()
        weekly_met = met_data.resample('W').mean()
        x = weekly_era.loc[:, ['precipitation']]
        y = weekly_met.loc[:, ['precipitation']]
        regr = LinearRegression()
        regr.fit(x, y)
        plot_x = (x.sort_values('precipitation'))
        y_pred = regr.predict(plot_x)
        print('r2 for precip conversion')
        rscore = regr.score(x, y)
        print(rscore)
        era5.loc[:, 'uncor_precipitation'] = xall = era5.loc[:, 'precipitation']
        era5.loc[:, 'precipitation'] = regr.predict(xall.values[:, np.newaxis])
        era5.loc[era5.precipitation < 0, 'precipitation'] = 0

        rainax.scatter(x.values[:, 0], y, color='k', label='Original data')
        rainax.plot(plot_x.values[:, 0], y_pred, color='k', ls=':', label='Predicted data')
        rainax.set_title(f'Rainfall prediction\nfunction of weekly rainfall\nR2:{round(rscore, 2)}')
        rainax.set_xlabel('ERA5-Land weekly rainfall')
        rainax.set_ylabel('Measured weekly rainfall')
        rainax.legend()
        fig.tight_layout()

        era5.to_csv(processed_path)
        era5.index = pd.to_datetime(era5.index)
        if return_figs:
            return era5, fig
        return era5
    else:
        return _get_raw_era5_land()


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

    # plot soil paw
    soil_paw = get_soil_classes()
    smt.plot.plt_matrix(soil_paw, title='soil_clases', base_map=True)
    for k in ['scs_curve', 'fracstore', 'taw', 'raw_p', 'soil_retention']:
        smt.plot.plt_matrix(_map_from_soil_class(soil_paw, k), title=k, base_map=True)

    print('number of soil PAWs', len(np.unique(soil_paw)))
    print('soil paws', np.unique(soil_paw))
    ibound = smt.get_no_flow(0)
    print('number of nan soils', np.isnan(soil_paw[ibound >= 1]).sum())
    smt.plot.plt_matrix(np.isnan(soil_paw), title='PAW is nan', base_map=True)

    smt.plot.plt_matrix(soil_paw == 0, title='soil paw 0', base_map=True)

    zones = get_model_zones()
    for y in [2015, 2020, 2021]:
        t = get_irrigation_code(y, recalc=True)
        zones[f'irrigated_{y}'] = t = t >= 0
        smt.plot.plt_matrix(t, title='irrigated area ' + str(y), base_map=True)
    annual = {}
    for v in True, False:
        if v:
            k = 'limited'
        else:
            k = 'unlimited'
        a_dates, temp = get_rch(None, None, 'Y', limited_irrigation=v, fun='sum')
        annual[k] = temp

    for i, d in enumerate(a_dates):
        d = pd.to_datetime(d)
        fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=smt.default_figsize)

        smt.plot.plt_matrix(annual['limited'][i], no_flow_layer=0, base_map=True, vmin=0, vmax=500,
                            title=str(d.year) + ' limited', ax=ax1)
        smt.plot.plt_matrix(annual['unlimited'][i], no_flow_layer=0, base_map=True, vmin=0, vmax=500,
                            title=str(d.year) + ' unlimited', ax=ax2)
        fig.tight_layout()

    for k, z in zones.items():
        if 'irrigated_2015' not in k:
            continue
        fig, ax = plt.subplots()
        ax.set_title(k)
        ax.plot(a_dates, annual['limited'][:, z].mean(axis=1), c='r', label='limited', alpha=0.5)
        ax.plot(a_dates, annual['unlimited'][:, z].mean(axis=1), c='b', label='unlimited', alpha=0.5)
        ax.legend()
    fig, ax = plt.subplots()
    ax.set_title('full model')
    ax.plot(a_dates, annual['limited'].mean(axis=(1, 2)), c='r', label='limited', alpha=0.5)
    ax.plot(a_dates, annual['unlimited'].mean(axis=(1, 2)), c='b', label='unlimited', alpha=0.5)
    ax.legend()

    w_dates, weekly_unlimit = get_rch(None, None, 'W', limited_irrigation=False, fun='sum')
    w_dates, weekly_limit = get_rch(None, None, 'W', limited_irrigation=True, fun='sum')
    for k, z in zones.items():
        if 'irrigated_2015' not in k:
            continue
        fig, ax = plt.subplots()
        ax.set_title(k)
        ax.plot(w_dates, weekly_limit[:, z].mean(axis=1), c='r', label='limited', alpha=0.5)
        ax.plot(w_dates, weekly_unlimit[:, z].mean(axis=1), c='b', label='unlimited', alpha=0.5)
        ax.legend()
    fig, ax = plt.subplots()
    ax.set_title('full model')
    ax.plot(w_dates, weekly_limit.mean(axis=(1, 2)), c='r', label='limited', alpha=0.5)
    ax.plot(w_dates, weekly_unlimit.mean(axis=(1, 2)), c='b', label='unlimited', alpha=0.5)
    ax.legend()
    smt.plot.show()


def get_soil_classes(recalc=False, show=False):
    soil_classes_path = processed_model_build_data_dir.joinpath('soil_classes.txt')
    if soil_classes_path.exists() and not recalc:
        return np.loadtxt(soil_classes_path).astype(int)

    soil_classes = smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('soils_with_paw.shp'),
                                                    'Jens_soil', alltouched=True)
    soil_classes[np.isnan(soil_classes)] = 0
    smt.plot.plt_matrix(soil_classes, base_map=True, no_flow_layer=0, cmap='tab10')
    if show:
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


def get_irrig_avaliblity(shape, plot=False):
    # keynote set avaliblity to mean of full model domain. not much difference between sets
    # keynote I would suggest using unlimited water as the total recharge is not much different; however local border
    #  dyke and wild flooding tends to be lower due to the even apportionment across all irrigation types.
    #  at the end of the day most of the recharge occurs during the winter and shoulder seasons.
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
            axs[i].axhline(y=total.mean(), c='k', ls=':')
            axs[i].legend()
        pass

    if plot:
        plt.show()
    return np.full(shape, data_1d['all'].mean())


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
    return irrig_codes


def get_historical_rch_model_results(data_source='historical', limited_irrigation=False, recalc=False,
                                     from_year=None, to_year=None):
    """

    :param data_source:
    :param limited_irrigation:
    :param recalc:
    :param from_year:
    :param to_year:
    :return: rch in mm
    """
    assert data_source in ['historical', 'era5']
    if from_year is None:
        assert to_year is None
    else:
        assert to_year is not None

    if limited_irrigation:
        irrigation_record_dir = processed_model_build_data_dir.joinpath(
            f'rch_historical_record_from_{data_source}_limited')
    else:
        irrigation_record_dir = processed_model_build_data_dir.joinpath(
            f'rch_historical_record_from_{data_source}_unlimited')
    irrigation_record_dir.mkdir(exist_ok=True)

    # get met data
    if data_source == 'historical':
        data = get_met_data('2012-07-01', None)
    elif data_source == 'era5':
        warnings.warn('this data is uncorrected and under estimates recharge significantly')
        data = get_era5_land()
        data.rename(columns={'precipitation': 'Rainfall', 'potential_et': 'PET'}, inplace=True)
    else:
        raise ValueError(f'bad data source: {data_source}')
    data.loc[:, 'water_year'] = (data.index + pd.DateOffset(months=-6)).year
    if from_year is not None:
        temp_data = data.loc[(data.index.year <= to_year + 1) & (data.index.year >= from_year - 1)]
    else:
        temp_data = data
    water_years = temp_data.water_year.unique()
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

        if from_year is not None:
            idx = (pd.Series(dates).dt.year >= from_year) & (pd.Series(dates).dt.year <= to_year)
            dates = dates[idx]
            data = data[idx]

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
            irrig_aval = get_irrig_avaliblity((len(temp_data), *smt.model_shape[1:]))
        else:
            irrig_aval = np.full((len(temp_data), *smt.model_shape[1:]), np.inf)

        irrig_trig = np.repeat(_map_from_irrig_code(irrig_codes, 'irrig_trig')[np.newaxis, :],
                               len(temp_data), axis=0)  # 3d, static
        irrig_targ = np.repeat(_map_from_irrig_code(irrig_codes, 'irrig_targ')[np.newaxis, :],
                               len(temp_data), axis=0)

        rush = Rushton(
            dates=temp_data.index,
            # 3d arrays in
            rainfall=np.repeat(temp_data.Rainfall.values[:, np.newaxis], np.prod(smt.model_shape[1:]),
                               axis=1).reshape((len(temp_data), *smt.model_shape[1:])),
            pet=np.repeat(temp_data.PET.values[:, np.newaxis], np.prod(smt.model_shape[1:]),
                          axis=1).reshape((len(temp_data), *smt.model_shape[1:])),
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
            irrig_max_store=np.full(smt.model_shape[1:], irrig_max_store),
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
        irrig_init_store = np.zeros(smt.model_shape[1:])

        dates.append(deepcopy(rush.dates))
        outdata.append(deepcopy(rush.recharge))
        rush = None
        gc.collect()

    outdata = np.concatenate(outdata, axis=0)
    dates = np.concatenate(dates, axis=0)
    if from_year is not None:
        idx = (pd.Series(dates).dt.year >= from_year) & (pd.Series(dates).dt.year <= to_year)
        dates = dates[idx]
        outdata = outdata[idx]
    return dates, outdata


def get_weekly_plus_era5_rch(start_date=None, end_date=None, frequency='W', limited_irrigation=False, fun='mean'):
    """

    :param start_date:
    :param end_date:
    :param frequency:
    :param limited_irrigation:
    :param fun:
    :return: rch in mm
    """
    if start_date is None:
        start_date = datetime.date(1950, 1, 1)

    if end_date is None:
        end_date = datetime.date(2020, 12, 31)

    start_water_year = start_date.year
    end_water_year = end_date.year
    outdates, outdata = [], []
    num_years = 5
    for sy in range(start_water_year, end_water_year, num_years):
        dates, rch = get_historical_rch_model_results('era5', limited_irrigation=limited_irrigation,
                                                      from_year=sy, to_year=sy + num_years)

        temp = pd.DataFrame(index=pd.to_datetime(dates),
                            data=rch.reshape(rch.shape[0], np.prod(rch.shape[1:]))
                            )

        temp = select_resample(temp, None, None, frequency, fun)
        out_rch = temp.values.reshape((len(temp), *rch.shape[1:]))
        outdata.append(out_rch)
        outdates.append(temp.index)

    outdates = np.concatenate(outdates)
    outdata = np.concatenate(outdata, axis=0)

    idx = pd.Series(outdates).duplicated()
    outdates = outdates[~idx]
    outdata = outdata[~idx]
    outdates = pd.to_datetime(outdates)
    idx = (outdates >= pd.to_datetime(start_date)) & (outdates <= pd.to_datetime(end_date))
    outdates = outdates[idx]
    outdata = outdata[idx]

    return outdates, outdata


def get_corrected_historical_era5_rch(start_date, end_date, recalc=False, limited_irrigation=False,
                                      frequency='W', fun='mean', return_fig=False):
    """
    # keynote corrected recharge is a little low for dryland, but about right for irrigated.
    :param start_date: None or start date
    :param end_date: None or end date
    :param recalc: boolean recaclualte
    :param limited_irrigation: boolean limit amount of irrigation applied
    :param frequency: pd freq code (weekly plus)
    :param fun: function to resample if needed
    :return: rch in mm
    """
    if return_fig:
        assert recalc
    if frequency == 'D':
        raise ValueError('must be weekly plus')
    if limited_irrigation:
        lm_path = ''
    else:
        lm_path = 'un'

    processed_rch_path = processed_model_build_data_dir.joinpath(
        f'corrected_weekly_historical_era5_rch_{lm_path}limited_irr.npz')
    processed_dates_path = processed_model_build_data_dir.joinpath(
        f'corrected_weekly_historical_era5_rch_dates_{lm_path}limited_irr.npz')
    if processed_dates_path.exists() and processed_rch_path.exists() and not recalc:
        print('loading from repo')
        dates = np.load(processed_dates_path).get('arr_0')
        rch = np.load(processed_rch_path).get('arr_0')

        temp = pd.DataFrame(index=pd.to_datetime(dates),
                            data=rch.reshape(rch.shape[0], np.prod(rch.shape[1:]))
                            )

        temp = select_resample(temp, start_date, end_date, frequency, fun, start_ends_out_bounds='warn')
        idx = temp.isna().all(axis=1)
        if any(idx):
            warnings.warn(f'na values for full model in: {dates[idx]}')

        out_rch = temp.values.reshape((len(temp), *rch.shape[1:]))

        return temp.index, out_rch
    print(
        'ignore user warnings re uncorrected data.  correcting uncorrected data so I need to get the uncorrected data')
    historical_dates, historical_rch = get_rch(None, None, frequency='W', limited_irrigation=False)
    era5_dates, era5_rch_raw = get_weekly_plus_era5_rch(start_date=None,
                                                        end_date=None,
                                                        limited_irrigation=False, frequency='W')
    era5_dates = pd.to_datetime(era5_dates)

    era5_season = np.array([int_season_mapper[e.month] for e in era5_dates])
    era5_year = np.array([e.year for e in era5_dates])

    historical_dates = pd.to_datetime(historical_dates)
    hist_year = np.array([e.year for e in historical_dates])

    expected_dates = np.array(sorted(set(era5_dates).intersection(historical_dates)))

    era5_idx = np.array([e in expected_dates for e in era5_dates])
    hist_idx = np.array([e in expected_dates for e in historical_dates])
    assert (historical_dates[hist_idx] == era5_dates[era5_idx]).all()
    ibound = smt.get_no_flow(0)
    irrigated = {}
    for y in [2015, 2020, 2021]:
        t = get_irrigation_code(y, recalc=True)
        irrigated[y] = (t >= 0) & (ibound == 1)

    irrigated_era5_fit_data = []
    irrigated_era5_fit_data_season = []
    irrigated_hist_fit_data = []
    unirrigated_era5_fit_data = []
    unirrigated_era5_fit_data_season = []
    unirrigated_hist_fit_data = []
    for y in [2015, 2020, 2021]:
        if y <= 2015:
            era5_year_idx = (era5_year <= y)
            hist_year_idx = (hist_year <= y)
        elif y <= 2020:
            era5_year_idx = (era5_year <= 2020) & (era5_year > 2015)
            hist_year_idx = (hist_year <= 2020) & (hist_year > 2015)
        elif y >= 2021:
            era5_year_idx = (era5_year >= 2021)
            hist_year_idx = (hist_year >= 2021)
        else:
            raise ValueError('shouldnt get here')

        t = np.nanmean(era5_rch_raw[era5_idx & era5_year_idx][:, irrigated[y]], axis=1)
        irrigated_era5_fit_data.append(t)
        irrigated_era5_fit_data_season.append(era5_season[era5_idx & era5_year_idx])
        t2 = np.nanmean(historical_rch[hist_idx & hist_year_idx][:, irrigated[y]], axis=1)
        irrigated_hist_fit_data.append(t2)

        # unirrigated_data
        t = np.nanmean(era5_rch_raw[era5_idx & (era5_year == y)][:, ~irrigated[y] & (ibound == 1)], axis=1)
        unirrigated_era5_fit_data.append(t)
        unirrigated_era5_fit_data_season.append(era5_season[era5_idx & (era5_year == y)])
        t2 = np.nanmean(historical_rch[hist_idx & (hist_year == y)][:, ~irrigated[y] & (ibound == 1)], axis=1)
        unirrigated_hist_fit_data.append(t2)

    irrigated_era5_fit_data = np.concatenate(irrigated_era5_fit_data)
    irrigated_era5_fit_data_season = np.concatenate(irrigated_era5_fit_data_season)
    irrigated_hist_fit_data = np.concatenate(irrigated_hist_fit_data)
    unirrigated_era5_fit_data = np.concatenate(unirrigated_era5_fit_data)
    unirrigated_era5_fit_data_season = np.concatenate(unirrigated_era5_fit_data_season)
    unirrigated_hist_fit_data = np.concatenate(unirrigated_hist_fit_data)

    fig, (irrig_ax, unirrig_ax) = plt.subplots(2, figsize=(10, 8))
    # make fit
    from sklearn.linear_model import LinearRegression
    regr_irrig = LinearRegression()
    x = np.concatenate((irrigated_era5_fit_data[:, np.newaxis], irrigated_era5_fit_data_season[:, np.newaxis]), axis=1)
    y = irrigated_hist_fit_data
    regr_irrig.fit(x, y)
    rscore = regr_irrig.score(x, y)
    print('irrigated r2', rscore)
    y_pred = regr_irrig.predict(x)
    irrig_ax.scatter(x[:, 0], y, color='k', label='Original data')
    irrig_ax.scatter(x[:, 0], y_pred, color='r', label='Predicted data')
    irrig_ax.set_title(f'Irrigated weekly recharge\nFunction of ERA5 recharge and season\nR2:{round(rscore, 2)}')
    irrig_ax.set_ylabel('Recharged modelled from measured data')
    irrig_ax.set_xlabel('Recharged modelled from ERA5-land data')

    regr_unirrig = LinearRegression()
    x = unirrigated_era5_fit_data[:, np.newaxis]
    y = unirrigated_hist_fit_data
    regr_unirrig.fit(x, y)
    rscore = regr_unirrig.score(x, y)
    print('unirrigated r2', rscore)
    y_pred = regr_unirrig.predict(x)
    unirrig_ax.scatter(x[:, 0], y, color='k', label='Original data')
    unirrig_ax.plot(x[:, 0], y_pred, color='r', label='Predicted data')
    unirrig_ax.set_title(f'Un-irrigated weekly recharge\nFunction of ERA5 recharge\nR2:{round(rscore, 2)}')
    unirrig_ax.set_ylabel('Recharged modelled from measured data')
    unirrig_ax.set_xlabel('Recharged modelled from ERA5-land data')

    fig.suptitle('ERA5-Land recharge correction')
    fig.tight_layout()

    # predict new data
    outdata = np.full(era5_rch_raw.shape, np.nan)
    for y in [2015, 2020, 2021]:
        print(y)
        if y <= 2015:
            era5_year_idx = (era5_year <= y)

        elif y <= 2020:
            era5_year_idx = (era5_year <= 2020) & (era5_year > 2015)
        elif y >= 2021:
            era5_year_idx = (era5_year >= 2021)
        else:
            raise ValueError('shouldnt get here')
        if era5_year_idx.sum() == 0:
            continue
        # irrigated
        data = era5_rch_raw[era5_year_idx][:, irrigated[y]]
        expect_shape = data.shape
        seasons = np.repeat(era5_season[era5_year_idx][:, np.newaxis], expect_shape[-1], axis=1)
        assert data.shape == seasons.shape
        temp = regr_irrig.predict(np.concatenate((data.flatten()[:, np.newaxis],
                                                  seasons.flatten()[:, np.newaxis]), axis=1))
        temp2 = outdata[era5_year_idx]
        temp2[:, irrigated[y]] = temp.reshape(expect_shape)
        outdata[era5_year_idx] = temp2

        # unirrigated
        data = era5_rch_raw[era5_year_idx][:, ~irrigated[y] & (ibound == 1)]
        expect_shape = data.shape
        seasons = np.repeat(era5_season[era5_year_idx][:, np.newaxis], expect_shape[-1], axis=1)
        temp = regr_unirrig.predict(data.flatten()[:, np.newaxis])
        temp2 = outdata[era5_year_idx]
        temp2[:, ~irrigated[y] & (ibound == 1)] = temp.reshape(expect_shape)
        outdata[era5_year_idx] = temp2
        gc.collect()
    idx = np.isfinite(outdata[:, ibound == 1]).all(axis=1)
    assert idx.all(), f'na values for full model in: {era5_dates[idx]}'

    np.savez_compressed(processed_rch_path, outdata)
    np.savez_compressed(processed_dates_path, era5_dates)

    temp = pd.DataFrame(index=pd.to_datetime(era5_dates),
                        data=outdata.reshape(outdata.shape[0], np.prod(outdata.shape[1:]))
                        )

    temp = select_resample(temp, start_date, end_date, frequency, fun)
    idx = temp.isna().all(axis=1)
    if any(idx):
        warnings.warn(f'na values for full model in: {era5_dates[idx]}')
    out_rch = temp.values.reshape((len(temp), *outdata.shape[1:]))
    if return_fig:
        return temp.index, out_rch, fig

    return temp.index, out_rch


def get_rch(start_date, end_date, frequency='D', limited_irrigation=False, recalc=False, fun='mean'):
    # keynote all rch is in mm
    dates, rch = get_historical_rch_model_results('historical', limited_irrigation=limited_irrigation, recalc=recalc)

    temp = pd.DataFrame(index=dates,
                        data=rch.reshape(rch.shape[0], np.prod(rch.shape[1:]))
                        )

    temp = select_resample(temp, start_date, end_date, frequency, fun)
    out_rch = temp.values.reshape((len(temp), *rch.shape[1:]))
    return temp.index.values, out_rch


if __name__ == '__main__':
    rerun_rch_model = False
    if rerun_rch_model:
        get_era5_land(True, True)
        get_historical_rch_model_results(data_source='historical', limited_irrigation=False, recalc=True)
        get_historical_rch_model_results(data_source='historical', limited_irrigation=True, recalc=True)
        get_historical_rch_model_results(data_source='era5', limited_irrigation=False, recalc=True)
        get_historical_rch_model_results(data_source='era5', limited_irrigation=True, recalc=True)

    get_corrected_historical_era5_rch(None, None, recalc=True, limited_irrigation=False)
    get_corrected_historical_era5_rch(None, None, recalc=True, limited_irrigation=True)
