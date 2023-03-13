"""
created matt_dumont 
on: 1/03/23
"""
from project_base import proj_root, unbacked_dir
from Scenarios.scenario_outputs import quantile_plots, q_qplots, compare_scenarios
from Scenarios.model_info_scenarios import scen_tdis
from Scenarios.allocation_scenarios import zones_to_model, get_pumping_in_zones
from Scenarios.allo_rch_hillside import get_allo_zone_rch_hillside

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


def compare_grid_allocation_scens_v2():  # todo run and check
    for zone in zones_to_model:
        print(zone)
        if zone == 'Mangawera Valley':
            continue  # did not run scenarios as already seeing implications at full allo

        # plot comparisons modifing below
        use_outdir = outdir.joinpath(f'{zone}_results')
        use_outdir.mkdir(exist_ok=True)
        use_keys = ['long_current']
        data_dirs = {k: info_data_dir.joinpath(k) for k in use_keys}

        use_keys2 = ['max_allocation_on_pump_curve', 'max_allocation']
        data_dirs2 = {k: allo_data_dir.joinpath(k) for k in use_keys2}
        use_keys = use_keys + use_keys2
        data_dirs.update(data_dirs2)

        # add datadirs for grid runs (where are these)
        grid_runs = sorted(unbacked_dir.joinpath('grid_scenarios',
                                                 'grid_allo_v2/all_grid_outputs').glob(f'{zone.replace(" ", "_")}*'))
        for p in grid_runs:
            name = f'{zone} {int(p.name.split("_")[-1])}'
            data_dirs[name] = p
            use_keys.append(name)

        all_lss = {k: 'solid' for k in use_keys} # dummy

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
    rch_hill = get_allo_zone_rch_hillside()
    # todo get current annual usage (min/mean/max)
    # todo get max allocation (on pump curve)
    # todo get max allocation (total)

    # todo barchart??? probably

    # todo
    raise NotImplementedError


if __name__ == '__main__':
    #compare_long_current_max_full_allo()
    compare_grid_allocation_scens_v2()
