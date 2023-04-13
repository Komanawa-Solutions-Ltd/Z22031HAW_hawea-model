"""
created matt_dumont 
on: 1/03/23
"""
import datetime
import shutil
import traceback

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from model_build.project_model_tools import smt
from Scenarios.run_flow_scenario import run_scenario, run_scenario_mp
from Scenarios.boundary_conditions import get_scen_ghb_data, get_scen_well_data, get_scen_str_data, get_scen_rch, \
    get_grid_pump_scen_well_data
from Scenarios.supporting_data_analysis.pumping_data import get_grid_locs
from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from Scenarios.scen_period import scen_tdis
from Scenarios.allocation_zones import get_allo_zones
from project_base import unbacked_dir, proj_root, opt_proj_root, opt_model_tools, processed_scen_dir
import inspect

base_run_dir = unbacked_dir.joinpath('allocation_scenarios')
base_run_dir.mkdir(exist_ok=True)
base_outdir = proj_root.joinpath('Scenarios/allocation_scenarios')
base_outdir.mkdir(exist_ok=True)

zones_to_model = ['Terrace-River', 'Terrace-Hill',
                  'Te Awa', 'Maungawera Flat',
                  'Mangawera Valley',
                  'Hawea Flat']


def print_myself(name):
    print(f'{inspect.stack()[1][3]}: {name}')


def plot_grid_locs(save=False):
    outdir = proj_root.joinpath('Scenarios/boundary_condition_plots/pumping/grid_pumping_locs')
    outdir.mkdir(exist_ok=True)
    all_locs = get_grid_locs()
    for zone in zones_to_model:
        zone_idx = get_allocation_zone(zone)
        zone_locs = smt.io.select_df_from_idx_array(all_locs, zone_idx, True)
        fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
        ax.scatter(zone_locs.mx, zone_locs.my)
        ax.set_title(f'{zone} additional pumping wells')
        fig.tight_layout()
        if save:
            fig.savefig(outdir.joinpath(f'{zone}_grid_pumps.png'))
        else:
            smt.plot.show()


def get_allocation_zone(zone):
    zones, mapper = get_allo_zones()
    mapper = {v: k for k, v in mapper.items()}
    assert zone in mapper
    return np.isclose(zones, mapper[zone])


def get_pumping_in_zones(recalc=False):
    out_path = processed_scen_dir.joinpath('current_full_max_allo.csv')
    if out_path.exists() and not recalc:
        outdata = pd.read_csv(out_path, index_col=0)
        return outdata
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    usage = get_scen_well_data('extended_pump', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                               return_unique_spd=True, recalc=False)['pump']
    full_allo = get_scen_well_data('extended_full_allo', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                   return_unique_spd=True, recalc=False)['pump']
    max_allo = get_scen_well_data('extended_max_allo', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                  return_unique_spd=True, recalc=False)['pump']
    max_allo_pc = get_scen_well_data('extended_max_allo_pc',
                                     tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                     return_unique_spd=True, recalc=False)['pump']
    pers = np.arange(1, 53)
    plot_data = {'usage': [], 'full_allo': [], 'max_allo': [], 'max_allo_pc': []}
    for w in pers:
        for k, v in plot_data.items():
            temp = pd.DataFrame(eval(k)[w])
            temp.loc[:, 'per'] = w
            v.append(temp)
    for k, v in plot_data.items():
        plot_data[k] = pd.concat(v)
    outdata = pd.DataFrame(index=zones_to_model)
    for zone in zones_to_model:
        zone_idx = get_allocation_zone(zone)
        for k, data in plot_data.items():
            data = smt.io.select_df_from_idx_array(data, zone_idx, True)
            data.loc[:, 'site'] = [f'{i}-{j}' for i, j in data.loc[:, ['i', 'j']].itertuples(False, None)]
            total_data = data.groupby('per').sum()

            outdata.loc[zone, f'{k}_mean'] = total_data.flux.mean()
            outdata.loc[zone, f'{k}_min'] = total_data.flux.min()
            outdata.loc[zone, f'{k}_max'] = total_data.flux.max()
    outdata.to_csv(out_path)
    return outdata


def plot_pumping_in_zones(save=False):
    out_plot_dir = proj_root.joinpath('Scenarios/boundary_condition_plots/pumping_use_allo_difs')
    out_plot_dir.mkdir(exist_ok=True)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    usage = get_scen_well_data('extended_pump', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                               return_unique_spd=True, recalc=False)['pump']
    full_allo = get_scen_well_data('extended_full_allo', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                   return_unique_spd=True, recalc=False)['pump']
    max_allo = get_scen_well_data('extended_max_allo', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                  return_unique_spd=True, recalc=False)['pump']
    max_allo_pc = get_scen_well_data('extended_max_allo_pc',
                                     tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                     return_unique_spd=True, recalc=False)['pump']
    pers = np.arange(1, 53)
    plot_data = {'usage': [], 'full_allo': [], 'max_allo': [], 'max_allo_pc': []}
    for w in pers:
        for k, v in plot_data.items():
            temp = pd.DataFrame(eval(k)[w])
            temp.loc[:, 'per'] = w
            v.append(temp)
    for k, v in plot_data.items():
        plot_data[k] = pd.concat(v)

    for zone in zones_to_model:
        zone_idx = get_allocation_zone(zone)
        fig, ax = plt.subplots(figsize=(10, 10))
        fig_site, ax_site = plt.subplots(figsize=(10, 10))
        colos = smt.plot.get_colors(plot_data.keys())
        lss = ['solid', '--', ':', 'dashdot']
        for (k, data), c, ls in zip(plot_data.items(), colos, lss):
            data = smt.io.select_df_from_idx_array(data, zone_idx, True)
            data.loc[:, 'site'] = [f'{i}-{j}' for i, j in data.loc[:, ['i', 'j']].itertuples(False, None)]
            total_data = data.groupby('per').sum()
            ax.plot(total_data.index, total_data.flux, color=c, label=k)
            site_data = data.groupby(['site', 'per']).mean().reset_index()
            sites = site_data.site.unique()
            site_colors = smt.plot.get_colors(sites, 'tab20')
            for site, sc in zip(sites, site_colors):
                ax_site.plot(data.loc[data.site == site, 'per'], data.loc[data.site == site, 'flux'], color=sc,
                             label=f'{site}-{k}', ls=ls)
            pass

        ax.set_title(zone)
        ax.set_xlabel('ISO week')
        ax.set_ylabel('pumping flux')
        ax.legend()
        ax_site.set_title(f'{zone} by site')
        ax_site.set_xlabel('Indicative Date')
        ax_site.set_ylabel('pumping flux')
        ax_site.legend()

        tick_per = 4
        dates = pd.Series(scen_tdis.per_middle_dates)
        all_labs = [d.date().isoformat() for d in dates.loc[pers]]
        ax.set_xticks([e for i, e in enumerate(pers) if i % tick_per == 0])
        ax.set_xticklabels([e for i, e in enumerate(all_labs) if i % tick_per == 0], rotation=-30)
        ax_site.set_xticks([e for i, e in enumerate(pers) if i % tick_per == 0])
        ax_site.set_xticklabels([e for i, e in enumerate(all_labs) if i % tick_per == 0], rotation=-30)

        fig.tight_layout()
        fig_site.tight_layout()
        if save:
            fig.savefig(out_plot_dir.joinpath(f'{zone}_total_fluxes.png'))
            fig_site.savefig(out_plot_dir.joinpath(f'{zone}_site_fluxes.png'))
        else:
            plt.show()


def run_grid_allocation_scenario(zone, total_increase, local_run_dir: Path, base_outputs_dir: Path,
                                 rerun=False, pers=None):
    """
    plan is to run this via ssh dist
    :param zone:
    :param total_increase:
    :param local_run_dir:
    :param base_outputs_dir:
    :param rerun:
    :param pers pers to run
    :return:
    """
    model_name = f'{zone}_{int(total_increase):010d}'
    model_name = model_name.replace(" ", "_")
    model_ws = local_run_dir.joinpath(model_name)
    lst_file = model_ws.joinpath(f'{model_name}.list')
    build_run_model = True
    if not rerun and lst_file.exists():
        build_run_model = False
    print_myself(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    idx_array = get_allocation_zone(zone)
    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    wel_data = get_grid_pump_scen_well_data(idx_array=idx_array,
                                            total_increase=total_increase,
                                            tdis=scen_tdis, hill_param=hill_param, race_param=race_param, )
    use_out = base_outputs_dir.joinpath(model_name)
    use_out.mkdir(exist_ok=True, parents=True)
    model_ws.mkdir(exist_ok=True, parents=True)
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=use_out,
                 build_run_model=build_run_model, process_results=process_results,
                 plot_data=False, save_hds=False, save_list=True,
                 stress_periods=pers
                 )
    shutil.rmtree(model_ws)  # files get big!


def run_grid_allocation_scenario_mp(kwargs):
    try:
        run_grid_allocation_scenario(**kwargs)
    except Exception:
        problem = traceback.format_exc()
        zone = kwargs.get('zone')
        total_increase = kwargs.get('total_increase')
        model_name = f'{zone}_{int(total_increase):010d}'
        brd = Path(kwargs.get('local_run_dir'))
        base_outputs_dir = Path(kwargs.get('base_outputs_dir'))
        logfile = base_outputs_dir.joinpath(f'0_{model_name}.log')
        with logfile.open('w') as f:
            f.write(f'model_name: {model_name}')
            f.write(f'model_ws: {brd.joinpath(model_name)}')
            f.write(f'outdir: {base_outputs_dir.joinpath(model_name)}')
            f.write(problem)


def run_all_grid_allocation_scens(name, local_cores: int, pump_rate: dict, rm_remote_files=True, external_ips=None,
                                  pers=None):
    """

    :param pump_rate: dict {zone:[p1, p2, p3]}
    :param rm_remote_files: remove files on remote machine
    :return:
    """
    for z, pr in pump_rate.items():
        assert z in zones_to_model, f'bad rate: zone: {z}, rate:{pr}'
        assert np.issubdtype(np.atleast_1d(pr).dtype, np.number)

    from run_managers.ssh_distributor import SshDist # keynote private repo

    base_paths = {'100.124.148.71': unbacked_dir.joinpath('grid_scenarios'),
                  '100.121.150.68': Path('/media/matt_dumont/data/mh_unbacked/hawea').joinpath('grid_scenarios')}

    num_cores = {
        '100.124.148.71': local_cores,
        '100.121.150.68': None,
    }

    core_weigtings = {'100.124.148.71': 5.774154806025006, '100.121.150.68': 1.0}

    for ip in external_ips:
        if ip not in base_paths:
            base_paths[ip] = unbacked_dir.joinpath('grid_scenarios')
        if ip not in num_cores:
            num_cores[ip] = None
        if ip not in core_weigtings:
            core_weigtings[ip] = 3.1815599663742145

    branch = 'main'
    ssh_dist = SshDist(
        base_path=base_paths,
        ips=['100.124.148.71'] + external_ips,
        script_path=opt_proj_root.joinpath('Scenarios/run_scenario.py'),
        conda_env='hawea',
        num_cores=num_cores,
        core_weigtings=core_weigtings,
        user_names=None,
        short_names=None,
        prepend_bash_commands=[
            f"cd {opt_model_tools} ; git fetch --all ; git reset --hard origin/Z22031HAW_hawea-model",
            f"cd {opt_proj_root} ; git fetch --all ; git reset --hard origin/{branch}"
        ],
        use_tailscale=True,
        python_paths=[opt_proj_root, opt_model_tools],
        sys_paths="default"
    )

    # make runs
    runs = []
    for z, all_tinc in pump_rate.items():
        all_tinc = np.atleast_1d(all_tinc)
        for tinc in all_tinc:
            runs.append(
                dict(zone=z, total_increase=tinc, local_run_dir='grid_runs',
                     base_outputs_dir='grid_outputs', pers=pers)
            )

    print(f'running {len(runs)} models')
    ssh_dist.distribute_runs(run_name=name, runs=runs, rm_remote_files=rm_remote_files, run=True, compile=True,
                             run_in_series=False, kwargs_relative_to_base_dir=['base_outputs_dir', 'local_run_dir'])


def full_allocation():
    model_name = 'full_allocation'
    print_myself(model_name)
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    wel_data = get_scen_well_data('extended_full_allo', scen_tdis, hill_param, race_param, False)
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=run_modflow, process_results=process_results,
                 plot_data=plot_data, save_hds=save_hds, save_list=True
                 )


def max_allocation():
    model_name = 'max_allocation'
    print_myself(model_name)
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    wel_data = get_scen_well_data('extended_max_allo', scen_tdis, hill_param, race_param, False)
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=run_modflow, process_results=process_results,
                 plot_data=True, save_hds=save_hds, save_list=True,
                 nwt_kwargs=dict(maxiterout=1500, maxitinner=300,
                                 headtol=0.5, fluxtol=2500,
                                 )
                 )


def mangawera_reduction():
    num_cores = 7
    reductions = [0.95, 0.9, 0.85, 0.8, 0.7, 0.6, 0.5]
    runs = []
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    base_wel_data = get_scen_well_data('extended_max_allo_pc', scen_tdis, hill_param, race_param, False)
    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    zone_idx = get_allocation_zone('Mangawera Valley')
    for r in reductions:
        model_name = f'mangawera_reduction_{r}'
        print_myself(model_name)
        model_ws = base_run_dir.joinpath(model_name)

        # apply reductions to mangawera pumping only
        from copy import deepcopy
        wel_data = deepcopy(base_wel_data)
        for k, v in wel_data.items():
            idx = zone_idx[v['i'], v['j']] & (v['flux'] < 0)
            v['flux'][idx] *= r

        temp = dict(model_name=model_name, model_ws=model_ws,
                    tdis=scen_tdis,
                    sy_param=sy_param,
                    kh_param=kh_param,
                    rch_data=rch,
                    ghb_spd=lake,
                    str_spd=str_vals,
                    well_spd=wel_data,
                    outdir=base_outdir.joinpath('mangawera_reductions', model_name),
                    build_run_model=run_modflow, process_results=process_results,
                    plot_data=False, save_hds=save_hds, save_list=True,
                    nwt_kwargs=dict(maxiterout=1500, maxitinner=300)
                    )
        runs.append(temp)
    from dummy_packages.run_multiprocess import run_multiprocess
    print(len(runs))
    pool_outputs = run_multiprocess(run_scenario_mp, runs, num_cores=num_cores)
    print('\n'.join([str(e) for e in pool_outputs]))


def max_allocation_on_pump_curve():
    model_name = 'max_allocation_on_pump_curve'
    print_myself(model_name)
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    wel_data = get_scen_well_data('extended_max_allo_pc', scen_tdis, hill_param, race_param, False)
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=run_modflow, process_results=process_results,
                 plot_data=False, save_hds=save_hds, save_list=True,
                 nwt_kwargs=dict(maxiterout=1500, maxitinner=300)
                 )


plot_data = False
save_hds = False
process_results = True
run_modflow = True

if __name__ == '__main__':
    mangawera_reduction()
    # full_allocation()
    # max_allocation()
    # max_allocation_on_pump_curve()

    pass
