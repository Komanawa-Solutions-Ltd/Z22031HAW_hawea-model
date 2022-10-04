"""
created matt_dumont 
on: 15/08/22
"""
import itertools
import warnings
import datetime
from ppscore import score as ppscore
from sklearn.feature_selection import mutual_info_regression
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd
from model_build.supporting_data_analysis import get_all_wells, get_hillside_flows, get_lake_heads, get_lake_hawea_loc
from model_build.project_model_tools import smt
from model_build.utils import select_resample
from model_build.zones import get_param_zones
from project_base import processed_target_dir, base_target_dir
from model_build.utils import get_colors
from model_build.supporting_data_analysis.recharge_model import get_corrected_historical_era5_rch, get_irrigation_code
from optimisation.optimisation_period import start, end


# todo it may be worth comparing recharge and lake levels... at a water year level to see how to apply
# targets that occur outside of period.

def get_last_nmonths(nmonths, indates, data):
    out = []
    for t in indates:
        tstart_date = pd.to_datetime(datetime.date(t.year, t.month, 1) + relativedelta(months=-nmonths))
        tend_date = pd.to_datetime(datetime.date(t.year, t.month, 1) + relativedelta(months=1, days=-1))

        out.append(data[(data.index >= tstart_date) & (data.index <= tend_date)].sum())

    return np.array(out)


def get_dryland_mean_era5_rch(freq='M'):
    dates, rch = get_corrected_historical_era5_rch(None, None,
                                                   frequency=freq)
    print('got rch')
    use_rch = []
    irrig = {}
    for y in [2015, 2020, 2021]:
        irrig[y] = get_irrigation_code(y) == -1
    use_rch.append(np.nanmean(rch[dates.year <= 2015][:, ~irrig[2015]], axis=1))
    use_rch.append(np.nanmean(rch[(dates.year > 2015) & (dates.year <= 2020)][:, ~irrig[2020]], axis=1))
    use_rch.append(np.nanmean(rch[dates.year >= 2021][:, ~irrig[2021]], axis=1))
    use_rch = np.concatenate(use_rch)
    return dates, use_rch


def get_indicative_times_v2():
    freq = 'M'
    dates, use_rch = get_dryland_mean_era5_rch(freq)
    rch = pd.DataFrame(index=dates, columns=['rch'], data=use_rch)
    hill = get_hillside_flows(None, None, freq)
    hill = pd.DataFrame(hill.sum(axis=1), columns=['hill'])
    all_data = pd.merge(rch, hill, right_index=True, left_index=True)

    # normalize to 0-1
    all_data_norm = (all_data - all_data.mean()) / (all_data.max() - all_data.min())
    all_data_norm = all_data_norm - all_data_norm.min()
    print(all_data_norm.describe())

    # get the target dates
    well_data = _get_single_target_data()
    targ_dates = [datetime.date(2011, 9, 21)]
    targ_dates.extend(well_data.drilldate)

    targ_dates = pd.to_datetime(targ_dates)
    targ_dates = targ_dates[targ_dates < pd.to_datetime(start)]

    targ_data = pd.DataFrame(index=targ_dates)
    nmonths = 6
    targ_data.loc[:, 'rch'] = get_last_nmonths(nmonths, targ_dates, all_data_norm.loc[:, 'rch'])
    targ_data.loc[:, 'hill'] = get_last_nmonths(nmonths, targ_dates, all_data_norm.loc[:, 'hill'])
    targ_data.loc[:, 'month'] = targ_data.index.month

    period_dates = pd.date_range(start, end, freq='M')
    period_data = pd.DataFrame(index=period_dates)
    period_data.loc[:, 'rch'] = get_last_nmonths(nmonths, period_dates, all_data_norm.loc[:, 'rch'])
    period_data.loc[:, 'hill'] = get_last_nmonths(nmonths, period_dates, all_data_norm.loc[:, 'hill'])
    period_data.loc[:, 'month'] = period_data.index.month

    for m in range(1, 12):
        period_months = [
            (datetime.date(2020, m, 1) + relativedelta(months=-1)).month,
            (datetime.date(2020, m, 1) + relativedelta(months=1)).month,
        ]
        temp_targ = targ_data.loc[np.in1d(targ_data.month, [m])]
        temp_period = period_data.loc[np.in1d(period_data.month, period_months)]
        pass
        fig, ax = plt.subplots()
        ax.scatter(temp_period.rch, temp_period.hill, c='b', label='period data')
        for d, r, h, m in temp_period.itertuples(True, None):
            ax.text(r, h, f'{d.year}-{m}', color='b')
        ax.scatter(temp_targ.rch, temp_targ.hill, c='r', label='target data')
        for d, r, h, m in temp_targ.itertuples(True, None):
            ax.text(r, h, f'{d.year}-{m}', color='r')
        ax.set_title('months: {} to {} for month: {}'.format(*period_months, m))
        ax.set_ylabel('hillslope (normalized)')
        ax.set_xlabel('recharge (normalised)')
        ax.legend()

    plt.show()
    # todo need to id wheter to preference rch or hillslope or neither
    # todo could prefernce just on a model water budget basis... might be easiest/simlest, I like this
    # todo the other option is to just use all the dates, or all the dates within x percent
    # todo add in era5 for 2021
    raise NotImplementedError  # TODO  LOOK at mutual info regression


def get_indicative_times():
    well_data = _get_single_target_data()
    dates, use_rch = get_dryland_mean_era5_rch()
    hill = get_hillside_flows(None, None, 'M')
    hill = hill.sum(axis=1)

    targ_dates = [datetime.date(2011, 9, 21)]
    targ_dates.extend(well_data.drilldate)

    targ_dates = pd.to_datetime(targ_dates)
    targ_dates = targ_dates[targ_dates < pd.to_datetime(start)]

    targ_rch = []
    targ_hill = []
    nmonths = 6
    for t in targ_dates:
        tstart_date = pd.to_datetime(datetime.date(t.year, t.month, 1) + relativedelta(months=-nmonths))
        tend_date = pd.to_datetime(datetime.date(t.year, t.month, 1) + relativedelta(months=1, days=-1))

        targ_rch.append(use_rch[(dates >= tstart_date) & (dates <= tend_date)].sum())
        targ_hill.append(hill.loc[(hill.index >= tstart_date) & (hill.index <= tend_date)].sum())
    targ_data = pd.DataFrame({'date': targ_dates, 'rch': targ_rch, 'hill': targ_hill})
    targ_data.loc[:, 'month'] = targ_data.date.dt.month

    period_dates = pd.date_range(start, end, freq='M')
    period_rch = []
    period_hill = []
    for p in period_dates:
        pstart_date = pd.to_datetime(p + relativedelta(months=-nmonths))
        period_rch.append(use_rch[(dates >= pstart_date) & (dates <= p)].sum())
        period_hill.append(hill.loc[(hill.index >= pstart_date) & (hill.index <= p)].sum())
    period_data = pd.DataFrame({'date': period_dates, 'rch': period_rch, 'hill': period_hill})
    period_data.loc[:, 'month'] = period_data.date.dt.month
    # monthly mean target?
    # compare last n months of recharge...
    # normalize period and target data the same using mean std normalisation

    fig, ax = plt.subplots()
    ax.scatter(period_data.rch, period_data.hill, c='b', label='period data')
    ax.scatter(targ_data.rch, targ_data.hill, c='r', label='target data')
    for d, r, h, m in period_data.itertuples(False, None):
        ax.text(r, h, f'{d.year}-{m}', color='b')
    for d, r, h, m in targ_data.itertuples(False, None):
        ax.text(r, h, f'{d.year}-{m}', color='r')
    ax.set_title('all')
    ax.legend()

    for m in range(1, 12):
        temp_targ = targ_data.loc[targ_data.month == m]
        temp_period = period_data.loc[period_data.month == m]
        pass
        fig, ax = plt.subplots()
        ax.scatter(temp_period.rch, temp_period.hill, c='b', label='period data')
        for d, r, h, m in temp_period.itertuples(False, None):
            ax.text(r, h, f'{d.year}-{m}', color='b')
        ax.scatter(temp_targ.rch, temp_targ.hill, c='r', label='target data')
        for d, r, h, m in temp_targ.itertuples(False, None):
            ax.text(r, h, f'{d.year}-{m}', color='r')
        ax.set_title(f'month: {m}')
        ax.legend()

    fig, ax = plt.subplots()
    temp_targ = targ_data.iloc[0]
    print(temp_targ)
    temp_period = period_data.loc[period_data.month == 9]
    ax.scatter(temp_period.rch, temp_period.hill, c='b', label='period data')
    ax.scatter(temp_targ.rch, temp_targ.hill, c='r', label='target data')
    for d, r, h, m in temp_period.itertuples(False, None):
        ax.text(r, h, f'{d.year}-{m}')
    ax.set_title(f'sept 2011 vs sept')
    ax.legend()

    fig, ax = plt.subplots()
    ax.scatter(period_data.rch, period_data.hill, c='b', label='period data')
    ax.scatter(temp_targ.rch, temp_targ.hill, c='r', label='target data')
    ax.set_title(f'sept 2011 vs all')
    for d, r, h, m in period_data.itertuples(False, None):
        ax.text(r, h, f'{d.year}-{m}')
    ax.legend()
    plt.show()
    # stdev on the lake wave... how much does that vary monthly
    # look at relationship between rch, hillslope, time delta against lakewave for high frequency data
    # use this to determine minimum difference (e.g. weight deltas by correlation).
    # look at the ideal correlation between head, rch, hillslope (e.g. 1 month, 2 to 6 month mean)
    # correlation to lake levels will vary by distance.

    raise NotImplementedError('superseded, see get indicative times v2')


def predictive_power_hill_rch():
    freq = 'M'
    figs, names = [], []
    targs = get_high_freq_head_targets(None, None, freq=freq)
    targ_names = targs.keys()
    colors = get_colors(targ_names)
    all_wells = get_all_wells().loc[targ_names]
    lake_locs = get_lake_hawea_loc()
    lake_locs = smt.io.add_mxmy_to_df(lake_locs)
    lake_y = lake_locs.my.min()
    all_wells.loc[:, 'dist'] = lake_y - all_wells.loc[:, 'nztmy']
    print(all_wells.loc[:, 'dist'])

    dates, use_rch = get_dryland_mean_era5_rch(freq)
    rch = pd.DataFrame(index=dates, columns=['rch'], data=use_rch)
    hill = get_hillside_flows(None, None, freq)
    hill = pd.DataFrame(hill.sum(axis=1), columns=['hill'])
    lake = pd.DataFrame(get_lake_heads(None, None, frequency=freq))
    all_data = pd.merge(rch, hill, right_index=True, left_index=True)
    all_data = pd.merge(all_data, lake, right_index=True, left_index=True)
    all_data_norm = (all_data - all_data.mean()) / (all_data.max() - all_data.min())
    all_data_norm = all_data_norm - all_data_norm.min()
    print(all_data_norm.describe())
    keys = []
    nmonths = np.arange(1, 13)
    for n in nmonths:
        targs.loc[:, f'rch_{n}'] = get_last_nmonths(n, targs.index, all_data_norm.loc[:, 'rch'])
        targs.loc[:, f'hill_{n}'] = get_last_nmonths(n, targs.index, all_data_norm.loc[:, 'hill'])
        keys.extend([f'rch_{n}', f'hill_{n}'])
    outdata = pd.DataFrame(index=targ_names, columns=keys)
    outdata_pp = pd.DataFrame(index=targ_names, columns=keys)
    outdata_mutreggres = pd.DataFrame(index=targ_names, columns=keys)
    for t, k in itertools.product(targ_names, keys):
        n = int(k.split('_')[-1])
        k1, k2 = f'rch_{n}', f'hill_{n}'
        use_data = targs.loc[:, [t, k1, k2]].dropna()
        mut = mutual_info_regression(use_data.loc[:, [k1, k2]], use_data.loc[:, t])
        outdata_mutreggres.loc[t, k1] = mut[0]
        outdata_mutreggres.loc[t, k2] = mut[1]

        use_data = targs.loc[:, [t, k]].dropna()
        test = ppscore(use_data, k, t)['ppscore']
        outdata_pp.loc[t, k] = test
        corr_data = np.array([targs.loc[:, t], targs.loc[:, k]]).transpose()
        corr_data = corr_data[np.isfinite(corr_data).all(axis=1)]
        corr = np.corrcoef(corr_data[:, 0], corr_data[:, 1])
        outdata.loc[t, k] = corr[0, 1]

    outdata = outdata.abs()
    for df, n in zip([outdata_pp, outdata, outdata_mutreggres], ['pp score', 'correlation', 'mutual_info']):
        fig, axs = plt.subplots(2, sharex=True, sharey=True, figsize=(10, 8))
        fig.suptitle(n)
        for k, ax in zip(['rch', 'hill'], axs):
            use_keys = [f'{k}_{e}' for e in nmonths]
            for t, c in zip(targ_names, colors):
                ax.plot(nmonths, df.loc[t, use_keys], c=c, label=t, marker='.')
                ax.set_title(f'correlations to shifted to {k}')
                ax.set_ylabel('pearsons R correlation coeff')
                ax.set_xlabel('cumulative months shifted back')
    print('correlation coeff')
    print(outdata.max(axis=1))
    print('ppscore')
    print(outdata_pp.max(axis=1))
    print('mut_regress')
    print(outdata_mutreggres.max(axis=1))
    plt.show()
    # todo include this in writeup
    # Keynote 6 months is best for all except mutual regression


def get_compare_correlations_lake():
    freq = 'W'
    figs, names = [], []
    targs = get_high_freq_head_targets(None, None, freq=freq)
    targ_names = targs.keys()
    colors = get_colors(targ_names)
    all_wells = get_all_wells().loc[targ_names]
    lake_locs = get_lake_hawea_loc()
    lake_locs = smt.io.add_mxmy_to_df(lake_locs)
    lake_y = lake_locs.my.min()
    all_wells.loc[:, 'dist'] = lake_y - all_wells.loc[:, 'nztmy']
    print(all_wells.loc[:, 'dist'])

    dates, use_rch = get_dryland_mean_era5_rch(freq)
    rch = pd.DataFrame(index=dates, columns=['rch'], data=use_rch)
    hill = get_hillside_flows(None, None, freq)
    hill = pd.DataFrame(hill.sum(axis=1), columns=['hill'])
    lake = pd.DataFrame(get_lake_heads(None, None, frequency=freq))
    all_data = pd.merge(rch, hill, right_index=True, left_index=True)
    all_data = pd.merge(all_data, lake, right_index=True, left_index=True)
    all_data = pd.merge(all_data, targs, how='outer', right_index=True, left_index=True)
    all_data_norm = (all_data - all_data.mean()) / all_data.std()

    shift_months = np.arange(0, 105) * -1
    all_shifts = pd.DataFrame(index=targ_names, columns=shift_months)
    for targ, shift in itertools.product(targ_names, shift_months):
        corr_data = np.array([all_data_norm.loc[:, targ], all_data_norm.loc[:, 'lake_stage'].shift(shift)]).transpose()
        corr_data = corr_data[np.isfinite(corr_data).all(axis=1)]
        corr = np.corrcoef(corr_data[:, 0], corr_data[:, 1])
        all_shifts.loc[targ, shift] = corr[0, 1]
    all_shifts = all_shifts.transpose()
    fig, (ax, ax1) = plt.subplots(nrows=2, sharey=True, sharex=True, figsize=(10, 8))
    for t, c in zip(targ_names, colors):
        ax.plot(all_shifts.index * -7, all_shifts[t], c=c, label=t, marker='.')

    ax.legend()
    ax.axhline(0, ls=':', color='k')
    ax1.axhline(0, ls=':', color='k')
    ax.set_title('correlations to shifted lake level')
    fig.supylabel('pearsons R correlation coeff')
    fig.supxlabel('days shifted back')
    temp = pd.DataFrame({t: all_shifts[t].sort_values(ascending=False).index for t in targ_names})
    print(temp)

    # shift only the head data to g40_0415
    all_shifts_towell = pd.DataFrame(index=targ_names, columns=shift_months)
    for targ, shift in itertools.product(targ_names, shift_months):
        corr_data = np.array([all_data_norm.loc[:, targ], all_data_norm.loc[:, 'g40_0415'].shift(shift)]).transpose()
        corr_data = corr_data[np.isfinite(corr_data).all(axis=1)]
        corr = np.corrcoef(corr_data[:, 0], corr_data[:, 1])
        all_shifts_towell.loc[targ, shift] = corr[0, 1]
    all_shifts_towell = all_shifts_towell.transpose()

    for t, c in zip(targ_names, colors):
        ax1.plot(all_shifts_towell.index * -7, all_shifts_towell[t], c=c, label=t, marker='.')

    ax1.legend()
    ax1.set_title('correlations to shifted to g40_0415')
    ax1.set_ylabel('pearsons R correlation coeff')
    ax1.set_xlabel('days shifted back')
    temp = pd.DataFrame({t: all_shifts[t].sort_values(ascending=False).index for t in targ_names})
    print(temp)
    fig.tight_layout()
    for i in range(0, 800, 100):
        ax.axvline(i, color='k', alpha=0.5, ls=':')
        ax1.axvline(i, color='k', alpha=0.5, ls=':')

    fig, ax = smt.plot.plot_basemap(no_flow_layer=0)

    ax.scatter(all_wells.nztmx, all_wells.nztmy, color='r')
    for k, c in zip(targ_names, colors):
        x, y = all_wells.loc[k, ['nztmx', 'nztmy']]
        adder = np.random.randint(1, 500)
        ax.scatter(x, y, color=c, label=k)
        ax.text(x + 100, y + adder, k, color='k', fontdict={'weight': 'heavy'})
    ax.legend()
    ax.set_title('Head obs locations')
    figs.append(fig)
    names.append('high_frequency_locs')
    plt.show()

    # peak for flat 264 d  rate of 21.75 m/day # rate from bore c. 17m/day
    # peak for clutha first peak 200 d 50 m/day # rate from bore  37m/day
    # peak for clutha second peak 568 d rate of 17.57 m/day # rate from bore 15.2m/day
    # from mean weekly level we get shift of 50 days to flat (104m/day) , 130 days (72m/day)

    # in areas affected by lake level +- 1 month more is lower weight
    # in area not affected by lake level higher
    # keynote choose to simply use +- 1 month based on the inter-quartile range of high frequency data

    raise NotImplementedError


def _get_single_target_data():
    # from get_all_wells
    all_wells = get_all_wells()
    all_wells = all_wells.loc[all_wells.ibound > 0]
    param_zone = get_param_zones()
    all_wells.loc[:, 'param_zone'] = param_zone[all_wells.i, all_wells.j]

    idx = (all_wells.param_zone < 0) & (all_wells.quality_code < 3)
    all_wells = all_wells.loc[~idx]
    all_wells = all_wells.loc[all_wells.quality_code > 0]
    return all_wells


def get_single_head_targets(recalc=False):  # todo add recalc
    all_wells = _get_single_target_data()
    # todo, set indiciative times! how do I want to do this???
    warnings.warn('not finished, still need to set indicative times')

    return all_wells


def get_2011_piezo_survey(recalc=False):
    # piezo survey conducted 21-sept-2011
    data_path = base_target_dir.joinpath('Peizo Survey 20Sept2011.xlsx')
    processed_path = processed_target_dir.joinpath('piezo_targets.csv')

    if processed_path.exists() and not recalc:
        data = pd.read_csv(processed_path)
        # todo manage types
        raise NotImplementedError
        return data

    data = pd.read_excel(data_path, 'Appendix Table')
    data.rename(columns={'Easting': 'nztmx', 'Northing': 'nztmy', 'Water level elevation': 'head'}, inplace=True)
    row, col = smt.convert_coords_to_matix(data.nztmx, data.nztmy, coords_out_domain='coerce')
    data.loc[:, 'i'] = row
    data.loc[:, 'j'] = col
    data = data.loc[data.i >= 0]
    ibound = smt.get_no_flow(0)
    data.loc[:, 'ibound'] = ibound[data.i, data.j]
    data = data.loc[data.ibound > 0]

    # todo set indicative times! how do I want to do this
    warnings.warn('not finished, still need to set indicative times')
    data.to_csv(processed_path)
    return data


def get_low_freq_head_targets(start_date, end_date):
    data_path = base_target_dir.joinpath('NGMP bore fluctuations 1996 - 2019.csv')
    data = pd.read_csv(data_path)
    outdata = []
    for k in ['G40/0120', 'G40/0129']:
        temp = data.loc[:, [f'{k}_date', f'{k}_wl']].dropna()
        temp.loc[:, 'date'] = pd.to_datetime(temp.loc[:, f'{k}_date'], format='%d-%b-%Y').dt.date
        temp.rename(columns={f'{k}_wl': 'level'}, inplace=True)
        temp.loc[:, 'well'] = k.lower().replace('/', '_')
        outdata.append(temp.loc[:, ['date', 'well', 'level']])

    outdata = pd.concat(outdata)

    if start_date is None:
        start_date = outdata.loc[:, 'date'].min()
    if end_date is None:
        end_date = outdata.loc[:, 'date'].max()
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()

    outdata.loc[:, 'date'] = pd.to_datetime(outdata.loc[:, 'date'])
    use_outdata = []
    for w in outdata.well.unique():
        temp = outdata.loc[outdata.well == w, ['date', 'level']]
        temp.rename(columns={'level': w}, inplace=True)
        use_outdata.append(temp)
    outdata = pd.concat(use_outdata)
    outdata = outdata.groupby('date').mean()
    idx = (outdata.index >= pd.to_datetime(start_date)) & (outdata.index <= pd.to_datetime(end_date))
    return outdata.loc[idx]


def get_high_freq_head_targets(start_date, end_date, freq='D'):
    data_path = base_target_dir.joinpath('daily_head_obs.csv')
    data = pd.read_csv(data_path, comment='#')
    data.columns = [e.replace('/', '_').replace('Groundwater Level@', '').lower() for e in data.columns]
    data.loc[:, 'datetime'] = pd.to_datetime(data.loc[:, 'timestamp'], format='%d/%m/%Y %H:%M')
    data.set_index('datetime', inplace=True)
    data.drop(columns='timestamp', inplace=True)
    return select_resample(data, start_date, end_date, freq)


def plot_head_targets(how='all'):
    alpha = 0.8
    if how == 'all':
        fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, color_bar=False,
                                      base_map=True, no_flow_layer=0)

        all_wells = get_all_wells()
        all_wells = all_wells.loc[all_wells.ibound > 0]
        qcs = all_wells.loc[:, 'quality_code'].unique()
        colors = get_colors(qcs)
        for qc, c in zip(qcs, colors):
            temp = all_wells.loc[all_wells.quality_code == qc]
            ax.scatter(temp.nztmx, temp.nztmy, color=c, label=f'single targets qc: {qc}', marker='d', alpha=alpha)

        # add scott piezo locs
        piezo = get_2011_piezo_survey(recalc=True)
        ax.scatter(piezo.nztmx, piezo.nztmy, color='orange', marker='s', alpha=alpha, label='piezo 2011')

        # add ngmp wells
        t = get_low_freq_head_targets(None, None)
        wells = all_wells.loc[t.keys()]
        ax.scatter(wells.nztmx, wells.nztmy, color='b', marker='p', label='mod_freq')

        # add high frequency
        t = get_high_freq_head_targets(None, None)
        wells = all_wells.loc[t.keys()]
        ax.scatter(wells.nztmx, wells.nztmy, color='magenta', marker='*', label='high_freq')

        print('plotting all head targets')
        ax.set_title('all head targets')
        ax.legend()


    elif how == 'incl':
        fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, color_bar=False,
                                      base_map=True, no_flow_layer=0)

        all_wells = get_all_wells()
        single_targets = get_single_head_targets()
        all_wells = all_wells.loc[all_wells.ibound > 0]
        qcs = all_wells.loc[:, 'quality_code'].unique()
        colors = get_colors(qcs)
        for qc, c in zip(qcs, colors):
            temp = single_targets.loc[single_targets.quality_code == qc]
            ax.scatter(temp.nztmx, temp.nztmy, color=c, label=f'Single targets qc: {qc}', marker='d', alpha=alpha)

        # add scott piezo locs
        piezo = get_2011_piezo_survey(recalc=True)
        ax.scatter(piezo.nztmx, piezo.nztmy, color='orange', marker='s', alpha=alpha, label='Piezo 2011')

        # add ngmp wells
        t = get_low_freq_head_targets(None, None)
        wells = all_wells.loc[t.keys()]
        ax.scatter(wells.nztmx, wells.nztmy, color='b', marker='p', label='Moderate freq')

        # add high frequency
        t = get_high_freq_head_targets(None, None)
        wells = all_wells.loc[t.keys()]
        ax.scatter(wells.nztmx, wells.nztmy, color='magenta', marker='*', label='High freq')

        print('plotting head targets included in the model')
        ax.legend(loc='lower left')
        ax.set_title('Head targets included in the model')

    else:
        raise NotImplementedError
    return fig, ax


def export_incl_head_target_locs():
    outdata = []

    all_wells = get_all_wells()
    single_targets = get_single_head_targets()
    all_wells = all_wells.loc[all_wells.ibound > 0]
    qcs = single_targets.loc[:, 'quality_code'].unique()
    colors = get_colors(qcs)
    for qc, c in zip(qcs, colors):
        temp = single_targets.loc[single_targets.quality_code == qc]
        temp_out = {'nztmx': temp.nztmx.values, 'nztmy': temp.nztmy.values}
        temp_out = pd.DataFrame(temp_out)
        temp_out.loc[:, 'type'] = f'single_qc{qc}'
        outdata.append(temp_out)

    # add scott piezo locs
    piezo = get_2011_piezo_survey(recalc=True)
    temp_out = {'nztmx': piezo.nztmx.values, 'nztmy': piezo.nztmy.values}
    temp_out = pd.DataFrame(temp_out)
    temp_out.loc[:, 'type'] = 'piezo_2011'
    outdata.append(temp_out)

    # add ngmp wells
    t = get_low_freq_head_targets(None, None)
    wells = all_wells.loc[t.keys()]
    temp_out = {'nztmx': wells.nztmx.values, 'nztmy': wells.nztmy.values}
    temp_out = pd.DataFrame(temp_out)
    temp_out.loc[:, 'type'] = 'mod_freq'
    outdata.append(temp_out)

    # add high frequency
    t = get_high_freq_head_targets(None, None)
    wells = all_wells.loc[t.keys()]
    temp_out = {'nztmx': wells.nztmx.values, 'nztmy': wells.nztmy.values}
    temp_out = pd.DataFrame(temp_out)
    temp_out.loc[:, 'type'] = 'high_freq'
    outdata.append(temp_out)

    outdata = pd.concat(outdata)
    outdata.to_csv(processed_target_dir.joinpath('head_target_locations.csv'))


if __name__ == '__main__':
    get_indicative_times_v2()
    predictive_power_hill_rch()
    get_indicative_times()
    plot_head_targets(how='incl')
    smt.plot.show()
    plot_head_targets()
    export_incl_head_target_locs()
