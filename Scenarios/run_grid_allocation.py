"""
created matt_dumont 
on: 8/03/23
"""
import sys

sys.path.append('/home/matt_dumont/PycharmProjects/Z22031HAW_hawea-model')
sys.path.append('/home/matt_dumont/PycharmProjects/modflow_tools_haw')
from Scenarios.allocation_scenarios import run_all_grid_allocation_scens, zones_to_model, run_grid_allocation_scenario, \
    run_grid_allocation_scenario_mp, get_pumping_in_zones
from project_base import unbacked_dir, opt_model_tools, opt_proj_root
from pathlib import Path


def test_indvidual():
    z = zones_to_model[-1]
    tinc = 5000
    run_grid_allocation_scenario(zone=z, total_increase=tinc, local_run_dir=unbacked_dir.joinpath('grid_runs'),
                                 base_outputs_dir=unbacked_dir.joinpath('grid_outputs'))


def test_ind_mp():
    z = zones_to_model[-1]
    tinc = 6000
    run_grid_allocation_scenario_mp(dict(zone=z, total_increase=tinc, local_run_dir=unbacked_dir.joinpath('grid_runs'),
                                         base_outputs_dir=unbacked_dir.joinpath('grid_outputs')))


def test_grid_allo():
    runs = {}
    for z in zones_to_model:
        runs[z] = [5000]

    run_all_grid_allocation_scens(name='test_grid_run', local_cores=3, pump_rate=runs, rm_remote_files=False)


def how_long_per_run():  # todo run once I have droplet setup
    """
    individual times:
      * 100.124.148.71: 281.27804684638977s
      * 100.121.150.68: 1003.0472960472107s

    weights: {'100.124.148.71': 3.566034773396269, '100.121.150.68': 1.0}
    :return:
    """
    external_ips = [
        '170.64.182.254'
    ]
    from run_managers.ssh_distributor import SshDist
    branch = 'main'
    local_cores = 4
    base_paths = {'100.124.148.71': unbacked_dir.joinpath('grid_scenarios'),
                  '100.121.150.68': Path('/media/matt_dumont/data/mh_unbacked/hawea').joinpath('grid_scenarios')}

    num_cores = {
        '100.124.148.71': local_cores,
        '100.121.150.68': None,
    }
    for ip in external_ips:
        base_paths[ip] = unbacked_dir.joinpath('grid_scenarios')
        num_cores[ip] = None

    ssh_dist = SshDist(
        base_path=base_paths,
        ips=['100.124.148.71',
             '100.121.150.68',
             ] + external_ips,
        script_path=opt_proj_root.joinpath('Scenarios/run_scenario.py'),
        conda_env='hawea',
        num_cores=num_cores,
        core_weigtings=None,  # todo
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
    z = zones_to_model[-1]
    tinc = 2000
    pers = ([0] + list(range(1173, 2108)))[0:10]
    test_runs = [dict(zone=z, total_increase=tinc, local_run_dir='grid_runs',
                      base_outputs_dir='grid_outputs', pers=pers)]
    ssh_dist.get_core_weightings_from_test_runs(test_runs,
                                                kwargs_relative_to_base_dir=['base_outputs_dir', 'local_run_dir'],
                                                rm_files=False, compile=True, run_name='core_test3')


def main_grid_allo(test=False, print_runs_only=False):
    raise NotImplementedError('already run')
    local_cores = 4
    external_ips = ['170.64.170.143']

    max_allo = get_pumping_in_zones().loc[:, 'max_allo_min'].abs()
    max_allo.loc[max_allo.isna()] = 1
    max_allo = max_allo.to_dict()
    base_runs = {
        # fraction increase from current max allocation
        'Terrace-River': [0.1, 0.25, 0.5, 1, 1.5],
        'Terrace-Hill': [0.1, 0.25, 0.5, 1, 1.5],
        # 'Mangawera Valley': [],  No runs needed, current allocation could cause problems
        'Hawea Flat': [0.05, 0.1, 0.2, 0.3, 0.5, .75, 1, 1.5],

        # no useage/allocation presently (values of pumping to add)
        'Te Awa': [500, 1000, 2500, 5000, 7500, 10000],
        'Maungawera Flat': [500, 1000, 2500, 5000, 7500, 10000],
    }
    num_runs = 0
    for zone, pump_increases in base_runs.items():
        num_runs += len(pump_increases)

    print(f'number of runs: {num_runs}')
    if print_runs_only:
        return
    runs = {}
    for zone, pump_increases in base_runs.items():
        runs[zone] = [max_allo[zone] * pinc for pinc in pump_increases]

    if test:
        pers = ([0] + list(range(1173, 2108)))[0:10]
        rname = 'grid_allo_v2_test2'
    else:
        rname = 'grid_allo_v2'  # note v1 got lost in the learning to do stuff.
        pers = None

    run_all_grid_allocation_scens(name=rname, local_cores=local_cores,
                                  pump_rate=runs, rm_remote_files=False, pers=pers, external_ips=external_ips
                                  )


def main_grid_allov3(test=False, print_runs_only=False):
    local_cores = None  # todo how many
    external_ips = []  # todo

    max_allo = get_pumping_in_zones().loc[:, 'max_allo_min'].abs()
    max_allo.loc[max_allo.isna()] = 1
    max_allo = max_allo.to_dict()
    base_runs = {
        # fraction increase from current max allocation
        # 'Terrace-River': [0.1, 0.25, 0.5, 1, 1.5], # no more runs needed
        'Terrace-Hill': [2, 2.5, 5, 7.5, 10],
        # 'Mangawera Valley': [],  No runs needed, current allocation could cause problems
        # 'Hawea Flat': [],  # no more runs needed

        # no useage/allocation presently (values of pumping to add)
        'Te Awa': [15000, 20000, 25000, 50000],
        'Maungawera Flat': [15000, 20000, 30000],
    }
    num_runs = 0
    for zone, pump_increases in base_runs.items():
        num_runs += len(pump_increases)

    print(f'number of runs: {num_runs}')
    if print_runs_only:
        return
    runs = {}
    for zone, pump_increases in base_runs.items():
        runs[zone] = [max_allo[zone] * pinc for pinc in pump_increases]

    if test:
        pers = ([0] + list(range(1173, 2108)))[0:10]
        rname = 'grid_allo_v3_test2'
    else:
        rname = 'grid_allo_v3'  # note v1 got lost in the learning to do stuff.
        pers = None

    run_all_grid_allocation_scens(name=rname, local_cores=local_cores,
                                  pump_rate=runs, rm_remote_files=False, pers=pers, external_ips=external_ips
                                  )


if __name__ == '__main__':
    main_grid_allov3(print_runs_only=True)
    # how_long_per_run()
    # main_grid_allov3(test=False)
    # test_indvidual()
    # test_ind_mp()
    # test_grid_allo()
    # test_ssh_dist()
