"""
created matt_dumont 
on: 30/09/22
"""
import datetime
import pandas as pd
import numpy as np
from komanawa.hawea.model_build.utils import get_colors
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta
from komanawa.hawea.targets_and_sensitive_sites.head_targets import get_high_freq_head_targets, get_all_wells
from komanawa.hawea.model_build.project_model_tools import smt


def get_opt_start_stop():
    figs = []
    names = []
    targets = get_high_freq_head_targets('2015-07-01', None)

    targets.loc[:, 'month'] = targets.index.month
    targets.loc[:, 'week'] = targets.index.isocalendar().week
    mean_targets = targets.drop(columns=['week', 'month']).mean()
    targ_names = list(mean_targets.keys())
    mean_targets.loc['week'] = 0
    mean_targets.loc['month'] = 0
    colors = get_colors(targ_names)
    monthly = (targets.drop(columns='week') - mean_targets.drop('week')).groupby('month').describe()
    weekly = (targets.drop(columns='month') - mean_targets.drop('month')).groupby('week').describe()
    monthly.index = pd.to_datetime([f'2024-{int(m):02d}-15' for m in monthly.index])
    weekly.index = pd.to_datetime([datetime.date(2024, 1, 1)
                                   + relativedelta(weeks=int(w), days=3) for w in
                                   weekly.index])  # first of jan is monday in 2024
    weekly.loc[:, 'rmse'] = (weekly.loc[:, (slice(None), 'mean')] ** 2).sum(axis=1) ** 0.5
    monthly.loc[:, 'rmse'] = (monthly.loc[:, (slice(None), 'mean')] ** 2).sum(axis=1) ** 0.5
    print(monthly.rmse.sort_values())
    print(weekly.rmse.sort_values().iloc[0:10])
    weekly_ext = weekly.copy(deep=True)
    weekly_ext.index = [e + relativedelta(years=1) for e in weekly.index]
    weekly = pd.concat((weekly, weekly_ext))
    monthly_ext = monthly.copy(deep=True)
    monthly_ext.index = [e + relativedelta(years=1) for e in monthly.index]
    monthly = pd.concat((monthly, monthly_ext))
    fig, (ax1, ax2) = plt.subplots(nrows=2, sharex=True, sharey=True, figsize=(10, 8))
    fig3, (ax31, ax32) = plt.subplots(nrows=2, sharex=True, sharey=True, figsize=(10, 8))
    for t, c in zip(targ_names, colors):
        fig2, (ax21, ax22) = plt.subplots(nrows=2, sharex=True, sharey=True, figsize=(10, 8))
        ax21.fill_between((weekly.index - datetime.datetime(2024, 1, 1)).days,
                          weekly.loc[:, (t, '25%')], weekly.loc[:, (t, '75%')],
                          color=c, label=f'inter-quartile {t}', alpha=0.5)
        ax22.fill_between((monthly.index - datetime.datetime(2024, 1, 1)).days,
                          monthly.loc[:, (t, '25%')], monthly.loc[:, (t, '75%')],
                          color=c, label=f'inter-quartile {t}', alpha=0.5)
        ax21.plot((weekly.index - datetime.datetime(2024, 1, 1)).days,
                  weekly.loc[:, (t, 'mean')], c=c, label=t, marker='.')
        ax22.plot((monthly.index - datetime.datetime(2024, 1, 1)).days,
                  monthly.loc[:, (t, 'mean')], c=c, label=t, marker='.')

        ax1.plot((weekly.index - datetime.datetime(2024, 1, 1)).days,
                 weekly.loc[:, (t, 'mean')], c=c, label=t, marker='.')
        ax2.plot((monthly.index - datetime.datetime(2024, 1, 1)).days,
                 monthly.loc[:, (t, 'mean')], c=c, label=t, marker='.')
        ax21.axhline(0, color='k', ls=':')
        ax22.axhline(0, color='k', ls=':')
        ax21.legend()
        ax22.legend()
        fig2.suptitle(f'Monthly / weekly Head obs - mean head obs {t}')
        fig2.supxlabel('Days from Jan 1')
        fig2.supylabel('Difference (m)')
        figs.append(fig2)
        names.append(f'monthy_weekly_delta_to_mean_{t}')

    ax1.plot((weekly.index - datetime.datetime(2024, 1, 1)).days,
             weekly.loc[:, 'rmse'], c='k', label='RSME', marker='.')
    ax2.plot((monthly.index - datetime.datetime(2024, 1, 1)).days,
             monthly.loc[:, 'rmse'], c='k', label='RMSE', marker='.')
    ax1.axhline(0, color='k', ls=':')
    ax2.axhline(0, color='k', ls=':')
    ax1.legend()
    ax2.legend()
    fig.suptitle('Monthly / weekly Head obs - mean head obs')
    fig.supxlabel('days from Jan1')
    fig.supylabel('Difference (m)')

    fig.tight_layout()
    figs.append(fig)
    names.append('monthy_weekly_delta_to_mean_all')

    fig, ax = plt.subplots(figsize=(10, 8))
    targets = get_high_freq_head_targets(None, None)
    targets = targets - mean_targets

    targets.loc[:, 'rmse'] = (targets ** 2).sum(axis=1) ** 0.5
    for t, c in zip(targ_names, colors):
        ax.plot(targets.index, targets.loc[:, t], c=c, label=t)
    ax.plot(targets.index, targets.loc[:, 'rmse'], c='k', label='RSME')
    ax.axhline(0, color='k', ls=':')
    ax.legend()
    ax.set_title('Head obs - mean head obs')
    ax.set_xlabel('Time')
    ax.set_ylabel('Difference (m)')
    fig.tight_layout()
    figs.append(fig)
    names.append('real_time_delta_to_mean')

    all_wells = get_all_wells().loc[targ_names]
    fig, ax = smt.plot.plt_basemap(no_flow_layer=0)

    ax.scatter(all_wells.nztmx, all_wells.nztmy, color='r')
    for k, c in zip(targ_names, colors):
        x, y = all_wells.loc[k, ['nztmx', 'nztmy']]
        adder = np.random.randint(1, 500)
        ax.scatter(x, y, color=c, label=k)
        ax.text(x + 100, y + adder, k, color='k', fontdict={'weight': 'heavy'})
    ax.legend()
    ax.set_title('Head obs locations')
    figs.append(fig)
    names.append('high_frequency_locs')
    return figs, names


if __name__ == '__main__':
    get_opt_start_stop()
    plt.show()
