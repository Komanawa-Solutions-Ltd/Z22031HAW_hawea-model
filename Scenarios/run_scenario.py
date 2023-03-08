"""
created matt_dumont 
on: 7/03/23
"""
import sys

print(sys.path)
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
from pathlib import Path
import pickle
import socket
from Scenarios.allocation_scenarios import run_grid_allocation_scenario_mp
from run_managers.run_multiprocess import run_multiprocess

if __name__ == '__main__':
    pickle_path = Path(sys.argv[1])
    run_name, base_run_path, num_cores, runs = pickle.load(pickle_path.open('rb'))
    if len(runs) != 0:
        print(f'running: {run_name} on {socket.gethostname()}')
        pool_outputs = run_multiprocess(run_grid_allocation_scenario_mp, runs, num_cores=num_cores)
        print('\n'.join([str(e) for e in pool_outputs]))
