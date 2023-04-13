"""
created matt_dumont 
on: 12/03/23
"""
import shutil
import sys
import time

print(sys.path)
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
from pathlib import Path
import pickle
import socket
from dummy_packages.run_multiprocess import run_multiprocess


def mp_runner(kwargs):
    host = socket.gethostname()
    brd = Path(kwargs.get('local_run_dir'))
    zone = kwargs.get('zone')
    total_increase = kwargs.get('total_increase')
    model_name = f'{zone}_{int(total_increase):010d}'
    base_outputs_dir = Path(kwargs.get('base_outputs_dir'))
    if base_outputs_dir.exists():
        shutil.rmtree(base_outputs_dir)
    logfile = base_outputs_dir.joinpath(f'0_{model_name}.log')
    logfile.parent.mkdir(exist_ok=True, parents=True)
    with logfile.open('w') as f:
        f.write(f'host: {host}')
        f.write(f'model_name: {model_name}')
        f.write(f'model_ws: {brd.joinpath(model_name)}')
        f.write(f'outdir: {base_outputs_dir.joinpath(model_name)}')
    time.sleep(30)


if __name__ == '__main__':
    pickle_path = Path(sys.argv[1])
    run_name, base_run_path, num_cores, runs = pickle.load(pickle_path.open('rb'))
    if len(runs) != 0:
        print(f'running: {run_name} on {socket.gethostname()}')
        pool_outputs = run_multiprocess(mp_runner, runs, num_cores=num_cores)
        print('\n'.join([str(e) for e in pool_outputs]))
