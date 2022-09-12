"""
created matt_dumont 
on: 12/09/22
"""
import netCDF4 as nc
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from project_base import base_model_build_data_dir
from model_build.supporting_data_analysis.recharge_model import get_met_data, get_era5_land

def comp_plot_era5_v_measured():
    met = get_met_data(None, None)
    era5 = get_era5_land()
    # todo EC can you make some plots and summary statistics of the difference between the ERA5 land data and the
    # historical (met) data where these data overlap
    raise NotImplementedError

if __name__ == '__main__':
    pass
