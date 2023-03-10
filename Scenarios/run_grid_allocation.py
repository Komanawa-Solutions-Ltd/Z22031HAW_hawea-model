"""
created matt_dumont 
on: 8/03/23
"""
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


def how_long_per_run():
    """
    individual times:
      * 100.124.148.71: 281.27804684638977s
      * 100.121.150.68: 1003.0472960472107s

    weights: {'100.124.148.71': 3.566034773396269, '100.121.150.68': 1.0}
    :return:
    """

    from run_managers.ssh_distributor import SshDist
    branch = 'main'
    local_cores = 4
    ssh_dist = SshDist(
        base_path={
            '100.124.148.71': unbacked_dir.joinpath('grid_scenarios'),
            '100.121.150.68': Path('/media/matt_dumont/data/mh_unbacked/hawea').joinpath('grid_scenarios')
        },
        ips=['100.124.148.71',
             '100.121.150.68'],
        script_path=opt_proj_root.joinpath('Scenarios/run_scenario.py'),
        conda_env='hawea',
        num_cores={
            '100.124.148.71': local_cores,
            '100.121.150.68': None,
        },
        core_weigtings={
            '100.124.148.71': 2.6675381999814873,
            '100.121.150.68': 1.0},
        user_names=None,
        short_names=None,
        prepend_bash_commands={
            '100.124.148.71': [
                f"cd {opt_model_tools} ; git fetch --all ; git reset --hard origin/Z22031HAW_hawea-model",
                f"cd {opt_proj_root} ; git fetch --all ; git reset --hard origin/{branch}"
            ],
            '100.121.150.68': [
                f"cd {opt_model_tools} ; git fetch --all ; git reset --hard origin/Z22031HAW_hawea-model",
                f"cd {opt_proj_root} ; git fetch --all ; git reset --hard origin/{branch}"
            ]},
        use_tailscale=True,
        python_paths=[opt_proj_root, opt_model_tools],
        sys_paths="default"
    )
    z = zones_to_model[-1]
    tinc = 2000
    test_runs = [dict(zone=z, total_increase=tinc, local_run_dir='grid_runs',
                      base_outputs_dir='grid_outputs', pers=list(range(1173, 2108)))]
    ssh_dist.get_core_weightings_from_test_runs(test_runs,
                                                kwargs_relative_to_base_dir=['base_outputs_dir', 'local_run_dir'],
                                                rm_files=True)


def main_grid_allo():
    local_cores = 4  # todo how many
    max_allo = get_pumping_in_zones().loc[:, 'max_allo_min'].abs()
    max_allo.loc[max_allo.isna()] = 1
    max_allo = max_allo.to_dict()
    base_runs = {
        # fraction increase from current max allocation
        'Terrace-River': [],
        'Terrace-Hill': [],
        'Mangawera Valley': [],
        'Hawea Flat': [],

        # no useage/allocation presently (values of pumping to add)
        'Te Awa': [],
        'Maungawera Flat': [],
    }
    runs = {}
    for zone, pump_increases in base_runs.items():
        runs[zone] = [max_allo[zone] * pinc for pinc in pump_increases]

    run_all_grid_allocation_scens(name='test_grid_run', local_cores=local_cores,
                                  pump_rate=runs, rm_remote_files=False)

    # todo what are increased pumping values to use, should I make this more standartised (look at pumping in the zone)
    # todo roughly 1hr on wanganui, 5 hrs on tuke... need to shorten...
    raise NotImplementedError


if __name__ == '__main__':
    # test_indvidual()
    # test_ind_mp()
    # test_grid_allo()
    how_long_per_run()  # todo re-run now that it will likely converge!
