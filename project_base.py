"""
Template created by matt_dumont
on: 22/03/22
"""
from pathlib import Path
from kslcore import KslEnv

project_name = 'hawea'
proj_root = Path(__file__).parent  # base of git repo
project_dir = KslEnv.shared_gdrive.joinpath('YMULT_small_projects/Z22031HAW_hawea-model')
unbacked_dir = KslEnv.unbacked.joinpath(project_name)
unbacked_dir.mkdir(exist_ok=True)

modelling_dir = project_dir.joinpath('Modelling')
base_model_build_data_dir = proj_root.joinpath('model_build/base_data')
processed_model_build_data_dir = proj_root.joinpath('model_build/processed_input_data')

base_target_dir = proj_root.joinpath('targets_and_sensitive_sites/base_data')
processed_target_dir = proj_root.joinpath('targets_and_sensitive_sites/processed_data')

# todo check the ability to run this model without access to modelling_dir by setting modelling_dir=None
# todo label all things that need the external datasets via docstring
