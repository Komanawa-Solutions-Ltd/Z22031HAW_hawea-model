"""
created matt_dumont 
on: 16/03/23
"""
import numpy as np
import pandas as pd

from Scenarios.wetland_setback_butterfield.project_model_tools import smt
from pathlib import Path
from model_tools.util_functions.list_file_utils import ListSolverInfo


# todo!


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
        use_results = [e for e in all_results if e.name.split('_')[-2] == group]
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
                    assert (base_inputs == input_data).drop(index='max_pumping_rate').all()
                else:
                    assert (base_inputs == input_data.drop(index=['well_loc', 'model_name'])).all()
            if 'base' in inputs_path.name:
                ider = 'base'
            else:
                ider = input_data.loc['well_loc'].strip().replace(',', '_')
                pump_extract.loc[:, ider] = output_data.loc[:, f'well_pump_{ider}']
                pump_hds.loc[:, ider] = output_data.loc[:, f'well_hds_{ider}']

            wetland_hds.loc[:, ider] = output_data.loc[:, 'wetland_hds']
        pump_hds.to_csv(outdir.joinpath(f'group_{group}_pump_hds.csv'))
        wetland_hds.to_csv(outdir.joinpath(f'group_{group}_wetland_hds.csv'))
        pump_extract.to_csv(outdir.joinpath(f'group_{group}_pump_extract.csv'))
        base_inputs.to_csv(outdir.joinpath(f'group_{group}_base_inputs.csv'))


def build_impact_array():  # todo
    raise NotImplementedError


if __name__ == '__main__':
    collate_results('/home/matt_dumont/unbacked/hawea/butterfield/tranche1d','/home/matt_dumont/unbacked/hawea/butterfield/tranche1d_collated')