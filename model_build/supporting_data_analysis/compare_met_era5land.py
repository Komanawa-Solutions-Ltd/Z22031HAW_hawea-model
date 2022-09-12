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
from model_build.supporting_data_analysis.recharge_model import get_met_data, get_era5_land

def comp_plot_era5_v_measured():
    met = get_met_data(None, None)
    era5 = get_era5_land()
    # todo EC can you make some plots and summary statistics of the difference between the ERA5 land data and the
    # todo historical (met) data where these data overlap

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

    #era5 PET summary stats
    era5_pet = merged_df['potential_et']
    era5_pet_summary = era5_pet.describe()

    # comparing weekly mean
    # attempting to get weekly mean
    merged_df = merged_df.reset_index()
    weekly_data = merged_df.resample('W-Sun', label='right', closed='right', on='datetime').mean()


    # comparing monthly mean
    # attempting to get monthly mean
    monthly_data = merged_df.resample('M', label='right', closed='right', on='datetime').mean()



    # todo plot the two datasets comparing precip (over time)

    # todo plot the two datasets comparing PET (over time)

    # todo plots for the same above but with monthly means?

    # todo ask Matt what else he wants done



    raise NotImplementedError


if __name__ == '__main__':
    comp_plot_era5_v_measured()
