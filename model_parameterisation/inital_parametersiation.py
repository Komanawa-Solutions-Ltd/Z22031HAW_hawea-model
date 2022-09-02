"""
created matt_dumont 
on: 1/09/22
"""


# todo get initals and bounds
# todo param key in loc data or riv and well
def get_initial_riv_conductance():
    # these parameters are massively compensatory
    params = {
        'h1': (1000, (100, 10000)),  # todo roughly from Scott, discuss with Jens
        'h2': (1000, (100, 10000)),  # todo roughly from Scott, discuss with Jens
        'h3': (1000, (100, 10000)),  # todo roughly from Scott, discuss with Jens
        'c1': (500, (100, 10000))  # todo roughly from Scott, discuss with Jens
    }


def get_inital_lake_conductance():
    # todo how to manage conductance on the lake vs hk in the model... could set hk super high for the lake area
    # then just use lake conctance as the parameter
    raise NotImplementedError


def get_inital_kh():
    raise NotImplementedError


def get_inital_vka():
    # todo how does this get used in a single layer model, todo just set to 1
    raise NotImplementedError

def get_ss():
     # todo only water overheight would cause ss to be grabbed, so set to SY or set SS to super small,
     # todo set in model build
    raise NotImplementedError

def get_inital_sy():
    # todo o or set SS to super small
    raise NotImplementedError


def get_hillslope_multiplier():
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
    return params


def get_race_multiplier():
    # justification, simply allow the highly uncertain losses to move +- 10% (somewhat arbitrary)
    params = {
        'all': (1, (0.9, 1.1)),
    }
    return params
