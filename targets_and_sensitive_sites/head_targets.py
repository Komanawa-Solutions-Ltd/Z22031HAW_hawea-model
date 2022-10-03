"""
created matt_dumont 
on: 15/08/22
"""
import warnings
import datetime

import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd
from model_build.supporting_data_analysis import get_all_wells
from model_build.project_model_tools import smt
from model_build.utils import select_resample
from model_build.zones import get_param_zones
from project_base import processed_target_dir, base_target_dir
from model_build.utils import get_colors
from model_build.supporting_data_analysis.recharge_model import get_corrected_historical_era5_rch, get_irrigation_code
from model_build.supporting_data_analysis import get_hillside_flows
from optimisation.optimisation_period import start, end


# todo it may be worth comparing recharge and lake levels... at a water year level to see how to apply
# targets that occur outside of period.

def get_indicative_times():
    well_data = _get_single_target_data()
    dates, rch = get_corrected_historical_era5_rch(None, None,
                                                   frequency='M')  # todo separate irrigated from dryland? yes
    print('got rch')
    use_rch = []
    irrig = {}
    for y in [2015, 2020, 2021]:
        irrig[y] = get_irrigation_code(y) == -1
    use_rch.append(np.nanmean(rch[dates.year <= 2015][:, ~irrig[2015]], axis=1))
    use_rch.append(np.nanmean(rch[(dates.year > 2015) & (dates.year <= 2020)][:, ~irrig[2020]], axis=1))
    use_rch.append(np.nanmean(rch[dates.year >= 2021][:, ~irrig[2021]], axis=1))
    use_rch = np.concatenate(use_rch)
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
    # todo monthly mean target?
    # todo compare last n months of recharge...
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

    # todo stdev on the lake wave... how much does that vary monthly
    # todo look at relationship between rch, hillslope, time delta against lakewave for high frequency data
    #  use this to determine minimum difference (e.g. weight deltas by correlation).
    # todo look at the ideal correlation between head, rch, hillslope (e.g. 1 month, 2 to 6 month mean)


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


# todo wait 6 months to 1 year of data before fitting targets, 6 months should be suitable

if __name__ == '__main__':
    get_indicative_times()
    plot_head_targets(how='incl')
    smt.plot.show()
    plot_head_targets()
    export_incl_head_target_locs()
