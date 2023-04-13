"""
created matt_dumont 
on: 7/03/23
"""
import sys

print(sys.path)
import warnings
from pandas.errors import PerformanceWarning
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=PerformanceWarning)
from pathlib import Path
import pickle
import socket
from Scenarios.allocation_scenarios import run_grid_allocation_scenario_mp
from dummy_packages.run_multiprocess import run_multiprocess
# keynote need 2gb ram / cpu

if __name__ == '__main__':
    pickle_path = Path(sys.argv[1])
    run_name, base_run_path, num_cores, runs = pickle.load(pickle_path.open('rb'))
    if len(runs) != 0:
        print(f'running: {run_name} on {socket.gethostname()}')
        pool_outputs = run_multiprocess(run_grid_allocation_scenario_mp, runs, num_cores=num_cores)
        print('\n'.join([str(e) for e in pool_outputs]))
