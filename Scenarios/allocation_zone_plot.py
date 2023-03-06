"""
created matt_dumont 
on: 6/03/23
"""
import numpy as np
import geopandas as gpd
from project_base import proj_root, processed_scen_dir
from model_build.project_model_tools import smt

outdir = proj_root.joinpath('Scenarios/allocation_results')
outdir.mkdir(exist_ok=True)


def get_allo_zones(recalc=False):
    shp_path = proj_root.joinpath('Scenarios/base_data/recommended_zones/new_zones.shp')
    save_path = processed_scen_dir.joinpath('allo_zones.npy')
    if save_path.exists() and not recalc:
        return np.load(save_path)
    data = smt.io.shape_file_to_model_array(shp_path, 'ID', alltouched=True)
    np.save(save_path, data)
    return data


def plot_allocation_zone(save=False):
    shp_path = proj_root.joinpath('Scenarios/base_data/recommended_zones/new_zones.shp')
    line_path = proj_root.joinpath('Scenarios/base_data/recommended_zones/hflat_split.shp')
    data = gpd.read_file(shp_path)
    mapper = data.set_index('ID')['Zone'].to_dict()
    mapper_keys = list(mapper.keys())
    plot_data = get_allo_zones()
    plot_data[~np.isfinite(plot_data)] = -1
    colors = {i: c for i, c in zip(mapper_keys, smt.plot.get_colors(mapper_keys))}
    mapper[-1] = 'Out of Domain'
    colors[-1] = 'k'
    fig, ax, handles, labels = smt.plot.plt_discrete_matrix(plot_data, colors=colors, names=mapper, base_map=True,
                                                            no_flow_layer=None,
                                                            legend_loc='lower left', return_handles_labels=True)
    line_data = gpd.read_file(line_path)
    xs, ys = line_data.iloc[0].geometry.xy
    lines = ax.plot(xs, ys, color='k', ls='--', linewidth=2)
    handles.append(lines[0])
    labels.append('Approximate Location')
    ax.legend(handles, labels, loc='lower left')
    fig.tight_layout()
    if not save:
        smt.plot.show()
    else:
        fig.savefig(outdir.joinpath('new_allo_zones.png'))


if __name__ == '__main__':
    plot_allocation_zone()
