"""
created matt_dumont 
on: 15/03/23
"""
import itertools
import traceback

import numpy as np
import pandas as pd
from Scenarios.wetland_setback_campbells.scenarios import run_model_extrac_data, get_ssh_dist, run_multiple_models, \
    wetland_name, output_suffix
from Scenarios.wetland_setback_campbells.model_bcs import get_wetland_loc
from project_base import unbacked_dir
from Scenarios.wetland_setback_campbells.project_model_tools import smt


def get_run_locs():
    run_locs = []
    run_azimuths = np.arange(0, 360, 60)
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

    run_azimuths = np.arange(0, 360, 20)
    run_distances = [3250, 4000]
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
    idx = (i >= 0) & (smt.get_no_flow(0)[i, j] == 1)
    run_locs = run_locs.loc[idx]
    run_locs = run_locs.reset_index()
    print(len(run_locs))
    return run_locs


def plot_pumps():
    from Scenarios.wetland_setback_campbells.model_bcs import get_riv
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


def create_run_runs(run_name, max_pumping_rates, hk_modifers, sy_modifers, riv_conds,
                    external_ips, local_cores,
                    just_print_number=False, rerun=False):
    runs = []
    run_locs = get_run_locs()
    for groupnum, (max_pumping_rate, hk_modifer,
                   sy_modifer, riv_cond) in enumerate(zip(max_pumping_rates, hk_modifers,
                                                                   sy_modifers, riv_conds)):
        previously_completed_runs = unbacked_dir.joinpath(wetland_name).glob(f'**/*{output_suffix}')
        previously_completed_runs = [e.name.replace(output_suffix, '') for e in previously_completed_runs]
        base_model_name = f'base_group_{groupnum}'
        temp = dict(
            model_name=base_model_name,
            model_ws=base_model_name,
            locs=None,
            max_pumping_rate=0,
            hk_modifer=hk_modifer,
            sy_modifer=sy_modifer,
                        riv_cond=riv_cond,
            rm_files=True,
            keep_list=True
        )
        runs.append(temp)
        for i in range(len(run_locs)):
            direction = run_locs.loc[i, 'direction']
            dist_from_old = run_locs.loc[i, 'dist_from_old']
            model_name = f'{direction}_{dist_from_old}_group_{groupnum}'

            # allow a re-run (e.g. do outputs exist)
            if not rerun:
                if model_name in previously_completed_runs:
                    continue

            temp = dict(
                model_name=model_name,
                model_ws=model_name,
                locs=run_locs.loc[[i]],
                max_pumping_rate=max_pumping_rate,
                hk_modifer=hk_modifer,
                sy_modifer=sy_modifer,

                riv_cond=riv_cond,
                rm_files=True,
                keep_list=True
            )
            runs.append(temp)

    print('number of runs:', len(runs))
    if just_print_number:
        return
    run_multiple_models(run_name=run_name, runs=runs, local_cores=local_cores, external_ips=external_ips)


def test_run():
    locs = smt.io.get_new_points_from_points_azimuth(get_wetland_loc(0), 500, delta_azimuth=0)
    hk_modifer = 1
    sy_modifer = 1

    try:
        riv_cond = 1500
        run_model_extrac_data(
            model_name='test_keep_files',
        model_ws=unbacked_dir.joinpath('test_keep'),
        locs=locs,
        max_pumping_rate=500,
        hk_modifer=hk_modifer,
        sy_modifer=sy_modifer,
        riv_cond=riv_cond,
        rm_files=False,
        keep_list=False
    )
    except Exception:
        print(traceback.format_exc())

    from Scenarios.wetland_setback_campbells.process_results import plot_list_failures
    plot_list_failures(unbacked_dir.joinpath('test_keep', 'test_keep_files.list'), unbacked_dir.joinpath('test_keep'))


def test_ssh_dist():
    locs = smt.io.get_new_points_from_points_azimuth(get_wetland_loc(0), 500, delta_azimuth=0)
    locs2 = smt.io.get_new_points_from_points_azimuth(get_wetland_loc(0), 1000, delta_azimuth=0)

    hk_modifer = 1
    sy_modifer = 1
    riv_cond = 1500

    runs = [
        dict(
            model_name='test_rm',
            model_ws='test_rm',
            locs=locs,
            max_pumping_rate=500,
            hk_modifer=hk_modifer,
            sy_modifer=sy_modifer,
            riv_cond=riv_cond,
            rm_files=True,
            keep_list=True
        ),
        dict(
            model_name='test_keep',
            model_ws='test_keep',
            locs=locs2,
            max_pumping_rate=500,
            hk_modifer=hk_modifer,
            sy_modifer=sy_modifer,
            riv_cond=riv_cond,
            rm_files=False,
            keep_list=False
        ),
    ]
    ssh_dist = get_ssh_dist(local_cores=4,
                            external_ips=['100.121.150.68'])
    ssh_dist.get_core_weightings_from_test_runs(runs, run_name='camp_test1', kwargs_relative_to_base_dir=['model_ws'],
                                                rm_files=False, compile=True)

    # added a 4vcpu cpu optimised droplet to test

    # individual times:
    #   * 100.124.148.71: 221.1062831878662s
    #   * 100.121.150.68: 1145.9440772533417s
    #   * 170.64.138.9: 331.1592597961426s
    #
    #
    # weights: {'100.124.148.71': 5.182774820920279, '100.121.150.68': 1.0, '170.64.138.9': 3.460401735282203}


def tranche_1(just_print_number=True, rerun=False):
    local_cores = 4
    external_ips = ['100.121.150.68', '170.64.185.117']
    run_name = 'tranche1'
    rates = [100, 500, 1000, 2000]
    hks = [0.316, 1, 3.16]
    syvals = [0.316, 1, 3.16]
    riv_vals = [750, 1500, 2500]
    max_pumping_rates = []
    hk_modifers = []
    sy_modifers = []
    riv_conds = []

    for mp, fhk, fsy, rcond in itertools.product(rates, hks, syvals, riv_vals):
        max_pumping_rates.append(mp)
        hk_modifers.append(fhk)
        sy_modifers.append(fsy)
        riv_conds.append(rcond)

    create_run_runs(run_name,
                    max_pumping_rates=max_pumping_rates,
                    hk_modifers=hk_modifers,
                    sy_modifers=sy_modifers,
                    riv_conds=riv_conds,
                    external_ips=external_ips, local_cores=local_cores,

                    just_print_number=just_print_number, rerun=rerun)


if __name__ == '__main__':
    tranche_1(just_print_number=False)

