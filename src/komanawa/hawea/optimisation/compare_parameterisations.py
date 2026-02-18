"""
created matt_dumont 
on: 14/11/22
"""
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from komanawa.hawea.optimisation.model_utils_for_forward_run import read_param_data, _get_param_data
from komanawa.hawea.model_build.utils import get_colors


def compare_parameterisations(*parfiles, outdir=None):
    parameters = {}
    for f in parfiles:
        f = Path(f)
        name = str(f.relative_to(f.parents[3])).replace('Optimisations/', '')
        try:
            data = read_param_data(parameter_file=f, format_type='pest', return_individual=False)
        except KeyError:
            data = read_param_data(parameter_file=f, format_type='model', return_individual=False)
        parameters[name] = data

    # make dataframe
    iparam_data = _get_param_data().set_index('name')
    parameters = pd.DataFrame(parameters).transpose()
    if outdir is not None:
        outdir = Path(outdir)
        outdir.mkdir(exist_ok=True)

    data_groups = pd.unique([e.split('_')[0] for e in parameters.keys()])
    index_colors = get_colors(parameters.index, cmap_name='tab20')
    for g in data_groups:
        use_cols = [e for e in parameters.keys() if g == e.split('_')[0]]
        temp = parameters.loc[:, use_cols]
        fig, ax = plt.subplots(figsize=(14, 8))
        for i, c in zip(parameters.index, index_colors):
            ax.scatter(range(len(use_cols)), temp.loc[i, use_cols], label=i, color=c)
        ax.set_xticks(range(len(use_cols)))
        ax.set_xticklabels(use_cols, rotation=-45)
        ax.set_title(f'parameter values for {g}')
        if g in ['kh', 'riv', 'sy']:
            ax.set_yscale('log')

        for k in ['low', 'start', 'up']:
            ys = [iparam_data[k].loc[e] for e in use_cols]
            ax.plot(range(len(use_cols)), ys, ls=':', label=k, )

        ax.legend()
        fig.tight_layout()
        if outdir is not None:
            fig.savefig(outdir.joinpath(f'{g}.png'))
    if outdir is None:
        plt.show()


if __name__ == '__main__':
    compare_parameterisations(
        '/home/matt_dumont/unbacked/hawea/structure_v5/init_structure_v5/Optimisations/opt.par.50',
        '/home/matt_dumont/unbacked/hawea/structure_v6/init_structure_v6/Optimisations/opt.par.17',
        '/home/matt_dumont/unbacked/hawea/structure_v6a/ss_sy/Optimisations/opt.par.25',
    )
