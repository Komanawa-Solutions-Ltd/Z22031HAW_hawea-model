"""
created matt_dumont 
on: 1/03/23
"""

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
    use_keys = ['long_current', 'long_nat', 'optimised']
    all_lss = {k: l[-1] for k, l in zip(use_keys, linestyle_tuple)}
    data_dirs = {k: data_dir.joinpath(k) for k in use_keys}
    quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'),
                   aq_pen=['optimised', 'long_current'])
    compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                      tdis=scen_tdis,
                      data_dirs=data_dirs,
                      model_names=use_keys, lss=all_lss, tickper=100, aq_pen=['optimised', 'long_current'])
    base = data_dirs.pop('optimised')
    all_lss.pop('optimised')
    q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name='optimised',
             other_scens=data_dirs, other_scen_ls=all_lss)

    use_outdir = outdir.joinpath('nat_opt_long_opt_per_only')
    use_outdir.mkdir(exist_ok=True)
    use_keys = ['long_current', 'long_nat', 'optimised']
    all_lss = {k: l[-1] for k, l in zip(use_keys, linestyle_tuple)}
    data_dirs = {k: data_dir.joinpath(k) for k in use_keys}

    quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'),
                   usepers=[0] + list(range(1827, 2085)), aq_pen=['optimised', 'long_current'])
    compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                      tdis=scen_tdis,
                      data_dirs=data_dirs,
                      model_names=use_keys, lss=all_lss, tickper=10, aq_pen=['optimised', 'long_current'],
                      usepers=[0] + list(range(1827, 2085))
                      )
    base = data_dirs.pop('optimised')
    all_lss.pop('optimised')
    q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name='optimised',
             other_scens=data_dirs, other_scen_ls=all_lss, usepers=[0] + list(range(1827, 2085)))


def compare_bound_sense():
    use_outdir = outdir.joinpath('boundary_sense')
    use_outdir.mkdir(exist_ok=True)
    use_keys = [
        'long_current',
        'hillslope_only_var',
        'lake_only_var',
        'rch_only_var',
        'pump_only_var',
    ]
    all_lss = {k: l[-1] for k, l in zip(use_keys, linestyle_tuple)}
    data_dirs = {k: data_dir.joinpath(k) for k in use_keys}
    quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'))
    compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                      tdis=scen_tdis,
                      data_dirs=data_dirs,
                      model_names=use_keys, lss=all_lss, tickper=100)
    base = data_dirs.pop('long_current')
    all_lss.pop('long_current')
    q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name='long_current',
             other_scens=data_dirs, other_scen_ls=all_lss)


def compare_nat_opt_long_single():
    use_outdir = outdir.joinpath('nat_opt_long')
    use_outdir.mkdir(exist_ok=True)
    use_keys = ['long_current', 'long_nat', 'optimised']
    all_lss = {k: l[-1] for k, l in zip(use_keys, linestyle_tuple)}
    all_lss = {k: 'solid' for k, l in zip(use_keys, linestyle_tuple)}
    data_dirs = {k: data_dir.joinpath(k) for k in use_keys}
    quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'),
                   aq_pen=['optimised', 'long_current'], single_figs=True)
    compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                      tdis=scen_tdis,
                      data_dirs=data_dirs,
                      model_names=use_keys, lss=all_lss, tickper=100, aq_pen=['optimised', 'long_current'],
                      single_figs=True)
    base = data_dirs.pop('optimised')
    all_lss.pop('optimised')
    q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name='optimised',
             other_scens=data_dirs, other_scen_ls=all_lss, single_figs=True)

    use_outdir = outdir.joinpath('nat_opt_long_opt_per_only')
    use_outdir.mkdir(exist_ok=True)
    use_keys = ['long_current', 'long_nat', 'optimised']
    all_lss = {k: l[-1] for k, l in zip(use_keys, linestyle_tuple)}
    all_lss = {k: 'solid' for k, l in zip(use_keys, linestyle_tuple)}
    data_dirs = {k: data_dir.joinpath(k) for k in use_keys}

    quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'),
                   usepers=[0] + list(range(1827, 2085)), aq_pen=['optimised', 'long_current'], single_figs=True)
    compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                      tdis=scen_tdis,
                      data_dirs=data_dirs,
                      model_names=use_keys, lss=all_lss, tickper=10, aq_pen=['optimised', 'long_current'],
                      usepers=[0] + list(range(1827, 2085)), single_figs=True
                      )
    base = data_dirs.pop('optimised')
    all_lss.pop('optimised')
    q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name='optimised',
             other_scens=data_dirs, other_scen_ls=all_lss, usepers=[0] + list(range(1827, 2085)), single_figs=True)


def compare_bound_sense_single():
    use_outdir = outdir.joinpath('boundary_sense')
    use_outdir.mkdir(exist_ok=True)
    use_keys = [
        'long_current',
        'hillslope_only_var',
        'lake_only_var',
        'rch_only_var',
        'pump_only_var',
    ]
    all_lss = {k: l[-1] for k, l in zip(use_keys, linestyle_tuple)}
    all_lss = {k: 'solid' for k, l in zip(use_keys, linestyle_tuple)}
    data_dirs = {k: data_dir.joinpath(k) for k in use_keys}
    quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'),
                   single_figs=True)
    compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                      tdis=scen_tdis,
                      data_dirs=data_dirs,
                      model_names=use_keys, lss=all_lss, tickper=100, single_figs=True)
    base = data_dirs.pop('long_current')
    all_lss.pop('long_current')
    q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name='long_current',
             other_scens=data_dirs, other_scen_ls=all_lss, single_figs=True)


if __name__ == '__main__':
    compare_nat_opt_long_single()
    compare_bound_sense_single()
    compare_nat_opt_long()
    compare_bound_sense()
