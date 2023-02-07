"""
created matt_dumont 
on: 2/02/23
"""
from pathlib import Path

import flopy.utils
import matplotlib.pyplot as plt
import pandas as pd
from optimisation.manual_optimisations.manual_optimisation import base_regular_groupnames, tdis, get_colors, \
    _plot_regular
from model_build.project_model_tools import smt
from fpdf import FPDF
from PIL import Image


def _plot_high_freq_heads(all_obs_files, names, plot_dir):
    plot_dir.mkdir(exist_ok=True)
    regular_hds = {}
    success = {}
    # read in all of the regualr heads
    for f, name in zip(all_obs_files, names):
        f = Path(f)
        success[name] = True
        if '.rei' in f.name:
            hds_obs = pd.read_csv(f, delim_whitespace=True, skiprows=4)
            hds_obs = hds_obs.rename(columns={n: n.lower() for n in hds_obs.columns})
        else:
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

        regular_hds[name] = hds_obs

    scens = sorted(list(regular_hds.keys()))
    scen_cmap = 'tab20'
    colors = get_colors(scens, scen_cmap)

    reg_colormap = 'tab10'
    regular_wells = sorted(regular_hds[scens[0]].well_name.unique())
    regular_colors = get_colors(regular_wells, reg_colormap)
    # plotting
    for n, nc in zip(regular_wells, regular_colors):
        # full dataset
        _plot_regular(scens, 1000, colors, n, success, regular_hds, nc, plot_dir)


def make_opt_preso(outdir, pst_dir, all_obs_files, names):
    """
    make pdf for showing plots
    :param outdir:  directory to save to
    :param pst_dir: main optimsiation
    :param all_obs_files: all of the .dat files for various pest runs
    :param names: names fo rthe all .dat files to use as lables
    :return:
    """
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    pst_dir = Path(pst_dir)

    _plot_high_freq_heads(all_obs_files, names, outdir)

    filelist = [
        # big picture
        pst_dir.joinpath('jacobian_filled_0_of_1.png'),
        pst_dir.joinpath('final_opt_model/Steady_state_heads_(Hawea_aquifer).png'),
        pst_dir.joinpath('final_opt_model/3d_hds.png'),
        pst_dir.joinpath('final_opt_model/SS_budget.png'),

        # heads
        # modelled v measured
        pst_dir.joinpath('final_opt_model/hds_all_mod_v_meas.png'),
        pst_dir.joinpath('final_opt_model/hds_regular_mod_v_meas.png'),
        pst_dir.joinpath('final_opt_model/hds_h_piezo_mod_v_meas.png'),
        pst_dir.joinpath('final_opt_model/hds_h_single_3_mod_v_meas.png'),
        pst_dir.joinpath('final_opt_model/hds_h_single_1_mod_v_meas.png'),

        # high frequency
        outdir.joinpath('hds_closeup_h_g40_0415_0000.png'),
        outdir.joinpath('hds_closeup_h_g40_0041_0000.png'),
        outdir.joinpath('hds_closeup_h_g40_0416_0000.png'),
        outdir.joinpath('hds_closeup_h_g40_0129_0000.png'),
        outdir.joinpath('hds_closeup_h_g40_0120_0000.png'),
        outdir.joinpath('hds_closeup_h_g40_0367_0000.png'),
        outdir.joinpath('hds_closeup_h_g40_0366_0000.png'),

        # spatial heads
        pst_dir.joinpath('final_opt_model/spatial_hds/spatial_hds_residual_all.png'),
        pst_dir.joinpath('final_opt_model/spatial_hds/spatial_hds_residual_single.png'),
        pst_dir.joinpath('final_opt_model/spatial_hds/spatial_hds_residual_regular.png'),
        pst_dir.joinpath('final_opt_model/spatial_hds/spatial_hds_residual_piezo.png'),

        # rivers
        pst_dir.joinpath('final_opt_model/spatial_riv/riv_mean.png'),
        pst_dir.joinpath('final_opt_model/all_riv_targets_mes_mod.png'),

        # parameters
        pst_dir.joinpath('kh_array.png'),
        pst_dir.joinpath('hk_values.png'),
        pst_dir.joinpath('sy_array.png'),
        pst_dir.joinpath('sy_values.png'),

    ]

    # todo join into pdf

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    # imagelist is the list with all image filenames
    for image in filelist:
        image = str(image)
        cover = Image.open(image)
        width, height = cover.size
        width, height = float(width * 0.264583), float(height * 0.264583)
        scale = min(pdf.h / height, pdf.w / width)

        pdf.add_page()
        pdf.image(image, 0, 0, width * scale, height * scale)
    pdf.output(name=str(outdir.joinpath("opt_review.pdf")), dest="F")


def plot_saturated_thickenss():
    bot = smt.get_bottoms()[-1]
    top = smt.get_tops()[0]
    # hds = flopy.utils.HeadFile(
    #    '/home/matt_dumont/unbacked/hawea/3d_v1a/init2_3d_v1a/Optimisations/Final_opt_model/final_opt_model.hds'
    # ).get_alldata()[0]
    # idx = (top > hds[0]) & (hds[0] > 0)
    # top[idx] = hds[0][idx]
    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10, 8), sharex=True, sharey=True)
    smt.plot.plt_matrix(top - bot, no_flow_layer=0, base_map=True, contour=True, contour_levels=10, label_contours=True,
                        ax=ax1)
    smt.plot.plt_matrix(top, no_flow_layer=0, base_map=True, contour=True, contour_levels=10, label_contours=True,
                        ax=ax2)
    ax1.set_title('thickness')
    ax2.set_title('top')
    ax1.set_xlim((1.302e6, 1.308e6))
    ax1.set_ylim((5.046e6, 5.054e6))
    fig.tight_layout()

    pass


if __name__ == '__main__':
    pass
    #plot_saturated_thickenss()

    make_opt_preso(outdir='/home/matt_dumont/PycharmProjects/Z22031HAW_hawea-model/optimisation/optimisation_results',
                   pst_dir=Path.home().joinpath('unbacked/hawea',
                                                '3d_v1d',
                                                'init_3d_v1d',
                                                'Optimisations', 'Base_Optimisation_plots'),
                   all_obs_files=[
                       '/home/matt_dumont/unbacked/hawea/3d_v1a/init2_3d_v1a/Optimisations/Final_opt_model/observations.dat',
                       '/home/matt_dumont/unbacked/hawea/3d_v1b/init_3d_v1b/Optimisations/Final_opt_model/observations.dat',
                       '/home/matt_dumont/unbacked/hawea/3d_v1d/init_3d_v1d/Optimisations/Final_opt_model/observations.dat'
                   ],
                   names=[
                       '3d_v1a',
                       '3d_v1b',
                       '3d_v1d',
                   ]
                   )

    # todo add 3d_v1d newer if possible
