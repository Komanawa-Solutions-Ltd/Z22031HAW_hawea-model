"""
created matt_dumont 
on: 12/09/22
"""
import netCDF4 as nc
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date
from model_build.project_model_tools import smt
from model_build.utils import get_colors, plot_1_to_1, season_mapper
from project_base import base_model_build_data_dir
from model_build.supporting_data_analysis.recharge_model import get_met_data, get_era5_land, \
    get_historical_rch_model_results, get_weekly_plus_era5_rch, get_rch, get_irrigation_code, \
    get_corrected_historical_era5_rch


def examine_precip():
    met = get_met_data(None, None)
    met.rename(columns={'Rainfall': 'precipitation'}, inplace=True)
    era5 = get_era5_land(correct=False)
    era5_cor = get_era5_land(correct=True)
    expected_dates = sorted(set(met.index).intersection(era5.index))
    met = met.loc[expected_dates]
    era5 = era5.loc[expected_dates]
    era5_cor = era5_cor.loc[expected_dates]
    weekly_era5 = era5.resample('W').mean()
    weekly_era5_cor = era5_cor.resample('W').mean()
    weekly_met = met.resample('W').mean()

    for df in [era5, era5_cor, met]:
        df.loc[:, 'rain_day'] = df.precipitation > 0
        df.loc[:, 'month'] = df.index.month
        df.loc[:, 'year'] = df.index.year
        df.loc[:, 'season'] = [season_mapper[m] for m in df.month]

    # number of rain days per month
    monthly_era = era5.groupby(['month', 'year']).agg(
        {'precipitation': 'sum', 'rain_day': 'sum', 'season': 'first'}).reset_index()
    monthly_era_cor = era5_cor.groupby(['month', 'year']).agg(
        {'precipitation': 'sum', 'rain_day': 'sum', 'season': 'first'}).reset_index()
    monthly_met = met.groupby(['month', 'year']).agg(
        {'precipitation': 'sum', 'rain_day': 'sum', 'season': 'first'}).reset_index()
    fig, ax = plt.subplots()
    ax.set_title('number of rain days')
    ax.boxplot([monthly_era.rain_day, monthly_era_cor.rain_day, monthly_met.rain_day],
               labels=['era5', 'era5_cor', 'met'])

    # precip per rain days
    fig, ax = plt.subplots()
    ax.set_title('precip on rain days')
    ax.boxplot([era5.loc[era5.rain_day, 'precipitation'],
                era5_cor.loc[era5_cor.rain_day, 'precipitation'],
                met.loc[met.rain_day, 'precipitation']],
               labels=['era5', 'era5_cor', 'met'])

    # rain by month/season
    fig, (ax1, ax2) = plt.subplots(ncols=2)
    ax1.set_title('rain per month')
    colors = get_colors(range(12))
    for c, m in zip(colors, range(1, 13)):
        ax1.scatter(monthly_met.loc[monthly_met.month == m, 'precipitation'],
                    monthly_era.loc[monthly_era.month == m, 'precipitation'], color=c, label=m)
    plot_1_to_1(ax1, ls=':', c='k')
    ax1.legend()
    ax1.set_ylabel('era5')
    ax1.set_xlabel('historical')

    ax2.set_title('rain per month')
    colors = get_colors(range(12))
    for c, m in zip(colors, range(1, 13)):
        ax2.scatter(monthly_met.loc[monthly_met.month == m, 'precipitation'],
                    monthly_era_cor.loc[monthly_era.month == m, 'precipitation'], color=c, label=m)
    plot_1_to_1(ax2, ls=':', c='k')
    ax2.legend()
    ax2.set_ylabel('era5_cor')
    ax2.set_xlabel('historical')

    fig, (ax1, ax2) = plt.subplots(ncols=2)
    ax1.set_title('rain per season')
    colors = get_colors(np.unique(list(season_mapper.values())))
    for c, s in zip(colors, np.unique(list(season_mapper.values()))):
        ax1.scatter(monthly_met.loc[monthly_met.season == s, 'precipitation'],
                    monthly_era.loc[monthly_era.season == s, 'precipitation'], color=c, label=s)
    plot_1_to_1(ax1, ls=':', c='k')
    ax1.legend()
    ax1.set_ylabel('era5')
    ax1.set_xlabel('historical')

    ax2.set_title('rain per season')
    colors = get_colors(np.unique(list(season_mapper.values())))
    for c, s in zip(colors, np.unique(list(season_mapper.values()))):
        ax2.scatter(monthly_met.loc[monthly_met.season == s, 'precipitation'],
                    monthly_era_cor.loc[monthly_era.season == s, 'precipitation'], color=c, label=s)
    plot_1_to_1(ax2, ls=':', c='k')
    ax2.legend()
    ax2.set_ylabel('era5_cor')
    ax2.set_xlabel('historical')
    # rain weekly
    fig, (ax1, ax2) = plt.subplots(ncols=2)
    ax1.set_title('rain per week')
    ax1.scatter(weekly_met.loc[:, 'precipitation'],
                weekly_era5.loc[:, 'precipitation'], )
    plot_1_to_1(ax1, ls=':', c='k')
    ax1.legend()
    ax1.set_ylabel('era5')
    ax1.set_xlabel('historical')

    ax2.set_title('rain per week')
    ax2.scatter(weekly_met.loc[:, 'precipitation'], weekly_era5_cor.loc[:, 'precipitation'])
    plot_1_to_1(ax2, ls=':', c='k')
    ax2.legend()
    ax2.set_ylabel('era5_cor')
    ax2.set_xlabel('historical')

    fig, (ax1, ax2) = plt.subplots(ncols=2)
    ax1.set_title('rain per season')
    colors = get_colors(np.unique(list(season_mapper.values())))
    for c, s in zip(colors, np.unique(list(season_mapper.values()))):
        ax1.scatter(monthly_met.loc[monthly_met.season == s, 'precipitation'],
                    monthly_era.loc[monthly_era.season == s, 'precipitation'], color=c, label=s)
    plot_1_to_1(ax1, ls=':', c='k')
    ax1.legend()
    ax1.set_ylabel('era5')
    ax1.set_xlabel('historical')

    ax2.set_title('rain per season')
    colors = get_colors(np.unique(list(season_mapper.values())))
    for c, s in zip(colors, np.unique(list(season_mapper.values()))):
        ax2.scatter(monthly_met.loc[monthly_met.season == s, 'precipitation'],
                    monthly_era_cor.loc[monthly_era.season == s, 'precipitation'], color=c, label=s)
    plot_1_to_1(ax2, ls=':', c='k')
    ax2.legend()
    ax2.set_ylabel('era5_cor')
    ax2.set_xlabel('historical')

    plt.show()


def examine_pet():
    met = get_met_data(None, None)
    met.rename(columns={'PET': 'potential_et'}, inplace=True)
    era5 = get_era5_land(correct=False)
    era5_cor = get_era5_land(correct=True)
    expected_dates = sorted(set(met.index).intersection(era5.index))
    met = met.loc[expected_dates]
    era5 = era5.loc[expected_dates]
    era5_cor = era5_cor.loc[expected_dates]

    for df in [era5, era5_cor, met]:
        df.loc[:, 'month'] = df.index.month
        df.loc[:, 'year'] = df.index.year
        df.loc[:, 'season'] = [season_mapper[m] for m in df.month]

    monthly_era = era5.groupby(['month', 'year']).agg(
        {'potential_et': 'sum', 'season': 'first'}).reset_index()
    monthly_era_cor = era5_cor.groupby(['month', 'year']).agg(
        {'potential_et': 'sum', 'season': 'first'}).reset_index()
    monthly_met = met.groupby(['month', 'year']).agg(
        {'potential_et': 'sum', 'season': 'first'}).reset_index()

    # rain by month/season
    fig, (ax1, ax2) = plt.subplots(ncols=2)
    ax1.set_title('pet per month')
    colors = get_colors(range(12))
    for c, m in zip(colors, range(1, 13)):
        ax1.scatter(monthly_met.loc[monthly_met.month == m, 'potential_et'],
                    monthly_era.loc[monthly_era.month == m, 'potential_et'], color=c, label=m)
    plot_1_to_1(ax1, ls=':', c='k')
    ax1.legend()
    ax1.set_ylabel('era5')
    ax1.set_xlabel('historical')

    ax2.set_title('pet per month')
    colors = get_colors(range(12))
    for c, m in zip(colors, range(1, 13)):
        ax2.scatter(monthly_met.loc[monthly_met.month == m, 'potential_et'],
                    monthly_era_cor.loc[monthly_era.month == m, 'potential_et'], color=c, label=m)
    plot_1_to_1(ax2, ls=':', c='k')
    ax2.legend()
    ax2.set_ylabel('era5_cor')
    ax2.set_xlabel('historical')

    fig, (ax1, ax2) = plt.subplots(ncols=2)
    ax1.set_title('pet per season')
    colors = get_colors(np.unique(list(season_mapper.values())))
    for c, s in zip(colors, np.unique(list(season_mapper.values()))):
        ax1.scatter(monthly_met.loc[monthly_met.season == s, 'potential_et'],
                    monthly_era.loc[monthly_era.season == s, 'potential_et'], color=c, label=s)
    plot_1_to_1(ax1, ls=':', c='k')
    ax1.legend()
    ax1.set_ylabel('era5')
    ax1.set_xlabel('historical')

    ax2.set_title('pet per season')
    colors = get_colors(np.unique(list(season_mapper.values())))
    for c, s in zip(colors, np.unique(list(season_mapper.values()))):
        ax2.scatter(monthly_met.loc[monthly_met.season == s, 'potential_et'],
                    monthly_era_cor.loc[monthly_era.season == s, 'potential_et'], color=c, label=s)
    plot_1_to_1(ax2, ls=':', c='k')
    ax2.legend()
    ax2.set_ylabel('era5_cor')
    ax2.set_xlabel('historical')

    plt.show()


def comp_plot_era5_v_measured(corrected_pet=False):
    met = get_met_data(None, None)
    era5 = get_era5_land(correct=corrected_pet)
    # EC can you make some plots and summary statistics of the difference between the ERA5 land data and the
    # historical (met) data where these data overlap

    # in met, two columns rainfall and PET, with index as datetime
    # in era5 three columns, potential_et (PET), precipitation (rainfall) & reference_et, datetime as index
    # changing the name of the era5 index so it is the same as met index
    era5.index.names = ['datetime']

    # need to first subset for when the data overlap
    # using an inner join
    merged_df = pd.merge(era5, met, on='datetime', how='inner')

    # create summary statistics for each dataset
    # met rainfall summary stats
    met_rainfall = merged_df['Rainfall']
    met_rainfall_summary = met_rainfall.describe()

    # met PET summary stats
    met_pet = merged_df['PET']
    met_pet_summary = met_pet.describe()

    # era5 rainfall summary stats
    era5_rainfall = merged_df['precipitation']
    era5_rainfall_summary = era5_rainfall.describe()

    # era5 PET summary stats
    era5_pet = merged_df['potential_et']
    era5_pet_summary = era5_pet.describe()

    # comparing weekly mean
    # attempting to get weekly mean
    merged_df = merged_df.reset_index()
    weekly_pet_mean = merged_df[['datetime', 'potential_et', 'PET']].resample('W-Sun', label='right', closed='right',
                                                                              on='datetime').mean()
    weekly_precip_sum = merged_df[['datetime', 'precipitation', 'Rainfall']].resample('W-Sun', label='right',
                                                                                      closed='right',
                                                                                      on='datetime').mean()

    # comparing monthly mean
    # attempting to get monthly mean
    monthly_pet_mean = merged_df[['datetime', 'potential_et', 'PET']].resample('M', label='right', closed='right',
                                                                               on='datetime').mean()
    monthly_precip_sum = merged_df[['datetime', 'precipitation', 'Rainfall']].resample('M', label='right',
                                                                                       closed='right',
                                                                                       on='datetime').mean()
    annual_pet_mean = merged_df[['datetime', 'potential_et', 'PET']].resample('A', label='right', closed='right',
                                                                              on='datetime').mean()
    annual_precip_sum = merged_df[['datetime', 'precipitation', 'Rainfall']].resample('A', label='right',
                                                                                      closed='right',
                                                                                      on='datetime').mean()

    daily_pet = merged_df[['potential_et', 'PET']]
    daily_precip = merged_df[['precipitation', 'Rainfall']]

    df_keys = ['daily_pet', 'daily_precip', 'monthly_pet_mean', 'monthly_precip_sum', 'weekly_pet_mean',
               'weekly_precip_sum', 'annual_pet_mean', 'annual_precip_sum']
    for k in df_keys:
        df = eval(k)
        fig, ax = plt.subplots()
        ax.set_title(k)
        cols = df.columns
        assert len(cols) == 2
        ax.scatter(df[cols[0]], df[cols[1]])
        limits = np.nanmax(df.values), np.nanmin(df.values)
        plot_1_to_1(ax, c='k', ls=':')
        ax.set_xlabel('era5')
        ax.set_ylabel('historical')

    plt.show()
    run_ecs_stuff = False
    if run_ecs_stuff:
        # plot the two datasets comparing precip (over time)
        merged_df.plot(x='datetime', y=['precipitation', 'Rainfall'], kind='line')
        plt.ylabel('Precipitation (mm)')

        # plot the two datasets comparing PET (over time)
        merged_df.plot(x='datetime', y=['potential_et', 'PET'], kind='line')
        plt.ylabel('PET ??')

        #  plots for the same above but with monthly means
        monthly_precip_sum.plot(use_index=True, y=['precipitation', 'Rainfall'], kind='line')
        plt.ylabel('Precipitation (mm)')

        monthly_pet_mean.plot(use_index=True, y=['potential_et', 'PET'], kind='line')
        plt.ylabel('PET ??')

        # comparison of the diffs e.g era5 on y met on x
        # daily precip diffs
        merged_df.plot(x='Rainfall', y='precipitation', kind='scatter')
        plt.xlabel('Met precip data (mm)')
        plt.ylabel('Era5 precip data (mm)')
        # weekly precip diffs
        weekly_precip_sum.plot(x='Rainfall', y='precipitation', kind='scatter')
        plt.xlabel('Met precip data (mm)')
        plt.ylabel('Era5 precip data (mm)')
        # monthly precip diffs
        monthly_precip_sum.plot(x='Rainfall', y='precipitation', kind='scatter')
        plt.xlabel('Met precip data (mm)')
        plt.ylabel('Era5 precip data (mm)')

        # daily PET diffs
        merged_df.plot(x='PET', y='potential_et', kind='scatter')
        plt.xlabel('Met PET data (?)')
        plt.ylabel('Era5 PET data (?)')
        # weekly PET diffs
        weekly_pet_mean.plot(x='PET', y='potential_et', kind='scatter')
        plt.xlabel('Met PET data (?)')
        plt.ylabel('Era5 PET data (?)')
        # monthly PET diffs
        monthly_pet_mean.plot(x='PET', y='potential_et', kind='scatter')
        plt.xlabel('Met PET data (?)')
        plt.ylabel('Era5 PET data (?)')
        plt.show()

        raise NotImplementedError


def compare_era5_hist_rch(show=False, freq='W'):
    era5_dates_cor, era5_rch_cor = get_corrected_historical_era5_rch(start_date=date(2010, 1, 1),
                                                                     end_date=date(2022, 1, 1),
                                                                     limited_irrigation=False,
                                                                     frequency=freq)
    historical_dates, historical_rch = get_rch(None, None, frequency=freq, limited_irrigation=False)
    era5_dates, era5_rch = get_weekly_plus_era5_rch(start_date=date(2010, 1, 1),
                                                    end_date=date(2022, 1, 1), limited_irrigation=False,
                                                    frequency=freq)
    era5_dates = pd.to_datetime(era5_dates)
    historical_dates = pd.to_datetime(historical_dates)
    era5_cor_dates = pd.to_datetime(era5_dates_cor)
    expected_dates = sorted(set(era5_dates).intersection(historical_dates).intersection(era5_cor_dates))
    era5_idx = [e in expected_dates for e in era5_dates]
    era5_cor_idx = [e in expected_dates for e in era5_cor_dates]
    era5_rch = era5_rch[era5_idx]
    era5_rch_cor = era5_rch_cor[era5_cor_idx]
    hist_idx = [e in expected_dates for e in historical_dates]
    historical_rch = historical_rch[hist_idx]
    assert ((historical_dates[hist_idx] == era5_dates[era5_idx])
           & (era5_dates[era5_idx] == era5_cor_dates[era5_cor_idx])).all()

    ibound = smt.get_no_flow(0)
    zones = {'all': ibound == 1}
    for y in [2015]:
        t = get_irrigation_code(y, recalc=True)
        zones[f'irrigated_{y}'] = (t >= 0) & (ibound == 1)
        zones[f'not_irrigated_{y}'] = (t < 0) & (ibound == 1)

    for k, z in zones.items():
        era5 = np.nanmean(era5_rch[:, z], axis=1)
        era5_cor = np.nanmean(era5_rch_cor[:, z], axis=1)
        hist = np.nanmean(historical_rch[:, z], axis=1)
        temp = np.concatenate((hist, era5))
        lims = (np.nanmin(temp), np.nanmax(temp))
        fig, (ax1, ax2) = plt.subplots(ncols=2)
        ax1.set_title(k + f' freq:{freq}')
        ax1.set_ylabel('era5')
        ax1.set_xlabel('historical')
        ax1.scatter(hist, era5)
        plot_1_to_1(ax1)

        ax2.set_title(k + f' freq:{freq}')
        ax2.set_ylabel('era5 corrected')
        ax2.set_xlabel('historical')
        ax2.scatter(hist, era5_cor)
        plot_1_to_1(ax2)

        if freq != 'A':
            seasons = np.array([season_mapper[e.month] for e in expected_dates])
            colors = get_colors(np.unique(seasons))
            fig, (ax1, ax2) = plt.subplots(ncols=2)
            for c, s in zip(colors, np.unique(seasons)):
                idx = seasons == s
                era5 = np.nanmean(era5_rch[:, z], axis=1)[idx]
                era5_cor = np.nanmean(era5_rch_cor[:, z], axis=1)[idx]
                hist = np.nanmean(historical_rch[:, z], axis=1)[idx]
                ax1.scatter(hist, era5, color=c, label=s)
                ax2.scatter(hist, era5_cor, color=c, label=s)
            ax1.set_title(k + f' freq:{freq}')
            ax1.set_ylabel('era5')
            ax1.set_xlabel('historical')
            ax1.legend()
            plot_1_to_1(ax1, ls=':', c='k')
            ax2.set_title(k + f' freq:{freq}')
            ax2.set_ylabel('era5 corrected')
            ax2.set_xlabel('historical')
            ax2.legend()
            plot_1_to_1(ax2, ls=':', c='k')
            months = np.array([e.month for e in expected_dates])
            colors = get_colors(np.unique(months))
            fig, (ax1, ax2) = plt.subplots(ncols=2)
            for c, s in zip(colors, np.unique(months)):
                idx = months == s
                era5 = np.nanmean(era5_rch[:, z], axis=1)[idx]
                era5_cor = np.nanmean(era5_rch_cor[:, z], axis=1)[idx]
                hist = np.nanmean(historical_rch[:, z], axis=1)[idx]
                ax1.scatter(hist, era5, color=c, label=s)
                ax2.scatter(hist, era5_cor, color=c, label=s)
            ax1.set_title(k + f' freq:{freq}')
            ax1.set_ylabel('era5')
            ax1.set_xlabel('historical')
            ax1.legend()
            plot_1_to_1(ax1, ls=':', c='k')
            ax2.set_title(k + f' freq:{freq}')
            ax2.set_ylabel('era5 corrected')
            ax2.set_xlabel('historical')
            ax2.legend()
            plot_1_to_1(ax2, ls=':', c='k')

    fig, (ax1, ax2, ax3) = plt.subplots(ncols=3)
    smt.plot.plt_matrix(np.nanmean(era5_rch, axis=0) * 365, base_map=True, title='era5_rch', ax=ax1, vmin=150,
                        vmax=500)
    smt.plot.plt_matrix(np.nanmean(era5_rch_cor, axis=0) * 365, base_map=True, title='era5_rch corrected', ax=ax3, vmin=150,
                        vmax=500)
    smt.plot.plt_matrix(np.nanmean(historical_rch, axis=0) * 365, base_map=True, title='hist_rch', ax=ax2, vmin=150,
                        vmax=500)
    if show:
        plt.show()


if __name__ == '__main__':
    # era5 = get_era5_land()
    # dates, rch = get_weekly_plus_era5_rch(None, None)
    compare_era5_hist_rch(freq='M')
    plt.show()
    compare_era5_hist_rch()
    compare_era5_hist_rch(freq='A')
    examine_precip()
    examine_pet()
    comp_plot_era5_v_measured(corrected_pet=True)
