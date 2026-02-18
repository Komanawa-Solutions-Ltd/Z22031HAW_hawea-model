"""
created matt_dumont 
on: 1/03/23
"""
from komanawa.hawea.hawea_base import proj_root
from komanawa.hawea.Scenarios.scenario_outputs import quantile_plots, q_qplots, compare_scenarios
from komanawa.hawea.Scenarios.low_lake_scenarios import get_lake_hds, low_lake_groups, low_lake_tdis

low_lake_dir = proj_root.joinpath('Scenarios/low_lake_scenarios')
outdir = low_lake_dir.joinpath('0_results')
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


def compare_lowlake():
    xs, data = get_lake_hds('all')
    for kg in low_lake_groups:
        use_outdir = outdir.joinpath(kg)
        use_outdir.mkdir(exist_ok=True)
        use_keys = ['base'] + [k for k in data.keys() if kg in k]
        all_lss = {k: l[-1] for k, l in zip(use_keys, linestyle_tuple)}
        data_dirs = {k: low_lake_dir.joinpath(k) for k in use_keys}
        quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'))
        compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                          tdis=low_lake_tdis,
                          data_dirs=data_dirs,
                          model_names=use_keys, lss=all_lss, tickper=100)
        base = data_dirs.pop('base')
        all_lss.pop('base')
        q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name='base',
                 other_scens=data_dirs, other_scen_ls=all_lss)


if __name__ == '__main__':
    compare_lowlake()
