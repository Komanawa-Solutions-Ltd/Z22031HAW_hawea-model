"""
created matt_dumont 
on: 13/02/23
"""
import tempfile

import pandas as pd
from Scenarios.run_flow_scenario import run_scenario
import os
import shutil
import flopy
import numpy as np
from optimisation.optimisation_period import tdis as opt_tdis
from model_build.get_boundary_condition_data import get_rch_data, get_ghb_data, get_well_data, get_str_data
from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from project_base import unbacked_dir, proj_root
from model_build.project_model_tools import smt
from model_build.supporting_data_analysis import get_river_loc_data, get_race_locs, get_hillside_catchment_locs, \
    get_lake_hawea_loc
from model_tools.regular_modeltools import ModelTools_RegularGrid
from optimisation.final_opt_models.compress_uncompress_model import uncompress_model
from pathlib import Path


def save_opt_spd(outdir):
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    opt_ghb_spd = get_ghb_data(opt_tdis)[0]
    opt_rch = get_rch_data(opt_tdis, rch_param)[0]
    opt_str_spd = get_str_data(opt_tdis, riv_params=riv_params)[0]
    opt_well_spd = get_well_data(opt_tdis,
                                 hill_param=hill_param,
                                 race_param=race_param)[0]
    np.savez_compressed(outdir.joinpath('opt_spd.npz'), rch=opt_rch)
    from model_build.get_boundary_condition_data import get_river_loc_data, get_race_locs, get_hillside_catchment_locs, \
        get_pumping_locs
    outpath = outdir.joinpath('spd.hdf')
    pd.DataFrame(opt_ghb_spd).to_hdf(outpath, 'ghb')
    t = pd.DataFrame(opt_str_spd)
    t = pd.merge(t, get_river_loc_data().reset_index(), on=['k', 'i', 'j'])
    t.to_hdf(outpath, 'str')
    t = pd.DataFrame(opt_well_spd)
    all_wells = []
    temp = get_pumping_locs().reset_index()
    temp.loc[:, 'wtype'] = 'pumping'
    all_wells.append(temp)
    temp = get_hillside_catchment_locs().reset_index()
    temp.loc[:, 'wtype'] = 'hillside'
    all_wells.append(temp)
    temp = get_race_locs().reset_index()
    temp.loc[:, 'wtype'] = 'race'
    all_wells.append(temp)
    t = pd.merge(t, pd.concat(all_wells), on=['k', 'i', 'j'])
    t.to_hdf(outpath, 'wel')


def get_ftl(recalc=False):
    model_name = 'opt_ss'
    base_run_dir = unbacked_dir.joinpath('ftl_creation')
    base_run_dir.mkdir(exist_ok=True)
    model_ws = base_run_dir.joinpath(model_name)

    ftl_path = model_ws.joinpath(f'{model_name}.ftl')
    if ftl_path.exists() and not recalc:
        return ftl_path

    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    opt_ghb_spd = get_ghb_data(opt_tdis)
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


def create_ssm_data(race_con=0, all_hill=0,
                    hawear_con=0, clutha_con=0, lake_con=0, john_con=0, gview_con=0,
                    maungawera=None, flat_west=None, flat_east=None, terrace_east=None, south_east=None, ):
    sub_hills_none = np.array(
        [maungawera is None, flat_west is None, flat_east is None, terrace_east is None, south_east is None])
    assert all_hill is None or all(sub_hills_none), 'only one of (all hill, subhills) can be passed'
    assert all_hill is not None or all(~sub_hills_none), 'only one of (all hill, subhills) can be passed'

    hill_locs = get_hillside_catchment_locs()
    str_locs = get_river_loc_data()
    lake_locs = get_lake_hawea_loc()
    race_locs = get_race_locs()

    # specify itype
    hill_locs.loc[:, 'itype'] = 2
    race_locs.loc[:, 'itype'] = 2
    lake_locs.loc[:, 'itype'] = 5
    str_locs.loc[:, 'itype'] = 4

    # specify concentration
    'css'
    if all_hill is not None:
        hill_locs.loc[:, 'css'] = all_hill
    else:
        for g in hill_locs.group.unique():
            hill_locs.loc[hill_locs.group == g, 'css'] = eval(g)
    race_locs.loc[:, 'css'] = race_con
    lake_locs.loc[:, 'css'] = lake_con

    str_locs.loc[str_locs.rname == 'hawea', 'css'] = hawear_con
    str_locs.loc[str_locs.rname == 'clutha', 'css'] = clutha_con
    str_locs.loc[str_locs.rname == 'gview', 'css'] = gview_con
    str_locs.loc[str_locs.rname == 'john', 'css'] = john_con

    ssm_spd = pd.concat((hill_locs, race_locs, str_locs, lake_locs))
    ssm_spd = ssm_spd.loc[:, ['k', 'i', 'j', 'css', 'itype']]
    ssm_spd = ssm_spd.loc[(~np.isclose(ssm_spd.css, 0) | (ssm_spd.itype == 1))]
    return ssm_spd


def get_default_mt3d_kwargs():
    """
    get the default mt3d parameters for most arguments that do not need to be changed for create_mt3d
    :return: dictionary of kwargs
    """
    default_mt3d_dict = {
        'adv_sov': 0,  # 
        'adv_percel': 1,  # matcheds 
        'btn_porsty': 0.3,  #
        'btn_scon': 0.1,  #
        'btn_nprs': 0,  # output timing (only at end)
        'btn_timprs': None,  # not needed
        'dsp_lon': 10,  #
        'dsp_trpt': 0.1,  #
        'dsp_trpv': 0.01,  #
        'nper': 1,  # tried to   but didn't run so set back to 1
        'perlen': 7.3050E5,  # 's
        'nstp': 1,  # s
        'tsmult': 1.5,  # s
        'ssflag': None,  # DO NOT SET
        'dt0': 1000,  # s # I may be able to increase this and reduce run time
        'mxstrn': 10000000,  # s
        'ttsmult': 1.5,  # s
        'ttsmax': 50000,  # s # I may be able to increase this and reduce run time
        'gcg_isolve': 3,  # s
        'gcg_inner': 500,  # s
        'gcg_outer': 100  # s
    }
    return default_mt3d_dict


def create_mt3d(ftl_path, mt3d_name, mt3d_ws, smt, run_model=True, num_species=1,
                ssm_crch=None, ssm_stress_period_data=None,
                adv_sov=0, adv_percel=1,
                btn_porsty=0.05, btn_scon=0, btn_nprs=0, btn_timprs=None,
                dsp_lon=0.1, dsp_trpt=0.1, dsp_trpv=0.01,
                nper=1, perlen=1, nstp=1, tsmult=1,  # these can be either value of list of values
                # and must match flow model if it is not SS
                ssflag=None, dt0=0, mxstrn=50000, ttsmult=1.0, ttsmax=0,  # these can be either value of list of values
                gcg_isolve=1, gcg_inner=50, gcg_outer=1, rerun=False):
    """
    create a mt3d model
    :param ftl_path: path to the FTL file to use with MT3D
    :param mt3d_name: the name for all mt3d files if none name will mirror that of the modflow model name
    :param mt3d_ws: working directory for the MT3D model
    :param num_species: number of species to calculate
    :param ssm_crch: the recharge concentration for species 1 this must be a dict {stressperiod: crch}
    :param ssm_stress_period_data: stress period data for other source/sinks this must be a dict {stressperiod: ssm}

    below here can generally be added by the default mt3d dictionary
    :param adv_sov: is an integer flag for the advection solution option.
                       0: the standard finite-difference method with upstream or central-in-space weighting,
                          depending on the value of NADVFD;
                       1: the forward-tracking method of characteristics (MOC)
                       2: the backward-tracking modified method of characteristics (MMOC)
                       3: the hybrid method of characteristics (HMOC) with MOC or MMOC
                          automatically and dynamically selected
                       -1: the third-order TVD scheme (ULTIMATE).
                    currently set up for only -1 or 0
    :param adv_percel: PERCEL is the Courant number (i.e., the number of cells, or a fraction of a cell)
                       advection will be allowed in any direction in one transport step. For implicit finite-difference
                       or particle-tracking-based schemes, there is no limit on PERCEL, but for accuracy reasons, it is
                       generally not set much greater than one. Note, however, that the PERCEL limit is checked over the
                       entire model grid. Thus, even if PERCEL > 1, advection may not be more than one cell's length at
                       most model locations. For the explicit finite-difference or the third-order TVD scheme,
                       PERCEL is also a stability constraint which must not exceed one and will be automatically reset
                       to one if a value greater than one is specified.
    :param btn_porsty: porosity for the model
    :param btn_scon: float, array of (nlay, nrow, ncol), or filename, or a list (length ncomp) of these for
                     multi-species simulations The starting concentration for the solute transport simulation
    :param btn_nprs: A flag indicating (i) the frequency of the output and (ii) whether the output frequency is
                     specified in terms of total elapsed simulation time or the transport step number. If nprs > 0
                     results will be saved at the times as specified in timprs; if nprs = 0, results will not be saved
                     except at the end of simulation; if NPRS < 0, simulation results will be saved whenever the number
                     of transport steps is an even multiple of nprs. (default is 0).
    :param btn_timprs: The total elapsed time at which the simulation results are saved. The number of entries in timprs
                       must equal nprs. (default is None).
    :param dsp_lon: the longitudinal dispersivity, for every cell of the model grid (unit, L).
    :param dsp_trpt: is a 1D real array defining the ratio of the horizontal transverse dispersivity to the longitudinal
                     dispersivity. Each value in the array corresponds to one model layer.
    :param dsp_trpv: is the ratio of the vertical transverse dispersivity to the longitudinal dispersivity. Each value
                     in the array corresponds to one model layer. Some recent field studies suggest that TRPT is
                     generally not greater than 0.01. Set TRPV equal to TRPT to use the standard isotropic dispersion
                     model (Equation 10 in Chapter 2). Otherwise, the modified isotropic dispersion model is used
    :param nper: number to periods for the tranport simulation
    :param perlen: the length of the transport simulation (must match flow model if the flow model is not steady state
    :param nstp: number of time steps for the transient flow simulation
    :param tsmult: multiplier for time steps in flow solution
    :param ssflag:  If SSFlag is set to SSTATE (case insensitive), the steady-state transport simulation is
                    automatically activated. (see mt3dms_V5_ supplemental for more info) must be an iterable otherwise
                    only the first letter will be written
    :param dt0: The user-specified initial transport step size within each time-step of the flow solution.
    :param mxstrn: The maximum number of transport steps allowed within one time step of the flow solution.
    :param ttsmult: The multiplier for successive transport steps within a flow time-step if the GCG solver is used
                    and the solution option for the advection term is the standard finite-difference method.
    :param ttsmax: The maximum transport step size allowed when transport step size multiplier TTSMULT > 1.0.
    :param gcg_isolve: is the type of preconditioners to be used with the Lanczos/ORTHOMIN acceleration scheme:
                       1: Jacobi
                       2: SSOR
                       3: Modified Incomplete Cholesky (MIC)
                         (MIC usually converges faster, but it needs significantly more memory)
    :param gcg_inner: is the maximum number of inner iterations;
                      a value of 30-50 should be adequate for most problems. (default is 50)
    :param gcg_outer: is the maximum number of outer iterations;
                      it should be set to an integer greater than one only when a nonlinear sorption isotherm
                      is included in simulation. (default is 1)
    :return: mt3d instance
    """
    assert isinstance(smt, ModelTools_RegularGrid)
    # to add the parameters that are missing

    # convert from pd.dataframe to record arrays as record arrays cannot be handled by pickle
    ssm_stress_period_data = opt_tdis.manage_dtypes(ssm_stress_period_data, flopy.mt3d.Mt3dSsm.get_default_dtype(),
                                                    check_periods_match=False)
    # check that FTL is in the model_ws folder and if not move it there

    listfile = os.path.join(mt3d_ws, f'{mt3d_name}.list')
    if not rerun and os.path.exists(listfile):
        if smt.modelchecks.mt3d_converged(listfile):
            return None

    if not os.path.exists(mt3d_ws):
        os.makedirs(mt3d_ws)

    ftl_name = os.path.basename(ftl_path)
    if not os.path.dirname(ftl_path) == mt3d_ws:
        shutil.copyfile(ftl_path, os.path.join(mt3d_ws, ftl_name))

    # packages I'll likely need
    mt3d = flopy.mt3d.Mt3dms(modelname=mt3d_name,
                             modflowmodel=None,
                             ftlfilename=ftl_name,
                             ftlfree=False,  # formatted FTL to handle bug
                             version='mt3d-usgs',
                             exe_name='mt3dusgs',
                             structured=True,
                             # defualt probably fine, though a point of weakness I don't know what it is
                             listunit=500,
                             ftlunit=501,
                             model_ws=mt3d_ws,
                             load=True,  # defualt
                             silent=0  # defualt
                             )

    # BTN
    elv_db = smt.get_elv_db()

    # Open source improve mt3dms the dry cell line in the BTN (via flopy) is a bug fix!!!  # A3; Keywords, also a user warning for setting them
    btn = flopy.mt3d.Mt3dBtn(mt3d,
                             MFStyleArr=False,  # defualt it's a reader, should hopefully not cause problems
                             DRYCell=True,  # pass through dry cells
                             Legacy99Stor=False,  # defualt
                             FTLPrint=False,  # defualt
                             NoWetDryPrint=False,  # defualt shouldn't be a problem
                             OmitDryBud=True,  # as passing through dry cells
                             AltWTSorb=False,  # defualt not using sorbing to my knowledge
                             ncomp=1,  # number of species
                             mcomp=1,  # number of moblile species
                             tunit='D',
                             lunit='M',
                             munit='G',
                             prsity=btn_porsty,
                             icbund=smt.get_no_flow(),  # all cells active
                             sconc=btn_scon,
                             cinact=-1,  # 's
                             thkmin=0.01,  # defualt

                             # printing flags 0 is not print
                             ifmtcn=0,
                             ifmtnp=0,
                             ifmtrf=0,
                             ifmtdp=0,

                             savucn=True,  # default
                             nprs=btn_nprs,
                             timprs=btn_timprs,
                             obs=None,  # default not using as it is easier to pull from the UCN file
                             nprobs=1,  # not using obs so doesnt matter
                             chkmas=True,
                             nprmas=1,  # defualt print mass balance for each time period

                             # modflow model parameters
                             nper=nper,
                             perlen=perlen,
                             nstp=nstp,
                             tsmult=tsmult,
                             ncol=smt.cols,
                             nlay=smt.layers,
                             nrow=smt.rows,
                             laycon=smt.layer_type,
                             delr=smt.grid_space,
                             delc=smt.grid_space,
                             htop=elv_db[0],
                             dz=elv_db[0:-1] - elv_db[1:],

                             ssflag=ssflag,
                             dt0=dt0,
                             mxstrn=mxstrn,
                             ttsmult=ttsmult,
                             ttsmax=ttsmax,
                             species_names=['N'],
                             extension='btn',
                             unitnumber=503
                             )

    # ADV
    if adv_sov >= 1:
        raise ValueError('mt3d object not configured for specified advection solver {}'.format(adv_sov))

    adv = flopy.mt3d.Mt3dAdv(mt3d,
                             mixelm=adv_sov,
                             percel=adv_percel,
                             mxpart=5000,  # not using particles
                             nadvfd=1,  # default to upstream weighting
                             itrack=3,  # not using particles
                             wd=0.5,  # not using particles
                             dceps=1e-05,  # defualt
                             nplane=2,  # not using particles
                             npl=10,  # not using particles
                             nph=40,  # not using particles
                             npmin=5,  # not using particles
                             npmax=80,  # not using particles
                             nlsink=0,  # not using particles
                             npsink=15,  # not using particles
                             dchmoc=0.0001,  # not using MOC or MMOC or HMOC
                             unitnumber=502
                             )
    # DSP
    dsp = flopy.mt3d.Mt3dDsp(mt3d,
                             al=np.full((smt.layers, smt.rows, smt.cols), dsp_lon),
                             trpt=np.full((smt.layers), dsp_trpt),
                             trpv=np.full((smt.layers), dsp_trpv),
                             dmcoef=smt.get_model_zeros(True),
                             # default don't think I need as only if multidiff True
                             extension='dsp',
                             multiDiff=True,  # only one component
                             unitnumber=504)

    # SSM
    # warnings.warn('SSM Package: mxss is None and modflowmodel is ' +
    #              'None.  Cannot calculate max number of sources ' +
    #              'and sinks.  Estimating from stress_period_data. ')

    ssm = flopy.mt3d.Mt3dSsm(mt3d,
                             crch=ssm_crch,
                             cevt=None,
                             mxss=100000,
                             # default max number of sources and sinks this is calculated from modflow model # define aprioi
                             stress_period_data=ssm_stress_period_data,
                             dtype=None,  # default I should not need to specify this, but we'll see
                             extension='ssm',
                             unitnumber=505,
                             )

    # GCG
    gcg = flopy.mt3d.Mt3dGcg(mt3d,
                             mxiter=gcg_outer,  # defualt
                             iter1=gcg_inner,  # defualt
                             isolve=gcg_isolve,  # 1, Jacobi = 2, SSOR = 3, Modified Incomplete Cholesky (MIC)
                             ncrs=0,  # lump despersion tensor to RHS
                             accl=1,  # defualt and likely not used
                             cclose=1e-06,  # defualt
                             iprgcg=0,  # defualt print max changes at end of each iteration
                             extension='gcg',
                             unitnumber=506,
                             )

    # to add output for the standard output update flopy with this at some point in teh btn package
    # i could also add the species name if supplied
    mt3d.add_output('{}.CNF'.format(mt3d_name), 17)
    for i in range(1, num_species + 1):
        mt3d.add_output('{}{:03d}.UCN'.format(mt3d_name, i), 200 + i, True)
        # mt3d.add_output('{}{:03d}.OBS'.format(mt3d_name,i),400+i,False) # not using, but should put in flopy
        mt3d.add_output('{}{:03d}.MAS'.format(mt3d_name, i), 600 + i, False)

    if run_model:
        mt3d.write_input()
        mt3d.run_model()
        assert smt.modelchecks.mt3d_converged(listfile)

    return mt3d


if __name__ == '__main__':
    save_opt_spd(Path(
        '/home/matt_dumont/PycharmProjects/modflow_tools_haw/modflow_suite_support/test_modflow_suite_support/from_hawea_model'))
    get_ftl(True)
    pass
