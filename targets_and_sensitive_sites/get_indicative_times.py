"""
created matt_dumont 
on: 4/10/22
"""
import itertools
import datetime
from ppscore import score as ppscore
from sklearn.feature_selection import mutual_info_regression
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd
from model_build.supporting_data_analysis import get_all_wells, get_hillside_flows, get_lake_heads, get_lake_hawea_loc
from model_build.project_model_tools import smt
from model_build.utils import get_colors
from model_build.supporting_data_analysis.recharge_model import get_corrected_historical_era5_rch, get_irrigation_code
from optimisation.optimisation_period import start, end
from targets_and_sensitive_sites.get_raw_target_data import get_single_target_data, get_high_freq_head_targets
from project_base import processed_target_dir


# targets that occur outside of period.

def get_last_nmonths(nmonths, indates, data):
    out = []
    for t in indates:
        tstart_date = pd.to_datetime(datetime.date(t.year, t.month, 1) + relativedelta(months=-nmonths))
        tend_date = pd.to_datetime(datetime.date(t.year, t.month, 1) + relativedelta(months=1, days=-1))

        out.append(data[(data.index >= tstart_date) & (data.index <= tend_date)].sum())

    return np.array(out)


def get_mean_era5_rch(freq='M', dryland_only=False):
    """
    in mm
    :param freq:
    :param dryland_only:
    :return:
    """
    dates, rch = get_corrected_historical_era5_rch(None, None,
                                                   frequency=freq)
    print('got rch')
    use_rch = []
    if dryland_only:
        irrig = {}
        for y in [2015, 2020, 2021]:
            irrig[y] = get_irrigation_code(y) == -1
        use_rch.append(np.nanmean(rch[dates.year <= 2015][:, ~irrig[2015]], axis=1))
        use_rch.append(np.nanmean(rch[(dates.year > 2015) & (dates.year <= 2020)][:, ~irrig[2020]], axis=1))
        use_rch.append(np.nanmean(rch[dates.year >= 2021][:, ~irrig[2021]], axis=1))
        use_rch = np.concatenate(use_rch)
    else:
        use_rch = np.nanmean(rch, axis=(1, 2))
    return dates, use_rch


def get_indicative_times_v2(recalc=False, return_figs=False):
    save_path = processed_target_dir.joinpath('indicative_time_mapper.csv')
    if return_figs:
        assert recalc, 'must re-run full process to create figures'

    if save_path.exists() and not recalc:
        data = pd.read_csv(save_path, index_col=0)['0']
        data = data.to_dict()
        return data

    freq = 'M'
    dates, use_rch = get_mean_era5_rch(freq)
    rch = pd.DataFrame(index=dates, columns=['rch'], data=use_rch)
    hill = get_hillside_flows(None, None, freq)
    hill = pd.DataFrame(hill.sum(axis=1), columns=['hill'])
    all_data = pd.merge(rch, hill, right_index=True, left_index=True)

    mean_rch_vol = np.nanmean(use_rch * ((smt.get_no_flow(0) == 1) * smt.grid_space ** 2 / 1000).sum())
    mean_hill_vol = hill['hill'].mean()
    rch_dist_mult = mean_rch_vol / mean_hill_vol
    # normalize to 0-1
    all_data_norm = (all_data - all_data.mean()) / (all_data.max() - all_data.min())
    all_data_norm = all_data_norm - all_data_norm.min()
    print(all_data_norm.describe())

    # get the target dates
    well_data = get_single_target_data()
    targ_dates = [datetime.date(2011, 9, 21)]
    targ_dates.extend(well_data.drilldate)

    targ_dates = pd.to_datetime(targ_dates)
    targ_dates = targ_dates[targ_dates < pd.to_datetime(start)]

    targ_data = pd.DataFrame(index=targ_dates)
    nmonths = 12  # keynote choose 12 months as mutual info is largest and it makes most sense
    targ_data.loc[:, 'rch'] = get_last_nmonths(nmonths, targ_dates, all_data_norm.loc[:, 'rch'])
    targ_data.loc[:, 'hill'] = get_last_nmonths(nmonths, targ_dates, all_data_norm.loc[:, 'hill'])
    targ_data.loc[:, 'month'] = targ_data.index.month

    period_dates = pd.date_range(start, end, freq='M')
    period_data = pd.DataFrame(index=period_dates)
    period_data.loc[:, 'rch'] = get_last_nmonths(nmonths, period_dates, all_data_norm.loc[:, 'rch'])
    period_data.loc[:, 'hill'] = get_last_nmonths(nmonths, period_dates, all_data_norm.loc[:, 'hill'])
    period_data.loc[:, 'month'] = period_data.index.month

    # re-normalise the sum values
    for k in ['rch', 'hill']:
        all_vals = np.concatenate((period_data[k].values, targ_data[k].values))
        targ_data.loc[:, k] = (targ_data.loc[:, k] - all_vals.min()) / (all_vals.max() - all_vals.min())
        period_data.loc[:, k] = (period_data.loc[:, k] - all_vals.min()) / (all_vals.max() - all_vals.min())

    # find best and plot lines betwen best
    # shape = (periods, targs)
    for m in range(1, 13):
        period_months = [
            (datetime.date(2020, m, 1) + relativedelta(months=-1)).month,
            m,
            (datetime.date(2020, m, 1) + relativedelta(months=1)).month,
        ]
        targ_idx = np.in1d(targ_data.month, [m])
        period_idx = np.in1d(period_data.month, period_months)

        rch_dif = (period_data.loc[period_idx].rch.values[:, np.newaxis] - targ_data.loc[targ_idx].rch.values[
                                                                           np.newaxis, :])
        hill_dif = (period_data.loc[period_idx].hill.values[:, np.newaxis] - targ_data.loc[targ_idx].hill.values[
                                                                             np.newaxis, :])
        # preferentially shift hillslope vs recharge in proportion to to total flux
        obj = ((rch_dif * rch_dist_mult) ** 2 + (hill_dif ** 2)) ** 0.5
        idxs = np.argmin(obj, axis=0)

        targ_data.loc[targ_idx, 'new_per'] = period_data.loc[period_idx].index[idxs]
        targ_data.loc[targ_idx, 'new_rch'] = period_data.loc[period_idx].rch.values[idxs]
        targ_data.loc[targ_idx, 'new_hill'] = period_data.loc[period_idx].hill.values[idxs]

    new_keys = ['new_per', 'new_rch', 'new_hill']

    # plotting
    figs, names = [], []
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.scatter(period_data.rch, period_data.hill, c='b', label='Period data')
    ax.scatter(targ_data.rch, targ_data.hill, c='r', label='Target data')

    # plot linking lines
    link_keys = ['rch', 'hill', 'new_rch', 'new_hill']
    for rch, hill, new_rch, new_hill in targ_data.loc[:, link_keys].itertuples(False, None):
        ax.plot([rch, new_rch], [hill, new_hill], color='k', ls=':')
    ax.set_ylabel('Hillslope (normalized)')
    ax.set_xlabel('Recharge (normalised)')
    ax.set_title('All date shifts\nnote target months can only shift +- 1 month')
    ax.legend()
    fig.tight_layout()
    figs.append(fig)
    names.append('all_targ_shifts')

    for m in range(1, 13):
        period_months = [
            (datetime.date(2020, m, 1) + relativedelta(months=-1)).month,
            m,
            (datetime.date(2020, m, 1) + relativedelta(months=1)).month,
        ]
        targ_idx = np.in1d(targ_data.month, [m])
        period_idx = np.in1d(period_data.month, period_months)
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.scatter(period_data.loc[period_idx].rch, period_data.loc[period_idx].hill, c='b', label='Period data')
        for d, r, h, im in period_data.loc[period_idx].itertuples(True, None):
            ax.text(r, h, f'{d.year}-{im}', color='b')
        ax.scatter(targ_data.loc[targ_idx].rch, targ_data.loc[targ_idx].hill, c='r', label='Target data')
        for d, r, h, im in targ_data.loc[targ_idx].drop(columns=new_keys).itertuples(True, None):
            ax.text(r, h, f'{d.year}-{im}', color='r')

        # plot linking lines
        link_keys = ['rch', 'hill', 'new_rch', 'new_hill']
        for rch, hill, new_rch, new_hill in targ_data.loc[targ_idx, link_keys].itertuples(False, None):
            ax.plot([rch, new_rch], [hill, new_hill], color='k', ls=':')
        ax.set_ylabel('Hillslope (normalized)')
        ax.set_xlabel('Recharge (normalised)')
        ax.set_title(f'Target time shifts for month: {m}\nnote target months can only shift +- 1 month')
        ax.legend()
        fig.tight_layout()
        figs.append(fig)
        names.append(f'{m}_targ_shifts')

    outdata = {
        f'{old.month}-{old.year}': f'{new.month}-{new.year}' for old, new in targ_data.new_per.items()
    }
    pd.Series(outdata).to_csv(save_path)
    if return_figs:
        return outdata, (figs, names)
    return outdata


def get_indicative_times():
    well_data = get_single_target_data()
    dates, use_rch = get_mean_era5_rch()
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
        for d, r, h, im in temp_period.itertuples(False, None):
            ax.text(r, h, f'{d.year}-{im}', color='b')
        ax.scatter(temp_targ.rch, temp_targ.hill, c='r', label='target data')
        for d, r, h, im in temp_targ.itertuples(False, None):
            ax.text(r, h, f'{d.year}-{im}', color='r')
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
    # remove mean monthly data
    targs.loc[:, 'month'] = targs.index.month
    mean_targs = targs.groupby('month').mean()
    for t in targ_names:
        targs.loc[:, t] = targs.loc[:, t] - targs.month.replace(mean_targs.loc[:, t].to_dict())

    colors = get_colors(targ_names)
    all_wells = get_all_wells().loc[targ_names]
    lake_locs = get_lake_hawea_loc()
    lake_locs = smt.io.add_mxmy_to_df(lake_locs)
    lake_y = lake_locs.my.min()
    all_wells.loc[:, 'dist'] = lake_y - all_wells.loc[:, 'nztmy']
    print(all_wells.loc[:, 'dist'])

    dates, use_rch = get_mean_era5_rch(freq)
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
        targs.loc[:, f'norm_rch_{n}'] = get_last_nmonths(n, targs.index, all_data_norm.loc[:, 'rch'])
        targs.loc[:, f'norm_hill_{n}'] = get_last_nmonths(n, targs.index, all_data_norm.loc[:, 'hill'])
        targs.loc[:, f'raw_rch_{n}'] = get_last_nmonths(n, targs.index, all_data.loc[:, 'rch'])
        targs.loc[:, f'raw_hill_{n}'] = get_last_nmonths(n, targs.index, all_data.loc[:, 'hill'])
        keys.extend([f'norm_rch_{n}', f'norm_hill_{n}'])
    outdata = pd.DataFrame(index=targ_names, columns=keys)
    outdata_pp = pd.DataFrame(index=targ_names, columns=keys)
    outdata_mutreggres = pd.DataFrame(index=targ_names, columns=keys)
    for t, k in itertools.product(targ_names, keys):
        n = int(k.split('_')[-1])
        k1, k2 = f'norm_rch_{n}', f'norm_hill_{n}'
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

    # plotting
    figs, names = [], []
    for df, n in zip([outdata_pp, outdata, outdata_mutreggres], ['Pp score', 'Pearson correlation', 'Mutual info']):
        fig, axs = plt.subplots(2, sharex=True, sharey=True, figsize=(10, 8))
        fig.suptitle(n)
        for k, ax in zip(['norm_rch', 'norm_hill'], axs):
            use_keys = [f'{k}_{e}' for e in nmonths]
            for t, c in zip(targ_names, colors):
                ax.plot(nmonths, df.loc[t, use_keys], c=c, label=t, marker='.')
            ax.plot(nmonths, df.loc[:, use_keys].mean(), c='k', marker='.', label='mean')
            ax.set_title(f'Correlations to shifted to {k}')
            ax.set_ylabel(n)
            ax.set_xlabel('Cumulative months shifted back')
        fig.tight_layout()
        figs.append(fig)
        names.append(f'target_time_correlations_{n}')
    print('correlation coeff')
    print(outdata.max(axis=1))
    print('ppscore')
    print(outdata_pp.max(axis=1))
    print('mut_regress')
    print(outdata_mutreggres.max(axis=1))

    for s in ['norm', 'raw']:
        for e in [6, 12]:
            fig, axs = plt.subplots(2, sharex=False, sharey=True, figsize=(10, 8))
            fig.suptitle(f'{e} months cumulative preceding {s} data')
            for k, ax in zip(['rch', 'hill'], axs):
                for t, c in zip(targ_names, colors):
                    ax.scatter(targs.loc[:, f'{s}_{k}_{e}'], targs.loc[:, t], color=c, label=t, marker='.')
                ax.set_title(k)
                ax.scatter(targs.loc[:, f'{s}_{k}_{e}'], targs.loc[:, targ_names].mean(axis=1), color='k', label='Mean',
                           marker='.')
                ax.legend()
            fig.supxlabel('Preceding normalised value')
            fig.supylabel('Normalised target')
            fig.tight_layout()
            figs.append(fig)
            names.append(f'target_time_{s}_data_{e}_preciding_months')
    return s, (figs, names)
    # keynote chose 1 year as it is the default and also one of the highest for both mutinfo, perarosns, and ppscore


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

    dates, use_rch = get_mean_era5_rch(freq)
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


if __name__ == '__main__':
    get_indicative_times_v2(recalc=True)
    plt.show()
    predictive_power_hill_rch()
    plt.show()
