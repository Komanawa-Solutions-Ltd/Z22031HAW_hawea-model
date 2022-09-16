"""
created matt_dumont 
on: 12/09/22
"""
import netCDF4 as nc
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime


from project_base import base_model_build_data_dir
from model_build.supporting_data_analysis.recharge_model import get_met_data, get_era5_land, get_historical_rch_model_results

def comp_plot_era5_v_measured():
    met = get_met_data(None, None)
    era5 = get_era5_land()
    # EC can you make some plots and summary statistics of the difference between the ERA5 land data and the
    # historical (met) data where these data overlap

    # in met, two columns rainfall and PET, with index as datetime
    # in era5 three columns, potential_et (PET), precipitation (rainfall) & reference_et, datetime as index
    # changing the name of the era5 index so it is the same as met index
    era5.index.names = ['datetime']
    # todo change the units of era5 PET

    # todo change the names of the columns to make it easier to identify?


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

    #era5 PET summary stats
    era5_pet = merged_df['potential_et']
    era5_pet_summary = era5_pet.describe()

    # comparing weekly mean
    # attempting to get weekly mean
    merged_df = merged_df.reset_index()
    weekly_pet_mean = merged_df[['datetime', 'potential_et', 'PET']].resample('W-Sun', label='right', closed='right', on='datetime').mean()
    weekly_precip_sum = merged_df[['datetime', 'precipitation', 'Rainfall']].resample('W-Sun', label='right', closed='right', on='datetime').sum()

    # comparing monthly mean
    # attempting to get monthly mean
    monthly_pet_mean = merged_df[['datetime', 'potential_et', 'PET']].resample('M', label='right', closed='right', on='datetime').mean()
    monthly_precip_sum = merged_df[['datetime', 'precipitation', 'Rainfall']].resample('M', label='right', closed='right', on='datetime').sum()



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

    # todo one to one line


    raise NotImplementedError

def compare_era5_hist_rch():  # todo
    raise NotImplementedError

if __name__ == '__main__':
    comp_plot_era5_v_measured()
