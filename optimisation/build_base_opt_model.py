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
    get_initial_riv_conductance, get_race_multiplier, get_hillslope_multiplier
from model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_riv_data
from targets_and_sensitive_sites.model_output import process_model_output


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
    get_rch_data(tdis)
    print(f'took {time.time() - t}s for get_rch_data')
    t = time.time()
    get_ghb_data(tdis)
    print(f'took {time.time() - t}s for get_ghb_data')
    t = time.time()
    get_riv_data(tdis, riv_params=get_initial_riv_conductance(True))
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
    oc_spd = {(p, 0): ['save head', 'save budget'] for p in tdis.pers}
    # keynote other steps if I end up with them
    build_model(smt=smt,
                tdis=tdis,
                oc_spd=oc_spd,
                exe_name=exe_name,
                model_name=model_name,
                model_ws=model_ws,
                hk=interpolate_kh_pilot_points(get_inital_kh(return_just_start=True)),
                vka=vka,
                layer_avg=0,
                ss=ss,
                sy=interpolate_sy_pilot_points(get_inital_sy(return_just_start=True)),
                strt=get_starting_heads(),
                chani=1,
                rch=get_rch_data(tdis),
                ghb_spd=get_ghb_data(tdis),
                riv_spd=get_riv_data(tdis, riv_params=get_initial_riv_conductance(True)),
                well_spd=get_well_data(tdis,
                                       hill_param=get_hillslope_multiplier(True),
                                       race_param=get_race_multiplier(True)),
                options='COMPLEX',
                nwt_kwargs={'maxiterout': 1000, 'maxitinner': 100},
                hani=None,
                mfv='mfnwt',
                run_model=run_model,
                verbose=True,
                t=t,
                noprint=True)


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
    # todo run in repo!
    model_ws = Path.home().joinpath('Downloads/test_model')
    model_name = 'test'
    build_initial_model(model_name=model_name, model_ws=model_ws,
                        run_model=True)
    process_model_output(model_ws, model_ws.joinpath(f'{model_name}.hds'), True)
    # todo compress model files! and remove the archive
