"""
created matt_dumont 
on: 8/03/23
"""
from Scenarios.allocation_scenarios import run_all_grid_allocation_scens, zones_to_model


def test_grid_allo():
    runs = {}
    for z in zones_to_model:
        runs[z] = [5000, 10000]

    run_all_grid_allocation_scens(name='test_grid_run', local_cores=2, pump_rate=runs)


def main_grid_allo():
    raise NotImplementedError


if __name__ == '__main__':
    test_grid_allo()
