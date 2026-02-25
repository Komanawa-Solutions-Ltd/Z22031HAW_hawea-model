"""
Run the final optimised model for Hawea, using the parameters from the optimisation process.
command line usage:
python -m komanawa.hawea.optimisation.run_final_opt_model [version] [model_ws]
version: one of 3d_v1a, 3d_v1b, 3d_v1d
model_ws: working directory to run the model in, will be created if it does not exist default is ~/Downloads/hawea_opt_model_{version}


created matt_dumont 
on: 2/25/26
"""
from komanawa.hawea.model_parameterisation.optimised_parameterisation import get_3d_v1d_params, get_3d_v1a_params, get_3d_v1b_params
from komanawa.hawea.optimisation.model_utils_for_forward_run import read_param_data, build_run_model


def run_opt_model(version, model_ws, verbose=False):
    """
    run the final optimised model

    :param version: model version one of 3d_v1a, 3d_v1b, 3d_v1d
    :param model_ws: working directory to run the model in
    :param verbose: whether to print model output to console
    :return:
    """

    if version == '3d_v1a':
        kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1a_params()
    elif version == '3d_v1b':
        kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1b_params()
    elif version == '3d_v1d':
        kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    else:
        raise ValueError('version must be one of 3d_v1a, 3d_v1b, 3d_v1d, ')

    build_run_model(
        model_name=f'hawea_{version}',
        model_ws=model_ws,
        kh_param=kh_param,
        sy_param=sy_param,
        riv_params=riv_params,
        hill_param=hill_param,
        race_param=race_param,
        rch_param=rch_param,
        verbose=verbose
    )


if __name__ == '__main__':
    verbose = True
    import sys
    from pathlib import Path
    if len(sys.argv) > 3:
        version = sys.argv[1]
        model_ws = sys.argv[2]
        verbose = bool(int(sys.argv[3]))
    elif len(sys.argv) == 3:
        version = sys.argv[1]
        model_ws = sys.argv[2]
    elif len(sys.argv) == 2:
        version = sys.argv[1]
        model_ws = Path.home().joinpath('Downloads', f'hawea_opt_model_{version}')
    else:
        version = '3d_v1d'
        model_ws = Path.home().joinpath('Downloads', f'hawea_opt_model_{version}')
    run_opt_model(version, model_ws, verbose)
