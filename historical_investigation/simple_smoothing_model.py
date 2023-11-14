"""
created matt_dumont 
on: 2/11/23
"""
import matplotlib.pyplot as plt

from model_build.supporting_data_analysis import get_lake_heads
from optimisation.manual_optimisations.explore_lake_g40_0415 import _fit_func as simple_smoothing_model
from optimisation.manual_optimisations.explore_lake_g40_0415 import curve_min as get_simple_smoothing_params
from historical_investigation.get_historical_data import get_historical_well_heads


def fit_simple_smoothing_model(lake):
    out = get_simple_smoothing_params()
    out = out.x
    return simple_smoothing_model(lake, *out, clip=False)

def fit_lake():
    lake = get_lake_heads('1975-12-30', '2020-01-01')
    temp = fit_simple_smoothing_model(lake)
    historical_well = get_historical_well_heads('bore_315')
    fig, ax = plt.subplots()
    ax.plot(lake.index, lake.values, label='Lake Head')
    ax.plot(lake.index, temp.values, label='Simple Smoothing Model')
    ax.plot(historical_well.index, historical_well.values, label='Historical Well Head')
    difffer = 4
    ax.plot(historical_well.index, historical_well.values-difffer, label=f'Historical Well Head - {difffer}')
    ax.legend()
    plt.show()
    pass

if __name__ == '__main__':
    fit_lake()