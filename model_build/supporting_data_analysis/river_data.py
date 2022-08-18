"""
created matt_dumont 
on: 2/08/22
"""
import numpy as np
import pandas as pd

from model_build.project_model_tools import smt, simplify_hawea_dem, _river_locs
from project_base import base_model_data_dir, processed_model_data_dir

default_recalc = False
hawea_shp_path = base_model_data_dir.joinpath('hawea_river.shp')
clutha_shp_path = base_model_data_dir.joinpath('lower_clutha.shp')
gageing_path = base_model_data_dir.joinpath('Hawea River - ORC Gaugings for Gain & Loss Estimation.xlsx')

riv_loc_data_path = processed_model_data_dir.joinpath('river_loc_data.csv')


def make_river_loc_data(recalc=default_recalc):
    if not recalc and riv_loc_data_path.exists():
        outdata = pd.read_csv(riv_loc_data_path)
        dtypes = {
            'i': 'int64',
            'j': 'int64',
            'dist': 'float64',
            'rbot': 'float64',
            'rname': 'str',
            'gage': 'int64'
        }

        for k, v in dtypes.items():
            outdata.loc[:, k] = outdata.loc[:, k].astype(v)
        return outdata
    outdata = _river_locs()
    outdata = get_river_gage_locs(outdata)
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
    for i,(s1, s2) in enumerate(zip(all_sites[0:-1], all_sites[1:])):
        assert (loc_data.loc[[s1, s2], 'rname'] == 'hawea').all()
        dist1, dist2 = loc_data.loc[[s1, s2], 'dist']
        idx = (riv_data.rname=='hawea') & (riv_data.dist>=dist1) & (riv_data.dist<=dist2)
        riv_data.loc[idx, 'gage'] = i+1
    return riv_data

def get_historical_stage_flow(start_date, end_date, frequency='D'):
    """
    stages in m, flow in L/s  resample to frequency
    length of records:
     lake_stage: 2012-01-01 to 2021-12-31
     lake_flow: 2012-01-01 to 2021-12-31
     camphill_stage: 2009-01-01 to 2021-12-31
     camphill_flow: 2009-01-01 to 2021-12-31
     clutha2200_stage: 2017-07-06 to 2021-11-09

    :param start_date:
    :param end_date:
    :param frequency: pd freq codes
    :return:
    """
    hawea_data = pd.read_csv(base_model_data_dir.joinpath('Lake_Hawea.csv'))
    hawea_data.loc[:, 'datetime'] = ht = pd.to_datetime(hawea_data.loc[:, 'DateLake'], format='%d/%m/%Y %H:%M')
    river_data = pd.read_csv(base_model_data_dir.joinpath('River_Level_Hawea.csv'))
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
        'clutha2200_stage': river_data.loc[:, 'Stage_Clutha2200'].dropna().resample('D').mean(),
    }
    for k, v in temp.items():
        idx = v.index
        all_data.loc[idx, k] = v
    idx = (all_data.index >= start_date) & (all_data.index <= end_date)
    return all_data.loc[idx].resample(frequency).mean()


def _print_flowlengths():
    data = get_historical_stage_flow(None, None)
    for k in data.keys():
        temp = data.loc[:, k].dropna().index
        print(f'length of record {k}: {temp.min().date()} to {temp.max().date()}')


def get_river_stage_data():  # todo
    # the river stage is largely stable
    # hawea 310-313, median 311
    # todo where is stage clutha 2200???
    # todo how do I manage the lake stage/top of the hawea river??? discuss with Jens
    # todo need to interpolate the river stage.
    # todo clutha 2200 is really short if we need to make this part of the model, possibly look at making a statistical
    # relationship
    # todo stage set at damn, 1km from dam there are transient records of stage... calibration dataset
    # todo as we only have 1 data point on each river, maybe just set stage to n meters above river bottom as defined by
    # todo the recorders for both the clutha and hawea rivers
    raise NotImplementedError


def get_river_conductance(river_loc_data, optimised):  # todo switch to passing conductance
    """
    get the river conductance values
    :param river_loc_data: river location data output of make_river_loc_data
    :param optimised: bool if True use the optimised parameters, else use the initial parameters
    :return:
    """
    if optimised:
        raise NotImplementedError('optimisation not complete')
    else:

        raise NotImplementedError


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
    river_locs = make_river_loc_data()
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
    hawea_data = pd.read_csv(base_model_data_dir.joinpath('Lake_Hawea.csv'))
    print(hawea_data.describe())
    hawea_data.loc[:, 'datetime'] = pd.to_datetime(hawea_data.loc[:, 'DateLake'], format='%d/%m/%Y %H:%M')
    hawea_data.loc[:, 'month'] = hawea_data.loc[:, 'datetime'].dt.month
    monthly = hawea_data.groupby('month').describe(percentiles=[.05, .25, .5, .75, .95])
    fig, ax = plt.subplots()
    monthly.LakeLevel_m.loc[:, ['min', '5%', '25%', '50%', '75%', '95%', 'max']].plot(ax=ax)
    ax.set_title('lake level')

    river_data = pd.read_csv(base_model_data_dir.joinpath('River_Level_Hawea.csv'))
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
    temp = smt.io.df_to_array(river_locs, 'gage')
    smt.plot.plt_matrix(temp, base_map=True, title='gaging locs')
    plt.show()

    # todo look at dist vs model top, bot, riv bot along each river. include min, 5th, 25th, 50th, 75th, 95th, max temporal stage
    raise NotImplementedError


def make_river_data():
    # todo put it all togeather to drop into modflow.
    raise NotImplementedError


if __name__ == '__main__':
    smt.get_elv_db(recalc=True)
    smt.plot.plt_matrix(smt.get_bottoms()[0], base_map=True, title='bottoms', no_flow_layer=0)
    simplify_hawea_dem(True)
    make_river_loc_data(True)
    data_checks()
