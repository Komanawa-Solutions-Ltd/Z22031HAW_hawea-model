"""
created matt_dumont 
on: 3/11/22
"""
import traceback
from pathlib import Path
import flopy
import numpy as np
import pandas as pd
from project_base import unbacked_dir, opt_proj_root, opt_model_tools
from Scenarios.wetland_setback_butterfield.params import get_hk, get_sy
from templates.modflow_model import build_model
from Scenarios.wetland_setback_butterfield.project_model_tools import tdis, smt
from Scenarios.wetland_setback_butterfield.model_bcs import get_riv, get_wells, get_rch, get_wetland_loc

wetland_name = 'butterfield'


def get_oc_spd():
    base_list = ['save head', 'save budget']
    out = {}
    for p, nstp in zip(tdis.pers, tdis.nstp):
        out[(p, nstp - 1)] = base_list
    return out


output_suffix = '_outputs.csv'
inputs_suffix = '_inputs.txt'


def extract_outputs(model_ws, model_name, well_loc):
    hdsfile = model_ws.joinpath(f'{model_name}.hds')

    outdata = pd.DataFrame(index=tdis.middle_step_dates)
    with flopy.utils.HeadFile(hdsfile) as hds:
        all_hds = hds.get_alldata()
    for k, i, j in well_loc.itertuples(False, None):
        outdata.loc[:, f'well_hds_{k}_{i}_{j}'] = all_hds[:, k, i, j]

    # extract actual well puming rate from cbc file!!!!
    with flopy.utils.CellBudgetFile(hdsfile.with_suffix('.cbc')) as cbc:
        all_pump = np.array(cbc.get_data(full3D=True, text='WELLS'))
    for k, i, j in well_loc.itertuples(False, None):
        outdata.loc[:, f'well_pump_{k}_{i}_{j}'] = all_pump[:, k, i, j]

    k, i, j = get_wetland_loc(0, return_just_kij=True)
    outdata.loc[:, 'wetland_hds'] = all_hds[:, k, i, j]

    outdata.to_csv(model_ws.joinpath(f'{model_name}{output_suffix}'))


def run_model_extrac_data(model_name, model_ws, locs, max_pumping_rate, terrace_hk, flat_hk,
                          terrace_sy, flat_sy, riv_cond, rm_files=True, keep_list=False):
    model_ws = Path(model_ws)
    model_ws.mkdir(exist_ok=True, parents=True)
    # write key input data
    well_spd, well_loc = get_wells(locs, max_pumping_rate)
    with model_ws.joinpath(f'{model_name}{inputs_suffix}').open('w') as f:
        f.write(f'{model_name = }\n')
        f.write(f'{max_pumping_rate = }\n')
        f.write(f'{terrace_hk = }\n')
        f.write(f'{flat_hk = }\n')
        f.write(f'{terrace_sy = }\n')
        f.write(f'{flat_sy = }\n')
        f.write(f'{riv_cond = }\n')
        for k, i, j in well_loc.itertuples(False, None):
            f.write(f'well_loc = {k},{i},{j}\n')
    hk = get_hk(terrace_hk, flat_hk)
    sy = get_sy(terrace_sy, flat_sy)

    build_model(
        smt, tdis,
        exe_name='mfnwt',
        model_name=model_name,
        model_ws=model_ws,
        hk=hk,
        vka=1,
        layer_avg=0,
        ss=1e-6,
        sy=sy,
        strt=smt.get_tops()[0],  # todo set to a better start value (quicker solve)
        chani=1,
        well_spd=well_spd,
        riv_spd=get_riv(riv_cond),
        oc_spd=get_oc_spd(),
        rch={0: get_rch()[0]},  # keynote hard coded in static recharge here to increase run speed.
        ghb_spd=None,
        options='COMPLEX',
        drn_spd=None,
        nwt_kwargs={},
        hani=None,
        mfv='mfnwt',
        run_model=True,
        verbose=False,
        t=None,
        noprint=False
    )

    extract_outputs(model_ws, model_name, well_loc)

    if rm_files:
        for file in model_ws.iterdir():
            if '.list' in file.name:
                if not keep_list:
                    file.unlink()
            elif output_suffix in file.name or inputs_suffix in file.name:
                continue
            else:
                file.unlink()


def run_model_mp(kwargs):
    model_ws = Path(kwargs['model_ws'])
    model_ws.mkdir(exist_ok=True, parents=True)
    try:
        run_model_extrac_data(**kwargs)
    except Exception:
        with model_ws.joinpath('log.log').open('w') as f:
            f.write(traceback.format_exc())


def get_ssh_dist(local_cores, external_ips):
    from run_managers.ssh_distributor import SshDist

    base_paths = {'100.124.148.71': unbacked_dir.joinpath(wetland_name),
                  '100.121.150.68': Path('/media/matt_dumont/data/mh_unbacked/hawea').joinpath(wetland_name)}

    num_cores = {
        '100.124.148.71': local_cores,
        '100.121.150.68': None,
    }

    core_weigtings = {'100.124.148.71': 2.5, '100.121.150.68': 1.0}

    for ip in external_ips:
        if ip not in base_paths:
            base_paths[ip] = unbacked_dir.joinpath(wetland_name)
        if ip not in num_cores:
            num_cores[ip] = None
        if ip not in core_weigtings:
            core_weigtings[ip] = 1.08

    branch = 'main'
    ssh_dist = SshDist(
        base_path=base_paths,
        ips=['100.124.148.71'] + external_ips,
        script_path=opt_proj_root.joinpath('Scenarios/wetland_setback_butterfield/run_scenario.py'),
        conda_env='hawea',
        num_cores=num_cores,
        core_weigtings=core_weigtings,
        user_names=None,
        short_names=None,
        prepend_bash_commands=[
            f"cd {opt_model_tools} ; git fetch --all ; git reset --hard origin/Z22031HAW_hawea-model",
            f"cd {opt_proj_root} ; git fetch --all ; git reset --hard origin/{branch}"
        ],
        use_tailscale=True,
        python_paths=[opt_proj_root, opt_model_tools],
        sys_paths="default"
    )
    return ssh_dist


def run_multiple_models(run_name, runs, local_cores, external_ips=(), rm_remote_files=True):
    ssh_dist = get_ssh_dist(local_cores, external_ips)
    print(f'running {len(runs)} models')
    ssh_dist.distribute_runs(run_name=run_name, runs=runs, rm_remote_files=rm_remote_files, run=True, compile=True,
                             run_in_series=False, kwargs_relative_to_base_dir=['model_ws'])
if __name__ == '__main__':
    pass