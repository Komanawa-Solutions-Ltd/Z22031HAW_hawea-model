"""
created matt_dumont 
on: 1/03/23
"""

# todo compare boundary sensitivity (e.g. rch only vs lake only etc.)

from project_base import proj_root
from Scenarios.scenario_outputs import quantile_plots, q_qplots, compare_scenarios
from Scenarios.model_info_scenarios import scen_tdis

data_dir = proj_root.joinpath('Scenarios/model_info_scen_results')
outdir = data_dir.joinpath('0_results')
outdir.mkdir(exist_ok=True)

linestyle_tuple = [
    ('solid', 'solid'),
    ('dotted', (0, (1, 1))),
    ('dashed', (0, (5, 5))),
    ('dashdotted', (0, (3, 5, 1, 5))),
    ('loosely dashdotted', (0, (3, 10, 1, 10))),
    ('loosely dashed', (0, (5, 10))),
    ('loosely dotted', (0, (1, 10))),

    ('densely dashdotted', (0, (3, 1, 1, 1))),
    ('long dash with offset', (5, (10, 3))),
    ('densely dashed', (0, (5, 1))),

    ('dashdotdotted', (0, (3, 5, 1, 5, 1, 5))),
    ('loosely dashdotdotted', (0, (3, 10, 1, 10, 1, 10))),
    ('densely dashdotdotted', (0, (3, 1, 1, 1, 1, 1)))]


def compare_nat_opt_long():
    use_outdir = outdir.joinpath('nat_opt_long')
    use_outdir.mkdir(exist_ok=True)
    use_keys = ['long_current', 'long_nat', 'optimised']  # todo make optimised in this style!
    all_lss = {k: l[-1] for k, l in zip(use_keys, linestyle_tuple)}
    data_dirs = {k: data_dir.joinpath(k) for k in use_keys}
    quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'))
    compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                      tdis=scen_tdis,
                      data_dirs=data_dirs,
                      model_names=use_keys, lss=all_lss, tickper=100)
    base = data_dirs.pop('optimised')
    all_lss.pop('optimised')
    q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name='optimised',
             other_scens=data_dirs, other_scen_ls=all_lss)


def compare_bound_sense():
    use_outdir = outdir.joinpath('boundary_sense')
    use_outdir.mkdir(exist_ok=True)
    use_keys = [
        'long_current',
        'hillslope_only_var',
        'lake_only_var',
        'rch_only_var',
        'pump_only_var',
        'static_pumping',
    ]
    all_lss = {k: l[-1] for k, l in zip(use_keys, linestyle_tuple)}
    data_dirs = {k: data_dir.joinpath(k) for k in use_keys}
    quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'))
    compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                      tdis=scen_tdis,
                      data_dirs=data_dirs,
                      model_names=use_keys, lss=all_lss, tickper=100)
    base = data_dirs.pop('base')
    all_lss.pop('base')
    q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name='base',
             other_scens=data_dirs, other_scen_ls=all_lss)
