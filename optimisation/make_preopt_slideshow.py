"""
created matt_dumont 
on: 7/10/22
"""
from project_base import proj_root
from pathlib import Path
from PyPDF2 import PdfMerger, PdfReader

base_path = proj_root.joinpath('optimisation/pre_optimisation_plots_pdf')

params = [
    'parameterisation/parameter_overview.pdf',
    'parameterisation/river_conductance.pdf',
    'parameterisation/kh_sy_params.pdf',
    'parameterisation/inital_trans.pdf',
    'parameterisation/example_rbf.pdf',
]

stress_period_data = [
    'stress_period_data/River_profile.pdf',
    'stress_period_data/Monthly_mean_camphill_levels.pdf',
    'stress_period_data/Monthly_mean_clutha_levels.pdf',
    'stress_period_data/lake_time.pdf',
    'stress_period_data/Monthly_mean_lake_levels.pdf',
    'stress_period_data/rch_time.pdf',
    'stress_period_data/well_hill_time.pdf',
    'stress_period_data/well_race_time.pdf',
    'stress_period_data/well_pump_time.pdf',
]

targets = [
    'targets/spatial_head_targets.pdf',
    'targets/river_conductance.pdf',
    'targets/high_freq_temporal_targets.pdf',
    'targets/low_freq_temporal_targets.pdf',
    'indicative_target_times/target_time_correlations_Mutual info.pdf',
    'indicative_target_times/9_targ_shifts.pdf',
    'indicative_target_times/all_targ_shifts.pdf',
]

ss_wb = [
    'steady_state_water_budget/water_budget.pdf',
    'steady_state_water_budget/spatial_mean_recharge.pdf',
    'steady_state_water_budget/spatial_start_heads.pdf',
]

era5_correction = [
    'era5_correction/era5_data_correction.pdf',
    'era5_correction/era5_rch_correction.pdf',
]
hillslope_correction = [
    'hillslope_inflow_correction/malf_fit.pdf',
    'hillslope_inflow_correction/flow_fitting.pdf',
]

model_structure = [
    'model_structure/Model bottoms.pdf',
    'model_structure/Model thickness.pdf',
    'model_structure/Model tops.pdf',
    'zones.pdf',
    'cross_sections/Bespoke_cross_section.pdf',
    'cross_sections/Cross_section_Row_100.pdf',
    'cross_sections/Cross_section_Row_170.pdf',
    'cross_sections/Cross_section_Row_50.pdf',
    'cross_sections/Cross_section_column_100.pdf',
    'cross_sections/Cross_section_column_80.pdf',
]
temporal = [
    'determine_opt_period/monthy_weekly_delta_to_mean_all.pdf',
    'determine_opt_period/monthy_weekly_delta_to_mean_g40_0367.pdf',
]

boundary_conditions = [
    'boundary_condition_locations/Lake_cells.pdf',
    'boundary_condition_locations/River_cells.pdf',
    'boundary_condition_locations/Race_Losses.pdf',
    'boundary_condition_locations/Hillside_Inflows.pdf',
    'boundary_condition_locations/Abstraction.pdf',
]


def build_slideshow(outpath):
    sections = [
        'model_structure',
        'temporal',
        'boundary_cond',

        'era5_correction',
        'hillslope_correction',

        'ss_wb',
        'spd',

        'initial model',

        'targets',
        'objective_function',

        'params',

        # other
    ]

    figures = {
        'model_structure': model_structure,
        'temporal': temporal,
        'boundary_cond': boundary_conditions,

        'ss_wb': ss_wb,
        'spd': stress_period_data,

        'targets': targets,
        'objective_function': ['obj_function.pdf'],

        'params': params,
        'initial model': ['model_stats.pdf'],

        # other
        'era5_correction': era5_correction,
        'hillslope_correction': hillslope_correction,

    }
    pos = 0
    file = PdfMerger()
    for s in sections:
        fig = figures[s]
        for i, f in enumerate(fig):
            use_path = base_path.joinpath(f)
            loaded = PdfReader(use_path)
            file.merge(position=pos, fileobj=loaded,
                       outline_item=f'{s}-{i}: {use_path.name.replace(".pdf", "")}')
            pos += loaded.numPages

    file.write(outpath)


if __name__ == '__main__':
    build_slideshow(Path.home().joinpath('Downloads/model_overview_slideshow.pdf'))
