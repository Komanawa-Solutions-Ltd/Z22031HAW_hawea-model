"""
created matt_dumont 
on: 1/09/22
"""
from model_parameterisation.pilot_points import get_pilot_point_locations
import numpy as np


# keynote these set initials and bounds
# keynote param key in loc data or riv and well


def get_initial_riv_conductance(return_just_start=False):
    # these parameters are massively compensatory
    # keynote parameters are roughly from scott's model
    params = {
        'h1': (1000, (100, 10000)),  # todo review
        'h2': (1000, (100, 10000)),  # todo review
        'h3': (1000, (100, 10000)),  # todo review
        'c1': (500, (100, 10000))  # todo review
    }
    if return_just_start:
        for k, v in params.items():
            params[k] = v[0]
    return params


def get_inital_lake_conductance(return_just_start=False):
    # keynote lake sy & model ss and lake kh are set to be so small and large,
    #  respectively, so as not to impact the model.
    #  lake fluxes are entirely dependent on the GHB conductance
    params = {'all': (1e4, (1e-2, 1e8))}  # todo review
    if return_just_start:
        for k, v in params.items():
            params[k] = v[0]
    return params


def get_inital_kh(return_just_start=False):
    # keynote one value for the whole model
    # keynote use log values
    start_val = (10, (0.01, 600))  # todo review
    # for reference scott's model ha min = 0.09, max = 300, median = 14
    if return_just_start:
        start_val = start_val[0]
    pps = get_pilot_point_locations()
    pps = pps.loc[~np.in1d(pps.group, ['sandyhill', 'mangawera'])]
    kh_data = {
        'sandyhill': start_val,
        'mangawera': start_val,
    }

    for i in pps.index:
        kh_data[i] = start_val

    return kh_data


def get_inital_sy(return_just_start=False):
    # keynote do not use log values
    # keynote one value for the whole model
    start_val = (0.02, 0.001, 0.3)  # todo review
    if return_just_start:
        start_val = start_val[0]
    pps = get_pilot_point_locations()
    pps = pps.loc[~np.in1d(pps.group, ['sandyhill', 'mangawera'])]
    sy_data = {
        'sandyhill': start_val,
        'mangawera': start_val,
    }

    for i in pps.index:
        sy_data[i] = start_val

    return sy_data


def get_hillslope_multiplier(return_just_start=False):
    # by inflow zones
    # rational... there is a strong N-S precip gradient, so southeast may have a very different signature
    # maungawera separate as its a distinct area and hill slope recharge is more important to the water budget
    # allow paramters to move +- 10% (somewhat arbitrary)
    params = {
        # k: (initial, (low, high),
        'south_east': (1, (0.9, 1.1)),
        'main': (1, (0.9, 1.1)),
        'maungawera': (1, (0.9, 1.1)),

    }
    if return_just_start:
        for k, v in params.items():
            params[k] = v[0]
    return params


def get_race_multiplier(return_just_start=False):
    # justification, simply allow the highly uncertain losses to move +- 10% (somewhat arbitrary)
    params = {
        'all': (1, (0.9, 1.1)),
    }
    if return_just_start:
        for k, v in params.items():
            params[k] = v[0]
    return params


if __name__ == '__main__':
    get_inital_kh()
