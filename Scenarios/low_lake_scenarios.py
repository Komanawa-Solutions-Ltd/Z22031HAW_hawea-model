"""
created matt_dumont 
on: 28/02/23
"""
import matplotlib.pyplot as plt
from Scenarios.run_flow_scenario import run_scenario
from Scenarios.boundary_conditions import get_scen_ghb_data, get_scen_well_data, get_scen_str_data, get_scen_rch
from model_parameterisation.optimised_parameterisation import get_3d_v1d_params
from Scenarios.scen_period import scen_tdis
from project_base import processed_scen_dir, proj_root, unbacked_dir
import pandas as pd
import datetime
from model_tools.time_discretization import TimeDis # todo nee dummy
import inspect
import numpy as np
from Scenarios.low_lake_scenario_data import get_low_lake_params, mod_sin_asym
import traceback
from model_build.project_model_tools import bund_top, l2_top


def get_lake_hds(key):
    xs = np.arange(1, 52 + 1)
    base_a, base_b, base_d = get_low_lake_params()

    possible_data = {
        'base': mod_sin_asym(xs, d=base_d,
                             low_a=base_a, low_b=base_b, low_k=1,
                             high_a=base_a, high_b=base_b, high_k=1),

        # widening the low
        'low_wide_0.75': mod_sin_asym(xs, d=base_d,
                                      low_a=base_a, low_b=base_b, low_k=.75,
                                      high_a=base_a, high_b=base_b, high_k=1),
        'low_wide_0.5': mod_sin_asym(xs, d=base_d,
                                     low_a=base_a, low_b=base_b, low_k=.5,
                                     high_a=base_a, high_b=base_b, high_k=1),
        'low_wide_0.3': mod_sin_asym(xs, d=base_d,
                                     low_a=base_a, low_b=base_b, low_k=.3,
                                     high_a=base_a, high_b=base_b, high_k=1),
        'low_wide_0.1': mod_sin_asym(xs, d=base_d,
                                     low_a=base_a, low_b=base_b, low_k=.1,
                                     high_a=base_a, high_b=base_b, high_k=1),

        # shifting the curve
        'shift_-.5': mod_sin_asym(xs, d=base_d,
                                  low_a=base_a, low_b=base_b - 0.5, low_k=1,
                                  high_a=base_a, high_b=base_b - 0.5, high_k=1),
        'shift_-1': mod_sin_asym(xs, d=base_d,
                                 low_a=base_a, low_b=base_b - 1, low_k=1,
                                 high_a=base_a, high_b=base_b - 1, high_k=1),
        'shift_-1.5': mod_sin_asym(xs, d=base_d,
                                   low_a=base_a, low_b=base_b - 1.5, low_k=1,
                                   high_a=base_a, high_b=base_b - 1.5, high_k=1),
        'shift_-2': mod_sin_asym(xs, d=base_d,
                                 low_a=base_a, low_b=base_b - 2, low_k=1,
                                 high_a=base_a, high_b=base_b - 2, high_k=1),
        'shift_-2.5': mod_sin_asym(xs, d=base_d,
                                   low_a=base_a, low_b=base_b - 2.5, low_k=1,
                                   high_a=base_a, high_b=base_b - 2.5, high_k=1),
        'shift_-3': mod_sin_asym(xs, d=base_d,
                                 low_a=base_a, low_b=base_b - 3, low_k=1,
                                 high_a=base_a, high_b=base_b - 3, high_k=1),
        'shift_-3.5': mod_sin_asym(xs, d=base_d,
                                   low_a=base_a, low_b=base_b - 3.5, low_k=1,
                                   high_a=base_a, high_b=base_b - 3.5, high_k=1),
        'shift_-5': mod_sin_asym(xs, d=base_d,
                                 low_a=base_a, low_b=base_b - 5, low_k=1,
                                 high_a=base_a, high_b=base_b - 5, high_k=1),
        'shift_-7': mod_sin_asym(xs, d=base_d,
                                 low_a=base_a, low_b=base_b - 7, low_k=1,
                                 high_a=base_a, high_b=base_b - 7, high_k=1),

        # amplitude
        'low_amp_1.25': mod_sin_asym(xs, d=base_d,
                                     low_a=base_a * 1.25, low_b=base_b, low_k=1,
                                     high_a=base_a, high_b=base_b, high_k=1),
        'low_amp_1.5': mod_sin_asym(xs, d=base_d,
                                    low_a=base_a * 1.5, low_b=base_b, low_k=1,
                                    high_a=base_a, high_b=base_b, high_k=1),
        'low_amp_1.75': mod_sin_asym(xs, d=base_d,
                                     low_a=base_a * 1.75, low_b=base_b, low_k=1,
                                     high_a=base_a, high_b=base_b, high_k=1),
        'low_amp_2': mod_sin_asym(xs, d=base_d,
                                  low_a=base_a * 2, low_b=base_b, low_k=1,
                                  high_a=base_a, high_b=base_b, high_k=1),
        'low_amp_2.5': mod_sin_asym(xs, d=base_d,
                                    low_a=base_a * 2.5, low_b=base_b, low_k=1,
                                    high_a=base_a, high_b=base_b, high_k=1),
        'low_amp_3': mod_sin_asym(xs, d=base_d,
                                  low_a=base_a * 3, low_b=base_b, low_k=1,
                                  high_a=base_a, high_b=base_b, high_k=1),
        'low_amp_3.5': mod_sin_asym(xs, d=base_d,
                                    low_a=base_a * 3.5, low_b=base_b, low_k=1,
                                    high_a=base_a, high_b=base_b, high_k=1),
        'low_amp_4': mod_sin_asym(xs, d=base_d,
                                  low_a=base_a * 4, low_b=base_b, low_k=1,
                                  high_a=base_a, high_b=base_b, high_k=1),

        'low_wid_amp_0.5_4': mod_sin_asym(xs, d=base_d,
                                          low_a=base_a * 3, low_b=base_b - 3, low_k=.5,
                                          high_a=base_a, high_b=base_b - 3, high_k=1),
        'low_wid_amp_0.75_4': mod_sin_asym(xs, d=base_d,
                                           low_a=base_a * 3, low_b=base_b - 3, low_k=.75,
                                           high_a=base_a, high_b=base_b - 3, high_k=1),
        'low_wid_amp_0.9_4': mod_sin_asym(xs, d=base_d,
                                          low_a=base_a * 3, low_b=base_b - 3, low_k=.9,
                                          high_a=base_a, high_b=base_b - 3, high_k=1),

    }
    t = [[np.mean(possible_data['base'])]] + [possible_data['low_amp_4'][0:np.argmin(possible_data['low_amp_4'])]]
    t = np.concatenate(t)
    t2 = np.concatenate((t, np.zeros((52 * low_lake_years + 1) - len(t)) + 333))
    possible_data['lake_drop_333'] = t2
    t2 = np.concatenate((t, np.zeros((52 * low_lake_years + 1) - len(t)) + 320))
    possible_data['lake_drop_320'] = t2

    if key == 'all':
        return xs, possible_data
    else:
        return xs, possible_data[key]


low_lake_groups = ('low_wide', 'shift', 'low_amp', 'low_wid_amp', 'lake_drop')


def plot_possible_hds(save=False):
    from model_build.utils import get_colors
    xs, data = get_lake_hds('all')

    for kg in low_lake_groups:
        save_path = proj_root.joinpath(f'Scenarios/boundary_condition_plots/low_lake_hds_{kg}.png')
        use_keys = ['base'] + [k for k in data.keys() if kg in k]
        colors = get_colors(use_keys)
        fig, ax = plt.subplots(figsize=(14, 14))

        for c, k in zip(colors, use_keys):
            v = data[k]
            if 'lake_drop' in k:
                xs = range(len(v))
            ax.plot(xs, v, color=c, label=k)
        ax.set_xlabel('ISO week')
        ax.set_ylabel('lake head')
        ax.legend()
        ax.set_title(kg)
        fig.tight_layout()
        if save:
            fig.savefig(save_path)
    if not save:
        plt.show()


def print_myself(key):
    print(f'{inspect.stack()[1][3]}: {key}')


low_lake_years = 3
start = '2001-01-1'
base_time = pd.date_range(start, periods=52 * low_lake_years, freq='W')
indates = [(base_time.min(), base_time.max() + datetime.timedelta(days=6))]
indates.extend(zip(base_time, base_time + datetime.timedelta(days=6)))

steady = [True] + [False for e in base_time]
nper = len(base_time) + 1  # one steady stated period and then the transient period

low_lake_tdis = TimeDis(
    name='low_lake',
    nper=nper,
    tsmult=1.2,
    steady=steady,
    dates=indates,
    nstp=[1 if e else 7 for e in steady],
    tunit='day',
    check_dates_in_order=False
)
low_lake_tdis.perlen[0] = 1  # manually set first stress period to length of 1
pass


def run_low_lake_scenario(key, base_run_dir, base_outdir, build_run_model=True, process_results=True,
                          plot=False, rerun=False):
    print_myself(key)
    model_ws = base_run_dir.joinpath(key)
    if model_ws.exists() and not rerun:
        build_run_model = False
    kh_param, sy_param, riv_params, hill_param, race_param, rch_param = get_3d_v1d_params()

    str_vals = low_lake_tdis.make_spd_steady(get_scen_str_data(scen_tdis, riv_params,
                                                               big_static=True, small_static=True),
                                             mismatch_keys='warn')
    rch = low_lake_tdis.make_spd_steady(get_scen_rch(scen_tdis, rch_param, dryland=False), mismatch_keys='warn')
    wel_data = low_lake_tdis.make_spd_steady(get_scen_well_data('static_pump', scen_tdis,
                                                                hill_param, race_param, False), mismatch_keys='warn')
    lake = low_lake_tdis.make_spd_steady(get_scen_ghb_data(scen_tdis), mismatch_keys='warn')
    xs, usehds = get_lake_hds(key)
    if len(usehds) == 52:
        usehds = np.concatenate([[usehds.mean()]] +
                                [usehds for e in range(low_lake_years)]
                                )
    elif len(usehds) == 52 * low_lake_years + 1:
        pass
    else:
        raise NotImplementedError
    for p, lh in enumerate(usehds):
        if lh < l2_top:
            temp = lake[p]
            temp = temp[temp['k'] > 1]
            temp['bhead'] = lh
            lake[p] = temp

        elif lh < bund_top:
            temp = lake[p]
            temp = temp[temp['k'] > 0]
            temp['bhead'] = lh
            lake[p] = temp
        else:
            lake[p]['bhead'] = lh

    if plot:
        from model_tools.model_plotting import plot_spd # keynote private repo
        from model_build.project_model_tools import smt
        plot_spd(lake, smt=smt, tdis=low_lake_tdis, func=np.nansum, key='bhead', title='lake head', tick_per=1,
                 show=True)

    run_scenario(model_name=key, model_ws=model_ws,
                 tdis=low_lake_tdis,
                 sy_param=sy_param,
                 kh_param=kh_param,
                 rch_data=rch,
                 ghb_spd=lake,
                 str_spd=str_vals,
                 well_spd=wel_data,
                 outdir=base_outdir.joinpath(key),
                 build_run_model=build_run_model, process_results=process_results,
                 tickper=8,save_hds=False, plot_data=False)


def try_run_all(rerun=False, subset=None):
    base_run_dir = unbacked_dir.joinpath('low_lake_scenarios')
    base_run_dir.mkdir(exist_ok=True)
    base_outdir = proj_root.joinpath('Scenarios/low_lake_scenarios')
    base_outdir.mkdir(exist_ok=True)
    x, hds = get_lake_hds('all')
    scens = list(hds.keys())
    with open(base_run_dir.joinpath(f'log_{datetime.datetime.now().isoformat()}.txt'), 'w') as f:
        for scen in scens:
            if subset is not None:
                if scen not in subset:
                    continue
            f.write(f'\n\nstarting {scen}\n')
            try:
                run_low_lake_scenario(scen,
                                      base_run_dir, base_outdir,
                                      build_run_model=True, process_results=True,
                                      plot=False, rerun=rerun)
                f.write(f'{scen} presumed successful\n')
            except Exception:
                f.write(f'{scen} failed\n')
                t = traceback.format_exc()
                f.write(t)
                f.write('\n')


if __name__ == '__main__':
    plot_possible_hds(True)
    try_run_all(rerun=False)
