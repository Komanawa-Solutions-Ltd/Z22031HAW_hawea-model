"""
created matt_dumont 
on: 7/09/22
"""
import flopy
import numpy as np
import pandas as pd

from targets_and_sensitive_sites.head_targets import get_all_hds_targets
from targets_and_sensitive_sites.riv_gain_loss_targets import get_riv_target_locs, get_hawea_gain_loss_nper
from optimisation.optimisation_period import tdis
from model_build.supporting_data_analysis import get_river_loc_data
from model_build.project_model_tools import get_bottom

# todo!!!
# thoughts target groups
"""
1. high frequency head targets  (high weight)
2. low frequency head targets   (high weight)
3. piezo data (mod weight)
4. single targets (weight by quality code)
5. river targets (high weight)

consider applying a temporal weighting to high frequency targets (later has better pumping data)
how to manage dry cells... weight misfit higher???

"""


# todo look into PYEMU for objective function calculation support
# todo make this fast to calculate!

def calc_obj(version, hds_path, cbc_path):
    if version == 1:
        out = _calc_obj_v1(hds_path=hds_path, cbc_path=cbc_path)
    else:
        raise NotImplementedError

    # todo
    raise NotImplementedError


def _calc_obj_v1(hds_path, cbc_path):
    all_hds = flopy.utils.HeadFile(hds_path).get_alldata()
    all_hds[all_hds > 1e20] = np.nan
    hds = get_all_hds_targets(tdis)
    # keynote this assumes 1 step per stress period
    hds.loc[:, 'modelled'] = all_hds[hds.nper, hds.k, hds.i, hds.j]
    bots = get_bottom()

    #  keynote set dry observations to bottom of cell -5m
    hds.loc[hds.modelled < -666, 'modelled'] = bots[hds.i, hds.j] - 5

    # dry cells at non-target data points
    dry_hds = all_hds < -666

    # extract riv targets
    riv = get_hawea_gain_loss_nper(tdis).reset_index()
    riv_locs = get_riv_target_locs()
    # keynote change if multiple steps
    pers = riv.nper.unique()
    all_riv = np.array(flopy.utils.CellBudgetFile(cbc_path).get_data(text='RIVER LEAKAGE', full3D=True))[:, 0]

    for per in pers:
        # todo in future submit pull request to get multiple Kstpkstper from cbc
        riv_leak = flopy.utils.CellBudgetFile(cbc_path).get_data(kstpkper=(0, per), text='RIVER LEAKAGE', full3D=True)
        all_riv[per] = np.array(riv_leak[0])[0]
    for i, target_key, nper in riv.loc[:, ['target_key', 'nper']].itertuples(True, None):
        riv.loc[i, 'modelled'] = all_riv[nper][riv_locs[target_key]].sum()

    # observations for clutha and hawea losses to see range
    all_riv_loc = get_river_loc_data()
    param_zones = all_riv_loc.param.unique()
    all_riv_obs = pd.DataFrame(index=tdis.pers, columns=param_zones)
    all_riv_obs.index.name = 'nper'
    for p in param_zones:
        temp = all_riv_loc.loc[all_riv_loc.param == p]
        all_riv_obs.loc[:, p] = all_riv[:, temp.i, temp.j].sum(axis=1)

    # todo pull out budget for mapping, here or in other script??

    # todo weighting (for all)
    groups = [f'hds_{e}' for e in hds.group.unique()]
    groups.append('river')
    groups.append('dry_cells')
    # todo https://pyemu.readthedocs.io/en/develop/pyemu.html#pyemu.ObservationEnsemble  # adjust_weights(obs_dict=None, obsgrp_dict=None)

    raise NotImplementedError  # todo what to return
    return obj, all_riv_obs, riv, hds, dry_hds.sum(axis=(0, 1))


if __name__ == '__main__':
    _calc_obj_v1('/home/matt_dumont/Downloads/test_model/test.hds', '/home/matt_dumont/Downloads/test_model/test.cbc')
