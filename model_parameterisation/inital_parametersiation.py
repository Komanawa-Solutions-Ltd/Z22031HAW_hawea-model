"""
created matt_dumont 
on: 1/09/22
"""
from model_parameterisation.pilot_points import get_pilot_point_locations
import numpy as np


# keynote these set initials and bounds
# keynote param key in loc data or riv and well

def get_initial_rch_mult(return_just_start=False):
    # keynote do not use log values
    # keynote one value for the whole model
    start_val = (1, (0.5, 1.2))
    if return_just_start:
        start_val = start_val[0]

    rch_mult = {'all': start_val}

    return rch_mult


def get_initial_riv_conductance(return_just_start=False):
    # these parameters are massively compensatory
    # keynote parameters are roughly from scott's model
    params = {
        'h1': (1000, (100, 10000)),
        'h2': (1000, (100, 10000)),
        'h3': (1000, (100, 10000)),
        'c1': (1000, (100, 10000)),
        'gview': (100, (50, 5000)),
        'john': (100, (50, 5000)),
    }
    if return_just_start:
        for k, v in params.items():
            params[k] = v[0]
    return params


def get_inital_kh(return_just_start=False):
    # keynote one value for the whole model based on the 10**mean(log10(scotts parameters))
    # keynote the tidal reference seems to suggest a kh of 32-43 (assuming 30-40m thickness and a T of 1300)
    # keynote use log values
    start_val = (300, (0.01, 1000))
    ter_start_val = (50, (0.01, 1000))
    lake_val = (3000, (0.001, 4000))
    moraine_l0 = (300, (0.001, 1000))
    moraine_l1 = (1e-4, (1e-7, 1))

    # for reference scott's model ha min = 0.09, max = 300, median = 14
    pps = get_pilot_point_locations()
    kh_data = {
        'lake': lake_val,
        'mor_l0': moraine_l0,  # keynote high conductivy upper area
        'mor_l1': moraine_l1,  # keynote low conductivity moraine
    }

    for i in pps.index:
        if 'ter' in i:
            kh_data[i] = ter_start_val
        else:
            kh_data[i] = start_val
    if return_just_start:
        kh_data = {k: v[0] for k, v in kh_data.items()}

    return kh_data


def get_inital_sy(return_just_start=False):
    # keynote do not use log values
    # keynote the tidal reference seems to suggest a sy of 0.012
    # keynote one value for the whole model
    start_val = (0.01, (0.0001, 0.3))
    ter_start_val = (0.01, (0.0001, 0.3))
    sy_mor_l1 = (0.001, (0.0001, 0.3))
    ss_start = (1e-4, (1e-6, 1e-3))

    pps = get_pilot_point_locations()
    sy_data = {
        'sy_mor_l0': start_val,
        'sy_mor_l1': sy_mor_l1,
        'ss_rest': ss_start,
        'ss_mor_l0': ss_start,
        'ss_mor_l1': ss_start,
    }

    for i in pps.index:
        if 'ter' in i:
            sy_data[i] = ter_start_val
        else:
            sy_data[i] = start_val
    if return_just_start:
        sy_data = {k: v[0] for k, v in sy_data.items()}

    return sy_data


def get_hillslope_multiplier(return_just_start=False):
    # by inflow zones
    # rational... there is a strong N-S precip gradient, so southeast may have a very different signature
    # maungawera separate as its a distinct area and hill slope recharge is more important to the water budget
    # allow paramters to move +- 10% (somewhat arbitrary)
    params = {
        # k: (initial, (low, high),
        'se': (1, (0.8, 1.2)),
        'main': (1, (0.8, 1.2)),
        'mang': (1, (0.8, 1.2)),

    }
    if return_just_start:
        for k, v in params.items():
            params[k] = v[0]
    return params


def get_race_multiplier(return_just_start=False):
    # justification, simply allow the highly uncertain losses to move +- 10% (somewhat arbitrary)
    params = {
        'all': (1, (0.8, 1.2)),
    }
    if return_just_start:
        for k, v in params.items():
            params[k] = v[0]
    return params


if __name__ == '__main__':
    get_inital_kh()
