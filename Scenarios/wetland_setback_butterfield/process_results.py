"""
created matt_dumont 
on: 16/03/23
"""
from Scenarios.wetland_setback_butterfield.project_model_tools import smt
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


def build_impact_array(model_dir):

    # for a given model set
    # 1. read in all of the data
    # create
    raise NotImplementedError