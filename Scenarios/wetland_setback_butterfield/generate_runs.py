"""
created matt_dumont 
on: 15/03/23
"""
import pandas as pd

from Scenarios.wetland_setback_butterfield.scenarios import run_model_extrac_data, get_ssh_dist, run_multiple_models
from Scenarios.wetland_setback_butterfield.model_bcs import get_wetland_loc
from project_base import unbacked_dir
from Scenarios.wetland_setback_butterfield.project_model_tools import smt


def create_run_runs(max_pumping_rate, terrace_hk, flat_hk, terrace_sy, flat_sy,
                    external_ips, local_cores,
                    just_print_number=False, rerun=False):
    run_name = '_'.join(
        [str(e) for e in [max_pumping_rate, terrace_hk, flat_hk, terrace_sy, flat_sy]])  # todo scientic notation!
    run_azimuths = []  # todo
    run_distances = []  # todo
    base_locs = []
    for azimuth in run_azimuths:
        wet = get_wetland_loc(azimuth)
        base_locs.append(wet)
    base_locs = pd.concat(base_locs)
    run_locs = []
    for dist in run_distances:
        locs = smt.io.get_new_points_from_points_azimuth(base_locs.copy(True), distance=dist, delta_azimuth=0)
        run_locs.append(locs)
    run_locs = pd.concat(run_locs).reset_index()
    # todo allow a re-run (e.g. do outputs exist)
    # todo cull runs if they land in no flow or are out of domain
    # todo cull runs if land in a river cell
    run_locs = run_locs.reset_index()
    runs = []
    for i in range(len(run_locs)):
        direction = run_locs.loc[i, 'direction']
        dist_from_old = run_locs.loc[i, 'dist_from_old']
        model_name = f'{direction}_{dist_from_old}'
        temp = dict(
            model_name=model_name,
            model_ws=model_name,
            locs=run_locs.loc[[i]],
            max_pumping_rate=max_pumping_rate,
            terrace_hk=terrace_hk,
            flat_hk=flat_hk,
            terrace_sy=terrace_sy,
            flat_sy=flat_sy,
            rm_files=False,
            keep_list=False
        )
        runs.append(temp)

    print('number of runs:', len(runs))
    if just_print_number:
        return
    run_multiple_models(run_name=run_name, runs=runs, local_cores=local_cores, external_ips=external_ips)


def test_run():
    locs = smt.io.get_new_points_from_points_azimuth(get_wetland_loc(90), 500, delta_azimuth=0)
    terrace_hk = None  # todo
    flat_hk = None  # todo
    terrace_sy = None  # todo
    flat_sy = None  # todo
    run_model_extrac_data(
        model_name='test_keep_files',
        model_ws=unbacked_dir.joinpath('test_keep'),
        locs=locs,
        max_pumping_rate=500,
        terrace_hk=terrace_hk,
        flat_hk=flat_hk,
        terrace_sy=terrace_sy,
        flat_sy=flat_sy,
        rm_files=False,
        keep_list=False
    )
    run_model_extrac_data(
        model_name='test_cull_files',
        model_ws=unbacked_dir.joinpath('test_cull'),
        locs=locs,
        max_pumping_rate=500,
        terrace_hk=terrace_hk,
        flat_hk=flat_hk,
        terrace_sy=terrace_sy,
        flat_sy=flat_sy,
        rm_files=True,
        keep_list=True
    )


def test_ssh_dist():  # todo run and check weighting
    locs = smt.io.get_new_points_from_points_azimuth(get_wetland_loc(90), 500, delta_azimuth=0)
    locs2 = smt.io.get_new_points_from_points_azimuth(get_wetland_loc(90), 1000, delta_azimuth=0)

    terrace_hk = None  # todo
    flat_hk = None  # todo
    terrace_sy = None  # todo
    flat_sy = None  # todo

    runs = [
        dict(
            model_name='test_keep_files',
            model_ws=unbacked_dir.joinpath('test_keep'),
            locs=locs,
            max_pumping_rate=500,
            terrace_hk=terrace_hk,
            flat_hk=flat_hk,
            terrace_sy=terrace_sy,
            flat_sy=flat_sy,
            rm_files=False,
            keep_list=False
        ),
        dict(
            model_name='test_keep_files',
            model_ws=unbacked_dir.joinpath('test_keep'),
            locs=locs2,
            max_pumping_rate=500,
            terrace_hk=terrace_hk,
            flat_hk=flat_hk,
            terrace_sy=terrace_sy,
            flat_sy=flat_sy,
            rm_files=False,
            keep_list=False
        ),
    ]
    ssh_dist = get_ssh_dist(local_cores=4,
                            external_ips=['100.121.150.68'])  # todo others??? (yes spin up a small droplet)
    ssh_dist.get_core_weightings_from_test_runs(runs, kwargs_relative_to_base_dir=['model_ws'])
