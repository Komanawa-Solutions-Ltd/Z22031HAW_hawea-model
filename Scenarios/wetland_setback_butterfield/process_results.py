"""
created matt_dumont 
on: 16/03/23
"""
import numpy as np
import pandas as pd
from project_base import butterfield_dir, unbacked_dir
from Scenarios.wetland_setback_butterfield.project_model_tools import smt
from pathlib import Path
from model_tools.util_functions.list_file_utils import ListSolverInfo # keynote private repo
from scipy.interpolate import griddata


def plot_list_failures(list_file, plot_dir):
    temp = ListSolverInfo(list_file)
    all_overs = temp.get_over(50, 0)

    limits = [50, 100, 300, 500, 800]
    for l in limits:
        temp = all_overs.loc[all_overs.outer_iter >= l]
        temp = temp.drop_duplicates(subset=['layer', 'row', 'column', 'nper', 'nstp'])
        plt_data = temp.groupby(['layer', 'row', 'column']).count().outer_iter.reset_index()
        fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
        ax.scatter(*smt.convert_matrix_to_coords(plt_data.row, plt_data.column), color='r')
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'more_than_{l}_outers.png'))
        smt.plot.close(fig)


def collate_results(model_dir, outdir):
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True, parents=True)
    model_dir = Path(model_dir)
    all_results = sorted(model_dir.glob('**/*_outputs.csv'))
    all_groups = np.unique([e.name.split('_')[-2] for e in all_results])

    for group in all_groups:
        use_results = np.array([e for e in all_results if e.name.split('_')[-2] == group])
        idx = np.argsort([e.name for e in use_results])
        use_results = use_results[idx]
        pump_hds = pd.DataFrame()
        wetland_hds = pd.DataFrame()
        pump_extract = pd.DataFrame()
        base_inputs = None
        for i, result in enumerate(use_results):
            output_data = pd.read_csv(result, index_col=0)
            inputs_path = result.parent.joinpath(result.name.replace('outputs.csv', 'inputs.txt'))
            input_data = pd.read_csv(inputs_path, sep='=', names=['key', 'val'])
            input_data.loc[:, 'key'] = input_data.loc[:, 'key'].str.strip()
            input_data.set_index('key', inplace=True)
            input_data = input_data['val']

            # check data matches!
            if i == 0:
                assert 'base' not in inputs_path.name
                base_inputs = input_data.drop(index=['well_loc', 'model_name'])
            else:
                if 'base' in inputs_path.name:
                    assert (base_inputs == input_data.drop(index='model_name')).drop(index='max_pumping_rate').all()
                else:
                    assert (base_inputs == input_data.drop(index=['well_loc', 'model_name'])).all()
            if 'base' in inputs_path.name:
                ider = 'base'
            else:
                ider = input_data.loc['well_loc'].strip().replace(',', '_')
                pump_extract.loc[:, ider] = output_data.loc[:, f'well_pump_{ider}']
                pump_hds.loc[:, ider] = output_data.loc[:, f'well_hds_{ider}']

            wetland_hds.loc[:, ider] = output_data.loc[:, 'wetland_hds']
        pump_hds.to_csv(outdir.joinpath(f'group_{int(group):03d}_pump_hds.csv'))
        wetland_hds.to_csv(outdir.joinpath(f'group_{int(group):03d}_wetland_hds.csv'))
        pump_extract.to_csv(outdir.joinpath(f'group_{int(group):03d}_pump_extract.csv'))
        base_inputs.to_csv(outdir.joinpath(f'group_{int(group):03d}_base_inputs.csv'))


def build_impact_points(collated_dir, outdir):
    collated_dir = Path(collated_dir)
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True, parents=True)
    groups = sorted(np.unique([e.name.split('_')[1] for e in collated_dir.iterdir()]))
    outdata_dd = pd.DataFrame(index=groups)  # (locs groups)
    outdata_dry = pd.DataFrame(index=groups)  # (locs groups)
    outdata_noflow = pd.DataFrame(index=groups)  # (locs groups)
    outdata_inputs = pd.DataFrame(index=groups)

    for group in groups:
        pump = pd.read_csv(collated_dir.joinpath(f'group_{int(group):03d}_pump_hds.csv'), index_col=0)
        wetland = pd.read_csv(collated_dir.joinpath(f'group_{int(group):03d}_wetland_hds.csv'), index_col=0)
        inputs = pd.read_csv(collated_dir.joinpath(f'group_{int(group):03d}_base_inputs.csv'), index_col=0).transpose()

        assert (wetland > -666).all().all()
        wetland = wetland - wetland.base.values[:, np.newaxis]
        wetland = wetland.drop(columns='base')
        outdata_dd.loc[group, wetland.columns] = wetland.min()
        outdata_noflow.loc[group, pump.columns] = (pump > 1e10).any()
        outdata_dry.loc[group, pump.columns] = (pump < -666).any()
        outdata_inputs.loc[group, inputs.columns] = inputs.loc['val']

    outdata_dd.to_csv(outdir.joinpath('outdata_dd.csv'))
    outdata_noflow.to_csv(outdir.joinpath('outdata_noflow.csv'))
    outdata_dry.to_csv(outdir.joinpath('outdata_dry.csv'))
    outdata_inputs.to_csv(outdir.joinpath('outdata_inputs.csv'))


def plot_outputs(points_dir, outdir):
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True, parents=True)

    outdata_dd = pd.read_csv(points_dir.joinpath('outdata_dd.csv'), index_col=0)
    outdata_noflow = pd.read_csv(points_dir.joinpath('outdata_noflow.csv'), index_col=0)
    outdata_dry = pd.read_csv(points_dir.joinpath('outdata_dry.csv'), index_col=0)
    outdata_inputs = pd.read_csv(points_dir.joinpath('outdata_inputs.csv'), index_col=0)
    xys = {}
    for col in outdata_dd.columns:
        k, i, j = np.array(col.split('_')).astype(int)
        x, y = smt.convert_matrix_to_coords(i, j)
        xys[col] = (x, y)

    for group in outdata_dd.index:
        drawdown = outdata_dd.loc[group, outdata_dd.columns]
        noflow = outdata_noflow.loc[group, outdata_dd.columns].values.astype(bool)
        dry = outdata_dry.loc[group, outdata_dd.columns].values.astype(bool)
        points = np.array([xys[c] for c in outdata_dd.columns])
        keep = [not (d or nf) for d, nf in zip(dry, noflow)]
        invals = drawdown.values
        use_inputs = outdata_inputs.loc[group]
        tcomps = [f'{k}={v}' for k, v in use_inputs.items()]
        title = ', '.join(tcomps[0:3]) + ',\n' + ', '.join(tcomps[3:])
        fname = '_'.join([ider + str(e) for e, ider in zip(use_inputs.values, ['mp', 'tk', 'fk', 'ts', 'fs', 'r'])])

        ibound = smt.get_no_flow(0)
        grid_xs, grid_ys = smt.get_model_x_y()

        vals = griddata(points=points[keep], values=invals[keep],
                        xi=np.array(list(zip(grid_xs[ibound == 1], grid_ys[ibound == 1]))),
                        method='cubic'
                        )
        plt_array = smt.get_model_zeros() * np.nan
        plt_array[ibound == 1] = vals

        fig, ax = smt.plot.plt_matrix(plt_array, base_map=True, no_flow_layer=0, contour=True,
                                      contour_levels=[-10, -5, -2, -1, -0.5, -0.2, -0.1], label_contours=True,
                                      title=title)
        ax.scatter(points[dry, 0], points[dry, 1], label='dry pumps (excluded from draw down)')
        ax.legend()
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'{fname}.png'))


if __name__ == '__main__':
    model_dir = unbacked_dir.joinpath('/home/matt_dumont/unbacked/hawea/butterfield/tranche1d')
    collate_dir = unbacked_dir.joinpath('/home/matt_dumont/unbacked/hawea/butterfield/tranche1d_collated')
    points_dir = butterfield_dir.joinpath('results/points')
    plot_dir = butterfield_dir.joinpath('results/plots')

    collate_results(model_dir, collate_dir)
    build_impact_points(collate_dir, points_dir)
    plot_outputs(points_dir, plot_dir)
