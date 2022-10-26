"""
created matt_dumont 
on: 27/10/22
"""
import shutil
from pathlib import Path
from optimisation.build_optimisation import raw_pest
from model_tools.beopest_manager import BeopestManager
from project_base import unbacked_dir

if __name__ == '__main__':
    pdir = unbacked_dir.joinpath('test_pest')
    for f in pdir.glob('*'):
        if f.is_dir():
            shutil.rmtree(f)
        else:
            f.unlink()

    pest_file = raw_pest(name='opt', pst_dir=pdir, noptmax=2, write_trial_paramfile=False)
    man = BeopestManager(
        pest_file=pest_file,
        num_cores={
            '100.124.148.71': 2,
            '100.67.70.2': None,
        },
        base_path={
            '100.124.148.71': None,
            '100.67.70.2': Path('/media/matt_dumont/data/mh_unbacked/hawea').joinpath(pdir.name),
        },
        user_names=None,
        short_names=None,
        port=4004,
        host_machine=None,
        use_tailscale=True)
    man.write_beopest_run_manager()
