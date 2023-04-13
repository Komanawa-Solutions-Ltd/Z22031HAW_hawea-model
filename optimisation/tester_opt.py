"""
created matt_dumont 
on: 27/10/22
"""
import shutil
from pathlib import Path
from project_base import unbacked_dir
from optimisation.a_build_run_optimisation_version import build_test_model

if __name__ == '__main__':
    mversion = 'test_pest'
    test_notes = """
    just a test for beopest
    """

    build_model = True
    build_pest = True
    safemode = True

    test_path = unbacked_dir.joinpath(mversion, 'base_model')
    test_path.parent.mkdir(exist_ok=True)
    # build base model
    if build_model:
        build_test_model(model_ws=test_path, notes=test_notes)

    # build pest
    if build_pest:
        from optimisation.build_optimisation import raw_pest, BeopestManager # keynote private repo

        pdir = unbacked_dir.joinpath(mversion, 'Optimisations')

        if pdir.exists() and safemode:
            temp = input(f'this will erase all files in: {pdir}\ndo you really want to do this y/n?')
            if 'y' not in temp.lower():
                raise KeyboardInterrupt(f'stopped to prevent deletion of all files in {pdir}')
        for fn in pdir.glob('*'):
            if fn.is_dir():
                shutil.rmtree(fn)
            else:
                fn.unlink()
        # copy notes over, as well as version!
        pest_file = raw_pest(name='opt', pst_dir=pdir, noptmax=1,
                             model_template_dir=test_path)

        man = BeopestManager(
            pest_file=pest_file,
            num_cores={
                '100.124.148.71': 2,
                '100.121.150.68': None,
            },
            base_path={
                '100.124.148.71': None,
                '100.121.150.68': Path('/media/matt_dumont/data/mh_unbacked/hawea').joinpath(pdir.name),
            },

        )
        man.write_beopest_run_manager()
        # copy across version and notes
        with open(pdir.joinpath('1_opt_notes_version.txt'), 'w') as f:
            f.write(f'version = {test_path.name}\n')
        f.write(test_notes)
