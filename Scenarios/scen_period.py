"""
created matt_dumont 
on: 24/11/22
"""
import datetime
import pandas as pd
from model_tools.time_discretization import TimeDis

# hill: '1976-09-23' to '2021-06-30'
# rch: '1950-01-01' to '2020-12-27' # todo could increase this?
# lake: 1975-12-30 to 2021-12-31

start = ''  # todo
end = ''  # todo
base_time = pd.date_range(start, end, freq='W')
indates = [(base_time.min(), base_time.max() + datetime.timedelta(days=6))]
indates.extend(zip(base_time, base_time + datetime.timedelta(days=6)))

steady = [True] + [False for e in base_time]
nper = len(base_time) + 1  # one steady stated period and then the transient period

tdis = TimeDis(
    name='scenario_period',
    nper=nper,
    tsmult=1.2,
    steady=steady,
    dates=indates,
    nstp=[1 if e else 7 for e in steady],
    tunit='day',
    check_dates_in_order=False
)
tdis.perlen[0] = 1  # manually set first stress period to length of 1
pass


def data_checks():  # todo look at variability to set start and end dates!,
    # todo look at correlation!!, discuss with Zeb
    from model_build.supporting_data_analysis.recharge_model import get_corrected_historical_era5_rch
    from model_build.supporting_data_analysis import get_lake_heads, get_hillside_flows
    import matplotlib.pyplot as plt
    import numpy as np
    lake = get_lake_heads(None, None, 'D')
    lake.name='lake'
    fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, sharex=True)

    ax1.set_title('lake ')
    for k, c in zip(['min', 'mean', 'max'], ['r', 'b', 'k']):
        temp = lake.resample('Y').agg(k)
        ax1.plot(temp.index, temp, color=c, label=k)
    lake = lake.resample('Y').mean()
    ax1.legend()
    ax2.set_title('hill')
    hill = get_hillside_flows(None, None, 'D')
    hill = hill.sum(axis=1).resample('Y').sum()
    hill.name='hill'
    ax2.plot(hill.index, hill)

    rch_dates, rch = get_corrected_historical_era5_rch(None, None)
    rch = pd.DataFrame(index=rch_dates, data={'rch': np.nanmean(rch, axis=(1, 2))})
    rch = rch.resample('Y').sum()
    rch.name='rch'
    ax3.set_title('rch')
    ax3.plot(rch.index, rch)

    all = pd.merge(pd.DataFrame(lake), pd.DataFrame(rch), how='outer', left_index=True, right_index=True)
    all = pd.merge(all, pd.DataFrame(hill), how='outer', left_index=True, right_index=True)
    fig, (ax1, ax2) = plt.subplots(ncols=2, sharex=True)
    ax1.scatter(all.rch, all.hill)
    ax1.set_ylabel('hill')
    ax1.set_xlabel('rch')
    ax2.scatter(all.rch, all.lake)
    ax2.set_ylabel('lake')
    ax2.set_xlabel('rch')
    plt.show()

    # todo look at daily, weekly, monthly, annually matched data for correllation




if __name__ == '__main__':
    data_checks()
