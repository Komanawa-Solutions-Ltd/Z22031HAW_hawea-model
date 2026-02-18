"""
created matt_dumont 
on: 2/11/23
"""


import datetime

try:
    from komanawa.modeltools import TimeDis
except ModuleNotFoundError:
    from komanawa.hawea.dummy_packages import TimeDis

import pandas as pd

from komanawa.hawea.Scenarios.run_flow_scenario import run_scenario
from komanawa.hawea.Scenarios.boundary_conditions import get_scen_ghb_data, get_scen_well_data, get_scen_str_data, get_scen_rch
from komanawa.hawea.model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from komanawa.hawea.Scenarios.scen_period import scen_tdis
from komanawa.hawea.hawea_base import unbacked_dir, processed_historical_data_dir
from komanawa.hawea.historical_investigation.get_historical_data import get_historical_data_locs, historical_well_names, select_resample
import numpy as np
import inspect



# hill: '1976-09-23' to '2021-06-30'
# rch: '1950-01-01' to '2020-12-27'
# lake: 1975-12-30 to 2021-12-31
# start 1980 or later to avoid significant problems with low lake levels (that's its own scenario)
start = '1975-12-30'
end = '2020-12-01'
base_time = pd.date_range(start, end, freq='W')
indates = [(base_time.min(), base_time.max() + datetime.timedelta(days=6))]
indates.extend(zip(base_time, base_time + datetime.timedelta(days=6)))

steady = [True] + [False for e in base_time]
nper = len(base_time) + 1  # one steady stated period and then the transient period

scen_tdis = TimeDis(
    name='hist_lows',
    nper=nper,
    tsmult=1.2,
    steady=steady,
    dates=indates,
    nstp=[1 if e else 7 for e in steady],
    tunit='day',
    check_dates_in_order=False
)
scen_tdis.perlen[0] = 1  # manually set first stress period to length of 1
pass
def print_myself():
    print(inspect.stack()[1][3])

base_run_dir = unbacked_dir.joinpath('historical_investigation', 'runs')
base_run_dir.mkdir(exist_ok=True, parents=True)
base_outdir = unbacked_dir.joinpath('historical_investigation', 'results')
base_outdir.mkdir(exist_ok=True, parents=True)

def long_naturalised():
    print_myself()
    model_name = 'long_nat'
    model_ws = base_run_dir.joinpath(model_name)
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    str_vals = get_scen_str_data(scen_tdis, riv_params, big_static=False, small_static=False, fill_na=True)
    nat_rch = get_scen_rch(scen_tdis, rch_param, dryland=True)
    lake = get_scen_ghb_data(scen_tdis, recalc=True)
    wel_data = get_scen_well_data('no_pump', scen_tdis, hill_param, race_param, False,
                                  fillna=True)
    run_scenario(model_name=model_name, model_ws=model_ws,
                 tdis=scen_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=nat_rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(model_name),
                 build_run_model=run_modflow, process_results=True)



def get_hist_nat_data(site, recalc=False, freq='D'):
    savepath = processed_historical_data_dir.joinpath('nat_historical_data.hdf')
    t = None
    assert site in historical_well_names
    key = f'all_modelled_period_hds'
    if not recalc and savepath.exists():
        try:
            t = pd.read_hdf(savepath, key=key)[site]
            assert isinstance(t, pd.Series)
        except KeyError:
            pass
    if t is None:

        import flopy
        hds_path = base_run_dir.joinpath('long_nat/long_nat.hds')
        all_hds = flopy.utils.HeadFile(hds_path).get_alldata()
        all_hds[all_hds > 1e20] = np.nan
        assert all_hds.shape[0] == scen_tdis.nper
        head_locs = get_historical_data_locs()

        out_hds = pd.DataFrame(index=scen_tdis.per_middle_dates, columns=historical_well_names)
        for site in historical_well_names:
            k = head_locs.loc[site, 'k']
            i = head_locs.loc[site, 'i']
            j = head_locs.loc[site, 'j']
            out_hds.loc[:, site] = all_hds[:, k, i, j]

        out_hds.to_hdf(savepath, key=key, complib='zlib', complevel=9)
        t = out_hds[site]
    t = select_resample(t, t.index.min(), t.index.max(), frequency=freq, interpolate=True)
    return t


if __name__ == '__main__':
    run_modflow = False
    if run_modflow:
        pass
    long_naturalised()
    t = get_hist_nat_data(historical_well_names[0])
    pass