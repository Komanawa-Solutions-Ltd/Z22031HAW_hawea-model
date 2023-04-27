"""
created matt_dumont 
on: 28/04/23
"""
import flopy
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt


def make_ss_waterbudget(cbc_file, kstpkper=(0, 0)):
    """
    Make a water budget for a steady state model
    :param cbc_file:
    :param kstpkper:
    :return:
    """
    outdata = pd.DataFrame()
    kstpkper_name = 'kstpkper_{}_{}'.format(*kstpkper)
    from model_build.get_boundary_condition_data import get_river_loc_data, get_hillside_catchment_locs, \
        get_pumping_locs, get_race_locs
    with flopy.utils.CellBudgetFile(cbc_file) as cbc:
        lake = cbc.get_data(text='HEAD DEP BOUNDS', kstpkper=kstpkper, full3D=True)[0]
        outdata.loc[kstpkper_name, 'Lake'] = np.nansum(lake)

        rch = cbc.get_data(text='RECHARGE', kstpkper=kstpkper, full3D=True)[0]
        outdata.loc[kstpkper_name, 'Recharge'] = np.nansum(rch)

        riv = cbc.get_data(text='STREAM LEAKAGE', kstpkper=kstpkper, full3D=True)[0]
        riv_locs = get_river_loc_data()
        for p in riv_locs.param.unique():
            temp = riv_locs.loc[riv_locs.param == p]
            if 'john' in p:
                p_name = p.replace('john', 'John')
            else:
                p_name = p.replace('h', 'Hawea').replace('c', 'Clutha').replace('gview', 'Grandview').replace('john',
                                                                                                          'John')
            outdata.loc[kstpkper_name, f'{p_name}_flux'] = np.nansum(riv[0, temp.i, temp.j])
        outdata.loc[kstpkper_name, 'all River'] = np.nansum(riv)
        wel = cbc.get_data(text='WELLS', kstpkper=kstpkper, full3D=True)[0]
        wel_locs = get_pumping_locs()
        race_locs = get_race_locs()
        hill_locs = get_hillside_catchment_locs()
        for name, df in zip(['Race', 'Abstraction'], [race_locs, wel_locs]):
            outdata.loc[kstpkper_name, f'{name}_flux'] = np.nansum(wel[df.k, df.i, df.j])

        for g in hill_locs.group.unique():
            temp = hill_locs.loc[hill_locs.group == g]
            outdata.loc[kstpkper_name, f'hill_{g}_flux'] = np.nansum(wel[temp.k, temp.i, temp.j])
        outdata.loc[kstpkper_name, 'all well'] = np.nansum(wel)
    outdata = outdata.iloc[0]
    outdata.loc['discrepancy'] = outdata.loc[['Lake', 'Recharge', 'all River', 'all well']].sum()
    return


def plot_ss_waterbudget(cbc_file, outdir, kstpkper=(0, 0)):
    bud = make_ss_waterbudget(cbc_file, kstpkper=kstpkper)

    raise NotImplementedError


if __name__ == '__main__':
    cbc_file = '/home/matt_dumont/unbacked/hawea/3d_v1d/init_3d_v1d/Optimisations/Final_opt_model/final_opt_model.cbc'
    make_ss_waterbudget(cbc_file)
