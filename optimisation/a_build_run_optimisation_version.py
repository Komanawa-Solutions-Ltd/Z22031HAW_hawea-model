"""
created matt_dumont 
on: 1/11/22
"""

# this allows testing multiple paramters sets/structures quickly, use git branches for some of this.
from pathlib import Path
from optimisation.model_utils_for_forward_run import _get_param_data
from project_base import unbacked_dir
import shutil
import matplotlib.pyplot as plt


def recalc_model_build(rerun_rushton=False):
    from model_build.project_model_tools import smt, get_ibound, get_elv_db, \
        get_lake_array, get_starting_heads
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
    from model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_riv_data
    from optimisation.optimisation_period import tdis
    from model_parameterisation.inital_parametersiation import get_initial_rch_mult

    get_ibound(recalc=True)
    get_elv_db(recalc=True)
    get_starting_heads(recalc=True)

    get_param_zones(recalc=True)
    get_lake_array(recalc=True)
    get_model_zones(recalc=True)

    get_river_loc_data(recalc=True)
    get_river_stage_data(None, None, recalc=True)
    get_all_wells(recalc=True)
    get_lake_hawea_loc(recalc=True)
    get_race_locs(recalc=True)
    print('#####here')
    get_hillside_catchment_locs(recalc=True)
    get_hillside_flows(None, None, recalc=True)
    get_well_flowmeter_mapper(recalc=True)
    get_historical_pumping_data(None, None, recalc=True)
    get_soil_classes(recalc=True)
    get_rch_data(tdis, rch_param=get_initial_rch_mult(True), recalc=True)
    get_ghb_data(tdis, recalc=True)
    get_well_data(tdis, hill_param={'south_east': 1, 'main': 1, 'maungawera': 1, }, race_param={'all': 1}, recalc=True)
    if rerun_rushton:
        for k in [True, False]:
            get_era5_land(correct=True, recalc=True)
            get_historical_rch_model_results(data_source='historical', limited_irrigation=k, recalc=True)
            get_historical_rch_model_results(data_source='era5', limited_irrigation=k, recalc=True)
            get_corrected_historical_era5_rch(None, None, recalc=True, limited_irrigation=k)
    plt.close('all')


def recalc_param_targets():
    from model_parameterisation.pilot_points import get_pilot_point_locations, get_rch_pilot_point_locations
    from targets_and_sensitive_sites.riv_gain_loss_targets import get_riv_target_locs
    from targets_and_sensitive_sites.head_targets import get_2011_piezo_survey, get_all_hds_targets
    from targets_and_sensitive_sites.senstive_sites import get_wetlands
    from targets_and_sensitive_sites.get_indicative_times import get_indicative_times_v2
    from optimisation.optimisation_period import tdis

    get_riv_target_locs(recalc=True)
    get_2011_piezo_survey(recalc=True)
    get_wetlands(recalc=True)
    get_indicative_times_v2(recalc=True)
    get_all_hds_targets(tdis, recalc=True)
    get_pilot_point_locations(recalc=True)
    get_rch_pilot_point_locations(recalc=True)


def build_test_model(model_ws, notes, recalc=True):
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
    param_data.to_csv(model_ws.joinpath('parameters.dat'), sep='\t', header=False, index=False)

    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = read_param_data(model_ws)
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


if __name__ == '__main__':
    # todo version here to run pest and base model
    #  for structural changes re-run build_base_opt_model.py, pre_optimisation_overview.py
    #  The pest optimisation will be run in unbacked_dir.joinpath(mversion,'optimisation')
    #  dont forget to update the git branch on tuke
    # make a new branch on major structural shifts
    mversion = 'up_init_kh'
    test_notes = """
    branch: structure_v2
    previous optimisation: structure_v2_init
    same as structure_v2_init, but set kh start to 30, allow rch to go down to .7
    """

    # todos for current version
    # todo run, look over pre_optimisation_overviews
    # todo look at river stage interpolation, particularly at the clutha near the bottom.
    # todo remove near river abstraction... its problematic and stopping the river conductnace from changing
    # todo consider making a new hds group (problematic vs non-problematic regular)
    # todo H_g40_0120  (mean c. 314m) is very close (1808m) to H_g40_0367 (mean 319)
    # todo could look at setting inital kh from scott (roughly)
    #   elevation between the two are 5 m different  all_wells.loc[['g40_0367', 'g40_0120']].transpose()
    #   might be fine???

    recalc = False
    build_model = True
    build_pest = True
    safemode = True

    test_path = unbacked_dir.joinpath(mversion, 'base_model')
    test_path.parent.mkdir(exist_ok=True)
    # build base model
    if build_model:
        build_test_model(model_ws=test_path, notes=test_notes, recalc=recalc)

    # build pest
    if build_pest:
        from optimisation.build_optimisation import raw_pest, BeopestManager

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
        pest_file = raw_pest(name='opt', pst_dir=pdir, noptmax=50,
                             model_template_dir=test_path)
        man = BeopestManager(
            pest_file=pest_file,
            num_cores={
                '100.124.148.71': None,
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

    # todo thoughts after first round:
    #  I need to see what is causing the model to fall over as it is not suitably optimised
    #  I should consider removing some of near river pumping wells as I think this may be causing a lot of my challenges
    #  carpet drains in mangawera, talk to Jens about streams

# todo time for optimisation???
