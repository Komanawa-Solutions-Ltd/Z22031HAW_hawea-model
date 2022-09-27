"""
created matt_dumont 
on: 6/09/22
"""
import datetime
import pandas as pd
from model_tools.time_discretization import TimeDis

start = '2015-07-01'  # todo this is just a dummy value
end = '2020-06-27'  # todo this is just a dummy value
# todo I could consider doing an average year run and then use the starting heads to define from there... or look at the head data,
#  what time does the mean best represent out of the year across all high frequency heads?, better approach
base_time = pd.date_range(start, end, freq='W')
indates = [(base_time.min(), base_time.max() + datetime.timedelta(days=6))]
indates.extend(zip(base_time, base_time + datetime.timedelta(days=6)))

steady = [True] + [False for e in base_time]
nper = len(base_time) + 1  # one steady stated period and then the transient period

tdis = TimeDis(nper=nper,
               tsmult=1.2,
               steady=steady,
               dates=indates,
               nstp=1,
               tunit='day',
               check_dates_in_order=False
               )
tdis.perlen[0] = 1  # manually set first stress period to length of 1
pass
