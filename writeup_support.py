"""
created matt_dumont 
on: 17/04/23
"""
import matplotlib.pyplot as plt
import numpy as np

from project_base import proj_root, base_model_build_data_dir
from model_build.project_model_tools import smt, elv_calc


def model_2d_structure_plots():
    elv_db = elv_calc(one_layer_version=True)
    fig, ax = plt.subplots(ncols=2, figsize=(14, 9))
    smt.plot.plt_matrix(elv_db[0], ax=ax[0], base_map=True, no_flow_layer=0, title='model top', contour=True,
                        contour_levels=20, label_contours=True)
    smt.plot.plt_matrix(elv_db[1], ax=ax[1], base_map=True, no_flow_layer=0, title='model bottom', contour=True,
                        contour_levels=20, label_contours=True)
    fig.tight_layout()
    fig.savefig(proj_root.joinpath('support_figures', 'model_2d_top_bot.png'))

    thick = elv_db[0] - elv_db[1]
    fig, ax = smt.plot.plt_matrix(thick, base_map=True, no_flow_layer=0, title='model thickness', contour=True,
                                  contour_levels=20, label_contours=True)
    fig.tight_layout()
    fig.savefig(proj_root.joinpath('support_figures', 'model_2d_thickness.png'))

    fixers = smt.get_model_zeros() * np.nan
    flat = np.isfinite(smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('bottoms_fixer_flat.shp'),
                                                        'id', alltouched=True))
    slope = np.isfinite(smt.io.shape_file_to_model_array(base_model_build_data_dir.joinpath('bottoms_fixer_slope.shp'),
                                                         'id', alltouched=True))
    legend = {1: 'Set bottom to nearby river cell bottom', 2: 'Reduce bottom gradient'}
    colors = {1: 'r', 2: 'b'}
    fixers[flat] = 1
    fixers[slope] = 2
    fig, ax = smt.plot.plt_discrete_matrix(fixers, base_map=True, no_flow_layer=0, colors=colors,
                                           title='Model bottom adjustment', names=legend, legend_loc='lower left')
    fig.tight_layout()
    fig.savefig(proj_root.joinpath('support_figures', 'model_2d_bottom_fixers.png'))
    plt.show()


def boundary_condition_figure():
    from model_build.get_boundary_condition_data import get_river_loc_data, get_race_locs, get_pumping_locs, \
        get_hillside_catchment_locs, get_lake_hawea_loc

    bnd_conditions = smt.get_model_zeros() * np.nan
    bnd_legend = {}
    bnd_colors = {}

    river_locs = get_river_loc_data()
    bnd_conditions[river_locs.i, river_locs.j] = 1
    bnd_legend[1] = 'STR Package'
    bnd_colors[1] = 'cornflowerblue'

    race_locs = get_race_locs()
    bnd_conditions[race_locs.i, race_locs.j] = 2
    bnd_legend[2] = 'Wel Package - Race losses'
    bnd_colors[2] = 'lightcoral'

    pumping_locs = get_pumping_locs()
    bnd_conditions[pumping_locs.i, pumping_locs.j] = 3
    bnd_legend[3] = 'Wel Package - Pumping'
    bnd_colors[3] = 'red'

    hillside_catchment_locs = get_hillside_catchment_locs()
    bnd_conditions[hillside_catchment_locs.i, hillside_catchment_locs.j] = 4
    bnd_legend[4] = 'Wel Package - Hillside inflows'
    bnd_colors[4] = 'maroon'

    lake_hawea_loc = get_lake_hawea_loc()
    bnd_conditions[lake_hawea_loc.i, lake_hawea_loc.j] = 5
    bnd_legend[5] = 'GHB Package - Lake Hawea'
    bnd_colors[5] = 'navy'

    fig, ax = smt.plot.plt_discrete_matrix(bnd_conditions, base_map=True, no_flow_layer=0, colors=bnd_colors,
                                           title='Boundary Conditions', names=bnd_legend,
                                           legend_loc='lower left', alpha=1)
    fig.tight_layout()
    fig.savefig(proj_root.joinpath('support_figures', 'model_2d_boundary_conditions.png'))
    plt.show()


def geography():
    from model_build.zones import get_model_zones
    legend = {}
    colors = {}

    plt_array = smt.get_model_zeros() + 4
    plt_array[smt.get_no_flow(0) < 1] = 1
    legend[1] = 'Out of domain'
    colors[1] = 'k'

    zones = get_model_zones()
    use_zones = ['lake', 'flat', 'east', 'terrace', 'sandypoint']
    use_colors = ['cornflowerblue', 'purple', 'red', 'orangered', 'maroon']
    use_names = ['Lake Hawea', 'Hawea Flat Aquifer', 'Te Awa, Maungawera Flat, & Riverside Aquifers', 'Terrace Aquifer',
                 ]

    for i, (uz, uc, un) in enumerate(zip(use_zones, use_colors, use_names)):
        if uz == 'lake':
            plt_array[zones[uz] & (smt.get_no_flow(0) == 1)] = 2 + i
        else:
            plt_array[zones[uz]] = 2 + i
        legend[2 + i] = un
        colors[2 + i] = uc

    from Scenarios.allocation_zones import get_allo_zones
    allo_zones, mapper = get_allo_zones()
    mapper = {v: k for k, v in mapper.items()}
    plt_array[allo_zones == 8] = 10
    legend[10] = 'Camp Hill Moraine'
    colors[10] = 'violet'

    plt_array[allo_zones == 9] = 11
    legend[11] = 'Mangawera Valley Aquifer'
    colors[11] = 'lightcoral'

    plt_array[allo_zones == 5] = 12
    legend[12] = 'Sandy Point Aquifer'
    colors[12] = 'gold'

    fig, ax, handles, labels = smt.plot.plt_discrete_matrix(plt_array, base_map=True, colors=colors,
                                                            title='Hawea Aquifer Geography', names=legend,
                                                            legend_loc='lower left', return_handles_labels=True)

    # todo grandview fault (infered)
    import geopandas as gpd
    line_path = proj_root.joinpath('support_figures/grandview_fault.shp')
    line_data = gpd.read_file(line_path)
    all_xs, all_ys = [], []
    for i in range(len(line_data)):
        xs, ys = line_data.iloc[i].geometry.xy
        all_xs.extend(xs)
        all_ys.extend(ys)
    all_ys = np.array(all_ys)
    all_xs = np.array(all_xs)
    idx = np.argsort(all_ys)
    lines = ax.plot(all_xs[idx], all_ys[idx], color='k', ls='--', linewidth=2)
    handles.append(lines[0])
    labels.append('Grandview Fault (inferred)')
    ax.legend(handles, labels, loc='lower left')
    # todo clutha/hawea river


    labels = [
       "Camp Hill",
       "Cameron Hill",
        "Grandview Ridge",
        "John Stream",
        "Grandview Creek",
        "Lagoon Creek",

    ]
    xsys = [
        (1302633, 5049463),
        (1307188.3, 5051411.5),
        (1311249, 5047951),
        (1308388.7, 5054729.7),
        (1308362.3, 5053127.4),
        (1308166.6, 5046628.5),
    ]
    for label, (x, y) in zip(labels, xsys):
        ax.annotate(label, xy=(x, y), xytext=(x, y-1500), fontsize=10, color='k', ha='center', va='center',
                    bbox=dict(boxstyle='round', fc='w', ec='k', alpha=0.5),
                    arrowprops=dict(facecolor='white', shrink=0.05, width=2, headwidth=10, headlength=10))
    fig.tight_layout()
    fig.savefig(proj_root.joinpath('support_figures', 'model_2d_geography.png'))
    plt.show()

def well_locations():
    from model_build.supporting_data_analysis import get_pumping_locs
    locs = get_pumping_locs()
    locs = smt.io.add_mxmy_to_df(locs)
    fig,ax =smt.plot.plt_basemap(no_flow_layer=0)
    for l,c in zip(range(3), ['r', 'b', 'm']):
        temp = locs[locs.k == l]
        ax.scatter(temp.mx, temp.my, color=c, label='Abstraction in Layer {}'.format(l))
    ax.legend(loc='lower left')
    ax.set_title('Groundwater Abstraction Well Locations')
    fig.tight_layout()
    fig.savefig(proj_root.joinpath('support_figures', 'model_2d_well_locations.png'))
    plt.show()

def large_hill_inflows():
    from model_build.supporting_data_analysis import get_river_flow_data

    rflows = get_river_flow_data('2015-01-01', None,frequency='W')

    fig, ax = plt.subplots(figsize=(8, 4))
    for nm, pn, c in zip(['gview', 'john'], ['Grandview Creek', 'John Creek'], ['r', 'b']):
        ax.plot(rflows[nm].index, rflows[nm].values, color=c, label=pn)
    ax.legend()
    ax.set_title('Large Hillside Inflows')
    ax.set_ylabel('Flow (m$^3$/d)')
    ax.set_xlabel('Date')
    fig.tight_layout()
    fig.savefig(proj_root.joinpath('support_figures', 'model_2d_large_hill_inflows.png'))
    plt.show()

def near_river():
    from model_build.supporting_data_analysis.get_pumping_data import get_pumping_locs
    all_locs = get_pumping_locs(force_near_river=True)
    all_locs = smt.io.add_mxmy_to_df(all_locs)
    fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
    for t in [True, False]:
        ax.scatter(all_locs[all_locs.near_river == t].mx, all_locs[all_locs.near_river == t].my,
                     color='r' if t else 'b', label='Near River' if t else 'Not Near River')
    ax.legend(loc='lower left')
    ax.set_title('Groundwater Abstraction Well Locations')
    fig.tight_layout()
    fig.savefig(proj_root.joinpath('support_figures', 'model_2d_well_locations_near_river.png'))
    plt.show()


if __name__ == '__main__':
    # model_2d_structure_plots()
    # boundary_condition_figure()
    #geography()
    # well_locations()
    #large_hill_inflows()
    near_river()
    pass
