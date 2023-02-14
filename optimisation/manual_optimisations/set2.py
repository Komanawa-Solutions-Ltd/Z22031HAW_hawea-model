"""
manual optimisations before running the 3d optimisation
created matt_dumont 
on: 21/12/22
"""
import itertools
from optimisation.a_build_run_optimisation_version import branch
from optimisation.manual_optimisations.manual_optimisation import run_manal_opt
import inspect
import numpy as np


def print_myself():
    print(inspect.stack()[1][3])


def test_1():
    print_myself()
    opt_name = 'test_1'

    params = {
        'bulk_kh': [1, 10, 50, 100],
        'kh_mor_l0': [1, 10, 50, 100],
        'kh_lake': [1, 10, 50, 100],

    }
    use_keys = params.keys()
    runs = []
    new_vals = np.array(list(itertools.product(*[params[e] for e in use_keys])))
    for r in new_vals:
        temp = {k: i for k, i in zip(use_keys, r)}
        runs.append(temp)
    print(len(runs))
    opt_name = f'{branch}_{opt_name}'
    run_manal_opt(opt_name, mod_params=runs,
                  safemode=True, replot=replot)


def test_2():
    print_myself()
    opt_name = 'test_2'

    params = {
        'bulk_kh': [50, 100, 300],
        'kh_mor_l0': [100, 200, 300, 400],
    }
    use_keys = params.keys()
    runs = []
    new_vals = np.array(list(itertools.product(*[params[e] for e in use_keys])))
    for r in new_vals:
        temp = {k: i for k, i in zip(use_keys, r)}
        runs.append(temp)
    print(len(runs))
    opt_name = f'{branch}_{opt_name}'
    run_manal_opt(opt_name, mod_params=runs,
                  safemode=True, replot=replot, rm_remote_files=False)


def initial_manual2():
    print_myself()
    opt_name = 'initial_manual2'

    params = {
        'bulk_kh': [50, 100, 300],
        'kh_mor_l0': [50, 100, 300],
        'bulkter_kh': [10, 50, 100],
        'sy_sy_mor_l0': [0.001, 0.01, 0.1],
        'bulk_sy': [0.001, 0.01, 0.1]

    }
    use_keys = params.keys()
    runs = []
    new_vals = np.array(list(itertools.product(*[params[e] for e in use_keys])))
    for r in new_vals:
        temp = {k: i for k, i in zip(use_keys, r)}
        runs.append(temp)
    print(len(runs))
    opt_name = f'{branch}_{opt_name}'
    run_manal_opt(opt_name, mod_params=runs,
                  safemode=True, replot=replot)


replot = False

# keynote can I fit the south most without lake wave??, nope
# keynote bulk parameters are ok:  ['bulk_kh', 'bulk_sy', 'bulk_riv', 'bulk_hill', 'bulk_race', 'bulk_rch']
#  bulk kh and sy are applied to everything other than the terrace, the lake, the low cond and moraine zone
# keynote bulkter parameters are supported ['bulkter_kh', 'bulkter_sy'] theses apply to all terrace pilot points
if __name__ == '__main__':
    initial_manual2()  #  didn't run
    if replot:
        test_2()
        pass
