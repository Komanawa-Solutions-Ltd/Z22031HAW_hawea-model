"""
 From GIMPZ_2020
 Author: Matt Hanson
 Created: 03-Oct-19 8:52 AM
 """

import flopy
import os
import pandas as pd
import numpy as np
from copy import copy
from model_tools.regular_modeltools import ModelTools_RegularGrid
from model_tools.time_discretization import TimeDis


def build_calibration_model(smt, tdis, exe_name, model_name, model_ws, hk, vka, layer_avg, chani, constant_heads, rch=None,
                            options='COMPLEX',
                            drn_spd=None, well_spd=None, mnwell_data=None, nwt_kwargs={},
                            hani=None, ss=0, sy=0, mfv='mfnwt', run_model=False):
    """
    build modflow model
    :param smt: instance of ModelTools
    :param tdis: time discritisation object for the model
    :param exe_name: path to the exe file for modflow
    :param model_name: model_name
    :param model_ws: model working directory
    :param hk: a 3d array or None for hydralic conductivity
    :param vka: single value or 3d array, for ratio of vertical conductivity true_vka = hk/vka
    :param layer_avg: a flag for each layer that defines the method of calculating interblock transmissivity.
                      • 0—harmonic mean
                      • 1—logarithmic mean
                      • 2—arithmetic mean of saturated thickness and logarithmic-mean hydraulic conductivity.
    :param chani: CHANI contains a value for each layer that is a flag or the horizontal anisotropy.
                  If CHANI is less than or equal to 0, then variable HANI defines horizontal anisotropy.
                  If CHANI is greater than 0, then CHANI is the horizontal anisotropy for the entire layer,
                  and HANI is not read. If any HANI parameters are used, CHANI for all
                  layers must be less than or equal to 0.
    :param constant_heads: 3d array of constant heads, where heads are not constant set to np.nan
    :param rch: single value or 2d array of recharge in mm/day
    :param options: one of ['SIMPLE', 'MODERATE', 'COMPLEX']
                    SIMPLE:  indicates that default solver input values will be defined that work well for nearly
                             linear models. This would be used for models that do not include nonlinear stress
                             packages, and models that are either confined or consist of a single unconfined layer that
                             is thick enough to contain the water table within a single layer.
                    MODERATE: indicates that default solver input values will be defined that work well for moderately
                              nonlinear models. This would be used for models that include nonlinear stress packages,
                              and models that consist of one or more unconfined layers. The “MODERATE” option should be
                              used when the “SIMPLE” option does not result in successful convergence.
                    COMPLEX: indicates that default solver input values will be defined that work well for highly
                             nonlinear models. This would be used for models that include nonlinear stress packages,
                             and models that consist of one or more unconfined layers representing complex geology
                             and sw/gw interaction. The “COMPLEX” option should be used when the “MODERATE” option
                             does not result in successful convergence.
                    for more details see options in modflownwt  at
                    https://water.usgs.gov/ogw/modflow-nwt/MODFLOW-NWT-Guide/index.html?nwt_newton_solver.htm
    :param drn_spd: dictionary of drain stress period values
    :param well_spd: dictionary of well stress period values
    :param mnwell_data: data to pass to the package dictionary:
                        node data : node data, note at present the pump location is 1 indexed while the node location
                                    is zero indexed. # todo pull request, and check
                        spd: stress period data
                        see flopy.modflow.ModflowMnw2 for more details
    :param nwt_kwargs: additonal kwargs for _create_nwt_package()
    :param hani: HANI is the ratio of hydraulic conductivity along columns to hydraulic conductivity
                 along rows, where HK of item 9 specifies the hydraulic conductivity along rows. Thus, the
                 hydraulic conductivity along columns is the product of the values in HK and HANI.
                 Read only if CHANI <= 0.
    :param ss: Ss is specific storage, single value or 3d array, Read only for a transient simulation
    :param sy: Sy is specific yield, single value or 3d array. Read only for a transient simulation
               and if the layer is convertible (LAYTYP >0).
    :param mfv: the modflow version mf2005 or mfnwt (e.g. lpf vs upw package)
               replace hk with files is assumed to be used
    :param run_model: boolean, if True run model and return converged string, other wise do not run and return m
    :return: 'model: {}, converged: {}'.format(model_name, boolean) (run_model=False) or m (run_model=False)
    """
    assert isinstance(smt, ModelTools_RegularGrid)
    assert isinstance(tdis, TimeDis)
    if not os.path.exists(model_ws):
        os.makedirs(model_ws)

    m = flopy.modflow.mf.Modflow(modelname=model_name,
                                 version=mfv,
                                 exe_name=exe_name,
                                 structured=True,
                                 model_ws=model_ws,
                                 external_path=None,
                                 verbose=False, )

    _create_dis_package(m, smt, tdis)
    _create_bas_package(m, smt, constant_heads)
    _create_lay_prop_package(m, smt, hk, vka, layer_avg, chani, hani=hani, ss=ss, sy=sy, mfv=mfv)
    _create_nwt_package(m, options=options, **nwt_kwargs)
    if rch is not None:
        _create_rch_package(m, rch)
    if drn_spd is not None:
        assert isinstance(drn_spd, dict), 'drain spd needs to be a dictionary'
        _create_drn_package(m, drn_spd)
    if well_spd is not None:
        assert mnwell_data is None, 'cannot have both well and multi node well packages'
        assert isinstance(well_spd, dict), 'well spd needs to be a dictionary'
        _create_wel_package(m, well_spd)
    if mnwell_data is not None:
        assert well_spd is None, 'cannot have both well and multi node well packages'
        _create_mnwell_package(m, mnwell_data)

    flopy.modflow.ModflowOc(m, stress_period_data={(0, 0): ['save head', 'save budget']})

    if run_model:
        m.write_input()
        m.run_model()

        out = 'model: {}, converged: {}'.format(model_name,
                                                smt.modelchecks.modflow_converged(
                                                    os.path.join(model_ws, '{}.list'.format(model_name))))
        return out
    else:
        return m


def _create_dis_package(m, smt, tdis):
    """
    create and add the dis package
    :param m: a flopy model instance
    :return:
    """
    assert isinstance(tdis, TimeDis)
    elv_db = smt.get_elv_db()
    dis = flopy.modflow.mfdis.ModflowDis(m,
                                         nlay=smt.layers,
                                         nrow=smt.rows,
                                         ncol=smt.cols,
                                         nper=tdis.nper,
                                         delr=smt.grid_space,
                                         delc=smt.grid_space,
                                         laycbd=0,  # no quasi confining bed
                                         top=elv_db[0],
                                         botm=elv_db[1:],
                                         perlen=tdis.perlen,
                                         nstp=tdis.nstp,
                                         tsmult=tdis.tsmult,
                                         steady=tdis.steady,
                                         itmuni=tdis.mftunit,  # days
                                         lenuni=2,  # meters
                                         unitnumber=719,
                                         xul=smt.ulx,
                                         yul=smt.uly,
                                         rotation=smt.rotation,
                                         proj4_str=f'EPSG:{smt.epsg}')


def _create_bas_package(m, smt, constant_heads):
    """
    create and add the bas package
    :param m: a flopy model instance
    :return:
    """

    bas = flopy.modflow.mfbas.ModflowBas(m,
                                         ibound=smt.get_no_flow(),
                                         strt=_create_starting_heads(smt, constant_heads),
                                         ifrefm=True,
                                         ixsec=False,
                                         ichflg=False,
                                         stoper=None,
                                         hnoflo=1e+30)


def _create_starting_heads(smt, constant_heads):
    """
    set starting heads at the top of the elevation except the constant heads
    :return:
    """
    hds = np.repeat(smt.get_elv_db()[0][np.newaxis, :, :],
                    smt.layers, axis=0)  # set to top of layer 1
    idx = smt.get_no_flow() < 0
    hds[idx] = constant_heads[idx]
    if not all(np.isfinite(hds).flatten()):
        raise ValueError('nan values in starting heads')
    return hds


def _create_lay_prop_package(m, smt, hk, vka, layer_avg, chani, hani=None, ss=0, sy=0, mfv='mfnwt'):
    """
    create the layer property package
    :param m: a flopy model instance
    :param smt: a Model Tools instance
    :param hk: a single value or 3d array for hydralic conductivity
    :param vka: single value or 3d array, for ratio of vertical conductivity to horizontal conductivity to calculate
                true_vka = hk/vka
    :param layer_avg: a flag for each layer that defines the method of calculating interblock transmissivity.
                      • 0—harmonic mean
                      • 1—logarithmic mean
                      • 2—arithmetic mean of saturated thickness and logarithmic-mean hydraulic conductivity.
    :param chani: CHANI contains a value for each layer that is a flag or the horizontal anisotropy.
                  If CHANI is less than or equal to 0, then variable HANI defines horizontal anisotropy.
                  If CHANI is greater than 0, then CHANI is the horizontal anisotropy for the entire layer,
                  and HANI is not read. If any HANI parameters are used, CHANI for all
                  layers must be less than or equal to 0.
    :param hani: HANI is the ratio of hydraulic conductivity along columns to hydraulic conductivity
                 along rows, where HK of item 9 specifies the hydraulic conductivity along rows. Thus, the
                 hydraulic conductivity along columns is the product of the values in HK and HANI.
                 Read only if CHANI <= 0.
    :param ss: Ss is specific storage, single value or 3d array, Read only for a transient simulation
    :param sy: Sy is specific yield, single value or 3d array. Read only for a transient simulation
               and if the layer is convertible (LAYTYP >0).
    :param mfv: the modflow version mf2005 or mfnwt (e.g. lpf vs upw package)
               replace hk with files is assumed to be used
    :return:
    """
    assert isinstance(smt, ModelTools_RegularGrid)
    chani = np.atleast_1d(chani)
    if len(chani) == 1:
        chani = np.repeat(chani, smt.model_array_shape[0])
    assert chani.shape == (smt.model_array_shape[0],), ('chani must match number of layers or be a single value '
                                                        'or length 1')
    if hani is None:
        assert (np.atleast_1d(chani) > 0).all(), 'if hani is not set then chani needs to be >0 for all layers'
        hani = 0
    else:
        assert (np.atleast_1d(chani) <= 0).all(), 'if hani is set then chani needs to be <=0 for all layers'
        assert np.atleast_1d(hani).shape == smt.model_array_shape, 'hani must match model shape'

    layer_vka = 1  # sets vertical conductivity (vk) as a ratio of hydralic conductivity (vk)

    if mfv == 'mfnwt':
        flopy.modflow.mfupw.ModflowUpw(m,
                                       laytyp=smt.layer_type,
                                       layavg=layer_avg,
                                       chani=chani,
                                       layvka=layer_vka,
                                       laywet=0,
                                       ipakcb=740,
                                       hdry=-888.0,
                                       iphdry=1,
                                       hk=hk,
                                       hani=hani,
                                       vka=vka,
                                       ss=ss,
                                       sy=sy,
                                       vkcb=0.0,
                                       noparcheck=False)
    elif mfv == 'mf2005':
        flopy.modflow.mflpf.ModflowLpf(m,
                                       laytyp=smt.layer_type,
                                       layavg=layer_avg,
                                       chani=chani,
                                       layvka=layer_vka,
                                       laywet=0,
                                       ipakcb=740,
                                       hdry=-888.0,
                                       iwdflg=0,
                                       wetfct=0.1,  # not using
                                       iwetit=1,  # not using
                                       ihdwet=0,  # not using
                                       hk=hk,
                                       hani=hani,
                                       vka=vka,
                                       ss=ss,
                                       sy=sy,
                                       vkcb=0.0,
                                       wetdry=-0.01,  # not using
                                       storagecoefficient=False,
                                       constantcv=False,
                                       thickstrt=False,
                                       nocvcorrection=False,
                                       novfc=False,
                                       unitnumber=704)
    else:
        raise ValueError('unexpected modflow version {}'.format(mfv))


def _create_nwt_package(m, options, headtol=0.01, fluxtol=500, maxiterout=100, thickfact=1e-05, linmeth=1, iprnwt=1,
                        ibotav=0, Continue=False):
    """
    create the nwt solver package
    :param m: input model
    :param options: one of ['SIMPLE', 'MODERATE', 'COMPLEX']
                    SIMPLE:  indicates that default solver input values will be defined that work well for nearly
                             linear models. This would be used for models that do not include nonlinear stress
                             packages, and models that are either confined or consist of a single unconfined layer that
                             is thick enough to contain the water table within a single layer.
                    MODERATE: indicates that default solver input values will be defined that work well for moderately
                              nonlinear models. This would be used for models that include nonlinear stress packages,
                              and models that consist of one or more unconfined layers. The “MODERATE” option should be
                              used when the “SIMPLE” option does not result in successful convergence.
                    COMPLEX: indicates that default solver input values will be defined that work well for highly
                             nonlinear models. This would be used for models that include nonlinear stress packages,
                             and models that consist of one or more unconfined layers representing complex geology
                             and sw/gw interaction. The “COMPLEX” option should be used when the “MODERATE” option
                             does not result in successful convergence.
                    for more details see options in modflownwt  at
                    https://water.usgs.gov/ogw/modflow-nwt/MODFLOW-NWT-Guide/index.html?nwt_newton_solver.htm

    :param headtol: HEADTOL (units of length)—is the maximum head change between outer iterations for solution of
                    the nonlinear problem (real).
    :param fluxtol: FLUXTOL (units of length cubed per time)—is the maximum root-mean-squared flux difference between
                    outer iterations for solution of the nonlinear problem (real).
    :param maxiterout: the maximum number of iterations to be allowed for solution of the outer
                       (nonlinear) problem (integer).


    :param thickfact: THICKFACT is the portion of the cell thickness (length) used for smoothly adjusting storage and
                      conductance coefficients to zero (symbol Ω in equation 9; real).
    :param linmeth: LINMETH is a flag that determines which matrix solver will be used (integer).
                        A value of 1 indicates GMRES will be used
                        A value of 2 indicates χMD will be used. The χMD can not be used with local grid refinement
                        in MODFLOW-OWHM.
    :param iprnwt: IPRNWT is a flag that indicates whether additional information about solver convergence will be
                   printed to the main listing file (integer).
    :param ibotav: IBOTAV is a flag that indicates whether corrections will be made to groundwater head relative to the
                   cell-bottom altitude if the cell is surrounded by dewatered cells (integer). A value of 1 indicates
                   that a correction will be made and a value of 0 indicates no correction will be made. This input
                   variable is problem specific and both options (IBOTAV=0 or 1) should be tested. MODFLOW-NWT provides
                   two different methods for simulating dry cells in the deepest layer, and the option is defined by
                   the NWT input file variable IBOTAV. Head for cells in the deepest layer, and for single-layer models,
                   cannot fall below the cell-bottom altitude if the input variable IBOTAV is set to 1; otherwise,
                   heads in the deepest layer can fall below the cell-bottom altitude. The value of IBOTAV does not
                   affect the solution because dry bottom-layer cells are effectively ignored in the solution
                   (that is, for a cell that does not receive inflow, the coefficients are essentially zero in the row
                   of the matrix in which a bottom-layer cell is the diagonal element). IBOTAV is provided because it
                   can affect convergence behavior for a cell with thin saturated thickness. The value of IBOTAV that
                   provides the fastest convergence rate appears to be problem specific.
    :param Continue: If True if the model fails to converge during a time step then it will continue to solve the
                     following time step. However, if the "CONTINUE" is removed from this line then the model will stop
                     after convergence failure. See also: the STOPERROR option in the Basic Package
    :return:
    """

    flopy.modflow.mfnwt.ModflowNwt(m,
                                   headtol=headtol,
                                   fluxtol=fluxtol,
                                   maxiterout=maxiterout,
                                   thickfact=thickfact,
                                   linmeth=linmeth,
                                   iprnwt=iprnwt,
                                   ibotav=ibotav,
                                   options=options,
                                   Continue=Continue
                                   )


def _create_drn_package(m, drn_spd):
    drn = flopy.modflow.ModflowDrn(m, stress_period_data=drn_spd)


def _create_rch_package(m, rch):
    """
    create and add the recharge package
    :param m: a flopy model instance
    :param rch: recharge in m3/day either numeric or array with shape (wai_smt.rows, wai_smt.cols)
    :return:
    """
    zone_recharge = copy(rch)  # m3/day

    if zone_recharge.max() > 23987 / 365 / 1000:
        raise ValueError('recharge is more than 1m/year greater than the maximum recorded annual '
                         'rainfall, check your units')

    rch = flopy.modflow.mfrch.ModflowRch(m,
                                         nrchop=3,  # recharege to highest cell
                                         ipakcb=740,  # save budget
                                         rech=zone_recharge,
                                         # does this need to be a dictionay?, no which is wierd
                                         unitnumber=716)


def _create_wel_package(m, well_spd):
    """
    create and add the well package
    :param m: a flopy model instance
    :param wel_version: which version of wells to use
    :return:
    """
    wel = flopy.modflow.mfwel.ModflowWel(m,
                                         ipakcb=740,  # save budget
                                         stress_period_data=well_spd,
                                         unitnumber=709)


def _create_mnwell_package(m, mnwell_data):
    """
    create a multi node well package
    :param m: model
    :param mnwell_data: data to pass to the package dictionary:
                        node data : node data, note at present the pump location is 1 indexed while the node location
                                    is zero indexed. # todo pull request
                        spd: stress period data
                        see flopy.modflow.ModflowMnw2 for more details
    :return:
    """
    assert isinstance(mnwell_data, dict)

    # todo write data checks!
    # data dimensions
    node_data = mnwell_data['node_data']
    node_data = node_data.to_records(index=False)
    spd = mnwell_data['spd']
    spd = spd.to_records(index=False)

    wel = flopy.modflow.ModflowMnw2(m,
                                    mnwmax=-len(mnwell_data['spd']),
                                    nodtot=len(mnwell_data['node_data']),
                                    ipakcb=740,  # requires separate cbc? 740 is the cbc file
                                    mnwprnt=0,
                                    aux=[],
                                    node_data=node_data,
                                    mnw=None,
                                    stress_period_data={0: spd},
                                    itmp=[len(mnwell_data['spd'])],
                                    extension="mnw2",
                                    unitnumber=None,
                                    filenames=None,
                                    gwt=False, )
