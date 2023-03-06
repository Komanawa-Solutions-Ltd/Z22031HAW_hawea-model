"""
created matt_dumont 
on: 2/03/23
"""
import flopy.utils
import numpy as np

from Scenarios.run_mt3d_scenario import get_default_mt3d_kwargs, get_ftl, create_ssm_data, create_mt3d
from project_base import unbacked_dir, proj_root
from model_build.project_model_tools import smt, get_layer_pinchout_area, get_2d_moraine, get_lake_array, get_lake_bar

base_run_dir = unbacked_dir.joinpath('mt3d_runs')


def run_indictors(rerun=False):
    ftl = get_ftl()
    base_run_dir.mkdir(exist_ok=True)

    data = dict(race_con=1, all_hill=1, lake_con=1,
                # Note for some reason the str package is causing problems
                # hawear_con=1, clutha_con=1, lake_con=1, john_con=1, gview_con=1
                )

    ssm = create_ssm_data()
    mname = f'rch_indicator'
    mdt3d = create_mt3d(
        ftl_path=ftl,
        mt3d_name=mname,
        mt3d_ws=base_run_dir.joinpath(mname),
        smt=smt,
        ssm_crch={0: smt.get_model_zeros() + 1},
        ssm_stress_period_data={0: ssm},
        rerun=rerun,
        **get_default_mt3d_kwargs())

    ssm = create_ssm_data(all_hill=1)
    mname = f'hill_rch_indicator'
    mdt3d = create_mt3d(
        ftl_path=ftl,
        mt3d_name=mname,
        mt3d_ws=base_run_dir.joinpath(mname),
        smt=smt,
        ssm_crch={0: smt.get_model_zeros() + 1},
        ssm_stress_period_data={0: ssm},
        rerun=rerun,
        **get_default_mt3d_kwargs())

    ssm = create_ssm_data(all_hill=1, race_con=1, lake_con=1)
    mname = f'not_str'
    mdt3d = create_mt3d(
        ftl_path=ftl,
        mt3d_name=mname,
        mt3d_ws=base_run_dir.joinpath(mname),
        smt=smt,
        ssm_crch={0: smt.get_model_zeros() + 1},
        ssm_stress_period_data={0: ssm},
        rerun=rerun,
        **get_default_mt3d_kwargs())

    ssm = create_ssm_data()
    mname = f'not_any'
    mdt3d = create_mt3d(
        ftl_path=ftl,
        mt3d_name=mname,
        mt3d_ws=base_run_dir.joinpath(mname),
        smt=smt,
        ssm_crch={0: smt.get_model_zeros()},
        ssm_stress_period_data={0: ssm},
        rerun=rerun,
        **get_default_mt3d_kwargs())

    for k, v in data.items():
        ssm = create_ssm_data(**{k: v})
        mname = f'{k}_indicator'
        mdt3d = create_mt3d(
            ftl_path=ftl,
            mt3d_name=mname,
            mt3d_ws=base_run_dir.joinpath(mname),
            smt=smt,
            ssm_crch={0: smt.get_model_zeros()},
            ssm_stress_period_data={0: ssm},
            rerun=rerun,
            **get_default_mt3d_kwargs())


def extract_data():
    base_out = proj_root.joinpath('Scenarios/mt3d_indicator_scenarios')
    base_out.mkdir(exist_ok=True)
    base_ucn = base_out.joinpath('ucn_data')
    base_ucn.mkdir(exist_ok=True)
    base_plots = base_out.joinpath('plots')
    base_plots.mkdir(exist_ok=True)

    data_paths = base_run_dir.glob('**/*001.UCN')

    for p in data_paths:
        all_data = flopy.utils.UcnFile(p).get_alldata()[0]
        all_data[np.isclose(all_data, -1)] = np.nan
        np.savez_compressed(base_ucn.joinpath(p.name.replace('001.UCN', '.npz')), id_conc=all_data)
        plt_array = all_data[2]
        fig, ax = smt.plot.plt_matrix(plt_array, vmin=0, vmax=1,
                                      title=f'fraction of water from {p.name.replace("001.UCN", "")}', no_flow_layer=0,
                                      base_map=True)
        fig.tight_layout()
        fig.savefig(base_plots.joinpath(p.name.replace('001.UCN', '.png')))
        smt.plot.close(fig)
        if 'not' in p.name:
            outname = p.name.replace("001.UCN", "").replace("not", "all")
            np.savez_compressed(base_ucn.joinpath(f'{outname}.npz'), id_conc=1 - all_data)
            plt_array = all_data[2]
            fig, ax = smt.plot.plt_matrix(
                1 - plt_array, vmin=0, vmax=1,
                title=f'fraction of water from {outname}', no_flow_layer=0,
                base_map=True)
            fig.tight_layout()
            fig.savefig(base_plots.joinpath(f'{outname}.png'))
            smt.plot.close(fig)
def ucn_to_raster():
    base_out = proj_root.joinpath('Scenarios/mt3d_indicator_scenarios')
    base_ucn = base_out.joinpath('ucn_data')
    outdir = base_ucn.home().joinpath('unbacked/hawea/rasters')
    outdir.mkdir(exist_ok=True)
    for p in base_ucn.glob('*.npz'):
        data = np.load(p)['id_conc'][2]
        smt.io.array_to_raster(outdir.joinpath(p.with_suffix('.tif').name), data, no_flow_layer=0)




if __name__ == '__main__':
    run_indictors(rerun=False)
    extract_data()
    ucn_to_raster()
