"""
created matt_dumont 
on: 25/11/22
"""
from pathlib import Path
import numpy as np
import shutil
from targets_and_sensitive_sites.model_output import process_model_output
from optimisation.model_utils_for_forward_run import read_param_data, build_run_model
from run_managers.run_multiprocess import run_multiprocess # keynote private repo


def _run_model_mp(kwargs):
    try:
        run_model(**kwargs)
        success = True
        error = 'None'
    except Exception as val:
        success = False
        error = val
    return kwargs, success, error


def run_model(name, model_ws, plot):
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = read_param_data(model_ws, format_type='pest')
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


def run_opt_step_models(pest_dir, run_dir, num_cores, itters=None, plot=True):
    assert isinstance(pest_dir, Path) and isinstance(run_dir, Path)
    if itters is not None:
        itters = np.array(itters).astype(int)
        param_files = []
        param_itters = []
        for i in itters:
            t = pest_dir.joinpath(f'opt.par.{i}')
            if t.exists():
                param_files.append(t)
                param_itters.append(i)
    else:
        param_files = np.array(sorted(list(pest_dir.glob('opt.par.*'))))
        param_itters = np.array([int(str(e).split('.')[-1]) for e in param_files])
    runs = []
    run_dir.mkdir(exist_ok=True)
    for pid, p in zip(param_itters, param_files):
        model_ws = run_dir.joinpath(f'opt_step_{pid:03d}')
        model_ws.mkdir(exist_ok=True)
        new_par_path = model_ws.joinpath('parameters.dat')
        new_par_path.unlink(missing_ok=True)
        shutil.copy(p, new_par_path)
        name = f'opt_step_{pid:03d}'
        runs.append(dict(model_ws=model_ws, name=name, plot=plot))

    run_multiprocess(_run_model_mp, runs, num_cores=num_cores)


if __name__ == '__main__':
    from optimisation.a_build_run_optimisation_version import unbacked_dir, branch, mversion

    pdir = unbacked_dir.joinpath(branch, mversion, 'Optimisations')
    result_dir = pdir.joinpath('all_opt_steps')

    run_opt_step_models(pdir, result_dir, 8, itters=np.arange(12, 18))
