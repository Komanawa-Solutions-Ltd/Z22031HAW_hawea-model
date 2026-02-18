"""
created matt_dumont 
on: 2/03/23
"""
import flopy.utils
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from komanawa.hawea.Scenarios.run_mt3d_scenario import get_default_mt3d_kwargs, create_ssm_data, create_mt3d
from komanawa.hawea.hawea_base import unbacked_dir, proj_root
from komanawa.hawea.model_build.project_model_tools import smt
from komanawa.hawea.optimisation.optimisation_period import tdis as opt_tdis
from komanawa.hawea.model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_str_data
from komanawa.hawea.model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from komanawa.hawea.Scenarios.run_flow_scenario import run_scenario


base_run_dir = unbacked_dir.joinpath('mt3d_runs')



def get_ftl(recalc=False):
    model_name = 'low_lake'
    base_run_dir = unbacked_dir.joinpath('ftl_creation')
    base_run_dir.mkdir(exist_ok=True)
    model_ws = base_run_dir.joinpath(model_name)

    ftl_path = model_ws.joinpath(f'{model_name}.ftl')
    if ftl_path.exists() and not recalc:
        return ftl_path

    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    opt_ghb_spd = get_ghb_data(opt_tdis)
    temp = opt_ghb_spd[0]
    # update this to use lower lake levels
    temp = pd.DataFrame(temp)
    temp = temp.loc[temp.k>0]
    temp.loc[:,'bhead'] = 330
    opt_ghb_spd[0] = opt_tdis.manage_period_dtypes(temp, flopy.modflow.ModflowGhb.get_default_dtype(), 0,)

    opt_rch = get_rch_data(opt_tdis, rch_param)
    opt_str_spd = get_str_data(opt_tdis, riv_params=riv_params)
    opt_well_spd = get_well_data(opt_tdis,
                                 hill_param=hill_param,
                                 race_param=race_param)

    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=opt_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=opt_rch,
                 ghb_spd=opt_ghb_spd,
                 str_spd=opt_str_spd,
                 well_spd=opt_well_spd,
                 outdir=model_ws,
                 build_run_model=True, process_results=False,
                 stress_periods=[0],
                 make_ftl=True)
    assert smt.modelchecks.modflow_converged(model_ws.joinpath(f'{model_name}.list')), 'did not converge!'
    assert ftl_path.exists()
    return ftl_path




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
    base_out = proj_root.joinpath('historical_investigation/mt3d_indicator_scenarios')
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
    base_out = proj_root.joinpath('historical_investigation/mt3d_indicator_scenarios')
    base_ucn = base_out.joinpath('ucn_data')
    outdir = base_ucn.home().joinpath('unbacked/hawea/rasters')
    outdir.mkdir(exist_ok=True)
    for p in base_ucn.glob('*.npz'):
        data = np.load(p)['id_conc'][2]
        smt.io.array_to_raster(outdir.joinpath(p.with_suffix('.tif').name), data, no_flow_layer=0)


def plot_joint_mt3d():
    base_out = proj_root.joinpath('historical_investigation/mt3d_indicator_scenarios')
    base_out.mkdir(exist_ok=True)
    base_ucn = base_out.joinpath('ucn_data')
    base_ucn.mkdir(exist_ok=True)
    base_plots = base_out.joinpath('plots')
    base_plots.mkdir(exist_ok=True)
    outdir = base_plots.joinpath('joint')
    outdir.mkdir(exist_ok=True)

    for p in base_ucn.glob('*.npz'):
        data_low = np.load(p)['id_conc'][2]
        data_high = np.load(proj_root.joinpath('Scenarios/mt3d_indicator_scenarios',
                                               p.relative_to(base_out)))['id_conc'][2]
        fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10, 10), sharex=True, sharey=True)
        smt.plot.plt_matrix(data_low, vmin=0, vmax=1,
                            title='At low lake levels (<330)', no_flow_layer=0,
                            base_map=True, ax=ax1)
        smt.plot.plt_matrix(data_high, vmin=0, vmax=1,
                            title='At high lake levels (>338)', no_flow_layer=0,
                            base_map=True, ax=ax2)

        fig.suptitle(f'fraction of water from {p.name.replace(".npz", "")}')
        fig.tight_layout()
        fig.savefig(outdir.joinpath(p.name.replace('.npz', '.png')))





if __name__ == '__main__':
    #get_ftl(False)
    #run_indictors(rerun=False)
    #extract_data()
    #ucn_to_raster()
    plot_joint_mt3d()