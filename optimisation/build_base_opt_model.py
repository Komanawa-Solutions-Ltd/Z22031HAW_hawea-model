"""
created matt_dumont 
on: 27/09/22
"""
import time
from pathlib import Path
import numpy as np
from model_build.modflow_model import build_model
from model_build.project_model_tools import smt, get_starting_heads
from optimisation.optimisation_period import tdis
from model_parameterisation.static_params import ss, vka
from model_parameterisation.pilot_points import interpolate_kh_pilot_points, interpolate_sy_pilot_points
from model_parameterisation.inital_parametersiation import get_inital_sy, get_inital_kh, \
    get_initial_riv_conductance, get_race_multiplier, get_hillslope_multiplier, get_initial_rch_mult
from model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_str_data
from targets_and_sensitive_sites.model_output import process_model_output
from project_base import proj_root
import py7zr
from optimisation.model_utils_for_forward_run import build_run_model, write_base_param_file


def test_times():
    t = time.time()
    interpolate_kh_pilot_points(get_inital_kh(return_just_start=True))
    print(f'took {time.time() - t}s for interpolate_kh_pilot_points')
    t = time.time()
    interpolate_sy_pilot_points(get_inital_sy(return_just_start=True))
    print(f'took {time.time() - t}s for interpolate_sy_pilot_points')
    t = time.time()
    get_starting_heads()
    print(f'took {time.time() - t}s for get_starting_heads')
    t = time.time()
    get_rch_data(tdis, get_initial_rch_mult(True))
    print(f'took {time.time() - t}s for get_rch_data')
    t = time.time()
    get_ghb_data(tdis)
    print(f'took {time.time() - t}s for get_ghb_data')
    t = time.time()
    get_str_data(tdis, riv_params=get_initial_riv_conductance(True))
    print(f'took {time.time() - t}s for get_riv_data')
    t = time.time()
    get_well_data(tdis,
                  hill_param=get_hillslope_multiplier(True),
                  race_param=get_race_multiplier(True))
    print(f'took {time.time() - t}s for get_well_data')
    t = time.time()


def build_initial_model(model_name, model_ws,
                        exe_name='mfnwt', run_model=False):
    t = time.time()
    oc_spd = {(0, 0): ['save head', 'save budget']}
    oc_spd.update({(p, 6): ['save head', 'save budget'] for p in tdis.pers[1:]})
    write_base_param_file(outdir=model_ws)
    # keynote other steps if I end up with them
    build_run_model(
        model_name, model_ws,
        kh_param=get_inital_kh(return_just_start=True),
        sy_param=get_inital_sy(return_just_start=True),
        riv_params=get_initial_riv_conductance(True),
        hill_param=get_hillslope_multiplier(True),
        race_param=get_race_multiplier(True),
        rch_param=get_initial_rch_mult(True)
    )


def check_for_dry(hds_file):
    import flopy
    hds = flopy.utils.HeadFile(hds_file).get_alldata()[:, 0]
    dry_hds = hds < -100
    out = dry_hds.sum(axis=0).astype(float)
    out[np.isclose(out, 0)] = np.nan
    smt.plot.plt_matrix(out, base_map=True)
    print(np.where(dry_hds.any(axis=(1, 2))))
    smt.io.array_to_raster(hds_file.parent.joinpath('dry_hds.tif'), out, 0)
    smt.plot.show()


if __name__ == '__main__':
    # see if adding daily steps helps speed up the run time, nope it basically doubled the time
    model_ws = proj_root.joinpath('optimisation/pre_opt_model')
    model_ws.mkdir(exist_ok=True)
    model_name = 'pre_opt'
    build_initial_model(model_name=model_name, model_ws=model_ws,
                        run_model=True)
    process_model_output(model_ws, model_ws.joinpath(f'{model_name}.hds'), True)

    # compress model files with 7zip
    filelist = list(model_ws.glob(f'{model_name}.*'))
    with py7zr.SevenZipFile(model_ws.joinpath(f'{model_name}.7z'), 'w') as archive:
        for p in filelist:
            print(f'zipping: {p.name}')
            archive.write(p)

    # delete files
    for f in filelist:
        f.unlink()

# todo re-run with final structure!
