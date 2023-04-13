"""
created matt_dumont 
on: 19/07/22
"""
import pickle
import tempfile
from pathlib import Path

import project_base
from model_build.project_model_tools import smt as hawea_smt
from project_base import campbells_dir
from Scenarios.wetland_setback_campbells.project_model_tools import smt, tdis, ss_dates, trans_dates
from Scenarios.scen_period import scen_tdis
from Scenarios.supporting_data_analysis.pumping_data import get_pump_curve
from Scenarios.boundary_conditions import get_scen_rch, _get_str_stage_flow
from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from model_build.supporting_data_analysis import get_river_loc_data
import pandas as pd
import geopandas as gpd
import flopy
import numpy as np



def get_wetland_loc(azimuth, return_just_kij=False):
    x = 1303547.68
    y = 5043411.37
    i, j = smt.convert_coords_to_matix(x, y)
    data = pd.DataFrame(data=dict(
        x=[x],
        y=[y],
        k=[0],
        i=[i],
        j=[j],
        azimuth=[azimuth],

    ))

    if return_just_kij:
        return 0, i, j
    return data


def get_strt_hds(recalc=False):
    save_path = campbells_dir.joinpath('processed_input_data', 'constant_hds.npy')
    if save_path.exists() and not recalc:
        with save_path.open('rb') as f:
            out = np.load(f)
        return out

    with tempfile.TemporaryDirectory() as tdir:
        tdir = Path(tdir)
        from optimisation.final_opt_models.compress_uncompress_model import uncompress_model
        uncompress_model(project_base.proj_root.joinpath('optimisation/final_opt_models/3d_v1d'),
                         tdir.joinpath('opt_model'))
        with flopy.utils.HeadFile(tdir.joinpath('opt_model', 'final_opt_model.hds')) as hds:
            ss_hds = hds.get_alldata()[0, 0]
        hawea_smt.io.array_to_raster(tdir.joinpath('temp.tif'), ss_hds)
        ss_hds = smt.io.raster_to_array(tdir.joinpath('temp.tif'), 'mean')

    np.save(save_path, ss_hds)
    return ss_hds


def get_wells(locs, max_pumping_rate):
    i, j = smt.convert_coords_to_matix(locs.new_x, locs.new_y)
    locs.loc[:, 'i'] = i
    locs.loc[:, 'j'] = j
    locs.loc[:, 'k'] = 0
    pump_curve = get_pump_curve(scen_tdis).flux * max_pumping_rate * -1
    well_spd = tdis.map_data_locations(locs,
                                       transient_data_dict={'flux': pump_curve},
                                       datatype=flopy.modflow.ModflowWel.get_default_dtype(),
                                       apply_to_all=True
                                       )
    return well_spd, locs[['k', 'i', 'j']]


def get_rch(recalc=False):
    save_path = campbells_dir.joinpath('processed_input_data', 'rch_data.p')
    if save_path.exists() and not recalc:
        with save_path.open('rb') as f:
            out = pickle.load(f)
        return out
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    scen_rch = get_scen_rch(scen_tdis, rch_param)
    use_rch = scen_rch[0]  # steady state rch
    with tempfile.TemporaryDirectory() as tdir:
        tdir = Path(tdir)
        hawea_smt.io.array_to_raster(tdir.joinpath('temp.tif'), use_rch)
        rch = smt.io.raster_to_array(tdir.joinpath('temp.tif'), 'mean')
    out_spd = {i: rch for i in tdis.pers}
    with save_path.open('wb') as f:
        pickle.dump(out_spd, f)
    return out_spd


def get_riv(conductance, recalc=False):
    save_path = campbells_dir.joinpath('processed_input_data', 'riv_data.p')
    if save_path.exists() and not recalc:
        with save_path.open('rb') as f:
            riv_spd = pickle.load(f)
    else:
        base_locs = get_river_loc_data()
        base_locs = base_locs.loc[np.in1d(base_locs.rname, ['hawea', 'clutha'])]
        base_locs = base_locs.reset_index().reset_index()
        riv_loc_array = hawea_smt.io.df_to_array(base_locs, 'level_0', _3d=False)
        with tempfile.TemporaryDirectory() as tdir:
            tdir = Path(tdir)
            hawea_smt.io.array_to_raster(tdir.joinpath('temp.tif'), riv_loc_array)
            use_riv_loc_array = smt.io.raster_to_array(tdir.joinpath('temp.tif'), 'mean').round()

        riv_locs = smt.io.array_to_df(use_riv_loc_array, 'id')
        riv_locs.loc[:, 'id'] = riv_locs.loc[:, 'id'].astype(int)
        riv_locs = riv_locs.set_index('id')
        riv_locs.loc[:, 'k'] = 0
        riv_locs.loc[:, 'cond'] = 1  # filler value
        riv_locs.loc[:, 'rbot'] = base_locs.loc[:, 'rbot']

        # get stage
        riv_flow, riv_stage = _get_str_stage_flow(*scen_tdis.date_limits, frequency='W')
        riv_stage = riv_stage.rename(columns={v: k for k, v in base_locs['index'].to_dict().items()})

        riv_stage = riv_stage.loc[:, riv_locs.index.unique()]
        riv_stage = riv_stage.loc[(riv_stage.index <= tdis.date_limits[1])
                                  & (riv_stage.index >= tdis.date_limits[0])]
        riv_spd = tdis.map_data_locations(riv_locs,
                                          transient_data_dict={'stage': riv_stage},
                                          datatype=flopy.modflow.ModflowRiv.get_default_dtype(),
                                          loc_duplicate_action='map'
                                          )
        with save_path.open('wb') as f:
            pickle.dump(riv_spd, f)

    # manage conuctange
    for k, v in riv_spd.items():
        v['cond'] = conductance

    return riv_spd


def data_checks():
    from model_tools.model_plotting import plot_spd # keynote private repo
    rch = get_rch()
    plot_spd(rch, smt, tdis, is_array=True, show=False, func=np.nanmean, title='rch')
    smt.plot.plt_matrix(rch[0], title='rch', no_flow_layer=0, base_map=True)

    riv = get_riv(500)
    locs = smt.io.get_new_points_from_points_azimuth(get_wetland_loc(30), distance=700, delta_azimuth=0)
    well, wloc = get_wells(locs, 500)
    fig, ax = smt.plot.plt_basemap(no_flow_layer=0)
    for pkg, k, c in zip(['riv', 'well'], ['stage', 'flux'], ['b', 'r']):
        print(pkg)
        plot_spd(eval(pkg), smt, tdis, key=k, show=False, func=np.nanmean, title=pkg)
        ax.set_title(pkg)
        ax.scatter(*smt.convert_matrix_to_coords(eval(pkg)[0]['i'], eval(pkg)[0]['j']), color=c, label=pkg)

    ax.scatter(*smt.convert_matrix_to_coords(*get_wetland_loc(30, return_just_kij=True)[1:]), color='purple',
               label='wetland')
    ax.legend()
    smt.plot.show()


if __name__ == '__main__':
    t = get_strt_hds()
    smt.plot.plt_matrix(t, title='strt', base_map=True, no_flow_layer=0)
    smt.plot.show()
    data_checks()
    pass
