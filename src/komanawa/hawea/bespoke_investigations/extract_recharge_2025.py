"""

This script facilitates extracting recharge data for a request from ORC on 11-11-2025.

created matt_dumont 
on: 11/12/25
"""
import flopy.utils
import numpy as np
import pandas as pd
from komanawa.hawea.Scenarios.allocation_zones import get_allo_zones
from komanawa.hawea.model_build.project_model_tools import smt
from komanawa.hawea.model_build.supporting_data_analysis.recharge_model import get_corrected_historical_era5_rch
from komanawa.hawea.model_build.supporting_data_analysis import get_hillside_catchment_locs, get_hillside_flows, get_race_locs, \
    get_race_well_losses, get_river_loc_data, get_lake_hawea_loc
from komanawa.hawea.model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from komanawa.hawea.optimisation.final_opt_models.compress_uncompress_model import uncompress_model
from komanawa.hawea.hawea_base import proj_root, unbacked_dir


def get_aq_bounds(recalc=False):
    """
    get active and extended area bounds for the Hawea Basin C-series aquifer

    Active is as per the shapefile

    extended includes any river and lake cells to support extracting fluxes from the model

    :param recalc:
    :return: active_area, extended_area : np.ndarray(bool)
    """
    rawpath = proj_root.joinpath('bespoke_investigations/data/Hawea_Basin_Cseries_aquifer.shp')
    savepath = proj_root.joinpath('bespoke_investigations/data/Hawea_Basin_Cseries_aquifer_bounds.npz')
    if savepath.exists() and not recalc:
        with np.load(savepath) as data:
            active_area = data['active_area']
            extended_area = data['extended_area']
        return active_area, extended_area

    active_area = np.isfinite(smt.io.shape_file_to_model_array(rawpath, 'Shape_Area', alltouched=True))
    extended_area = active_area.copy()
    riv_locs = get_river_loc_data()
    x, y = smt.convert_matrix_to_coords(riv_locs['i'], riv_locs['j'])
    ylimit = 5.04e6
    riv_locs = riv_locs[y > ylimit]  # remove a bit of the river to the south that is not in the aquifer
    lake_locs = get_lake_hawea_loc()
    extended_area[riv_locs['i'], riv_locs['j']] = True
    extended_area[lake_locs['i'], lake_locs['j']] = True
    smt.plot.plt_matrix(extended_area, base_map=True, title='extended area', color_bar=False)
    smt.plot.plt_matrix(active_area, base_map=True, title='active area', color_bar=False)
    smt.plot.show()
    np.savez_compressed(savepath, active_area=active_area, extended_area=extended_area)
    return active_area, extended_area


def _extract_mean_lsr():
    dates, raw_rch = get_corrected_historical_era5_rch('1950', '2021', frequency='YE')
    mean_rch = raw_rch.mean(axis=0)  # mean over time

    # pull area
    bounds, _ = get_aq_bounds()
    mean_rch[~bounds] = np.nan

    # convert from mm/day to m3/year
    mean_rch = mean_rch / 1000 * smt.grid_space ** 2 * 365.25

    # add parameter
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    mean_rch = np.nansum(mean_rch * rch_param['all'])

    return mean_rch


def _extract_hill_losses():
    locs = get_hillside_catchment_locs()
    flows = get_hillside_flows('2012-01-01', '2021-06-30')
    keep_flows = locs[locs.param == 'main']
    flows = flows[keep_flows.index.unique()]
    hill_losses = flows.mean() * 365.25  # m3/year
    # add parameter
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    hill_losses = (hill_losses * hill_param['main']).sum()
    return hill_losses


def _extract_race_losses():
    race_locs = get_race_locs()
    assert not race_locs.duplicated(['i', 'j']).any()
    race_losses = get_race_well_losses('2014-09-11', '2020-07-01', frequency='YE')
    race_losses = race_losses.mean() * 365.25  # m3/year
    race_losses = race_losses * len(race_locs)
    # add parameter
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()
    race_losses = race_losses * race_param['all']
    return race_losses


def _get_cbc_path():
    model_dir = unbacked_dir.joinpath('uncompressed_model')
    model_dir.mkdir(exist_ok=True)
    cbc_path = model_dir.joinpath('final_opt_model.cbc')
    if not cbc_path.exists():
        uncompress_model(proj_root.joinpath('optimisation/final_opt_models/3d_v1d'), model_dir)
    return cbc_path


def _extract_lake_from_model():
    cbc_path = _get_cbc_path()
    cbc = flopy.utils.CellBudgetFile(cbc_path)
    data = np.array(cbc.get_data(text='HEAD DEP BOUNDS', full3D=True))
    data = np.mean(data, axis=0)
    data = np.sum(data)  # m3/day
    data = data * 365.25  # m3/year
    return data


def _extract_river_to_model():
    cbc_path = _get_cbc_path()
    cbc = flopy.utils.CellBudgetFile(cbc_path)
    data = np.array(cbc.get_data(text='STREAM LEAKAGE', full3D=True))
    data[data < 0] = 0
    data = np.mean(data, axis=0)
    data = np.sum(data)  # m3/day
    data = data * 365.25  # m3/year
    return data


def _extract_river_from_model():
    cbc_path = _get_cbc_path()
    cbc = flopy.utils.CellBudgetFile(cbc_path)
    data = np.array(cbc.get_data(text='STREAM LEAKAGE', full3D=True))
    data[data > 0] = 0
    data = np.mean(data, axis=0)
    data = np.sum(data)  # m3/day
    data = data * 365.25  # m3/year
    return data


def _extract_wel_from_model():
    _, extended_area = get_aq_bounds()
    cbc_path = _get_cbc_path()
    cbc = flopy.utils.CellBudgetFile(cbc_path)
    data = np.array(cbc.get_data(text='WELLS', full3D=True))
    data[:, :, ~extended_area] = 0
    data = np.mean(data, axis=0)
    data[data > 0] = 0  # only pumped flows
    data = np.sum(data)  # m3/day
    data = data * 365.25  # m3/year
    return data


def extract_recharge_2025():
    outdata = pd.Series(dtype=float)
    outdata['mean_lsr'] = t1 = _extract_mean_lsr()
    outdata['hill_losses'] = t2 = _extract_hill_losses()
    outdata['race_losses'] = t3 = _extract_race_losses()
    outdata['lake_hawea'] = t4 = _extract_lake_from_model()
    outdata['river_to_aquifer'] = t5 = _extract_river_to_model()
    outdata['river_from_aquifer'] = f1 = _extract_river_from_model()
    outdata['well_losses'] = f2 = _extract_wel_from_model()
    outdata['total_recharge'] = t1 + t2 + t3 + t4 + t5
    outdata['total_discharge'] = f1 + f2
    outdata['delta'] = outdata['total_recharge'] + outdata['total_discharge']
    outdata['percent_difference'] = outdata['delta'] / outdata['total_recharge'] * 100
    outpath = proj_root.joinpath('bespoke_investigations/data/recharge_2025.csv')
    with outpath.open('w') as fout:
        fout.write(
            '# Mean recharge and discharge components extracted from the model (version 3d_v1d) for a ORC bespoke request on 11-11-2025\n')
        fout.write('# All values in m3/year\n')
        fout.write('# Positive values are inflows to the aquifer, negative values are outflows from the aquifer\n')
        fout.write(
            '# There is a small imbalance (delta) as some portions of the model are not included in the area of interest (see Hawea_Basin_Cseries_aquifer.shp)'
            'and because these are the sum of the mean fluxes\n')
        fout.write('# mean_lsr: Mean long-term surface recharge (1950 - 2021)\n')
        fout.write('# all other components are for the modelled period (2012 - 2021)\n')
        fout.write('# the recharge components are:\n')
        fout.write('# hill_losses: losses from hillside catchments\n')
        fout.write('# race_losses: losses from the races\n')
        fout.write('# lake_hawea: leakage from Lake Hawea to the aquifer\n')
        fout.write('# river_to_aquifer: leakage from rivers to the aquifer\n')
        fout.write('# the discharge components are:\n')
        fout.write('# river_from_aquifer: leakage from the aquifer to rivers\n')
        fout.write('# well_losses: losses from wells in the aquifer (this excludes the "near river bores"\n')
    outdata.to_csv(proj_root.joinpath('bespoke_investigations/data/recharge_2025.csv'), mode='a')

def extract_zonal_inflows_2025():

    zones, mapper = get_allo_zones()
    pass
    # setup the input arrays
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    # lsr
    dates, raw_rch = get_corrected_historical_era5_rch('1950', '2021', frequency='YE')
    mean_rch = raw_rch.mean(axis=0)  # mean over time
    mean_rch = mean_rch / 1000 * smt.grid_space ** 2 * 365.25
    mean_rch = mean_rch * rch_param['all']

    # hill losses
    locs = get_hillside_catchment_locs()
    flows = get_hillside_flows('2012-01-01', '2021-06-30')
    hill_losses = flows.mean() * 365.25  # m3/year
    locs['flux'] = np.nan
    for loc in locs.index.unique():
        loc_flux = hill_losses[loc] / len(locs.loc[loc].index) * hill_param[locs.loc[loc, 'param'].iloc[0]]
        locs.loc[loc, 'flux'] = loc_flux
    hill_loss_array = smt.get_model_zeros()
    hill_loss_array[locs['i'], locs['j']] = locs['flux']


    # race losses
    race_locs = get_race_locs()
    assert not race_locs.duplicated(['i', 'j']).any()
    race_losses = get_race_well_losses('2014-09-11', '2020-07-01', frequency='YE')
    race_losses = race_losses.mean() * 365.25  # m3/year
    race_losses = race_losses * race_param['all']
    race_locs['flux'] = race_losses
    race_locs_array = smt.get_model_zeros()
    race_locs_array[race_locs['i'], race_locs['j']] = race_locs['flux']

    outdata = pd.DataFrame(index=['mean_lsr', 'hill_losses', 'race_losses'], columns=mapper.values())
    for k,v in mapper.items():
        zone_mask = zones == k
        outdata.loc['mean_lsr', v] = np.nansum(mean_rch[zone_mask])
        outdata.loc['hill_losses', v] = np.nansum(hill_loss_array[zone_mask])
        outdata.loc['race_losses', v] = np.nansum(race_locs_array[zone_mask])
    outdata.loc['total_recharge'] = outdata.sum(axis=0)
    outpath = proj_root.joinpath('bespoke_investigations/data/zonal_inflows_2025.csv')
    with outpath.open('w') as fout:
        fout.write('Zonal inflows to the new allocation zones for the ORC bespoke request on 11-11-2025\n')
        fout.write('# All values in m3/year\n')
    outdata.to_csv(outpath, mode='a')

    pass

def convert_indicators_to_tif():
    base_paths = [
        'all_hill_indicator.npz',
        'lake_con_indicator.npz',
        'all_str.npz',
        'race_con_indicator.npz',
        'rch_indicator.npz',
    ]
    basedir = proj_root.joinpath('Scenarios/mt3d_indicator_scenarios/ucn_data')
    for base_path in base_paths:
        inpath = basedir.joinpath(base_path)
        data = np.load(inpath)['id_conc']
        for l in range(data.shape[0]):
            tdata = data[l]
            outpath = unbacked_dir.joinpath(f'{inpath.stem}_l{l}.tif')
            smt.io.array_to_raster(outpath, tdata)

if __name__ == '__main__':
    extract_recharge_2025()
    extract_zonal_inflows_2025()
    convert_indicators_to_tif()
