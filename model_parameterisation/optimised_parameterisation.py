"""
created matt_dumont 
on: 1/09/22
"""
import warnings

from project_base import proj_root
from model_build.project_model_tools import bund_top
from optimisation.model_utils_for_forward_run import read_param_data


def get_3d_v1a_params(return_individual=True):
    assert bund_top == 335, f'top of bund is expected to be 335msl but got {bund_top} wrong branch?'
    param_path = proj_root.joinpath('model_parameterisation/optimised_parameter_sets/3d_v1a_opt.par')
    return read_param_data(parameter_file=param_path, format_type='pest', return_individual=return_individual)


def get_3d_v1b_params(return_individual=True):
    assert bund_top == 332, f'top of bund is expected to be 332msl but got {bund_top} wrong branch?'
    param_path = proj_root.joinpath('model_parameterisation/optimised_parameter_sets/3d_v1b_opt.par')
    return read_param_data(parameter_file=param_path, format_type='pest', return_individual=return_individual)


def get_3d_v1d_params(return_individual=True):
    assert bund_top == 335, (f'top of bund is expected to be 335msl but got {bund_top} wrong branch?')
    param_path = proj_root.joinpath('model_parameterisation/optimised_parameter_sets/3d_v1d_opt.par')
    return read_param_data(parameter_file=param_path, format_type='pest', return_individual=return_individual)


if __name__ == '__main__':
    get_3d_v1a_params()
    get_3d_v1d_params()
    get_3d_v1b_params()
