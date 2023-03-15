"""
Template created by matt_dumont
on: 22/03/22
"""
import warnings
from pathlib import Path

project_name = 'hawea'

try:
    from kslcore import KslEnv  # package to allow access to internal KSL files.

    project_dir = KslEnv.shared_gdrive.joinpath('YMULT_small_projects/Z22031HAW_hawea-model')
    unbacked_dir = KslEnv.unbacked.joinpath(project_name)
    modelling_dir = project_dir.joinpath('Modelling')

except ImportError:
    warnings.warn('kslcore not installed,\n'
                  'some processes may not be able to be re-run as data is missing.\n'
                  'These processes should only include various outputs and re-calculating: \n'
                  '* model_build.supporting_data_analysis.hillside_inflows.get_luggate_catchment_area\n'
                  '* model_build.supporting_data_analysis.hillside_inflows.get_catchment_areas\n'
                  '* model_build.supporting_data_analysis.all_wells.get_all_wells\n'
                  '* model_build.project_model_tools.simplify_upper_clutha_dem\n'
                  '* model_build.project_model_tools.simplify_hawea_dem\n')
    unbacked_dir = Path.home().joinpath('Hawea_model_unbacked')
    modelling_dir = unbacked_dir.joinpath('modelling')

unbacked_dir.mkdir(exist_ok=True)
proj_root = Path(__file__).parent  # base of git repo

# keynote this is the root for the running optimization, to allow me to keep working on the repo while an opt is running
opt_proj_root = proj_root.parent.joinpath('hawea_model_optimisation_NO_EDIT')
opt_model_tools = proj_root.parent.joinpath('modflow_tools_haw_NO_EDIT')

base_model_build_data_dir = proj_root.joinpath('model_build/base_data')
processed_model_build_data_dir = proj_root.joinpath('model_build/processed_input_data')

base_target_dir = proj_root.joinpath('targets_and_sensitive_sites/base_data')
processed_target_dir = proj_root.joinpath('targets_and_sensitive_sites/processed_data')

base_param_dir = proj_root.joinpath('model_parameterisation/base_data')
processed_param_dir = proj_root.joinpath('model_parameterisation/processed_data')

base_scen_dir = proj_root.joinpath('Scenarios/base_data')
processed_scen_dir = proj_root.joinpath('Scenarios/processed_input_data')


butterfield_dir = proj_root.joinpath('Scenarios/wetland_setback_butterfield')

# todo write up a users guide in the README.md
