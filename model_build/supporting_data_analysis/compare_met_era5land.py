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

from project_base import base_model_build_data_dir
from model_build.supporting_data_analysis.recharge_model import get_met_data, get_era5_land, \
    get_historical_rch_model_results, get_weekly_plus_era5_rch, get_rch, get_irrigation_code


def comp_plot_era5_v_measured(corrected_pet=False):
    met = get_met_data(None, None)
    era5 = get_era5_land(correct_pet=corrected_pet)
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
    for k in df_keys: # todo look at precip by month/season!
        df = eval(k)
        fig, ax = plt.subplots()
        ax.set_title(k)
        cols = df.columns
        assert len(cols) == 2
        ax.scatter(df[cols[0]], df[cols[1]])
        limits = np.nanmax(df.values), np.nanmin(df.values)
        ax.plot(limits, limits, c='k', ls=':')
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


def compare_era5_hist_rch():  # todo review with corrected pet!
    historical_dates, historical_rch = get_rch(None, None, frequency='W', limited_irrigation=False)
    era5_dates, era5_rch = get_weekly_plus_era5_rch(start_date=date(2010, 1, 1),
                                                    end_date=date(2022, 1, 1), limited_irrigation=False)
    era5_dates = pd.to_datetime(era5_dates)
    historical_dates = pd.to_datetime(historical_dates)
    expected_dates = set(era5_dates).intersection(historical_dates)
    era5_idx = [e in expected_dates for e in era5_dates]
    era5_rch = era5_rch[era5_idx]
    hist_idx = [e in expected_dates for e in historical_dates]
    historical_rch = historical_rch[hist_idx]
    assert (historical_dates[hist_idx] == era5_dates[era5_idx]).all()

    ibound = smt.get_no_flow(0)
    zones = {'all': ibound == 1}
    for y in [2015, 2020, 2021]:
        t = get_irrigation_code(y, recalc=True)
        zones[f'irrigated_{y}'] = (t >= 0) & (ibound == 1)
        zones[f'not_irrigated_{y}'] = (t < 0) & (ibound == 1)

    comp_data = {}
    for k, z in zones.items():
        era5 = np.nanmean(era5_rch[:, z], axis=1)
        hist = np.nanmean(historical_rch[:, z], axis=1)
        comp_data[k] = (hist, era5)
        temp = np.concatenate((hist, era5))
        lims = (np.nanmin(temp), np.nanmax(temp))
        fig, ax = plt.subplots()
        ax.set_title(k)
        ax.set_ylabel('era5')
        ax.set_xlabel('historical')
        ax.scatter(hist, era5)
        ax.plot(lims, lims, c='k', ls=':')
    plt.show()


if __name__ == '__main__':  # todo probably need to correct precipitation as well, weekly or monthly to correct???
    comp_plot_era5_v_measured(corrected_pet=True)
    compare_era5_hist_rch()
