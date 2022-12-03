"""
created matt_dumont 
on: 28/11/22
"""
import itertools

from optimisation.a_build_run_optimisation_version import branch
from optimisation.manual_optimisations.manual_optimisation import run_manal_opt

import inspect


def print_myself():
    print(inspect.stack()[1][3])


def sy_test():
    print_myself()
    opt_name = 'sy_test'
    new_params = [{
        'sy_h_flat4': v,
        'sy_h_flat7': v,
        'sy_h_flat8': v,
    }
        for v in [0.0001, 0.0005, .001, 0.1, 0.2]]

    opt_name = f'{branch}_{opt_name}'
    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


def lake_kh_test():
    print_myself()
    opt_name = 'lake_test'
    new_params = [{
        'kh_lake': v

    }
        for v in [0.01, 0.1, 0.5, 1, 3, 5, 10, 50, 100]]

    opt_name = f'{branch}_{opt_name}'
    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


def lake_and_sy_test():
    print_myself()
    opt_name = 'lake_and_sy_test'
    new_params = [{
        'sy_h_flat4': v,
        'sy_h_flat7': v,
        'sy_h_flat8': v,
        'kh_lake': l
    }
        for l, v in itertools.product([0.1, 0.5, 1, 3, 5, 10, 50, 100],
                                      [0.00005, 0.0001, 0.0005, .001, 0.005, 0.01, 0.05])]

    opt_name = f'{branch}_{opt_name}'
    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


def north_kh():
    print_myself()
    opt_name = 'north_kh'
    new_params = [{
        'kh_h_flat4': l,  # lower
        'kh_h_flat3': l,
        'kh_h_flat6': l,

        'kh_h_flat7': r,  # raise
        'kh_h_flat8': r,  # raise

    }
        for l, r in itertools.product([50, 100, 200, 300],
                                      [300, 400, 500, 600]

                                      )]

    opt_name = f'{branch}_{opt_name}'
    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


def north_kh_lake():
    print_myself()
    opt_name = 'north_kh_and_lake'
    new_params = [{
        'kh_h_flat4': low,  # lower
        'kh_h_flat3': riv_long,
        'kh_h_flat6': low,

        'kh_h_flat7': inc,  # raise
        'kh_h_flat8': inc,  # raise
        'kh_lake': lake
    }
        for riv_long, low, inc, lake in itertools.product(
            [100],
            [50, 200, 400],
            [300, 500, 1000, 1200],
            [0.1, 1, 5, 10]
        )]

    opt_name = f'{branch}_{opt_name}'

    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


def lake_kh_sy():
    print_myself()
    opt_name = 'lake_kh_sy'
    new_params = [{
        'kh_h_flat4': kh,
        'kh_h_flat3': kh,
        'kh_h_flat6': kh,

        'kh_h_flat7': kh,
        'kh_h_flat8': kh,

        'sy_h_flat4': sy,
        'sy_h_flat7': sy,
        'sy_h_flat8': sy,

        'kh_lake': lake
    }
        for kh, sy, lake in itertools.product(
            [100, 300, 500, 1000, 1500],
            [0.00005, 0.0001, 0.0005, .001, 0.005, 0.01, 0.05],
            [0.1, 0.5, 1, 3, 5, 10, 50, 100],
        )]

    opt_name = f'{branch}_{opt_name}'

    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


# next thoughts:
# lower kh of h_flat 4, 6, 3
# lower conductance of riv grandview
# lower conductivity of all of the terrace kh points


replot = True
if __name__ == '__main__':
    # keynote bulk parameters are ok:  ['bulk_kh', 'bulk_sy', 'bulk_riv', 'bulk_hill', 'bulk_race', 'bulk_rch']
    if replot:
        lake_kh_test()
        lake_kh_sy()
        lake_and_sy_test()
        north_kh_lake()
        north_kh()
        sy_test()

    pass
