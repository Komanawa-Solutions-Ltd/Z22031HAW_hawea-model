"""
created matt_dumont 
on: 7/09/22
"""
import flopy
import numpy as np

from targets_and_sensitive_sites.head_targets import get_all_hds_targets
from targets_and_sensitive_sites.riv_gain_loss_targets import get_riv_target_locs, get_hawea_gain_loss_targets
from optimisation.optimisation_period import tdis

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
    hds.loc[:, 'measured'] = all_hds[hds.nper, hds.k, hds.i, hds.j]

    # todo what to do with dry cells!

    # todo extract riv targets
    riv = get_hawea_gain_loss_targets()
    riv_locs = get_riv_target_locs()
    kstpkstper=None# todo pull from datasets
    riv_leak = flopy.utils.CellBudgetFile(cbc_path).get_data(kstpkper=kstpkstper, text='RIVER LEAKAGE', full3D=True)
    # todo pull out the expected

    # todo weighting (for all)

    raise NotImplementedError
