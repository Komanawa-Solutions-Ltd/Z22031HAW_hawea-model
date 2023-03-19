"""
created matt_dumont 
on: 15/03/23
"""
import numpy as np
import pandas as pd
from Scenarios.wetland_setback_butterfield.scenarios import run_model_extrac_data, get_ssh_dist, run_multiple_models, \
    wetland_name, output_suffix
from Scenarios.wetland_setback_butterfield.model_bcs import get_wetland_loc
from project_base import unbacked_dir
from Scenarios.wetland_setback_butterfield.project_model_tools import smt


def get_run_locs():
    run_locs = []
    run_azimuths = np.arange(0, 360, 45)
    run_distances = [200, 500, ]
    base_locs = []
    for azimuth in run_azimuths:
        wet = get_wetland_loc(azimuth)
        base_locs.append(wet)
    base_locs = pd.concat(base_locs)
    for dist in run_distances:
        locs = smt.io.get_new_points_from_points_azimuth(base_locs.copy(True), distance=dist, delta_azimuth=0)
        run_locs.append(locs)

    run_azimuths = np.arange(0, 360, 20)
    run_distances = [1000, 1500, 2000, 2500, ]
    base_locs = []
    for azimuth in run_azimuths:
        wet = get_wetland_loc(azimuth)
        base_locs.append(wet)
    base_locs = pd.concat(base_locs)
    for dist in run_distances:
        locs = smt.io.get_new_points_from_points_azimuth(base_locs.copy(True), distance=dist, delta_azimuth=0)
        run_locs.append(locs)

    run_azimuths = np.arange(0, 360, 10)
    run_distances = [3250, 4000, 5000]
    base_locs = []
    for azimuth in run_azimuths:
        wet = get_wetland_loc(azimuth)
        base_locs.append(wet)
    base_locs = pd.concat(base_locs)
    for dist in run_distances:
        locs = smt.io.get_new_points_from_points_azimuth(base_locs.copy(True), distance=dist, delta_azimuth=0)
        run_locs.append(locs)

    run_locs = pd.concat(run_locs).reset_index()

    # cull runs if they land in no flow or are out of domain
    i, j = smt.convert_coords_to_matix(run_locs.new_x, run_locs.new_y, coords_out_domain='coerce')
    run_locs.loc[:, 'i'] = i
    run_locs.loc[:, 'j'] = j
    idx = np.isfinite(i) & (smt.get_no_flow(0)[i, j] == 1)
    run_locs = run_locs.loc[idx]
    run_locs = run_locs.reset_index()
    print(len(run_locs))
    return run_locs


def plot_pumps():
    from Scenarios.wetland_setback_butterfield.model_bcs import get_riv
    riv = get_riv(500)
    well = {}
    well[0] = get_run_locs()
    fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
    for pkg, k, c in zip(['riv', 'well'], ['stage', 'flux'], ['b', 'r']):
        print(pkg)
        ax.set_title(pkg)
        ax.scatter(*smt.convert_matrix_to_coords(eval(pkg)[0]['i'], eval(pkg)[0]['j']), color=c, label=pkg)

    ax.scatter(*smt.convert_matrix_to_coords(*get_wetland_loc(30, return_just_kij=True)[1:]), color='purple',
               label='wetland')
    ax.legend()
    smt.plot.show()


def create_run_runs(max_pumping_rate, terrace_hk, flat_hk, terrace_sy, flat_sy, riv_cond,
                    external_ips, local_cores,
                    just_print_number=False, rerun=False):
    run_name = '_'.join(
        [f'{float(e):.1e}' for e in [max_pumping_rate, terrace_hk, flat_hk, terrace_sy, flat_sy, riv_cond]])
    runs = []
    previously_completed_runs = unbacked_dir.joinpath(wetland_name).glob(f'**/*{output_suffix}')
    previously_completed_runs = [e.name.replace(output_suffix, '') for e in previously_completed_runs]

    run_locs = get_run_locs()
    for i in range(len(run_locs)):
        direction = run_locs.loc[i, 'direction']
        dist_from_old = run_locs.loc[i, 'dist_from_old']
        model_name = f'{direction}_{dist_from_old}'

        # allow a re-run (e.g. do outputs exist)
        if not rerun:
            if model_name in previously_completed_runs:
                continue

        temp = dict(
            model_name=model_name,
            model_ws=model_name,
            locs=run_locs.loc[[i]],
            max_pumping_rate=max_pumping_rate,
            terrace_hk=terrace_hk,
            flat_hk=flat_hk,
            terrace_sy=terrace_sy,
            flat_sy=flat_sy,
            riv_cond=riv_cond,
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
    terrace_hk = 1
    flat_hk = 1
    terrace_sy = 1
    flat_sy = 1
    riv_cond = 1500
    run_model_extrac_data(
        model_name='test_keep_files',
        model_ws=unbacked_dir.joinpath('test_keep'),
        locs=locs,
        max_pumping_rate=500,
        terrace_hk=terrace_hk,
        flat_hk=flat_hk,
        terrace_sy=terrace_sy,
        flat_sy=flat_sy,
        riv_cond=riv_cond,
        rm_files=False,
        keep_list=False
    )

    from Scenarios.wetland_setback_butterfield.process_results import plot_list_failures
    plot_list_failures(unbacked_dir.joinpath('test_keep', 'test_keep_files.list'), unbacked_dir.joinpath('test_keep'))
    run_model_extrac_data(
        model_name='test_cull_files',
        model_ws=unbacked_dir.joinpath('test_cull'),
        locs=locs,
        max_pumping_rate=500,
        terrace_hk=terrace_hk,
        flat_hk=flat_hk,
        terrace_sy=terrace_sy,
        flat_sy=flat_sy,
        riv_cond=riv_cond,
        rm_files=True,
        keep_list=True
    )


def test_ssh_dist():  # todo run and check weighting
    locs = smt.io.get_new_points_from_points_azimuth(get_wetland_loc(90), 500, delta_azimuth=0)
    locs2 = smt.io.get_new_points_from_points_azimuth(get_wetland_loc(90), 1000, delta_azimuth=0)

    terrace_hk = 1
    flat_hk = 1
    terrace_sy = 1
    flat_sy = 1
    riv_cond = 1500

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
            riv_cond=riv_cond,
            rm_files=True,
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
            rm_files=True,
            keep_list=False
        ),
    ]
    ssh_dist = get_ssh_dist(local_cores=4,
                            external_ips=['100.121.150.68', ''])  # todo others??? (yes spin up a small droplet)
    ssh_dist.get_core_weightings_from_test_runs(runs, kwargs_relative_to_base_dir=['model_ws'])


if __name__ == '__main__':
    test_ssh_dist()