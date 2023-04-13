"""
created matt_dumont 
on: 6/09/22
"""
import datetime
import pandas as pd

try:
    from model_tools.time_discretization import TimeDis
except ModuleNotFoundError:
    from dummy_packages import TimeDis

start = '2015-07-18'  # Keynote set based on the minimisation of the RSME to the mean values
end = '2020-06-27'  # Keynote this is the end of the available data
base_time = pd.date_range(start, end, freq='W')
indates = [(base_time.min(), base_time.max() + datetime.timedelta(days=6))]
indates.extend(zip(base_time, base_time + datetime.timedelta(days=6)))

steady = [True] + [False for e in base_time]
nper = len(base_time) + 1  # one steady stated period and then the transient period

tdis = TimeDis(
    name='optimisation_period',
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
