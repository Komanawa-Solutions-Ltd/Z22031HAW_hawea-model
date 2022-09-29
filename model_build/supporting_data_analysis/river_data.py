"""
created matt_dumont 
on: 2/08/22
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from model_build.utils import select_resample, get_colors
from model_build.project_model_tools import smt, _river_locs
from project_base import base_model_build_data_dir, processed_model_build_data_dir

default_recalc = False
hawea_shp_path = base_model_build_data_dir.joinpath('hawea_river.shp')
clutha_shp_path = base_model_build_data_dir.joinpath('lower_clutha.shp')
gageing_path = base_model_build_data_dir.joinpath('Hawea River - ORC Gaugings for Gain & Loss Estimation.xlsx')

riv_loc_data_path = processed_model_build_data_dir.joinpath('river_loc_data.csv')
riv_stage_data_path = processed_model_build_data_dir.joinpath('river_stage_data.csv')


def get_river_loc_data(recalc=default_recalc):
    if not recalc and riv_loc_data_path.exists():
        outdata = pd.read_csv(riv_loc_data_path, index_col=0)
        dtypes = {
            'i': 'int64',
            'j': 'int64',
            'k': 'int64',
            'dist': 'float64',
            'rbot': 'float64',
            'rname': 'str',
        }

        for k, v in dtypes.items():
            outdata.loc[:, k] = outdata.loc[:, k].astype(v)
        return outdata
    outdata = _river_locs()
    outdata = get_river_gage_locs(outdata)
    outdata = get_stage_locs(outdata)
    outdata.loc[:, 'seg_name'] = [f'{r}_{int(d):05d}' for r, d
                                  in outdata.loc[:, ['rname', 'dist']].itertuples(index=False, name=None)]
    outdata.set_index('seg_name', inplace=True)
    outdata.loc[outdata.rname == 'hawea', 'param'] = 'h3'
    outdata.loc[outdata.rname == 'clutha', 'param'] = 'c1'
    for g in range(1, 4):
        outdata.loc[outdata.gage == g, 'param'] = f'h{g}'
    outdata.loc[:, 'k'] = 0
    outdata.to_csv(riv_loc_data_path)
    return outdata


def get_river_gage_locs(riv_data):
    loc_data = pd.read_excel(gageing_path, 'locs').set_index('site')
    temp = riv_data.copy(deep=True)
    temp = smt.io.add_mxmy_to_df(temp)

    loc_data.loc['Below Control', 'dist'] = 0
    loc_data.loc['Below Control', 'rname'] = 'hawea'
    all_sites = ['Below Control', 'Camp Hill', 'Below Camphill', 'Campground']
    for s in ['Camp Hill', 'Below Camphill', 'Campground']:
        t = ((temp.mx - loc_data.loc[s, 'x']) ** 2 + (temp.my - loc_data.loc[s, 'y']) ** 2)
        loc_data.loc[s, 'dist'] = temp.loc[t.argmin(), 'dist']
        loc_data.loc[s, 'rname'] = temp.loc[t.argmin(), 'rname']
    for i, (s1, s2) in enumerate(zip(all_sites[0:-1], all_sites[1:])):
        assert (loc_data.loc[[s1, s2], 'rname'] == 'hawea').all()
        dist1, dist2 = loc_data.loc[[s1, s2], 'dist']
        idx = (riv_data.rname == 'hawea') & (riv_data.dist >= dist1) & (riv_data.dist <= dist2)
        riv_data.loc[idx, 'gage'] = i + 1
    return riv_data


def get_stage_locs(riv_data):
    loc_data = pd.read_excel(gageing_path, 'locs').set_index('site')
    temp = riv_data.copy(deep=True)
    temp = smt.io.add_mxmy_to_df(temp)
    t = ((temp.mx - loc_data.loc['Camp Hill', 'x']) ** 2 + (temp.my - loc_data.loc['Camp Hill', 'y']) ** 2)
    riv_data.loc[t.argmin(), 'stage'] = 'hawea_camphill'

    x, y = 1307859, 5038569
    t = ((temp.mx - x) ** 2 + (temp.my - y) ** 2)
    riv_data.loc[t.argmin(), 'stage'] = 'clutha_luggate'

    temp = smt.get_model_zeros() * np.nan
    temp[riv_data['i'], riv_data['j']] = 1
    fig, ax = smt.plot.plt_matrix(temp, title='river_locs', base_map=True)
    ax.scatter(x, y, c='r', label='clutha_luggate')
    ax.scatter(loc_data.loc['Camp Hill', 'x'], loc_data.loc['Camp Hill', 'y'], c='b', label='hawea_camphill')
    smt.plot.show()

    return riv_data


def get_historical_stage_flow(start_date, end_date, frequency='D'):
    """
    stages in m, flow in L/s  resample to frequency
    length of records:
     lake_stage: 2012-01-01 to 2021-12-31  # note we have longer records here
     lake_flow: 2012-01-01 to 2021-12-31
     camphill_stage: 2009-01-01 to 2021-12-31
     camphill_flow: 2009-01-01 to 2021-12-31
     clutha2200_stage: 2017-07-06 to 2021-11-09

    :param start_date:
    :param end_date:
    :param frequency: pd freq codes
    :return:
    """
    hawea_data = pd.read_csv(base_model_build_data_dir.joinpath('Lake_Hawea.csv'))
    hawea_data.loc[:, 'datetime'] = ht = pd.to_datetime(hawea_data.loc[:, 'DateLake'], format='%d/%m/%Y %H:%M')
    river_data = pd.read_csv(base_model_build_data_dir.joinpath('River_Level_Hawea.csv'))
    river_data.loc[:, 'datetime'] = rt = pd.to_datetime(river_data.loc[:, 'DateTime'], format='%d/%m/%Y')
    hawea_data.set_index('datetime', inplace=True)
    river_data.set_index('datetime', inplace=True)
    mint = min(ht.min(), rt.min())
    maxt = max(ht.max(), rt.max())
    if start_date is None:
        start_date = mint
    if end_date is None:
        end_date = maxt

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    all_data = pd.DataFrame(index=pd.date_range(mint, maxt, freq='D'))

    temp = {
        'lake_stage': hawea_data.loc[:, 'LakeLevel_m'].dropna().resample('D').mean(),
        'lake_flow': hawea_data.loc[:, 'Flow_L_s'].dropna().resample('D').mean(),
        'camphill_stage': river_data.loc[:, 'Level_Camphill'].dropna().resample('D').mean(),
        'camphill_flow': river_data.loc[:, 'Flow_Camphill_L_s'].dropna().resample('D').mean(),
        'clutha_luggate': river_data.loc[:, 'Stage_Clutha2200'].dropna().resample('D').mean(),
    }
    for k, v in temp.items():
        idx = v.index
        all_data.loc[idx, k] = v

    return select_resample(all_data, start_date, end_date, frequency, 'mean')


def _print_flowlengths():
    data = get_historical_stage_flow(None, None)
    for k in data.keys():
        temp = data.loc[:, k].dropna().index
        print(f'length of record {k}: {temp.min().date()} to {temp.max().date()}')


def get_river_stage_data(start_date, end_date, frequency='D', recalc=False):
    if riv_stage_data_path.exists() and not recalc:
        outdata = pd.read_csv(riv_stage_data_path, index_col=0).astype(float)
        outdata.index = pd.to_datetime(outdata.index)
        return select_resample(outdata, start_date, end_date, frequency, 'mean')

    loc_data = get_river_loc_data()
    stage_data = get_historical_stage_flow(None, None)
    stage_data.loc[:, 'month'] = stage_data.index.month
    stage_data.loc[:, 'week'] = stage_data.index.isocalendar().week.astype(float)

    # fill missing clutha stage data with week of year mean.
    temp = stage_data.groupby('week').mean().clutha_luggate.to_dict()
    idx = stage_data.clutha_luggate.isna()
    stage_data.loc[idx, 'clutha_luggate'] = stage_data.loc[idx, 'week'].replace(temp)

    fig, ax = plt.subplots()
    ax.scatter(stage_data.loc[:, 'camphill_stage'], stage_data.loc[:, 'clutha_luggate'])
    ax.set_xlabel('hawea_camphill')
    ax.set_ylabel('clutha luggate')

    fig, ax = plt.subplots()
    ax.boxplot([stage_data.loc[stage_data.month == m, 'clutha_luggate'].dropna() for m in range(1, 13)],
               positions=range(1, 13))
    ax.set_xlabel('month')
    ax.set_ylabel('clutha luggate')

    # initialize the dataframe
    hawea_keys = loc_data.index[loc_data.loc[:, 'rname'] == 'hawea']
    clutha_keys = loc_data.index[loc_data.loc[:, 'rname'] == 'clutha']
    outdata = pd.DataFrame(index=stage_data.index, columns=loc_data.index, dtype=float)

    # set hawea_stage
    elv_at_camphill = loc_data.loc[loc_data.stage == 'hawea_camphill', 'rbot'][0]
    delta_at_camphill = (stage_data.loc[:, 'camphill_stage'] - elv_at_camphill).values
    t = (loc_data.loc[hawea_keys, 'rbot'].values[np.newaxis, :]
         + delta_at_camphill[:, np.newaxis])
    outdata.loc[:, hawea_keys] = t

    # set clutha stage, feather in the deltas at luggate to the deltas at clutha so there is no step change.
    elv_at_luggate = loc_data.loc[loc_data.stage == 'clutha_luggate', 'rbot'][0]
    delta_at_luggate = (stage_data.loc[:, 'clutha_luggate'] - elv_at_luggate).values
    clutha_dist = loc_data.loc[loc_data.loc[:, 'rname'] == 'clutha', 'dist']
    luggate_idx = np.where(loc_data.loc[loc_data.loc[:, 'rname'] == 'clutha', 'stage'].notna())[0][0]

    clutha_deltas = np.zeros((len(delta_at_luggate), len(clutha_keys))) * np.nan
    clutha_deltas[:, 0] = delta_at_camphill
    clutha_deltas[:, luggate_idx:] = delta_at_luggate[:, np.newaxis]

    clutha_deltas[:, 0:luggate_idx] = np.array(
        [delta_at_camphill * ((clutha_dist[luggate_idx] - d) / clutha_dist[luggate_idx])
         + delta_at_luggate * (d / clutha_dist[luggate_idx])
         for d in clutha_dist[0:luggate_idx]]).transpose()

    t = (loc_data.loc[clutha_keys, 'rbot'].values + clutha_deltas)
    outdata.loc[:, clutha_keys] = t

    assert (outdata.min() >= loc_data.loc[:, 'rbot']).all(), 'some stages are below rbot, address this'

    plt_stg_data = outdata.dropna().describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95])
    k_cs = ['min', '5%', '25%', '50%', '75%', '95%', 'max', ]
    colors = get_colors(k_cs, cmap_name='winter')

    temp_data = loc_data.copy(deep=True)
    tops = smt.get_tops()[0]
    bottoms = smt.get_bottoms()[0]
    temp_data.loc[:, 'model_top'] = tops[temp_data.loc[:, 'i'], temp_data.loc[:, 'j']]
    temp_data.loc[:, 'model_bot'] = bottoms[temp_data.loc[:, 'i'], temp_data.loc[:, 'j']]
    hawea_clutha_divide = temp_data.loc[temp_data.rname == 'hawea', 'dist'].max()
    temp_data.loc[temp_data.rname == 'clutha', 'dist'] += hawea_clutha_divide
    temp_data.sort_values('dist', inplace=True)
    fig, ax = plt.subplots()
    ax.set_title('both rivers')
    ax.plot(temp_data.dist, temp_data.rbot, c='y', label='river_bottom_fixed')
    ax.plot(temp_data.dist, temp_data.model_bot, c='firebrick', label='model_bottom')
    ax.plot(temp_data.dist, temp_data.model_top, c='r', label='model_top')
    for k, c in zip(k_cs, colors):
        ax.plot(temp_data.dist, plt_stg_data.loc[k].values.transpose(), c=c)
    ax.axvline(hawea_clutha_divide, ls=':', c='k')
    ax.set_ylabel('elevation')
    ax.set_xlabel('distance from top of river')
    ax.legend()

    plt.show()
    outdata.to_csv(riv_stage_data_path)
    return select_resample(outdata, start_date, end_date, frequency, 'mean')



def data_checks():
    import matplotlib.pyplot as plt

    # look at riv locations, make sure none of the locations are in the lake!!!
    ibound = smt.get_no_flow(0)
    hawea = smt.io.shape_file_to_model_array(hawea_shp_path, 'dist_top', alltouched=True)
    hawea[ibound < 1] = np.nan
    smt.plot.plt_matrix(hawea, title='hawea', base_map=True)
    clutha = smt.io.shape_file_to_model_array(clutha_shp_path, 'dist_top', alltouched=True)
    clutha[ibound < 1] = np.nan
    smt.plot.plt_matrix(clutha, title='clutha', base_map=True)

    # look at dist vs model top, bot, riv bot, looks good
    river_locs = get_river_loc_data()
    tops = smt.get_tops()[0]
    bottoms = smt.get_bottoms()[0]
    river_locs.loc[:, 'model_top'] = tops[river_locs.loc[:, 'i'], river_locs.loc[:, 'j']]
    river_locs.loc[:, 'model_bot'] = bottoms[river_locs.loc[:, 'i'], river_locs.loc[:, 'j']]
    for r in ['clutha', 'hawea', 'both']:
        if r == 'both':
            temp_data = river_locs.copy(deep=True)
            temp_data.loc[temp_data.rname == 'clutha', 'dist'] += temp_data.loc[
                temp_data.rname == 'hawea', 'dist'].max()
        else:
            temp_data = river_locs.loc[river_locs.rname == r]
        temp_data.sort_values('dist', inplace=True)
        fig, ax = plt.subplots()
        ax.set_title(r)
        ax.plot(temp_data.dist, temp_data.rbot_raw, c='b', label='river_bottom_raw')
        ax.plot(temp_data.dist, temp_data.rbot, c='y', label='river_bottom_fixed')
        ax.plot(temp_data.dist, temp_data.model_bot, c='k', label='model_bottom')
        ax.plot(temp_data.dist, temp_data.model_top, c='r', label='model_top')
        ax.set_ylabel('elevation')
        ax.set_xlabel('distance from top of river')
        ax.legend()
    # look at stage through time at our locations( which are???)
    hawea_data = pd.read_csv(base_model_build_data_dir.joinpath('Lake_Hawea.csv'))
    print(hawea_data.describe())
    hawea_data.loc[:, 'datetime'] = pd.to_datetime(hawea_data.loc[:, 'DateLake'], format='%d/%m/%Y %H:%M')
    hawea_data.loc[:, 'month'] = hawea_data.loc[:, 'datetime'].dt.month
    monthly = hawea_data.groupby('month').describe(percentiles=[.05, .25, .5, .75, .95])
    fig, ax = plt.subplots()
    monthly.LakeLevel_m.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('lake level')

    river_data = pd.read_csv(base_model_build_data_dir.joinpath('River_Level_Hawea.csv'))
    print(river_data.describe())
    river_data.loc[:, 'datetime'] = pd.to_datetime(river_data.loc[:, 'DateTime'], format='%d/%m/%Y')
    river_data.loc[:, 'month'] = river_data.loc[:, 'datetime'].dt.month
    monthly = river_data.groupby('month').describe(percentiles=[.05, .25, .5, .75, .95])
    fig, ax = plt.subplots()
    monthly.Level_Camphill.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('camp hill stage')
    fig, ax = plt.subplots()
    monthly.Stage_Clutha2200.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('clutha 2200 stage')

    # look at gaging sites
    temp2 = smt.io.df_to_array(river_locs, 'gage')
    smt.plot.plt_matrix(temp2, base_map=True, title='gaging locs')
    plt.show()


if __name__ == '__main__':
    _print_flowlengths()
    t = get_river_loc_data(True)
    smt.get_elv_db(recalc=True)
    t = get_river_stage_data(None, None, recalc=True)
    data_checks()
