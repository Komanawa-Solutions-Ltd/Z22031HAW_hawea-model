"""
created matt_dumont 
on: 25/11/22
"""
from pathlib import Path
from model_build.project_model_tools import smt
from copy import deepcopy
import matplotlib.pyplot as plt
import pandas as pd
from targets_and_sensitive_sites.model_output import process_model_output, plot_hds_regular_locator, \
    base_regular_groupnames
from optimisation.model_utils_for_forward_run import build_run_model
from model_parameterisation.inital_parametersiation import *
from optimisation.optimisation_period import tdis
from model_build.utils import get_colors
import matplotlib.gridspec as gridspec
from run_managers.ssh_distributor import SshDist
from project_base import unbacked_dir
from optimisation.a_build_run_optimisation_version import opt_model_tools, opt_proj_root, branch

base_opt_dirs = unbacked_dir.joinpath('manual')

ssh_dist = SshDist(
    base_path={
        '100.124.148.71': base_opt_dirs,
        '100.121.150.68': Path('/media/matt_dumont/data/mh_unbacked/hawea').joinpath(
            base_opt_dirs.relative_to(unbacked_dir))
    },
    ips=['100.124.148.71',
         '100.121.150.68'],
    script_path=opt_proj_root.joinpath('optimisation/manual_optimisations/run_manual_opt.py'),
    conda_env='hawea',
    num_cores={
        '100.124.148.71': 8,
        '100.121.150.68': None,
    },
    core_weigtings={
        '100.124.148.71': 2.6675381999814873,
        '100.121.150.68': 1.0},
    user_names=None,
    short_names=None,
    prepend_bash_commands={
        '100.124.148.71': [
            f"cd {opt_model_tools} ; git fetch --all ; git reset --hard origin/Z22031HAW_hawea-model",
            f"cd {opt_proj_root} ; git fetch --all ; git reset --hard origin/{branch}"
        ],
        '100.121.150.68': [
            f"cd {opt_model_tools} ; git fetch --all ; git reset --hard origin/Z22031HAW_hawea-model",
            f"cd {opt_proj_root} ; git fetch --all ; git reset --hard origin/{branch}"
        ]},
    use_tailscale=True,
    python_paths=[opt_proj_root, opt_model_tools],
    sys_paths="default"
)


def _run_model_mp(kwargs):
    try:
        manual_opt(**kwargs)
        success = True
        error = 'None'
    except Exception as val:
        success = False
        error = val
    return kwargs, success, error


def manual_opt(mod_params, model_name, base_dir, re_run=False, remove_unneccisary=True):
    assert isinstance(base_dir, Path)
    model_ws = base_dir.joinpath(model_name)
    run_model = True
    listfile = model_ws.joinpath(f'{model_name}.list')
    if not re_run and listfile.exists():
        if smt.modelchecks.modflow_converged(listfile):
            run_model = False

    if run_model:
        kh_param, sy_param, riv_params, hill_param, race_param, rch_param = mod_params
        print(f'building and running {model_name}')
        build_run_model(
            model_name=model_name, model_ws=model_ws,
            kh_param=kh_param,
            sy_param=sy_param,
            riv_params=riv_params,
            hill_param=hill_param,
            race_param=race_param,
            rch_param=rch_param
        )

    print(f'processing output for: {model_name}')
    process_model_output(model_ws=model_ws,
                         hds_file=model_ws.joinpath(f'{model_name}.hds'),
                         plot=False, savelist=False, save_param=False, run_if_unconverged=True,
                         plot_failures=False)
    if remove_unneccisary:
        files = Path(model_ws).glob('**/*.*')
        for p in files:
            if p.is_dir():
                continue
            if p.name.split('.')[-1] in ['list', 'dat', 'png', 'p', 'log']:
                continue
            if p.name in ['param_overview.txt', 'mse.csv']:
                continue


# todo abstract and save

def run_manal_opt(name, mod_params, safemode=True, replot=False):
    """
    plan is to send in runs (via mod params), it then runs everything, makes necissary plots, and plots up key values
    :param opt_dir
    :param mod_params:
    :param safemode: bool, if True then raise exception if the optdir exists
    :return:
    """
    opt_dir = base_opt_dirs.joinpath(name)
    assert isinstance(opt_dir, Path)

    mod_params = np.atleast_1d(mod_params)

    all_mod_keys = []
    for m in mod_params:
        all_mod_keys.extend(m.keys())
    sen_names = ['base'] + [f'sen_{i:04d}' for i in range(len(mod_params))]
    overview_data = pd.DataFrame(index=pd.unique(all_mod_keys), columns=sen_names)

    kh_param = get_inital_kh(True)
    sy_param = get_inital_sy(True)
    riv_params = get_initial_riv_conductance(True)
    hill_param = get_hillslope_multiplier(True)
    race_param = get_race_multiplier(True)
    rch_param = get_initial_rch_mult(True)
    all_params = (kh_param, sy_param, riv_params, hill_param, race_param, rch_param)
    tags = ['kh', 'sy', 'riv', 'hill', 'race', 'rch']
    base_pdict = {t: deepcopy(p) for t, p in zip(tags, all_params)}
    for k in overview_data.index:
        tag = k.split('_')[0]
        pname = '_'.join(k.split('_')[1:])
        v = base_pdict.get(tag)
        if v is not None:
            v = v.get(pname)
        overview_data.loc[k, :] = v

    runs = []
    # setup base model
    runs.append({'model_name': 'base', 'base_dir': '', 'mod_params': [base_pdict[t] for t in tags]})

    # setup manual calibration models
    for i, single_mod_params in enumerate(mod_params):
        pdict = deepcopy(base_pdict)

        bulk_keys = [e for e in single_mod_params.keys() if 'bulk_' in e]  # todo add terrace vs bulk
        if len(bulk_keys) > 0:
            for k in bulk_keys:
                val = single_mod_params.pop(k)
                tag = k.split('_')[-1]
                overview_data.loc[k, f'sen_{i:04d}'] = val
                for pr in pdict[tag].keys():
                    if 'ter' in pr:
                        continue
                    pdict[tag][pr] = val

        bulk_ter_keys = [e for e in single_mod_params.keys() if 'bulkter_' in e]
        if len(bulk_ter_keys) > 0:
            for k in bulk_ter_keys:
                val = single_mod_params.pop(k)
                tag = k.split('_')[-1]
                overview_data.loc[k, f'sen_{i:04d}'] = val
                for pr in pdict[tag].keys():
                    if 'ter' not in pr:
                        continue
                    pdict[tag][pr] = val

        for k, v in single_mod_params.items():
            overview_data.loc[k, f'sen_{i:04d}'] = v
            tag = k.split('_')[0]
            pname = '_'.join(k.split('_')[1:])
            pdict[tag][pname] = v
        runs.append({'model_name': f'sen_{i:04d}', 'base_dir': '', 'mod_params': [pdict[t] for t in tags]})

    # run all models
    opt_dir.mkdir(exist_ok=not safemode or replot, parents=True)
    if not replot:
        print(f'running {len(runs)} models')
        ssh_dist.distribute_runs(run_name=name, runs=runs, rm_remote_files=True, run=True, compile=True,
                                 run_in_series=False, kwargs_relative_to_base_dir=['base_dir'])

    # write overview of changed parameters
    with open(opt_dir.joinpath('param_overview.txt'), 'w') as f:
        f.write(f'{opt_dir.name}\n'
                f'{opt_dir}\n\n')
        f.write(overview_data.transpose().to_string())
    # plot the results
    print('plotting')
    _plot_high_freq_heads(opt_dir, opt_dir.joinpath('0_plots'))


def _plot_success_fail(success, plot_dir):
    names = np.array(list(success.keys()))
    conv = np.array([success[k] for k in names])
    xs = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.scatter(xs[conv], np.ones(conv.sum()), color='blue', label='converged')
    ax.scatter(xs[~conv], np.zeros((~conv).sum()), color='red', label='converged')

    ax.legend()
    ax.set_xticks(xs)
    ax.set_xticklabels(names, rotation=-90)
    ax.set_title('converged')
    fig.tight_layout()
    fig.savefig(plot_dir.joinpath('0_converged.png'))


def _plot_high_freq_heads(opt_dir, plot_dir):
    max_per_fig = 10
    plot_dir.mkdir(exist_ok=True)
    regular_hds = {}
    success = {}
    all_obs_files = sorted(list(opt_dir.glob('**/observations.dat')))
    # read in all of the regualr heads
    for f in all_obs_files:
        lf = f.parent.joinpath(f'{f.parent.name}.list')
        i = f.parent.name
        success[i] = smt.modelchecks.modflow_converged(lf)
        hds_obs = pd.read_csv(f, sep='\t', skiprows=0)
        hds_obs.rename(columns={e: e.lower() for e in hds_obs.keys()}, inplace=True)
        hds_obs.loc[:, 'modelled'] = pd.to_numeric(hds_obs.loc[:, 'modelled'], 'coerce')
        hds_obs.loc[:, 'measured'] = pd.to_numeric(hds_obs.loc[:, 'measured'], 'coerce')
        mapper = {'h_piezo': 'h_piezo',
                  'h_single_3': 'h_single_3',
                  'h_single_1': 'h_single_1'}
        mapper.update({k: 'regular' for k in base_regular_groupnames})
        hds_obs.loc[:, 'group'] = hds_obs.loc[:, 'group'].replace(mapper)
        hds_obs.loc[:, 'well_name'] = [f'{"_".join(e.split("_")[:-1])}' for e in hds_obs.loc[:, 'name']]
        hds_obs = hds_obs.loc[hds_obs.loc[:, 'group'] == 'regular']
        hds_obs.loc[:, 'nper'] = hds_obs.name.str.split('_').str.get(-1).astype(int)
        hds_obs.loc[:, 'date'] = tdis.get_date(hds_obs.loc[:, 'nper'])
        hds_obs.loc[:, 'week'] = hds_obs.date.dt.isocalendar().loc[:, 'week']

        regular_hds[i] = hds_obs

    scens = sorted(list(regular_hds.keys()))
    scen_cmap = 'tab20'
    colors = get_colors(scens, scen_cmap)

    reg_colormap = 'tab10'
    regular_wells = sorted(regular_hds[scens[0]].well_name.unique())
    regular_colors = get_colors(regular_wells, reg_colormap)
    # plotting
    for n, nc in zip(regular_wells, regular_colors):
        # full dataset
        _rank_best_shape_fit(regular_hds, n, nc, max_per_fig, success, opt_dir)
        _plot_regular(scens, max_per_fig, colors, n, success, regular_hds, nc, plot_dir)
    _plot_success_fail(success, plot_dir)


def _plot_regular(scens, max_per_fig, colors, well_name, success, regular_hds, well_color, plot_dir):
    plot_dir.mkdir(exist_ok=True)
    num_figs = len(scens) // max_per_fig
    if len(scens) > num_figs * max_per_fig:
        num_figs += 1
    for figi in range(num_figs):
        use_scens = scens[figi * max_per_fig: (figi + 1) * max_per_fig]
        use_colors = colors[figi * max_per_fig: (figi + 1) * max_per_fig]
        fig = plt.figure(figsize=(14, 9))
        gs = gridspec.GridSpec(2, 2, width_ratios=(2, 1), height_ratios=(3, 1))
        ax = fig.add_subplot(gs[0, 0])
        ax_lake = fig.add_subplot(gs[1, 0])

        ax_loc = fig.add_subplot(gs[0, 1])
        ax_leg = fig.add_subplot(gs[1, 1])
        for i, (k, c) in enumerate(zip(use_scens, use_colors)):
            if not success[k]:
                lab = f'{k} (failed)'
            else:
                lab = k
            temp2 = regular_hds[k].loc[regular_hds[k].well_name == well_name].sort_values('date')
            ax.plot(temp2.date, temp2.modelled, color=c, label=lab)

            # add text label
            if i % 2 == 0:
                idx = -1
            else:
                idx = 0

            t = temp2.dropna()
            if not t.empty:
                ax.text(t.date.values[idx], t.modelled.values[idx], k, color=c)

        ax.scatter(temp2.date, temp2.measured, color=well_color, label=f'{well_name.capitalize()} measured')
        ax.plot([temp2.date.iloc[0]], [temp2.modelled.iloc[0]], color=well_color,
                label=f'{well_name.capitalize()} modelled')

        from model_build.supporting_data_analysis import get_lake_heads
        lake = get_lake_heads(temp2.date.min(), temp2.date.max())
        ax_lake.plot(lake.index, lake, label='lake heads')
        ax_lake.set_ylabel('lake heads (m)')
        ax_lake.set_xlim(ax.get_xlim())
        ax.set_xticks([])
        ax.set_xticklabels([])
        ax.set_xlabel('')

        plot_hds_regular_locator(ax_loc, {well_name: well_color})
        ax.set_title(f'{well_name.capitalize()} hds {figi + 1} of {num_figs}')
        ax.set_xlabel('Date')
        ax.set_ylabel('Weekly mean Head (m)')
        ax_leg.legend(*ax.get_legend_handles_labels())
        ax_leg.set_xticks([])
        ax_leg.set_yticks([])

        # kill frame around ax..
        ax_leg.spines["top"].set_visible(False)
        ax_leg.spines["right"].set_visible(False)
        ax_leg.spines["left"].set_visible(False)
        ax_leg.spines["bottom"].set_visible(False)
        fig.tight_layout()
        fig.savefig(plot_dir.joinpath(f'hds_closeup_{well_name}_{figi:04d}.png'))
        plt.close(fig)


def _rank_best_shape_fit(regular_hds, well_name, well_color, max_per_fig, success, opt_dir):
    assert isinstance(opt_dir, Path)
    mse = _calc_shape_fit_mse(regular_hds, well_name)
    _add_params(mse, param_path=opt_dir.joinpath('param_overview.txt'))
    mse.loc[:, 'success'] = [success.get(e) for e in mse.index]
    mse.to_csv(opt_dir.joinpath(f'{well_name}_mse.csv'))
    num_plot = 20
    for k in ['shape_mse', 'mse', 'joint_mse']:
        scens = mse.sort_values(k).index
        scens = [e for e in scens if success[e]]
        if len(scens) > num_plot:
            scens = scens[0:num_plot]
        _plot_regular(scens=scens, max_per_fig=max_per_fig,
                      colors=get_colors(range(num_plot)), well_name=well_name,
                      success=success, regular_hds=regular_hds, well_color=well_color,
                      plot_dir=opt_dir.joinpath(f'0_{k}_plots'))


def _add_params(df, param_path):
    temp = pd.read_csv(param_path, index_col=0,
                       skiprows=3, delim_whitespace=True)
    for k in temp.columns:
        df.loc[:, k] = temp.loc[df.index, k]


def _calc_shape_fit_mse(regular_hds, wellname):
    assert isinstance(regular_hds, dict)
    outdata = pd.DataFrame(index=regular_hds.keys(), columns=['shape_mse', 'mse'])
    for k, v in regular_hds.items():
        temp2 = v.loc[v.well_name == wellname].sort_values('date').copy(deep=True)
        mse = ((temp2.loc[:, 'measured'] - temp2.loc[:, 'modelled']) ** 2).sum()
        outdata.loc[k, 'mse'] = mse
        temp2.loc[:, 'modelled'] += -temp2['modelled'].min()
        temp2.loc[:, 'measured'] += -temp2['measured'].min()
        mse = ((temp2.loc[:, 'measured'] - temp2.loc[:, 'modelled']) ** 2).sum()
        outdata.loc[k, 'shape_mse'] = mse
    outdata.loc[:, 'joint_mse'] = outdata.loc[:, ['shape_mse', 'mse']].mean(axis=1)
    return outdata
