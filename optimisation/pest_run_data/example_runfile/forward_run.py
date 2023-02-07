"""
created matt_dumont 
on: 11/10/22
"""
import sys
from pathlib import Path

t = Path('/home/matt_dumont/PycharmProjects/Z22031HAW_hawea-model')
sys.path.append(str(t))
sys.path.append(str(t.parent.joinpath('modflow_tools_haw')))  # supporting KSL package
print(f'pythonpath: {sys.path}')
from targets_and_sensitive_sites.model_output import process_model_output
from optimisation.model_utils_for_forward_run import read_param_data, build_run_model

if __name__ == '__main__':
    plot = False
    name = 'opt_model'
    model_ws = Path(__file__).parent
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = read_param_data(model_ws)
    build_run_model(
        model_name=name, model_ws=model_ws,
        kh_param=kh_param,
        sy_param=sy_param,
        riv_params=riv_params,
        hill_param=hill_param,
        race_param=race_param,
        rch_param=rch_param
    )
    process_model_output(model_ws=model_ws,
                         hds_file=model_ws.joinpath(f'{name}.hds'),
                         plot=plot)
