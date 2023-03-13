"""
created matt_dumont 
on: 1/03/23
"""
import matplotlib.pyplot as plt

from project_base import proj_root, unbacked_dir
from Scenarios.scenario_outputs import quantile_plots, q_qplots, compare_scenarios
from Scenarios.model_info_scenarios import scen_tdis
from Scenarios.allocation_scenarios import zones_to_model, get_allocation_zone
from Scenarios.allo_rch_hillside import get_allo_zone_rch_hillside
from model_build.supporting_data_analysis.get_pumping_data import get_most_upto_date_allocation_info

outdir = proj_root.joinpath('Scenarios/allocation_results')
outdir.mkdir(exist_ok=True)
info_data_dir = proj_root.joinpath('Scenarios/model_info_scen_results')
allo_data_dir = proj_root.joinpath('Scenarios/allocation_scenarios')

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


def compare_long_current_max_full_allo():
    use_outdir = outdir.joinpath('nat_current_full')
    use_outdir.mkdir(exist_ok=True)
    use_keys = ['long_current', 'long_nat']
    data_dirs = {k: info_data_dir.joinpath(k) for k in use_keys}

    use_keys2 = ['full_allocation', 'max_allocation', 'max_allocation_on_pump_curve']
    data_dirs2 = {k: allo_data_dir.joinpath(k) for k in use_keys2}
    use_keys = use_keys + use_keys2
    data_dirs.update(data_dirs2)
    all_lss = {k: l[-1] for k, l in zip(use_keys, linestyle_tuple)}

    quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'),
                   aq_pen=['long_nat', 'long_current'], single_figs=True)
    compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                      tdis=scen_tdis,
                      data_dirs=data_dirs,
                      model_names=use_keys, lss=all_lss, tickper=100, aq_pen=['long_nat', 'long_current'],
                      single_figs=True)
    base_name = 'long_current'
    base = data_dirs.pop(base_name)
    all_lss.pop(base_name)
    q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name=base_name,
             other_scens=data_dirs, other_scen_ls=all_lss, single_figs=True)


def compare_grid_allocation_scens():
    for zone in zones_to_model:
        print(zone)
        if zone == 'Mangawera Valley':
            continue  # did not run scenarios as already seeing implications at full allo

        # plot comparisons modifing below
        use_outdir = outdir.joinpath(f'{zone}_results')
        use_outdir.mkdir(exist_ok=True)
        use_keys = ['long_current']
        data_dirs = {k: info_data_dir.joinpath(k) for k in use_keys}

        use_keys2 = ['max_allocation_on_pump_curve']
        data_dirs2 = {k: allo_data_dir.joinpath(k) for k in use_keys2}
        use_keys = use_keys + use_keys2
        data_dirs.update(data_dirs2)

        grid_keys = []
        # add datadirs for grid runs (where are these)
        grid_runs = sorted(unbacked_dir.joinpath('grid_scenarios',
                                                 'all_grid_outputs').glob(f'{zone.replace(" ", "_")}*'))
        max_num = max([len(str(int(p.name.split("_")[-1]))) for p in grid_runs])
        for p in grid_runs:
            num = int(p.name.split("_")[-1])
            name = f'{zone} {num:0{max_num}d}'
            data_dirs[name] = p
            grid_keys.append(name)

        all_lss = {k: 'dashed' for k in use_keys}
        all_lss.update({k: 'solid' for k in grid_keys})
        use_keys = use_keys + sorted(grid_keys)

        quantile_plots(scenarios=data_dirs, senario_ls=all_lss, outdir=use_outdir.joinpath('quantile_plots'),
                       aq_pen=['long_nat', 'long_current'], single_figs=True)
        compare_scenarios(outdir=use_outdir.joinpath('comp_plots'),
                          tdis=scen_tdis,
                          data_dirs=data_dirs,
                          model_names=use_keys, lss=all_lss, tickper=100, aq_pen=['long_nat', 'long_current'],
                          single_figs=True)
        base_name = 'long_current'
        base = data_dirs.pop(base_name)
        all_lss.pop(base_name)
        q_qplots(base_scen_dir=base, outdir=use_outdir.joinpath('qq_plots'), base_scen_name=base_name,
                 other_scens=data_dirs, other_scen_ls=all_lss, single_figs=True)


def compare_current_allo_to_rch_hillside():
    from model_build.project_model_tools import smt
    from Scenarios.scen_period import scen_tdis
    from Scenarios.supporting_data_analysis.pumping_data import get_pump_curve
    outdir = proj_root.joinpath('Scenarios/allocation_results/allo_zone_rch/plots')
    outdir.mkdir(exist_ok=True)
    all_rch_hill = get_allo_zone_rch_hillside()
    allo_data = get_most_upto_date_allocation_info()
    pump_curve = get_pump_curve(scen_tdis)
    pump_curve = pump_curve.iloc[1:53].flux.mean()
    allo_data.loc[:, 'max_allo_pc'] = allo_data.loc[:, 'max_allo'] * pump_curve

    for zone, rch_hill in all_rch_hill.items():
        zone_array = get_allocation_zone(zone)
        temp_allo = smt.io.select_df_from_idx_array(allo_data, zone_array, d2_only=True)

        rch_hill.loc[:, 'total'] = rch_hill[['hill', 'scen_rch']].sum(axis=1)
        names = ['Hill inflow', 'Recharge', 'Total inflow']
        dfnames = ['hill', 'scen_rch', 'total']
        plot_data = []
        positions = []
        for i, n in enumerate(dfnames):
            temp = rch_hill[n]
            if temp.sum() < 500:
                continue
            else:
                plot_data.append(temp.values)
                positions.append(i)
        names.append('Usage 2015-2020')
        positions.append(i + 1)
        plot_data.append([temp_allo[f'current_use_{y}'].sum() for y in range(2015, 2021)])

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.violinplot(plot_data, positions=positions)
        ax.set_yscale('log')
        ax.set_title(zone)
        ax.set_ylabel('m3/year')
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names)
        ax.set_xlim(-0.5, len(names) - 0.5)

        # max allo, allo on pumping curve as hlines
        for k, pretty_k, c, va in zip(['max_allo', 'max_allo_pc'],
                                      ['Max Allo.', 'Max Allo.\nPump Curve'],
                                      ['red', 'darkorange'],
                                      ['top', 'bottom']):
            total = temp_allo[k].sum()
            if total > 1:
                ax.axhline(total, color=c)
                ax.text(-0.4, total, pretty_k, color=c, va=va,
                        bbox=dict(facecolor='white', edgecolor=c, pad=10.0))

        fig.tight_layout()
        fig.savefig(outdir.joinpath(f'{zone}.png'))


if __name__ == '__main__':
    compare_current_allo_to_rch_hillside()
    # compare_long_current_max_full_allo()
    # compare_grid_allocation_scens()
    pass
