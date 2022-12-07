"""
created matt_dumont 
on: 28/11/22
"""
import itertools

import numpy as np

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


def near_lake_raise_lower():
    print_myself()
    opt_name = 'near_lake_raise_lower'

    lower = [100, 50, 10, 5]
    inc = [500, 1000, 1500]
    sy_vals = [0.005, 0.01, 0.05]
    lakes = [5, 10, 50, 100]

    num_runs = len(list(itertools.product(lower, inc, sy_vals, lakes)))
    print(f'num_runs: {num_runs}')

    new_params = [{
        'kh_h_flat4': l,
        'kh_h_flat3': l,
        'kh_h_flat6': l,

        'kh_h_flat2': u,
        'kh_h_flat5': u,
        'kh_h_flat7': u,
        'kh_h_flat8': u,
        'kh_h_flat10': u,
        'kh_riv_g25': u,
        'kh_riv_g26': u,

        'sy_h_flat4': sy,
        'sy_h_flat7': sy,
        'sy_h_flat8': sy,

        'kh_lake': lake
    }

        for l, u, sy, lake in itertools.product(lower, inc, sy_vals, lakes)
    ]

    opt_name = f'{branch}_{opt_name}'

    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


def near_lake_raise_rl_lower():
    print_myself()
    opt_name = 'near_lake_raise_lower'

    lower = [100, 50, 10, 5]
    raise_lower = [10, 50, 100, 500, 1000]
    inc = [500, 1000, 1500]
    sy_vals = [0.005, 0.01, 0.05]
    lakes = [5, 10, 50, 100]

    num_runs = len(list(itertools.product(lower, raise_lower, inc, sy_vals, lakes)))
    print(f'num_runs: {num_runs}')

    new_params = [{
        # kh
        'kh_h_flat4': low,
        'kh_h_flat3': low,
        'kh_h_flat6': low,
        'kh_h_flat40': low,
        'kh_h_flat41': low,
        'kh_h_flat42': low,

        'kh_h_flat43': rl,
        'kh_h_flat44': rl,
        'kh_h_flat45': rl,
        'kh_h_flat10': rl,
        'kh_riv_g25': rl,

        'kh_h_flat7': u,
        'kh_h_flat8': u,
        'kh_h_flat46': u,
        'kh_riv_g26': u,

        # sy
        'sy_h_flat4': sy,
        'sy_h_flat3': sy,
        'sy_h_flat6': sy,
        'sy_h_flat40': sy,
        'sy_h_flat41': sy,
        'sy_h_flat42': sy,
        'sy_h_flat43': sy,
        'sy_h_flat44': sy,
        'sy_h_flat45': sy,
        'sy_h_flat10': sy,
        'sy_riv_g25': sy,
        'sy_h_flat7': sy,
        'sy_h_flat8': sy,
        'sy_h_flat46': sy,
        'sy_riv_g26': sy,

        # lake
        'kh_lake': lake
    }

        for low, rl, u, sy, lake in itertools.product(lower, raise_lower, inc, sy_vals, lakes)
    ]

    opt_name = f'{branch}_{opt_name}'

    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


def near_lake_raise_rl_lower_str():
    print_myself()
    opt_name = 'near_lake_raise_lower_str'

    lower = [100, 50, 10, 5]
    inc = [500, 1000, 1500, 2000]
    sy_vals = [0.001, 0.005, 0.01]
    lakes = [5, 10, 50, 100]
    str_vals = [5, 10, 50, 100]

    num_runs = len(list(itertools.product(lower, inc, sy_vals, lakes, str_vals)))
    print(f'num_runs: {num_runs}')

    new_params = [{
        # kh
        'kh_h_flat4': low,
        'kh_h_flat3': low,
        'kh_h_flat6': low,
        'kh_h_flat40': low,
        'kh_h_flat41': low,
        'kh_h_flat42': low,

        'kh_h_flat43': low,
        'kh_h_flat44': low,
        'kh_h_flat45': low,
        'kh_h_flat10': low,
        'kh_riv_g25': low,

        'kh_h_flat7': u,
        'kh_h_flat8': u,
        'kh_h_flat46': u,
        'kh_riv_g26': u,

        # sy
        'sy_h_flat4': sy,
        'sy_h_flat3': sy,
        'sy_h_flat6': sy,
        'sy_h_flat40': sy,
        'sy_h_flat41': sy,
        'sy_h_flat42': sy,
        'sy_h_flat43': sy,
        'sy_h_flat44': sy,
        'sy_h_flat45': sy,
        'sy_h_flat10': sy,
        'sy_riv_g25': sy,
        'sy_h_flat7': sy,
        'sy_h_flat8': sy,
        'sy_h_flat46': sy,
        'sy_riv_g26': sy,

        # lake
        'kh_lake': lake,

        # str
        'riv_gview': stv,
    }

        for low, u, sy, lake, stv in itertools.product(lower, inc, sy_vals, lakes, str_vals)
    ]

    opt_name = f'{branch}_{opt_name}'

    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


def extreme_bounds():
    print_myself()
    opt_name = 'extreme_bounds'

    lower = [100, 50, 10, 5, 1]
    raise_lower = [50, 100, 500, 1000, 2000]
    inc = [1000, 2000, 3000]
    sy_vals = [0.0001, 0.001, 0.01]
    lakes = [1, 5, 10]

    num_runs = len(list(itertools.product(lower, raise_lower, inc, sy_vals, lakes)))
    print(f'num_runs: {num_runs}')

    new_params = [{
        # kh
        'kh_h_flat4': low,
        'kh_h_flat3': low,
        'kh_h_flat6': low,
        'kh_h_flat40': low,
        'kh_h_flat41': low,
        'kh_h_flat42': low,

        'kh_h_flat43': rl,
        'kh_h_flat44': rl,
        'kh_h_flat45': rl,
        'kh_h_flat10': rl,
        'kh_riv_g25': rl,

        'kh_h_flat7': u,
        'kh_h_flat8': u,
        'kh_h_flat46': u,
        'kh_riv_g26': u,

        # sy
        'sy_h_flat4': sy,
        'sy_h_flat3': sy,
        'sy_h_flat6': sy,
        'sy_h_flat40': sy,
        'sy_h_flat41': sy,
        'sy_h_flat42': sy,
        'sy_h_flat43': sy,
        'sy_h_flat44': sy,
        'sy_h_flat45': sy,
        'sy_h_flat10': sy,
        'sy_riv_g25': sy,
        'sy_h_flat7': sy,
        'sy_h_flat8': sy,
        'sy_h_flat46': sy,
        'sy_riv_g26': sy,

        # lake
        'kh_lake': lake
    }

        for low, rl, u, sy, lake in itertools.product(lower, raise_lower, inc, sy_vals, lakes)
    ]

    opt_name = f'{branch}_{opt_name}'

    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


def explore_kh_south2():
    print_myself()
    opt_name = 'explore_kh_south_v2'
    lower_names = [
        'kh_ter34',
        'kh_ter35',
        'kh_ter38',
        'kh_ter39',
        'kh_ter38',

    ]
    lower_vals = [5, 10, 50, 100, 300]
    raise_lower_names = [
        'kh_h_flat1',
        'kh_h_flat9',
        'kh_riv_g23',
    ]
    raise_lower_vals = [50, 100, 300, 500]
    runs = []
    for lv, rlv in itertools.product(lower_vals, raise_lower_vals):
        temp = {k: rlv for k in raise_lower_names}
        temp.update({k: lv for k in lower_names})
        runs.append(temp)
    opt_name = f'{branch}_{opt_name}'

    run_manal_opt(opt_name, mod_params=runs,
                  safemode=True, replot=replot)


def explore_kh_south3():
    print_myself()
    opt_name = 'explore_kh_south_v3'
    lower_names = [
        'kh_ter34',
        'kh_ter35',
        'kh_ter38',
        'kh_ter39',
        'kh_ter38',

    ]
    lower_vals = [5, 10, 50, 100, 300]
    raise_lower_names = [
        'kh_h_flat1',
        'kh_h_flat9',
        'kh_riv_g23',
    ]
    raise_lower_vals = [50, 100, 300, 500, 1000]

    mid_vals = [50, 100, 300, 500, 1000]
    mid_names = [
        'kh_h_flat2',
        'kh_h_flat5',
        'kh_h_flat7',
        'kh_h_flat8',
        'kh_h_flat46',

    ]

    runs = []
    for lv, rlv, mid in itertools.product(lower_vals, raise_lower_vals, mid_vals):
        temp = {k: rlv for k in raise_lower_names}
        temp.update({k: lv for k in lower_names})
        temp.update({k: mid for k in mid_names})
        runs.append(temp)
    opt_name = f'{branch}_{opt_name}'

    run_manal_opt(opt_name, mod_params=runs,
                  safemode=True, replot=replot)


def lake_bar_kh_sy_test():
    print_myself()
    opt_name = 'lake_bar_kh_sy_test'
    new_params = [{
        'sy_lake_bar': sy,
        'kh_lake_bar': kh,
    }
        for sy, kh in itertools.product(
            10. ** np.arange(-8, 0),  # sy
            10. ** np.arange(-11, 3)  # kh
        )]
    print(f'{len(new_params)} runs')
    opt_name = f'{branch}_{opt_name}'
    run_manal_opt(opt_name, mod_params=new_params,
                  safemode=True, replot=replot)


replot = False
# todo can I fit the south most without lake wave??, nope
# keynote bulk parameters are ok:  ['bulk_kh', 'bulk_sy', 'bulk_riv', 'bulk_hill', 'bulk_race', 'bulk_rch']
if __name__ == '__main__':
    lake_bar_kh_sy_test()
    if replot:
        # explore_kh_south3()
        # explore_kh_south2()
        # near_lake_raise_rl_lower_str()
        # near_lake_raise_rl_lower()

        # previous structure
        # near_lake_raise_lower()
        # lake_kh_sy()
        # lake_kh_test()
        # lake_and_sy_test()
        # north_kh_lake()
        # north_kh()
        # sy_test()
        pass

    pass
