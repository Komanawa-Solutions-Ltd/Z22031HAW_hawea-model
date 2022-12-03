"""
created matt_dumont 
on: 2/12/22
"""
import sys

print(sys.path)
from pathlib import Path
import pickle
import socket
from optimisation.manual_optimisations.manual_optimisation import _run_model_mp
from run_managers.run_multiprocess import run_multiprocess

if __name__ == '__main__':
    pickle_path = Path(sys.argv[1])
    run_name, base_run_path, num_cores, runs = pickle.load(pickle_path.open('rb'))
    if len(runs) != 0:
        print(f'running: {run_name} on {socket.gethostname()}')
        pool_outputs = run_multiprocess(_run_model_mp, runs, num_cores=num_cores)
        print('\n'.join([str(e) for e in pool_outputs]))

        # remove unnecessary files
        files = Path(base_run_path).glob('**/*.*')
        for p in files:
            if p.is_dir():
                continue
            if p.name.split('.')[-1] in ['list', 'dat', 'png', 'p', 'log']:
                continue
            if p.name in ['param_overview.txt', 'mse.csv']:
                continue
            p.unlink()
