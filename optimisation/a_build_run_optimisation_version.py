"""
created matt_dumont 
on: 1/11/22
"""

# this allows testing multiple paramters sets/structures quickly, use git branches for some of this.
from pathlib import Path

import pandas as pd
from model_build.project_model_tools import smt
from optimisation.model_utils_for_forward_run import _get_param_data, read_param_data
from project_base import unbacked_dir, opt_proj_root, opt_model_tools
import shutil
import matplotlib.pyplot as plt


def recalc_model_build(rerun_rushton=False):
    from model_build.project_model_tools import smt, get_ibound, get_elv_db, \
        get_lake_array, get_starting_heads, get_2d_moraine, get_layer_pinchout_area, get_xsection_points
    from model_build.supporting_data_analysis.river_data import get_river_stage_data, get_river_loc_data
    from model_build.supporting_data_analysis.recharge_model import get_historical_rch_model_results, get_soil_classes, \
        get_era5_land, get_corrected_historical_era5_rch
    from model_build.supporting_data_analysis.lake_data import get_lake_hawea_loc
    from model_build.supporting_data_analysis.irrigation_race_losses import get_race_locs
    from model_build.supporting_data_analysis.hillside_inflows import get_hillside_catchment_locs, get_catchment_areas, \
        get_luggate_catchment_area, get_hillside_flows
    from model_build.supporting_data_analysis.get_pumping_data import get_historical_pumping_data
    from model_build.supporting_data_analysis.map_flowmeter_to_wells import get_well_flowmeter_mapper
    from model_build.supporting_data_analysis.all_wells import get_all_wells
    from model_build.zones import get_param_zones, get_model_zones
    from model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_str_data
    from optimisation.optimisation_period import tdis
    from model_parameterisation.inital_parametersiation import get_initial_rch_mult

    get_ibound(recalc=True)
    get_elv_db(recalc=True)
    get_xsection_points(True)
    get_2d_moraine(True)
    get_layer_pinchout_area(recalc=True)

    get_param_zones(recalc=True)
    get_lake_array(recalc=True)
    get_model_zones(recalc=True)

    get_river_loc_data(recalc=True)
    get_river_stage_data(None, None, recalc=True)
    get_all_wells(recalc=True)
    get_lake_hawea_loc(recalc=True)
    get_race_locs(recalc=True)
    get_hillside_catchment_locs(recalc=True)
    get_hillside_flows(None, None, recalc=True)
    get_well_flowmeter_mapper(recalc=True)
    get_historical_pumping_data(None, None, recalc=True)
    get_soil_classes(recalc=True)
    get_rch_data(tdis, rch_param=get_initial_rch_mult(True), recalc=True)
    get_ghb_data(tdis, recalc=True)
    get_well_data(tdis, hill_param={'se': 1, 'main': 1, 'mang': 1, }, race_param={'all': 1}, recalc=True)
    if rerun_rushton:
        for k in [True, False]:
            get_era5_land(correct=True, recalc=True)
            get_historical_rch_model_results(data_source='historical', limited_irrigation=k, recalc=True)
            get_historical_rch_model_results(data_source='era5', limited_irrigation=k, recalc=True)
            get_corrected_historical_era5_rch(None, None, recalc=True, limited_irrigation=k)
    plt.close('all')


def recalc_param_targets():
    from model_parameterisation.pilot_points import get_pilot_point_locations, get_spatial_temporal_rch_mult
    from model_parameterisation.inital_parametersiation import get_initial_rch_mult
    from targets_and_sensitive_sites.riv_gain_loss_targets import get_riv_target_locs, get_hawea_gain_loss_nper
    from targets_and_sensitive_sites.head_targets import get_2011_piezo_survey, get_all_hds_targets
    from targets_and_sensitive_sites.senstive_sites import get_wetlands
    from targets_and_sensitive_sites.get_indicative_times import get_indicative_times_v2
    from optimisation.optimisation_period import tdis
    from model_parameterisation.plot_parameter_names import plot_parameter_locator

    get_riv_target_locs(recalc=True)
    get_hawea_gain_loss_nper(tdis, recalc=True)
    get_2011_piezo_survey(recalc=True)
    get_wetlands(recalc=True)
    get_indicative_times_v2(recalc=True)
    get_all_hds_targets(tdis, recalc=True)
    get_pilot_point_locations(recalc=True)
    get_spatial_temporal_rch_mult(get_initial_rch_mult(True), tdis, recalc=False)
    plot_parameter_locator()


def build_test_model(model_ws, notes, start_param_vals=None, recalc=True):
    from targets_and_sensitive_sites.model_output import process_model_output
    from optimisation.model_utils_for_forward_run import read_param_data, build_run_model

    if recalc:
        recalc_param_targets()
        recalc_model_build()

    plot = True
    name = 'opt_model'
    model_ws.mkdir(exist_ok=True)
    with open(model_ws.joinpath('0_new_model_notes'), 'w') as f:
        f.write(notes)

    param_data = _get_param_data()
    if start_param_vals is not None:
        assert isinstance(start_param_vals, dict)
        all_params = param_data.loc[:, 'name']
        assert len(all_params) == len(pd.unique(all_params))
        assert set(all_params) == set(start_param_vals.keys())
        start_vals = [start_param_vals[k] for k in all_params]
        param_data.loc[:, 'start'] = start_vals
    param_data.to_csv(model_ws.joinpath('parameters.dat'), sep='\t', header=False, index=False)

    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = read_param_data(model_ws)
    print('running base model')
    build_run_model(
        model_name=name, model_ws=model_ws,
        kh_param=kh_param,
        sy_param=sy_param,
        riv_params=riv_params,
        hill_param=hill_param,
        race_param=race_param,
        rch_param=rch_param
    )
    process_model_output(model_ws=model_ws,
                         hds_file=model_ws.joinpath(f'{name}.hds'),
                         plot=plot)
    return model_ws.joinpath(f'{name}.list')


# todo version here to run pest and base model
#  for structural changes pre_optimisation_overview.py
#  The pest optimisation will be run in unbacked_dir.joinpath(mversion,'optimisation')
#  dont forget to update the git branch on tuke
# make a new branch on major structural shifts
mversion = 'init_3d_v1'
previous_mversion = 'init_v12'
branch = '3d_v1'
previous_branch = 'structure_v12'
# todo to use previous parameters, put file here, else None
param_file = None
notes = f""" 
* move to 3d structure (near lake)
* remove the slope fixer on the east side
* remove additional parameterization of v12
* Address the 3d moraine issues in structure
* 3 layers the bottom two pinch out against the bottom of the model.
* Add abrupt parameter change at terrace interface
* Remove from dam to “dam control” road from model (e.g. no flow)


"""
noptmax = 300
recalc = True
build_model = True
build_pest = True
safemode = True
local_cores = None  # set to a lower number of core if you plan on using the local machine at the same time as a run

# todo fill above here

if param_file is not None:
    start_param = read_param_data(parameter_file=param_file,
                                  return_individual=False,
                                  format='pest')
    str_sps = '\n'.join([f'* {k}: {v}' for k, v in start_param.items()])
else:
    start_param = None
    str_sps = 'n/a'

test_notes = f"""
mversion = {mversion}
branch: {branch}
previous optimisation: {previous_mversion}
previous branch: {previous_branch}

{notes}

unique start params from: {param_file}
unique start prams: 
{str_sps}

"""
if __name__ == '__main__':
    test_path = unbacked_dir.joinpath(branch, mversion, 'base_model')
    test_path.parent.mkdir(exist_ok=True, parents=True)
    # build base model
    if build_model:
        listf = build_test_model(model_ws=test_path, start_param_vals=start_param, notes=test_notes, recalc=recalc)
        assert smt.modelchecks.modflow_converged(listf)

    # build pest
    if build_pest:
        from optimisation.build_optimisation import raw_pest
        from run_managers.beopest_manager import BeopestManager

        pdir = unbacked_dir.joinpath(branch, mversion, 'Optimisations')

        if pdir.exists() and safemode:
            temp = input(f'this will erase all files in: {pdir}\ndo you really want to do this y/n?')
            if 'y' not in temp.lower():
                raise KeyboardInterrupt(f'stopped to prevent deletion of all files in {pdir}')
        for fn in pdir.glob('*'):
            if fn.is_dir():
                shutil.rmtree(fn)
            else:
                fn.unlink()
        pest_file, pst = raw_pest(name='opt', pst_dir=pdir, noptmax=noptmax,
                                  model_template_dir=test_path, start_param_vals=start_param)
        man = BeopestManager(
            ips=['100.124.148.71', '100.121.150.68'],
            pest_file=pest_file,
            num_cores={
                '100.124.148.71': local_cores,
                '100.121.150.68': None,
            },
            base_path={
                '100.124.148.71': None,
                '100.121.150.68': Path('/media/matt_dumont/data/mh_unbacked/hawea').joinpath(
                    pdir.relative_to(unbacked_dir)),
            },
            prepend_bash_commands={
                '100.124.148.71': [
                    f"cd {opt_model_tools} ; git fetch --all ; git reset --hard origin/Z22031HAW_hawea-model",
                    f"cd {opt_proj_root} ; git fetch --all ; git reset --hard origin/{branch}"
                ],
                '100.121.150.68': [
                    f"cd {opt_model_tools} ; git fetch --all ; git reset --hard origin/Z22031HAW_hawea-model",
                    f"cd {opt_proj_root} ; git fetch --all ; git reset --hard origin/{branch}"
                ]
            }
        )
        man.write_beopest_run_manager()
        man.write_pest_check_sh(pst, test_parfiles=[pdir.joinpath('trial.par')])
        # copy across version and notes
        with open(pdir.joinpath('1_opt_notes_version.txt'), 'w') as f:
            f.write(f'version = {test_path.name}\n')
            f.write(test_notes)
        print(f'pest files written, pest dir: {pdir}')
