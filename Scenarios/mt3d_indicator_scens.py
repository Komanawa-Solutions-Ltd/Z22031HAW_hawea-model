"""
created matt_dumont 
on: 2/03/23
"""
import numpy as np

from Scenarios.run_mt3d_scenario import get_default_mt3d_kwargs, get_ftl, create_ssm_data, create_mt3d
from project_base import unbacked_dir, proj_root
from model_build.project_model_tools import smt





def run_indictors(rerun=False):
    ftl = get_ftl()
    base_run_dir = unbacked_dir.joinpath('mt3d_runs')
    base_run_dir.mkdir(exist_ok=True)

    data = dict(race_con=1, all_hill=1,
                hawear_con=1, clutha_con=1, lake_con=1, john_con=1, gview_con=1)

    ssm = create_ssm_data()
    mname = f'rch_indicator'
    mdt3d = create_mt3d(
        ftl_path=ftl,
        mt3d_name=mname,
        mt3d_ws=base_run_dir.joinpath(mname),
        smt=smt,
        ssm_crch={0: smt.get_model_zeros() + 1},
        ssm_stress_period_data={0: ssm},
        rerun=rerun,
        **get_default_mt3d_kwargs())

    ssm = create_ssm_data(all_hill=1)
    mname = f'hill_rch_indicator'
    mdt3d = create_mt3d(
        ftl_path=ftl,
        mt3d_name=mname,
        mt3d_ws=base_run_dir.joinpath(mname),
        smt=smt,
        ssm_crch={0: smt.get_model_zeros() + 1},
        ssm_stress_period_data={0: ssm},
        rerun=rerun,
        **get_default_mt3d_kwargs())

    ssm = create_ssm_data()
    mname = f'blank'
    mdt3d = create_mt3d(
        ftl_path=ftl,
        mt3d_name=mname,
        mt3d_ws=base_run_dir.joinpath(mname),
        smt=smt,
        ssm_crch={0: smt.get_model_zeros()},
        ssm_stress_period_data={0: ssm},
        rerun=rerun,
        **get_default_mt3d_kwargs())

    for k, v in data.items():
        ssm = create_ssm_data(**{k: v})
        mname = f'{k}_indicator'
        mdt3d = create_mt3d(
            ftl_path=ftl,
            mt3d_name=mname,
            mt3d_ws=base_run_dir.joinpath(mname),
            smt=smt,
            ssm_crch={0: smt.get_model_zeros()},
            ssm_stress_period_data={0: ssm},
            rerun=rerun,
            **get_default_mt3d_kwargs())


def extract_data():
    base_out = proj_root.joinpath('Scenarios/mt3d_indicator_scenarios')
    base_out.mkdir(exist_ok=True)
    base_ucn = base_out.joinpath('ucn_data')
    base_plots = base_out.joinpath('ucn_data')
    # todo run indicator scenarios for each unit, save the ucn array, and make a plot of the UCN array (what layer??)


if __name__ == '__main__':
    run_indictors(rerun=False)
