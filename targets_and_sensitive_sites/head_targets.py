"""
created matt_dumont 
on: 15/08/22
"""
import pickle
import time
import warnings
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import numpy as np
from dateutil.relativedelta import relativedelta
import pandas as pd
from model_build.supporting_data_analysis import get_all_wells
from model_build.project_model_tools import smt
from project_base import processed_target_dir, base_target_dir
from model_build.utils import get_colors, select_resample
from targets_and_sensitive_sites.get_raw_target_data import get_single_target_data, get_high_freq_head_targets
from targets_and_sensitive_sites.get_indicative_times import get_indicative_times_v2
from model_build.zones import get_model_zones

base_regular_groupnames = ['h_hf_riv', 'h_hf', 'h_lf']  # ensures coheriance across functions


def get_single_head_targets():
    all_wells = get_single_target_data()
    all_wells.loc[:, 'org_time'] = [f'{e.month}-{e.year}' for e in all_wells.drilldate]
    indicative_times = get_indicative_times_v2()
    all_wells.loc[:, 'model_time'] = all_wells.loc[:, 'org_time'].replace(indicative_times)
    all_wells.loc[:, 'model_month'] = all_wells.model_time.str.split('-').str.get(0).astype(int)
    assert all_wells.model_time.notna().all()

    outdata = []

    # duplicate all times
    for i, r in all_wells.reset_index().iterrows():
        start_date = pd.to_datetime('01-' + r.model_time, format='%d-%m-%Y')
        dates = pd.date_range(start_date, start_date + relativedelta(months=1, days=-1), freq='D')
        temp = pd.DataFrame(np.repeat(r.to_numpy()[np.newaxis, :], len(dates), axis=0), columns=r.keys())
        temp.loc[:, 'use_datetime'] = dates
        outdata.append(temp)
    outdata = pd.concat(outdata)
    outdata.loc[:, 'k'] = 0
    outdata.loc[:, 'i'] = outdata.loc[:, 'i'].astype(int)
    outdata.loc[:, 'j'] = outdata.loc[:, 'j'].astype(int)
    outdata.loc[:, 'head'] = outdata.loc[:, 'depth_to_water_elv'].astype(float)
    return outdata


def get_2011_piezo_survey(recalc=False):
    # piezo survey conducted 21-sept-2011
    data_path = base_target_dir.joinpath('Peizo Survey 20Sept2011.xlsx')
    processed_path = processed_target_dir.joinpath('piezo_targets.csv')

    if processed_path.exists() and not recalc:
        data = pd.read_csv(processed_path, index_col=0)
        data.loc[:, 'i'] = data.loc[:, 'i'].astype(int)
        data.loc[:, 'j'] = data.loc[:, 'j'].astype(int)
        data.loc[:, 'k'] = data.loc[:, 'k'].astype(int)
        data.loc[:, 'use_datetime'] = pd.to_datetime(data.loc[:, 'use_datetime'])

        return data

    data = pd.read_excel(data_path, 'Appendix Table')
    data.rename(columns={'Easting': 'nztmx', 'Northing': 'nztmy', 'Water level elevation': 'head'}, inplace=True)
    row, col = smt.convert_coords_to_matix(data.nztmx, data.nztmy, coords_out_domain='coerce')
    data.loc[:, 'i'] = row
    data.loc[:, 'j'] = col
    data = data.loc[data.i >= 0]
    ibound = smt.get_no_flow(0)
    data.loc[:, 'ibound'] = ibound[data.i, data.j]
    data = data.loc[data.ibound > 0]

    indicative_time = get_indicative_times_v2()['9-2011']
    start_date = pd.to_datetime('01-' + indicative_time, format='%d-%m-%Y')
    outdata = []
    dates = pd.date_range(start_date, start_date + relativedelta(months=1, days=-1), freq='D')
    for d in dates:
        temp = data.copy(True)
        temp.loc[:, 'use_datetime'] = d
        outdata.append(temp)
    outdata = pd.concat(outdata).reset_index(drop=True)
    outdata.loc[:, 'k'] = 0
    outdata.to_csv(processed_path)
    return outdata


def get_low_freq_head_targets(start_date, end_date, freq='D'):
    data_path = base_target_dir.joinpath('NGMP bore fluctuations 1996 - 2019.csv')
    data = pd.read_csv(data_path)
    outdata = []
    for k in ['G40/0120', 'G40/0129']:
        temp = data.loc[:, [f'{k}_date', f'{k}_wl']].dropna()
        temp.loc[:, 'date'] = pd.to_datetime(temp.loc[:, f'{k}_date'], format='%d-%b-%Y').dt.date
        temp.rename(columns={f'{k}_wl': 'level'}, inplace=True)
        temp.loc[:, 'well'] = k.lower().replace('/', '_')
        outdata.append(temp.loc[:, ['date', 'well', 'level']])

    outdata = pd.concat(outdata)

    if start_date is None:
        start_date = outdata.loc[:, 'date'].min()
    if end_date is None:
        end_date = outdata.loc[:, 'date'].max()
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()

    outdata.loc[:, 'date'] = pd.to_datetime(outdata.loc[:, 'date'])
    use_outdata = []
    for w in outdata.well.unique():
        temp = outdata.loc[outdata.well == w, ['date', 'level']]
        temp.rename(columns={'level': w}, inplace=True)
        use_outdata.append(temp)
    outdata = pd.concat(use_outdata)
    outdata = outdata.groupby('date').mean()
    outdata = select_resample(outdata, start_date, end_date, frequency=freq)
    return outdata


def plot_head_targets(how='all'):
    alpha = 0.8
    if how == 'all':
        fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, color_bar=False,
                                      base_map=True, no_flow_layer=0)

        all_wells = get_all_wells()
        all_wells = all_wells.loc[all_wells.ibound > 0]
        qcs = all_wells.loc[:, 'quality_code'].unique()
        colors = get_colors(qcs)
        for qc, c in zip(qcs, colors):
            temp = all_wells.loc[all_wells.quality_code == qc]
            ax.scatter(temp.nztmx, temp.nztmy, color=c, label=f'single targets qc: {qc}', marker='d', alpha=alpha)

        # add scott piezo locs
        piezo = get_2011_piezo_survey(recalc=True)
        ax.scatter(piezo.nztmx, piezo.nztmy, color='orange', marker='s', alpha=alpha, label='piezo 2011')

        marker_size = 50
        # add ngmp wells
        t = get_low_freq_head_targets(None, None)
        wells = all_wells.loc[t.keys()]
        ax.scatter(wells.nztmx, wells.nztmy, color='r', marker='p', label='mod_freq', s=marker_size)

        # add high frequency
        t = get_high_freq_head_targets(None, None)
        wells = all_wells.loc[t.keys()]
        ax.scatter(wells.nztmx, wells.nztmy, color='magenta', marker='*', label='high_freq', s=marker_size)

        print('plotting all head targets')
        ax.set_title('all head targets')
        ax.legend()


    elif how == 'incl':
        fig, ax = smt.plot.plt_matrix(smt.get_model_zeros() * np.nan, color_bar=False,
                                      base_map=True, no_flow_layer=0)

        all_wells = get_all_wells()
        single_targets = get_single_head_targets()
        all_wells = all_wells.loc[all_wells.ibound > 0]
        qcs = all_wells.loc[:, 'quality_code'].unique()
        colors = get_colors(qcs)
        for qc, c in zip(qcs, colors):
            temp = single_targets.loc[single_targets.quality_code == qc]
            ax.scatter(temp.nztmx, temp.nztmy, color=c, label=f'Single targets qc: {qc}', marker='d', alpha=alpha)

        # add scott piezo locs
        piezo = get_2011_piezo_survey(recalc=True)
        ax.scatter(piezo.nztmx, piezo.nztmy, color='orange', marker='s', alpha=alpha, label='Piezo 2011')

        marker_size = 120
        # add ngmp wells
        t = get_low_freq_head_targets(None, None)
        wells = all_wells.loc[t.keys()]
        ax.scatter(wells.nztmx, wells.nztmy, color='r', marker='p', label='Moderate freq', s=marker_size)

        # add high frequency
        t = get_high_freq_head_targets(None, None)
        wells = all_wells.loc[t.keys()]
        ax.scatter(wells.nztmx, wells.nztmy, color='magenta', marker='*', label='High freq', s=marker_size)

        print('plotting head targets included in the model')
        ax.legend(loc='lower left')
        ax.set_title('Head targets included in the model')

    else:
        raise NotImplementedError
    return fig, ax


def export_incl_head_target_locs():
    outdata = []

    all_wells = get_all_wells()
    single_targets = get_single_head_targets()
    all_wells = all_wells.loc[all_wells.ibound > 0]
    qcs = single_targets.loc[:, 'quality_code'].unique()
    colors = get_colors(qcs)
    for qc, c in zip(qcs, colors):
        temp = single_targets.loc[single_targets.quality_code == qc]
        temp_out = {'nztmx': temp.nztmx.values, 'nztmy': temp.nztmy.values}
        temp_out = pd.DataFrame(temp_out)
        temp_out.loc[:, 'type'] = f'single_qc{qc}'
        outdata.append(temp_out)

    # add scott piezo locs
    piezo = get_2011_piezo_survey(recalc=True)
    temp_out = {'nztmx': piezo.nztmx.values, 'nztmy': piezo.nztmy.values}
    temp_out = pd.DataFrame(temp_out)
    temp_out.loc[:, 'type'] = 'piezo_2011'
    outdata.append(temp_out)

    # add ngmp wells
    t = get_low_freq_head_targets(None, None)
    wells = all_wells.loc[t.keys()]
    temp_out = {'nztmx': wells.nztmx.values, 'nztmy': wells.nztmy.values}
    temp_out = pd.DataFrame(temp_out)
    temp_out.loc[:, 'type'] = 'mod_freq'
    outdata.append(temp_out)

    # add high frequency
    t = get_high_freq_head_targets(None, None)
    wells = all_wells.loc[t.keys()]
    temp_out = {'nztmx': wells.nztmx.values, 'nztmy': wells.nztmy.values}
    temp_out = pd.DataFrame(temp_out)
    temp_out.loc[:, 'type'] = 'high_freq'
    outdata.append(temp_out)

    outdata = pd.concat(outdata)
    outdata.to_csv(processed_target_dir.joinpath('head_target_locations.csv'))


def get_all_hds_targets(tdis, recalc=False):
    save_path = processed_target_dir.joinpath(f'optimisation_hds_targets-{tdis.name}.p')
    if save_path.exists() and not recalc:
        out = pickle.load(open(save_path, 'rb'))
        return out

    need_keys = ['k', 'i', 'j', 'use_datetime', 'head', 'group', 'name']
    all_head_targets = []
    piezo = get_2011_piezo_survey(recalc=recalc).rename(columns={'Site': 'name'})
    piezo.loc[:, 'name'] = piezo.loc[:, 'name'].str.replace('/', '_').str.replace('bore', '')
    piezo.loc[:, 'group'] = 'h_piezo'
    all_head_targets.append(piezo.loc[:, need_keys])

    single = get_single_head_targets().rename(columns={'well_name': 'name'})
    single.loc[:, 'group'] = 'h_single_' + single.quality_code.astype(str)
    all_head_targets.append(single.loc[:, need_keys])

    low = get_low_freq_head_targets(*tdis.date_limits, 'W')
    all_high = get_high_freq_head_targets(*tdis.date_limits, 'W')
    high_near_riv = all_high.loc[:, ['g40_0041', 'g40_0416']]
    high_far_riv = all_high.loc[:, ['g40_0367', 'g40_0366', 'g40_0415']]

    all_wells = get_all_wells()

    regular_datasets = [high_near_riv, high_far_riv, low]
    regular_groupnames = ['h_hf_riv', 'h_hf', 'h_lf']
    assert regular_groupnames == base_regular_groupnames

    for hdatset, group_name in zip(regular_datasets, regular_groupnames):
        hdatset.index.name = 'use_datetime'
        for k in hdatset.columns:
            temp = pd.DataFrame(hdatset.loc[:, k]).reset_index().dropna()
            temp.rename(columns={k: 'head'}, inplace=True)
            i, j = all_wells.loc[k, ['i', 'j']]
            temp.loc[:, 'name'] = k
            temp.loc[:, 'k'] = 0
            temp.loc[:, 'i'] = i
            temp.loc[:, 'j'] = j
            temp.loc[:, 'group'] = group_name
            all_head_targets.append(temp)
    all_head_targets = pd.concat(all_head_targets).reset_index(drop=True)
    all_head_targets = all_head_targets.loc[all_head_targets.loc[:, 'head'].notna()]

    # add step and per, remove duplicated data
    all_head_targets = tdis.add_nstp_nper_to_df(all_head_targets, datetime_col='use_datetime',
                                                action_on_duplicates='last')

    all_head_targets = all_head_targets.loc[all_head_targets.nper > 0]
    all_head_targets = all_head_targets.drop_duplicates(subset=['i', 'j', 'group', 'nper']).reset_index(drop=True)
    all_head_targets.loc[:, 'name'] = ('h_'
                                       + all_head_targets.name.str.replace(' ', '_')
                                       + '_'
                                       + all_head_targets.nper.astype(str)).str.lower()
    all_head_targets.drop_duplicates(subset=['name'], keep='last', inplace=True)

    # add zone
    zones = get_model_zones()
    use_zones = [
        'sandypoint',
        'flat',
        'east',
        'mangawera',
        'terrace'

    ]
    all_head_targets.loc[:, 'zone'] = 'east'
    for z in use_zones:
        idx = zones[z]
        idx = idx[all_head_targets.i, all_head_targets.j]
        all_head_targets.loc[idx, 'zone'] = z

    pickle.dump(all_head_targets, open(save_path, 'wb'))
    return all_head_targets


def plot_hds_regular_locator(ax, colors_dict, truncate_to_active=True):
    all_wells = get_all_wells()
    smt.plot.plt_basemap(ax=ax, no_flow_layer=0)

    for k, c in colors_dict.items():
        k = k.replace('h_', '')
        x, y = all_wells.loc[k, ['nztmx', 'nztmy']]
        ax.scatter(x, y, color=c, label=k, s=80)
    if truncate_to_active:
        xs, ys = smt.get_model_x_y()
        ibound = smt.get_no_flow(0)
        ys = ys[ibound == 1]
        ax.set_ylim(ys.min() - 200, ys.max() + 200)
    ax.legend(loc='lower left')


def plot_hds_zone_locator(ax, colors_dict, default_zone='east'):
    use_zones = list(colors_dict.keys())
    use_colors = [colors_dict[k] for k in use_zones]
    vals = {k: i for i, k in enumerate(use_zones)}
    zones = get_model_zones()
    zone_plot = smt.get_model_zeros() * np.nan
    zone_plot[zones['active']] = vals[default_zone]
    for i, z in enumerate(use_zones):
        zone_plot[zones[z]] = i

    cmap = ListedColormap(use_colors)
    smt.plot.plt_matrix(zone_plot, no_flow_layer=0, base_map=True,
                        cmap=cmap, color_bar=False, ax=ax, alpha=0.5)
    handles, labels = [], []
    for c, n in zip(use_colors, use_zones):
        handles.append(Patch(facecolor=c))
        labels.append(n.capitalize())
    ax.legend(handles, labels, loc='lower left')


def get_annual_mean_head_targets(hds_df):
    """

    :param hds_df: from get_all_hds_targets(tdis)
    :return:
    """
    assert isinstance(hds_df, pd.DataFrame)
    hds_df = hds_df.copy(deep=True).loc[np.in1d(hds_df.group, base_regular_groupnames[0:-1])]

    t = hds_df.name.str.split('_')
    hds_df.loc[:, 'well_name'] = t.str.get(1) + '_' + t.str.get(2)
    hds_df.loc[:, 'week'] = hds_df.use_datetime.dt.isocalendar().loc[:, 'week']
    out = hds_df.groupby(['well_name', 'week']).agg({
        'group': 'first',
        'zone': 'first',
        'head': 'mean',
        'modelled': 'mean',
    })
    out = out.reset_index()
    out.loc[:, 'nper'] = out.week * -1
    out.loc[:, 'name'] = 'h_' + out.well_name + '_rw' + pd.Series([f'{e:02d}' for e in out.week])
    out = out.replace({
        'h_hf': 'rwh_hf',
        'h_hf_riv': 'rwh_hf_riv',
    })

    return out


if __name__ == '__main__':
    from optimisation.optimisation_period import tdis

    get_all_hds_targets(tdis, recalc=True)
    raise NotImplementedError
    print('piezo')
    print(get_2011_piezo_survey(recalc=True).dtypes)
    time.sleep(1)
    print('single')
    print(get_single_head_targets().dtypes)
    time.sleep(1)
    print('low')
    print(get_low_freq_head_targets(None, None).dtypes)
    time.sleep(1)
    print('high')
    print(get_high_freq_head_targets(None, None).dtypes)
    time.sleep(1)
    plot_head_targets(how='incl')
    smt.plot.show()
    plot_head_targets()
    export_incl_head_target_locs()
