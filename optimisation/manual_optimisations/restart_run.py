"""
created matt_dumont 
on: 4/12/22
"""
from manual_optimisation import ssh_dist, _plot_high_freq_heads, _plot_success_fail, base_opt_dirs
from optimisation.a_build_run_optimisation_version import branch

if __name__ == '__main__':
    run_name = 'lake_kh_sy'
    re_run = False
    re_plot = True


    name = f'{branch}_{run_name}'
    if re_run:
        ssh_dist.restart_runs(run_name=name, rm_remote_files=False)
    if re_plot:
        print('plotting')
        opt_dir = base_opt_dirs.joinpath(name)
        _plot_high_freq_heads(opt_dir, opt_dir.joinpath('0_plots'))
        _plot_success_fail(opt_dir, opt_dir.joinpath('0_plots'))
