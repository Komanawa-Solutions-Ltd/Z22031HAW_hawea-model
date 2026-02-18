"""
created matt_dumont 
on: 23/08/22
"""
import datetime
import warnings
from collections.abc import Iterable
import numpy as np
from copy import deepcopy
import pandas as pd


class DummyTimeDis(object):
    def __init__(self, name, nper, tsmult, steady, dates=None, startdate=None, perlen=None, nstp=None, tunit='day',
                 check_dates_in_order=False):
        """
        A class to take in time series data and map it into the correct NPER system.
        Also holds other time discrisiation data
        periods are ultimately defined by dates and are inclusive of both start and end  [start:end]
        assumes minimum period is daily.
        :param name: a user readable name to identify this tdis object
        :param nper: Number of model stress periods
        :param tsmult: Time step multiplier, float or array of floats (nper)
        :param steady: Bool indicating whether or not stress period is steady state,
                       bool or array of bool (nper)
        either supply dates or perlen and startdate
        :param dates: None, or list length nper containting (startdate, enddate) for the stress period,
                      dates are inclusive e.g. (2022-01-01, 2022-01-03) contains the 1st, 2nd, and 3rd of Jan 2022
        :param perlen: None, or list of per lengths
        :param startdate: None, or datetime or compatible with pd.to_datetime or list of datetimes of len(nper)
        :param nstp: None or Number of time steps in each stress period, int or array of ints (nper)
                     if None then nstp will be calculated as daily data from dates/perlen
        :param tunit: time unit: one of ['sec','min','hr','day','yr']
        :param check_dates_in_order: bool if True check there are no duplicate dates or dates out of order.
        """
        self.name = name
        mftunits = {
            'sec': 1,
            'min': 2,
            'hr': 3,
            'day': 4,
            'yr': 5,
        }
        if tunit.lower() not in mftunits:
            raise ValueError(f'expected one of {mftunits.keys()}, got {tunit.lower()}')

        self.tunit = tunit.lower()
        self.mftunit = mftunits[self.tunit]
        if self.mftunit != 4:
            raise NotImplementedError('time units other than day have not been implemented')

        assert isinstance(nper, int)
        self.nper = nper
        self.pershape = (nper,)
        self.pers = tuple(range(nper))

        if isinstance(tsmult, Iterable):
            tsmult = np.atleast_1d(tsmult).astype(float)
            assert tsmult.shape == self.pershape
        else:
            assert isinstance(tsmult, float)
            tsmult = np.full(self.pershape, tsmult)

        if isinstance(steady, Iterable):
            steady = np.atleast_1d(steady)
            assert np.issubdtype(steady.dtype, bool)
            assert steady.shape == self.pershape
        else:
            assert isinstance(steady, bool)
            steady = np.full(self.pershape, steady)

        self.tsmult = tsmult
        self.steady = steady

        assert ((perlen is not None and startdate is not None and dates is None) or
                (dates is not None and perlen is None and startdate is None))

        if dates is None:
            # passed as perlen and start date
            assert len(perlen) == self.pershape[0]
            if isinstance(startdate, datetime.date) or isinstance(startdate, str):
                # continous model
                startdate = pd.to_datetime(startdate).date()
                dates = []
                base_date = startdate
                for p, pl in zip(self.pers, perlen):
                    end = (base_date + datetime.timedelta(days=pl - 1))
                    dates.append((base_date, end))
                    base_date = (end + datetime.timedelta(days=1))

            elif len(startdate) == self.pershape[0]:
                dates = []
                for sd, p, pl in zip(startdate, self.pers, perlen):
                    sd = pd.to_datetime(sd).date()
                    end = (sd + datetime.timedelta(days=pl - 1))
                    dates.append((sd, end))
        else:
            # passed as dates
            # check dates format
            assert len(dates) == self.pershape[0]
            dates = [pd.to_datetime(e) for e in dates]
            all_dates = []
            use_dates = []
            perlen = []
            for i, (s, e) in enumerate(dates):
                try:
                    s = pd.to_datetime(s).date()
                    e = pd.to_datetime(e).date()
                except Exception as val:
                    raise ValueError(f'problem with dates format: period:{i} data:{(s, e)} exception:{val}')
                p = (e - s).days + 1
                assert isinstance(p, int)
                perlen.append(p)
                use_dates.append((s, e))
                all_dates.extend(pd.date_range(s, e, freq='D').date)
            temp = [s for s, e in use_dates]
            if check_dates_in_order:
                assert temp == sorted(temp), 'start dates were not in order, check'
                expected_dates = pd.date_range(use_dates[0][0], use_dates[-1][1], freq='D').date
                assert set(expected_dates) == set(all_dates), (f'missing or unexpected dates: '
                                                               f'{set(expected_dates).symmetric_difference(set(all_dates))}')
                assert len(expected_dates) == len(all_dates), 'duplicate dates present'

        self.per_dates = tuple(dates)
        self.perlen = perlen
        temp = np.array(dates)

        self.per_middle_dates = tuple(temp[:, 0] + (temp[:, 1] - temp[:, 0]) / 2)
        self.date_limits = (temp.min(), temp.max())

        if nstp is None:
            nstp = perlen

        if isinstance(nstp, Iterable):
            nstp = np.atleast_1d(nstp).astype(int)
            assert nstp.shape == self.pershape
        else:
            assert isinstance(nstp, int)
            nstp = np.full(self.pershape, nstp)
        self.nstp = nstp

        if (nstp == 1).all():
            stepdates = {i: (v,) for i, v in enumerate(self.per_dates)}
            self.stp_eq_per = True
        else:
            # calculate step dates
            self.stp_eq_per = False
            stepdates = {}

            for p, (s, e), nstp in zip(self.pers, self.per_dates, self.nstp):
                total_days = (e - s).days + 1  # +1 as dates include start and end
                days_per_stp = int(total_days // nstp)
                sdates = []
                check_days = []
                use_start = deepcopy(s)
                for stp in range(nstp):
                    if stp == nstp - 1:  # last step takes up the slack
                        sdates.append((use_start, e))
                        check_days.append((e - use_start).days + 1)
                    else:
                        nend = use_start + datetime.timedelta(days=days_per_stp - 1)
                        sdates.append((use_start, nend))
                        check_days.append((nend - use_start).days + 1)
                        use_start = nend + datetime.timedelta(days=1)
                assert sum(check_days) == total_days
                stepdates[p] = sdates

        self.step_dates = stepdates
        self.middle_step_dates = {p: tuple([pd.to_datetime(e).mean() for e in v]) for p, v in stepdates.items()}

    def map_data_locations(self, loc_data: pd.DataFrame, transient_data_dict: dict,
                           datatype: np.dtype, func=np.nanmean,
                           apply_to_all=False, raise_on_missing_cols=True,
                           group_cells=False,
                           grouper=None,
                           manage_datatypes=True,
                           loc_duplicate_action='raise'):
        """
        map transient data and location data into modflow packages
        :param loc_data: location and instransient data, e.g. i, j, k, conductance
        :param transient_data_dict: {key: time varying data (pd.Dataframe/Series with datetime index)}
        :param datatype: flopy datatype
        :param func: function to use to aggregate the transient data or a dictionary of functions
        :param apply_to_all: bool if True, then assume transient data applies to all location, other wise link index of
                             loc_data to columns of transient_data
        :param raise_on_missing_cols: bool raise a value error if missing columns otherwise fill missing with 0
        :param group_cells: bool if true group all data in a single cell (e.g. well data), else leave distinct
        :param grouper: None, function, or dictionary to group data by (e.g. mean etc.)
        :param manage_datatypes: manage the datatypes to the flopy data types If False return dictionary of
                                 pd.Dataframe objects
        :param loc_duplicate_action:  one of: 'raise': raise a value error if any duplicates in the loc data index
                                               dictionary, keys: equal to transient_data_dict
                                                values:
                                                 'raise': raise a value error if any duplicates in the loc data index
                                                 'apportion': apply (transient_data/number) of duplicate locs to all locs
                                                 'map': apply the transient_data to all locs
        :return:
        """

        for transient_key, transient_data in transient_data_dict.items():
            assert isinstance(transient_data, pd.DataFrame) or isinstance(transient_data, pd.Series)
            if not apply_to_all:
                assert set(transient_data.keys()) == set(loc_data.index.values), (
                    f'missing from transient: {set(loc_data.index.values) - set(transient_data.keys())}\n'
                    f'missing from loc: {set(transient_data.keys()) - set(loc_data.index.values)} ')

        expect_cols = set(datatype.names)
        given_cols = set(transient_data_dict.keys()).union(loc_data.columns)
        assert expect_cols.issubset(given_cols), f'missing necessary columns/keys: {expect_cols - given_cols}'
        poss_loc_duplicate_action = ['raise', 'apportion', 'map']
        assert loc_duplicate_action in poss_loc_duplicate_action or isinstance(loc_duplicate_action, dict), (
            'loc_duplicate_action expected '
            f'to be in {poss_loc_duplicate_action} or a dictionary, got:{poss_loc_duplicate_action}')
        if isinstance(loc_duplicate_action, str):
            loc_duplicate_action = {k: loc_duplicate_action for k in transient_data_dict.keys()}
        if isinstance(loc_duplicate_action, dict):
            assert (set(loc_duplicate_action.keys())
                    == set(transient_data_dict.keys())), (f'loc_duplicate_action keys must be the same as '
                                                          f'transient_data_dict keys expected '
                                                          f'{transient_data_dict.keys()} '
                                                          f'got {loc_duplicate_action.keys()}')
            bad_keys = []
            for k, v in loc_duplicate_action.items():
                if v not in poss_loc_duplicate_action:
                    bad_keys.append(f'{k}: {v}')
            if len(bad_keys) > 0:
                pbk = '\n'.join(bad_keys)
                raise ValueError(f'loc_duplicate_action expected one of {poss_loc_duplicate_action}, '
                                 f'got {pbk}')

        # check for duplicate columns and indexes
        locs_duplicated = loc_data.index.duplicated(False).any()

        duplicate_transient = []
        for k, tdata in transient_data_dict.items():
            if isinstance(tdata, pd.Series):
                continue
            if tdata.columns.duplicated(False).any():
                duplicate_transient.append(k)
        if len(duplicate_transient) > 0:
            raise ValueError(f'duplicate values in transient data columns for keys: {duplicate_transient}')

        out = {}
        for p, (s, e) in enumerate(self.per_dates):
            temp_out = loc_data.copy(deep=True)

            for transient_key, transient_data in transient_data_dict.items():
                idxs = (transient_data.index >= s) & (transient_data.index <= e)
                if isinstance(func, dict):
                    use_func = func[transient_key]
                else:
                    use_func = func
                temp = transient_data.loc[idxs].agg(use_func, axis=0)
                if apply_to_all:
                    assert (not isinstance(temp, pd.DataFrame)
                            and not isinstance(temp, pd.Series)), ('should only have a single value if you are '
                                                                   f'applying it to all instances, got:{temp}')
                    temp_out.loc[:, transient_key] = temp
                else:
                    chck = deepcopy(temp)
                    check = True
                    if locs_duplicated:
                        if loc_duplicate_action[transient_key] == 'raise':
                            raise ValueError(f'duplicated locations: '
                                             f'{set(loc_data.index[loc_data.index.duplicated()])}')
                        elif loc_duplicate_action[transient_key] == 'apportion':
                            temp = temp * 1 / loc_data.index.value_counts()

                        elif loc_duplicate_action[transient_key] == 'map':
                            check = False  # doesn' makes sence to check
                            pass  # apply as is
                        else:
                            raise ValueError("shouldn't get here")

                    temp_out.loc[:, transient_key] = temp
                    if check:
                        assert np.isclose(temp_out.loc[:, transient_key].sum(), chck.sum())
            if group_cells:
                temp_out = temp_out.groupby(['i', 'j', 'k']).agg(grouper).reset_index()

            if manage_datatypes:
                out[p] = self._manage_period_dtypes(temp_out, dtype=datatype, p=p,
                                                    raise_on_missing_cols=raise_on_missing_cols)
            else:
                out[p] = temp_out

        assert isinstance(out, dict)
        return out

    def map_array_to_spd(self, dates: np.ndarray, array: np.ndarray, func=np.nanmean):
        """

        :param dates: array of python dates
        :param array: 3d array (time, rows, cols)
        :param func: function to use to aggregate time period
        :return:
        """
        assert array.ndim == 3
        assert array.shape[0] == dates.shape[0]
        assert dates.ndim == 1

        out = {}
        for p, (s, e) in enumerate(self.per_dates):
            idxs = (dates >= s) & (dates <= e)
            temp = func(array[idxs], axis=0)
            out[p] = temp

        return out

    def merge_spd(self, to_merge, dtype, group_cells=False, grouper=None):
        """
        merge stress period data
        :param to_merge: tuple of things to merge
        :param dtype: flopy datatype expected
        :param group_cells: bool if true group all data in a single cell (e.g. well data), else leave distinct
        :param grouper: None, function, or dictionary to group data by (e.g. mean etc.)
        :return:
        """
        for m in to_merge:
            assert isinstance(m, dict)
            assert set(m.keys()).issubset(self.pers)
        out = {}
        for k in self.pers:
            temp = []
            for m in to_merge:
                d = m.get(k)
                if d is not None:
                    temp.append(pd.DataFrame(d))
            temp = pd.concat(temp)
            if group_cells:
                temp = temp.groupby(['k', 'i', 'j']).agg(grouper).reset_index()

            out[k] = self._manage_period_dtypes(temp, dtype, k)
        return out

    def manage_dtypes(self, spd, dtype, raise_on_missing_cols=True, group_cells=False,
                      grouper=None, check_periods_match=True):
        """

        :param spd: stress period data (made by Tdis, but with unmanaged datatypes
        :param dtype: expected record array frame
        :param raise_on_missing:bool raise a value error if missing columns otherwise fill missing with 0
        :param group_cells: bool if true group all data in a single cell (e.g. well data), else leave distinct
        :param grouper: None, function, or dictionary to group data by (e.g. mean etc.)
        :param check_periods_match: bool if True set(list(spd.keys())) == set(self.pers) must be True.
        :return:
        """
        assert isinstance(spd, dict)
        if check_periods_match:
            assert set(list(spd.keys())) == set(self.pers)
        out = {}
        for p, val in spd.items():
            if group_cells:
                val = val.groupby(['i', 'j', 'k']).agg(grouper).reset_index()
            out[p] = self._manage_period_dtypes(val, dtype=dtype, p=p,
                                                raise_on_missing_cols=raise_on_missing_cols)
        return out

    def _manage_period_dtypes(self, data: pd.DataFrame, dtype: np.dtype, p: int, raise_on_missing_cols=True):
        """
        convert pandas dataframe into correct record array
        :param data: pandas dataframe
        :param p: integer stress period (for exception handling)
        :param dtype: expected record array frame
        :param raise_on_missing_cols: bool raise a value error if missing columns otherwise fill missing with 0
        :return:
        """
        data = data.copy(deep=True)
        if not set(dtype.names).issubset(data.columns):
            if raise_on_missing_cols:
                raise ValueError(f'missing expected columns in '
                                 f'stress period {p} : {set(dtype.names).difference(data.columns)}')
            else:
                missing_cols = set(dtype.names).difference(data.columns)
                warnings.warn(f'missing expected columns in stress '
                              f'period {p}: {missing_cols}, '
                              f'substituting default values')
                for k in missing_cols:
                    data.loc[:, 'k'] = 0

        out = data.loc[:, dtype.names]
        for i, n in enumerate(dtype.names):
            assert pd.notna(out[n]).all(), f'got non finite data for {n} in stress period {p}'
            out.loc[:, n] = out.loc[:, n].astype(dtype[i])
        return out.to_records(index=False)

    def add_nstp_nper_to_df(self, data: pd.DataFrame, datetime_col=None,
                            action_on_duplicates='raise'):
        """
        add a nstp nper columns to a dataframe copy
        :param data: dataframe with datetime index or column
        :param datetime_col: None (assume index) or column name for the datetime
        :param action_on_duplicates: what to do if the time occurs in multiple periods/steps
                                    one of: 'raise': raise a value error
                                             'duplicate': duplicate the data and append to the dataframe
                                             'first': keep the first period
                                             'last': keep the last period
                                             'warn_return_idx': for debugging purposes, issues a user warning and
                                                                returns (number_of_duplicates, possible_periods,
                                                                        possible_steps)
        :return: copy of data, see action_on_duplicates
        """
        assert action_on_duplicates in ['raise', 'duplicate', 'first', 'last', 'warn_return_idx']
        data = data.copy(deep=True)
        if datetime_col is None:
            datetime_data = pd.to_datetime(np.array(data.index))
        else:
            datetime_data = pd.to_datetime(np.array(data.loc[:, datetime_col]))
        possible_steps = []  # collect step values for each possible.  Then handle duplicates after the fact
        possible_periods = []  # collect step values for each possible.  Then handle duplicates after the fact

        for p, (per_s, per_e) in enumerate(self.per_dates):
            per_idx = ((datetime_data <= per_e) & (datetime_data >= per_s))
            if self.nstp[p] == 1:
                temp_nper = np.full((len(data), 1), np.nan)
                temp_nper[per_idx] = p
                temp_nstp = np.full((len(data), 1), np.nan)
                temp_nstp[per_idx] = 0
                possible_periods.append(temp_nper)
                possible_steps.append(temp_nstp)
            else:
                for i, (stp_s, stp_e) in enumerate(self.step_dates[p]):
                    temp_nper = np.full((len(data), 1), np.nan)
                    temp_nstp = np.full((len(data), 1), np.nan)
                    use_stp_idx = np.full(len(data), False)
                    use_stp_idx[per_idx] = ((datetime_data[per_idx] <= stp_e) & (datetime_data[per_idx] >= stp_s))
                    temp_nper[use_stp_idx] = p
                    temp_nstp[use_stp_idx] = i
                    possible_periods.append(temp_nper)
                    possible_steps.append(temp_nstp)

        possible_steps = np.concatenate(possible_steps, axis=1)
        possible_periods = np.concatenate(possible_periods, axis=1)

        duplicate_idx_per = np.isfinite(possible_periods).sum(axis=1)
        duplicate_idx_stp = np.isfinite(possible_steps).sum(axis=1)
        assert (duplicate_idx_stp == duplicate_idx_per).all()

        if action_on_duplicates != 'duplicate':
            if (duplicate_idx_per > 1).any():
                if action_on_duplicates == 'raise':
                    raise ValueError(
                        f'duplicate periods/steps for data: to debug set action_on_duplicates="warn_return_idx"')
                elif action_on_duplicates == 'warn_return_idx':
                    warnings.warn(f'duplicate periods/steps for data, returning debug info: '
                                  f'number_of_duplicates, possible_periods, possible_steps')
                    return duplicate_idx_stp, possible_periods, possible_steps

                elif action_on_duplicates == 'first':
                    nper_out = np.nanmin(possible_periods, axis=1)
                    temp = possible_steps.copy()
                    temp[~np.isclose(possible_periods, nper_out[:, np.newaxis])] = np.nan
                    nstp_out = np.nanmin(temp, axis=1)
                elif action_on_duplicates == 'last':
                    nper_out = np.nanmax(possible_periods, axis=1)
                    temp = possible_steps.copy()
                    temp[~np.isclose(possible_periods, nper_out[:, np.newaxis])] = np.nan
                    nstp_out = np.nanmax(temp, axis=1)
                else:
                    raise ValueError('should not get here')

            else:
                # add data if no duplicates, only 1 non-nan value in each axis0
                nper_out = np.nanmax(possible_periods, axis=1)
                nstp_out = np.nanmax(possible_steps, axis=1)

            # set values and return data
            nper_out[np.isnan(nper_out)] = -1
            nper_out = nper_out.astype(int)
            nstp_out[np.isnan(nstp_out)] = -1
            nstp_out = nstp_out.astype(int)

            data.loc[:, 'nper'] = nper_out
            data.loc[:, 'nstp'] = nstp_out
            return data
        else:
            warnings.warn('duplicating data has not been carefully checked, please validate')
            duplicates = []

            # data that do not have a step/period
            temp = data.loc[np.isnan(np.nanmax(possible_periods, axis=1))]
            temp.loc[:, 'nper'] = -1
            temp.loc[:, 'nstp'] = -1
            duplicates.append(temp)

            for i in range(possible_steps.shape[1]):
                use_stp = possible_steps[:, i]
                use_per = possible_periods[:, i]

                idx = np.isfinite(use_per)
                if not idx.any():
                    continue
                temp = data.loc[idx]

                per = np.unique(use_per[np.isfinite(use_per)])
                stp = np.unique(use_stp[np.isfinite(use_stp)])

                assert len(per) == 1 and len(stp) == 1
                temp.loc[:, 'nper'] = int(per[0])
                temp.loc[:, 'nstp'] = int(stp[0])
                duplicates.append(temp)
            return pd.concat(duplicates)

    def get_date(self, nper, nstp=None, date_type='mid'):
        """
        get date given nper, nstp
        :param nper: periods
        :param nstp: steps, optional
        :param date_type: mid: middle of section,
                          start: start of section,
                          end: end of section
        :return:
        """
        nper = np.atleast_1d(nper).astype(int)
        assert date_type in ['mid', 'start', 'end']
        if nstp is not None:
            nstp = np.atleast_1d(nstp)
            assert nstp.shape == nper.shape
            out = []
            if date_type == 'mid':
                f = 'mean'
            elif date_type == 'start':
                f = 'min'
            elif date_type == 'end':
                f = 'max'
            else:
                raise ValueError("shouldn't get here")

            for per, stp in zip(nper, nstp):
                out.append(pd.to_datetime(self.step_dates[per][stp]).__getattribute__(f)())
            out = np.array(out)
        else:
            if date_type == 'mid':
                out = np.array(self.per_middle_dates)[nper]
            elif date_type == 'start':
                out = np.array(self.per_dates)[:, 0][nper]
            elif date_type == 'end':
                out = np.array(self.per_dates)[:, 1][nper]
            else:
                raise ValueError("shouldn't get here")
        return out

    def make_spd_steady(self, spd: dict, steady_index=None, mismatch_keys='raise',
                        deepcopy_spd=True):
        """
        apply the steady state data of spd to all timesteps
        :param spd: stress period data, must have all of the periods expected by self.periods
        :param steady_index: None or list index value (e.g. 0, -1)
        :param mismatch_keys: one of raise, warn
        :param deepcopy_spd: bool if true set as a deepcopy of the spd (allowing later changes) if False then all dict keys
                         point to the same object.
        :return:
        """
        assert mismatch_keys in ['raise', 'warn']
        assert isinstance(spd, dict)
        equal = set(spd.keys()) == set(self.pers)
        subset = set(self.pers).issubset(spd.keys())
        if equal:
            pass
        elif not equal and mismatch_keys == 'raise':
            raise ValueError(f'spd and tdis keys do not match: \n  spd: {spd.keys()}\n  tdis:{self.pers}')
        elif mismatch_keys == 'warn' and subset:
            warnings.warn(f'spd and tdis keys do not match: but tdis periods are a subset of spd')
        else:
            raise ValueError(f'spd and tdis keys do not match and spd is not a subset of '
                             f'tdis: \n  spd: {spd.keys()}\n  tdis:{self.pers}')
        steady_pers = np.array(self.pers)[self.steady]
        if steady_index is None and len(steady_pers) > 1:
            raise ValueError('multiple steady state periods, please provide steady_index')
        elif steady_index is None:
            steady_index = 0

        if deepcopy_spd:
            outdata = {p: deepcopy(spd[steady_pers[steady_index]]) for p in self.pers}
        else:
            outdata = {p: spd[steady_pers[steady_index]] for p in self.pers}
        return outdata
