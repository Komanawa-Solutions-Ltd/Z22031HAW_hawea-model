"""
created matt_dumont 
on: 24/11/22
"""
import datetime
import warnings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy
import netCDF4 as nc
from model_build.utils import select_resample
from model_build.project_model_tools import smt
from model_build.supporting_data_analysis.recharge_model import get_era5_land, get_soil_classes, _map_from_soil_class, \
    get_irrigation_code, _map_from_irrig_code, irrig_max_store, get_rch, int_season_mapper, get_weekly_plus_era5_rch
from project_base import processed_scen_dir
import gc


def _get_scenario_rch_model_results(from_year=None, to_year=None, dryland=False, recalc=False):
    """
    get scenario recharge modelling results.  Either dryland or all pivot irrigation
    :param from_year: start year or None (full record)
    :param to_year: end year or None (full record)
    :param dryland: bool if true dryland recharge (no irrigation)
    :param recalc:  bool recalc from datasets
    :return:
    """
    data_source = 'era5'
    assert data_source in ['historical', 'era5']
    if from_year is None:
        assert to_year is None
    else:
        assert to_year is not None

    extra = 'unlimited'
    if dryland:
        extra = 'dryland'
    irrigation_record_dir = processed_scen_dir.joinpath(
        f'rch_historical_record_from_{data_source}_{extra}')
    irrigation_record_dir.mkdir(exist_ok=True)

    # get met data
    warnings.warn('this data is uncorrected and under estimates recharge significantly')
    data = get_era5_land()
    data.rename(columns={'precipitation': 'Rainfall', 'potential_et': 'PET'}, inplace=True)
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

    from rushton_model.rushton import Rushton # keynote private repo
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

    irrig_codes = get_irrigation_code(2022)
    irrig_codes[irrig_codes >= 0] = 2  # keynote set all irrigation to pivot
    if dryland:
        irrig_codes[:] = -1

    for y in water_years:
        print(f'starting to run year: {y}')
        temp_data = data.loc[data.water_year == y]

        # get irrigation codes (note the shapefiles are additive/overwrite)
        max_irrig_apply = _map_from_irrig_code(irrig_codes, 'max_irrig_apply')
        min_irrig_return = _map_from_irrig_code(irrig_codes, 'min_irrig_return')
        irrig_effic = _map_from_irrig_code(irrig_codes, 'irrig_effic')

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


def get_weekly_plus_scenario_era5_rch(start_date=None, end_date=None, frequency='W', fun='mean',
                                      dryland=False):
    """
    get weekly era rcecharge (daily is really big)
    :param start_date: start date
    :param end_date: end date
    :param frequency: pd. frequency code (must be weekly or greater)
    :param fun: function to aggregate recharge
    :param dryland: bool if true return dryland recharge (no irrigation)
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
        dates, rch = _get_scenario_rch_model_results(from_year=sy, to_year=sy + num_years, dryland=dryland)

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


def get_corrected_scenario_era5_rch(start_date, end_date, recalc=False,
                                    frequency='W', fun='mean',
                                    dryland=False):
    """
    # keynote corrected recharge is a little low for dryland, but about right for irrigated.
    :param start_date: None or start date
    :param end_date: None or end date
    :param recalc: boolean recaclualte
    :param frequency: pd freq code (weekly plus)
    :param fun: function to resample if needed
    :param dryland: bool if true only non-irrigated recharge.
    :return: rch in mm
    """
    if frequency == 'D':
        raise ValueError('must be weekly plus')
    extra = 'unlimited'
    if dryland:
        extra = 'dryland'
    processed_rch_path = processed_scen_dir.joinpath(f'corrected_weekly_sen_era5_rch_{extra}_irr.npz')
    processed_dates_path = processed_scen_dir.joinpath(f'corrected_weekly_sen_era5_rch_dates_{extra}_irr.npz')
    if processed_dates_path.exists() and processed_rch_path.exists() and not recalc:
        print('loading from repo')
        dates = np.load(processed_dates_path).get('arr_0')
        rch = np.load(processed_rch_path).get('arr_0')
    else:
        dates, rch = _correct_sen_rch(dryland)
        np.savez_compressed(processed_rch_path, rch)
        np.savez_compressed(processed_dates_path, dates)

    temp = pd.DataFrame(index=pd.to_datetime(dates),
                        data=rch.reshape(rch.shape[0], np.prod(rch.shape[1:]))
                        )

    temp = select_resample(temp, start_date, end_date, frequency, fun, start_ends_out_bounds='warn')
    idx = temp.isna().all(axis=1)
    if any(idx):
        warnings.warn(f'na values for full model in: {dates[idx]}')

    out_rch = temp.values.reshape((len(temp), *rch.shape[1:]))

    return temp.index, out_rch


def _correct_sen_rch(dryland):
    ibound, regr_irrig, regr_unirrig = _make_corrections()

    # predict new data
    era5_dates_scen, outdata_scen = _predict_scenario_data(ibound, regr_irrig, regr_unirrig, dryland=dryland)

    return era5_dates_scen, outdata_scen


def _make_corrections():
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
    return ibound, regr_irrig, regr_unirrig


def _predict_scenario_data(ibound, regr_irrig, regr_unirrig, dryland=False):
    y = 2021  # keynote no irrigation expansion beyond current irrigated area
    era5_dates, era5_rch_raw = get_weekly_plus_scenario_era5_rch(dryland=dryland)
    if dryland:
        t = np.full(ibound.shape, -1)  # set all to unirrigated
    else:
        t = get_irrigation_code(y, recalc=True)  # code is only to identify irrigated area

    era5_season = np.array([int_season_mapper[e.month] for e in era5_dates])

    irrigated = (t >= 0) & (ibound == 1)
    outdata = np.full(era5_rch_raw.shape, np.nan)

    # irrigated
    if irrigated.sum() > 0:
        data = era5_rch_raw[:, irrigated]
        expect_shape = data.shape
        seasons = np.repeat(era5_season[:, np.newaxis], expect_shape[-1], axis=1)
        assert data.shape == seasons.shape
        temp = regr_irrig.predict(np.concatenate((data.flatten()[:, np.newaxis],
                                                  seasons.flatten()[:, np.newaxis]), axis=1))
        outdata[:, irrigated] = temp.reshape(expect_shape)

    # unirrigated
    un_irrigated = ~irrigated & (ibound == 1)
    if un_irrigated.sum() > 0:
        data = era5_rch_raw[:, un_irrigated]
        expect_shape = data.shape
        seasons = np.repeat(era5_season[:, np.newaxis], expect_shape[-1], axis=1)
        temp = regr_unirrig.predict(data.flatten()[:, np.newaxis])
        outdata[:, un_irrigated] = temp.reshape(expect_shape)

    gc.collect()
    idx = np.isfinite(outdata[:, ibound == 1]).all(axis=1)
    assert idx.all(), f'na values for full model in: {era5_dates[idx]}'

    return era5_dates, outdata


def data_checks(save=False):
    from model_build.supporting_data_analysis.recharge_model import get_corrected_historical_era5_rch, get_rch
    recalc = False
    if save:
        outdir = processed_scen_dir.parent.joinpath('boundary_condition_plots')
        outdir.mkdir(exist_ok=True)

    dryland_dates, dryland_rch = get_corrected_scenario_era5_rch(start_date=None, end_date=None, dryland=True,
                                                                 frequency='Y',
                                                                 fun='mean', recalc=recalc)
    irr_dates, irr_rch = get_corrected_scenario_era5_rch(start_date=None, end_date=None, dryland=False, frequency='Y',
                                                         fun='mean', recalc=recalc)
    hist_era5_dates, hist_era5_rch = get_corrected_historical_era5_rch(start_date=None, end_date=None, frequency='Y',
                                                                       fun='mean')
    hist_dates, hist_rch = get_rch(None, None, frequency='Y', fun='mean')
    irrig_area = get_irrigation_code(2021) >= 0
    ibound = smt.get_no_flow(0) == 1
    scens = ['dryland_rch', 'irr_rch', 'hist_rch', 'hist_era5_rch']
    temp = []
    for s in scens:
        temp.append(eval(s)[:, ibound].flatten())
    temp = np.concatenate(temp)
    vmin = np.percentile(temp, 1) * 365
    vmax = np.percentile(temp, 99) * 365
    # look at dryland vs irrigated recharge, spatially

    for nm in scens:
        data = eval(nm).mean(axis=0)
        fig, ax = smt.plot.plt_matrix(data * 365, vmin=vmin, vmax=vmax, title=f'Mean annual LSR (mm/yr): {nm}',
                                      no_flow_layer=0, base_map=True,
                                      )
        fig.tight_layout()
        if save:
            fig.savefig(outdir.joinpath(f'spatial_rch_{nm}.png'))

    fig, axs = plt.subplots(ncols=2, figsize=(14, 9), sharex=True, sharey=True)
    for ax, nm in zip(axs, scens[2:]):
        data = eval(nm).mean(axis=0)
        fig, ax = smt.plot.plt_matrix(data * 365, vmin=vmin, vmax=vmax, title=f'{nm}',
                                      no_flow_layer=0, base_map=True, ax=ax
                                      )
    fig.suptitle('Mean annual LSR (mm/yr)')
    fig.tight_layout()
    if save:
        fig.savefig(outdir.joinpath(f'spatial_rch_hist_comp.png'))
    from model_build.utils import get_colors
    colors = get_colors(scens, 'tab10')

    # look at mean recharge through time
    # look at mean irrigated recharge through time
    # look at mean dryland recharge throughtime
    fig, axs = plt.subplots(nrows=3, figsize=(14, 9), sharex=True, sharey=True)
    for ax, idx, nm in zip(axs, [ibound, irrig_area, ~irrig_area],
                       ['full_model', 'irrigated_area_2021', 'not_irrigated_area_2021']):
        ax.set_title(nm)
        for sc, c in zip(scens, colors):
            x = eval(sc.replace('rch', 'dates'))
            y = eval(sc)[:, idx & ibound].mean(axis=1) * 365
            ax.plot(x, y, c=c, label=sc)
        ax.legend()
    fig.suptitle('Mean annual recharge (mm/yr)')
    fig.tight_layout()

    if save:
        fig.savefig(outdir.joinpath(f'temporal_rch.png'))

    smt.plot.show()


if __name__ == '__main__':
    data_checks(save=True)
