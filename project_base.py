"""
Template created by matt_dumont
on: 22/03/22
"""
from pathlib import Path
from kslcore import KslEnv

project_name = 'hawea'
proj_root = Path(__file__).parent  # base of git repo

# keynote this is the root for the optimization, to allow me to keep working on the repo while an opt is running
opt_proj_root = proj_root.parent.joinpath('hawea_model_optimisation_NO_EDIT')
opt_model_tools = proj_root.parent.joinpath('modflow_tools_haw_NO_EDIT')

project_dir = KslEnv.shared_gdrive.joinpath('YMULT_small_projects/Z22031HAW_hawea-model')
unbacked_dir = KslEnv.unbacked.joinpath(project_name)
unbacked_dir.mkdir(exist_ok=True)

modelling_dir = project_dir.joinpath('Modelling')
base_model_build_data_dir = proj_root.joinpath('model_build/base_data')
processed_model_build_data_dir = proj_root.joinpath('model_build/processed_input_data')

base_target_dir = proj_root.joinpath('targets_and_sensitive_sites/base_data')
processed_target_dir = proj_root.joinpath('targets_and_sensitive_sites/processed_data')

base_param_dir = proj_root.joinpath('model_parameterisation/base_data')
processed_param_dir = proj_root.joinpath('model_parameterisation/processed_data')

base_scen_dir = proj_root.joinpath('Scenarios/base_data')
processed_scen_dir = proj_root.joinpath('Scenarios/processed_input_data')

# todo check the ability to run this model without access to modelling_dir by setting modelling_dir=None
# todo label all things that need the external datasets via docstring
# todo write up a users guide in the README.md
