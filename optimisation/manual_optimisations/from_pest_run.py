"""
created matt_dumont 
on: 24/01/23
"""
import itertools
from optimisation.a_build_run_optimisation_version import branch
from optimisation.manual_optimisations.manual_optimisation import run_simple_man_opt
import inspect
import numpy as np
from copy import deepcopy
from optimisation.model_utils_for_forward_run import read_param_data


def print_myself():
    print(inspect.stack()[1][3])


def kh_test():
    print_myself()
    opt_name = 'kh_test_from_opt1'
    base_params = read_param_data(
        parameter_file='/home/matt_dumont/unbacked/hawea/3d_v1a/init2_3d_v1a/Optimisations/opt.par',
        format='pest',
        return_individual=False

    )

    new_params = []

    lowers = [1, 50, 100]
    uppers = [1000, 500, 200]
    for l, u in zip(lowers, uppers):
        temp = deepcopy(base_params)
        temp['kh_h_flat5'] = l
        temp['kh_h_flat46'] = l
        temp['kh_h_flat89'] = u
        new_params.append(temp)

    opt_name = f'{branch}_{opt_name}'
    run_simple_man_opt(name=opt_name, mod_params=new_params, base_param_dict=base_params, replot=replot,
                       safemode=True, rm_remote_files=True)


replot = False
if __name__ == '__main__':
    kh_test()
