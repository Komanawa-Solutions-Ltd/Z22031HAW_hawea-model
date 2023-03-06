"""
created matt_dumont 
on: 1/03/23
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from model_build.project_model_tools import smt
# todo plot the locs in the allocation system.
from Scenarios.run_flow_scenario import run_scenario
from Scenarios.boundary_conditions import get_scen_ghb_data, get_scen_well_data, get_scen_str_data, get_scen_rch, \
    get_grid_pump_scen_well_data
from Scenarios.supporting_data_analysis.pumping_data import get_grid_locs
from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from Scenarios.scen_period import scen_tdis
from Scenarios.allocation_zones import get_allo_zones
from project_base import unbacked_dir, proj_root
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


def plot_pumping_in_zones(save=False):
    out_plot_dir = proj_root.joinpath('Scenarios/boundary_condition_plots/pumping_use_allo_difs')
    out_plot_dir.mkdir(exist_ok=True)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    usage = get_scen_well_data('extended_pump', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                               return_unique_spd=True, recalc=True)['pump']
    full_allo = get_scen_well_data('extended_full_allo', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                   return_unique_spd=True, recalc=True)['pump']
    max_allo = get_scen_well_data('extended_max_allo', tdis=scen_tdis, hill_param=hill_param, race_param=race_param,
                                  return_unique_spd=True, recalc=True)['pump']
    weeks = np.arange(1, 53)
    plot_data = {'usage': [], 'full_allo': [], 'max_allo': []}
    for w in weeks:
        for k, v in plot_data.items():
            temp = pd.DataFrame(eval(k)[w])
            temp.loc[:, 'week'] = w
            v.append(temp)
    for k, v in plot_data.items():
        plot_data[k] = pd.concat(v)

    for zone in zones_to_model:
        zone_idx = get_allocation_zone(zone)
        fig, ax = plt.subplots(figsize=(10, 10))
        fig_site, ax_site = plt.subplots(figsize=(10, 10))
        colos = smt.plot.get_colors(plot_data.keys())
        lss = ['solid', '--', ':']
        for (k, data), c, ls in zip(plot_data.items(), colos, lss):
            data = smt.io.select_df_from_idx_array(data, zone_idx, True)
            data.loc[:, 'site'] = [f'{i}-{j}' for i, j in data.loc[:, ['i', 'j']].itertuples(False, None)]
            total_data = data.groupby('week').sum()
            ax.plot(total_data.index, total_data.flux, color=c, label=k)
            site_data = data.groupby(['site', 'week']).mean().reset_index()
            sites = site_data.site.unique()
            site_colors = smt.plot.get_colors(sites, 'tab20')
            for site, sc in zip(sites, site_colors):
                ax_site.plot(data.loc[data.site == site, 'week'], data.loc[data.site == site, 'flux'], color=sc,
                             label=f'{site}-{k}', ls=ls)
            pass

        ax.set_title(zone)
        ax.set_xlabel('ISO week')
        ax.set_ylabel('pumping flux')
        ax.legend()
        ax_site.set_title(f'{zone} by site')
        ax_site.set_xlabel('ISO week')
        ax_site.set_ylabel('pumping flux')
        ax_site.legend()
        fig.tight_layout()
        fig_site.tight_layout()
        if save:
            fig.savefig(out_plot_dir.joinpath(f'{zone}_total_fluxes.png'))
            fig_site.savefig(out_plot_dir.joinpath(f'{zone}_site_fluxes.png'))
        else:
            plt.show()


def run_grid_allocation_scenario(zone, total_increase):  # todo
    model_name = f'{zone}_{int(total_increase):06d}'  # todo max value???,
    # todo what are increased pumping values to use, should I make this more standartised (look at pumping in the zone)
    model_ws = base_run_dir.joinpath(model_name)
    print_myself(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    idx_array = get_allocation_zone(zone)
    rch = get_scen_rch(scen_tdis, rch_param, dryland=False)
    lake = get_scen_ghb_data(scen_tdis)
    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False)
    wel_data = get_grid_pump_scen_well_data(idx_array=idx_array,
                                            total_increase=total_increase,
                                            tdis=scen_tdis, hill_param=hill_param, race_param=race_param, )
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
                 plot_data=plot_data, save_hds=save_hds,
                 )


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
                 plot_data=plot_data, save_hds=save_hds,
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
                 plot_data=plot_data, save_hds=save_hds,
                 )


plot_data = False
save_hds = False
process_results = True
run_modflow = True

if __name__ == '__main__':
    plot_grid_locs(True)
    plot_pumping_in_zones(True)

    pass
