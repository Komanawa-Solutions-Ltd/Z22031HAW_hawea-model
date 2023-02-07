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
        temp = {}
        temp['kh_mor_l0'] = 800
        temp['kh_h_flat5'] = l
        temp['kh_h_flat46'] = l
        temp['kh_h_flat89'] = u
        new_params.append(temp)

    opt_name = f'{branch}_{opt_name}'
    run_simple_man_opt(name=opt_name, mod_params=new_params, base_param_dict=base_params, replot=replot,
                       safemode=False, rm_remote_files=True)


def check_moraine():
    print_myself()
    opt_name = 'moraine_test'
    base_params = read_param_data(
        parameter_file='/home/matt_dumont/unbacked/hawea/3d_v1a/init2_3d_v1a/Optimisations/opt.par',
        format='pest',
        return_individual=False

    )

    new_params = []
    l = 100
    u = 200
    for m in [600, 700, 800, 900]:
        temp = {}
        temp['kh_mor_l0'] = m
        temp['kh_h_flat5'] = l
        temp['kh_h_flat46'] = l
        temp['kh_h_flat89'] = u
        new_params.append(temp)
    opt_name = f'{branch}_{opt_name}'
    run_simple_man_opt(name=opt_name, mod_params=new_params, base_param_dict=base_params, replot=replot,
                       safemode=False, rm_remote_files=True)


def moraine_sy():
    print_myself()
    opt_name = 'moraine_sy_test'
    base_params = read_param_data(
        parameter_file='/home/matt_dumont/unbacked/hawea/3d_v1a/init2_3d_v1a/Optimisations/opt.par',
        format='pest',
        return_individual=False

    )

    new_params = []
    l = 100
    u = 200
    moraine_vals = [600, 700, 800, 900]
    sy_vals = [.02, .08, .1, .2]
    for m, sy in itertools.product(moraine_vals, sy_vals):
        temp = {}
        temp['kh_mor_l0'] = m
        temp['kh_h_flat5'] = l
        temp['kh_h_flat46'] = l
        temp['kh_h_flat89'] = u
        hflats = [4, 10, 3, 45, 8, 7, 46, 5, 89, 2, 1, 51, 9]
        for hflat in hflats:
            temp[f'sy_h_flat{hflat}'] = sy
        new_params.append(temp)
    opt_name = f'{branch}_{opt_name}'
    run_simple_man_opt(name=opt_name, mod_params=new_params, base_param_dict=base_params, replot=replot,
                       safemode=False, rm_remote_files=True)


def large_run():
    print_myself()
    opt_name = 'large_run'
    base_params = read_param_data(
        parameter_file='/home/matt_dumont/unbacked/hawea/3d_v1a/init2_3d_v1a/Optimisations/opt.par',
        format='pest',
        return_individual=False

    )

    new_params = []
    lowers = [1, 50, 100]
    uppers = [1000, 500, 200]
    peak = [1000, 2000, 5000]
    moraine_vals = [600, 700, 800, 900]
    sy_vals = [.02, .08, .1, .2]
    for m, sy, l, u, pk in itertools.product(moraine_vals, sy_vals, lowers, uppers, peak):
        temp = {}
        temp['kh_mor_l0'] = m
        temp['kh_h_flat5'] = l
        temp['kh_h_flat46'] = l
        temp['kh_h_flat89'] = u
        hflats = [4, 10, 3, 45, 8, 7, 46, 5, 89, 2, 1, 51, 9]
        for hflat in hflats:
            temp[f'sy_h_flat{hflat}'] = sy

        hflats2 = [3, 45, 8, 7]
        for hflat in hflats2:
            temp[f'kh_h_flat{hflat}'] = pk

        new_params.append(temp)
    opt_name = f'{branch}_{opt_name}'
    run_simple_man_opt(name=opt_name, mod_params=new_params, base_param_dict=base_params, replot=replot,
                       safemode=False, rm_remote_files=True)


def try_shift_hflat():
    print_myself()
    opt_name = 'try_shift_hflat'
    base_params = read_param_data(
        parameter_file='/home/matt_dumont/unbacked/hawea/3d_v1a/init2_3d_v1a/Optimisations/opt.par',
        format='pest',
        return_individual=False

    )

    new_params = []
    lowers = [5, 50]
    uppers = [500, 200]
    peak = [300, 500, 700, 1000]
    moraine_vals = [200, 400, 600]
    sy_vals = [.1]
    for m, sy, l, u, pk in itertools.product(moraine_vals, sy_vals, lowers, uppers, peak):
        temp = {}
        temp['kh_mor_l0'] = m
        temp['kh_h_flat5'] = l
        temp['kh_h_flat46'] = l
        temp['kh_h_flat89'] = u
        hflats = [4, 10, 3, 45, 8, 7, 46, 5, 89, 2, 1, 51, 9]
        for hflat in hflats:
            temp[f'sy_h_flat{hflat}'] = sy

        hflats2 = [3, 45, 8, 7, 6, 51]
        for hflat in hflats2:
            temp[f'kh_h_flat{hflat}'] = pk

        new_params.append(temp)
    opt_name = f'{branch}_{opt_name}'
    run_simple_man_opt(name=opt_name, mod_params=new_params, base_param_dict=base_params, replot=replot,
                       safemode=False, rm_remote_files=True)


# todo play with morain l0 kh, play with rasing kh above 1000, play with setting sy to higher values, remove ngmp wells as targets
#  re-run opt from "manual" param file.


replot = False
if __name__ == '__main__':
    try_shift_hflat()
    # large_run()
    # moraine_sy()
    # check_moraine()
    # kh_test()
