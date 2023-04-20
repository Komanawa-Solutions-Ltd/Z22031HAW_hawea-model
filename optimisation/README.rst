Hawea Transient groundwater model (Hawea Model) build optimisation and results
############################################################################

.. figure:: ../support_figures/model_2d_boundary_conditions.png # todo replace 
   :height: 650 px
   :align: center

.. class::

    *Figure: Overview of model boundary conditions*

# todo mash up of these:
optimisation/optimisation_results/3d_v1d/Base_Optimisation_plots/obs_plots/residual_h_hf.png
optimisation/optimisation_results/3d_v1d/Base_Optimisation_plots/obs_plots/phi_plot.png
optimisation/optimisation_results/3d_v1d/Base_Optimisation_plots/regular_hds_closeup/hds_closeup_h_g40_0415.png

:Author:  Matt Dumont
:Date:  2021-11-02
:Version:  1.0.0
:Status:  Draft
:KSL project: Z22031HAW_hawea-model
:Purpose: This document provides the methodology and results for the model optimisation process and discusses the model limitations


Index
=====
.. contents:: Table of Contents


Module Index
============
-  `README.rst <../optimisation/README.rst>`_: readme document detailing the optimization process and methodology
-  Pest optimisation build, run, and post processing scripts
    -  `build_optimisation.py <../optimisation/build_optimisation.py>`_: script and functions to build the pest files
    -  `a_build_run_optimisation_version.py <../optimisation/a_build_run_optimisation_version.py>`_: build and run a pest optimisation
    -  `run_opt_step_models.py <../optimisation/run_opt_step_models.py>`_:  run the step models from a pest optimisation
    -  `manual_optimisations <../optimisation/manual_optimisations>`_:  manual optimisations that were run, in the end these never contributed more than some information to the modeller
    -  `model_utils_for_forward_run.py <../optimisation/model_utils_for_forward_run.py>`_: functions to build and run a model from pest parameter files
    -  `compare_parameterisations.py <../optimisation/compare_parameterisations.py>`_: script to compare parameters across multiple parameter files
    -  `hawea_plot_optimisation.py <../optimisation/hawea_plot_optimisation.py>`_: script to plot the optimisation results
    -  `plot_multiple_high_freq.py <../optimisation/plot_multiple_high_freq.py>`_: script to plot multiple high frequency observations for given pest obs files
-  Manage optimisation period:
    -  `determine_opt_start.py <../optimisation/determine_opt_start.py>`_: script to determine the start and end of the optimisation period
    -  `optimisation_period.py <../optimisation/optimisation_period.py>`_: script to manage and hold the information about the optimisation period
-  Optimisation Results
    -  `optimisation_results <../optimisation/optimisation_results>`_: results for the optimisation holding all of the pest input and output files
        -  `3d_v1a <../optimisation/optimisation_results/3d_v1a>`_:  optimisation results for the 3d model version 1a
        -  `3d_v1b <../optimisation/optimisation_results/3d_v1b>`_:  optimisation results for the 3d model version 1b
        -  `3d_v1d <../optimisation/optimisation_results/3d_v1d>`_:  optimisation results for the 3d model version 1d (final model)
    -  `final_opt_models <../optimisation/final_opt_models>`_:  The final optimised model files
        -  `3d_v1a <../optimisation/final_opt_models/3d_v1a>`_: final optimised model files for the 3d model version 1a
        -  `3d_v1b <../optimisation/final_opt_models/3d_v1b>`_: final optimised model files for the 3d model version 1b
        -  `3d_v1d <../optimisation/final_opt_models/3d_v1d>`_: final optimised model files for the 3d model version 1d (final model)
        -  `compress_uncompress_model.py <../optimisation/final_opt_models/compress_uncompress_model.py>`_:  utilities to compress and uncompress the model files so they could be included in the git repo (50mb limit)
-  computational support files
    -  `compile_pest <../optimisation/compile_pest>`_: compile pest for linux
    -  `pest_run_data <../optimisation/pest_run_data>`_: static data needed by pest to run the model
    -  `git_setup.sh <../optimisation/git_setup.sh>`_: script to setup the git repo for the optimisation on a machine
- Model overview
    -  `pre_optimisation_overview.py <../optimisation/pre_optimisation_overview.py>`_: make a pre optimisation overview plots
    -  `make_preopt_slideshow.py <../optimisation/make_preopt_slideshow.py>`_: make a pre optimisation slideshow
    -  `pre_optimisation_plots_png <../optimisation/pre_optimisation_plots_png>`_: pre optimisation plots of boundary conditions, targets, parameterization, and other supporting work, many of these figures are referenced in the various readme.rst files
    -  `make_opt_presentation.py <../optimisation/make_opt_presentation.py>`_: make a presentation of the optimisation results for a meeting


Optimisation overview
=====================

The optimisation process involved changing group weightings, parameter bounds, and the model structure. This chaotic
process is typical in model optimisation and is typically very difficult to follow for anyone other than the primary
modeller.  to try and make this process more transparent and to provide a record of the process, we created a new git
branch for each optimisation version.  This allowed us to track the changes to the model, reproduce and archive all of
the key input data with any changes.  To reduce the size of the github repo we deleted all of the abandoned branches,
but we produced a github release for each abandoned branch so that the data could be recovered if needed.

Broadly speaking there were 3 main stages to the optimisation process:

#. A 1 layer model (2d)
#. Specific sub model (2d) to test whether or not the terrace observations could be fit by
   disconnecting the terrace from the main model
#. A 3 layer model (3d)

Optimisation setup / PEST structure
===================================
The model was optimised via `PEST <http://www.pesthomepage.org/>`_ which is a model calibration and optimisation package.
the interface to the model was handled via `flopy <https://flopy.readthedocs.io/en/3.3.2/introduction.html>`_
which is a python package for working with MODFLOW models and `pyemu <https://pyemu.readthedocs.io/en/develop/pyemu.html>`_
which is a python package for working with PEST models. The pest iterations were run in parallel on a cluster
of linux machines using `Beopest <https://www.prinmath.com/pest/>`_ which is a subpackage of PEST. Beopest was managed
via an in house class called BeopestManager.  In addition some manual optimisation were undertaken in the course of
the optimisation process to better understand the limits of specific model structures.  These manual optimisations were
undertaken using another in house class called SshDist. The main optimisation script was
`a_build_run_optimisation_version.py <../optimisation/a_build_run_optimisation_version.py>`_

The build of the PEST runfile was undertaken in `build_optimisation.py <../optimisation/build_optimisation.py>`_.
which has a number of component functions:
- `raw_pest <../optimisation/build_optimisation.py#L251>`_:
   - Overarching function to build the pest runfile (calls the following functions).
   - Also handles the singular value decomposition (SVD) parameters.
- `make_template_and_infiles <../optimisation/build_optimisation.py#L37>`_:
   - make the template and in infiles for pest to interact with the model parameter inputs.
- `make_ins_and_output_files <../optimisation/build_optimisation.py#L50>`_:
   - make an example output files (model outputs) and the PEST instruction files to read the model output data (targets).
- `set_control_data <../optimisation/build_optimisation.py#L69>`_:
   - set the control data for the PEST runfile.
- `set_parameter_data_groups <../optimisation/build_optimisation.py#L145>`_:
   - set parameter data groups, limits, transformations, and derivative handling.
- `set_obs_data <../optimisation/build_optimisation.py#L190>`_:
   - set the observation data, weights, and GROUP WEIGHTINGS.

# todo modes for PEST (key control and svd data)

Standard optimisation outputs
=============================

For each optimisation version we produced a number of standard outputs that are consistent cross each optimisation
results.  We detail them here so that individuals can have easy access to the key outputs.

The output structure is as follows:

-  Base_Optimisation_plots:
    -  final_opt_model: plots of the final optimised model including the parameterisation, model heads, and the model
       fits to the observations
            -  cross_sections
            -  spatial_hds
            -  spatial_riv
            -  str_flow
            -  3d_hds.png: plot of heads in the 3d zone
            -  Max_heads_(Hawea_aquifer).png: minimum heads across
            -  Min_heads_(Hawea_aquifer).png
            -  Range_of_Heads_(Hawea_aquifer).png
            -  SS_budget.png
            -  Steady_state_heads_(Hawea_aquifer).png
            -  all_riv_targets_mes_mod.png
            -  all_riv_targets_residual.png
            -  all_river_fluxes_hill.png
            -  all_river_fluxes_large.png
            -  dry_cells_l0.png
            -  dry_cells_l1.png
            -  dry_cells_l2.png
            -  flooded_cells_l0.png
            -  flooded_cells_l1.png
            -  flooded_cells_l2.png
            -  hds_all_mod_v_meas.png
            -  hds_all_residual_time.png
            -  hds_closeup_h_g40_0041.png
            -  hds_closeup_h_g40_0120.png
            -  hds_closeup_h_g40_0129.png
            -  hds_closeup_h_g40_0366.png
            -  hds_closeup_h_g40_0367.png
            -  hds_closeup_h_g40_0415.png
            -  hds_closeup_h_g40_0416.png
            -  hds_h_piezo_mod_v_meas.png
            -  hds_h_piezo_residual_time.png
            -  hds_h_single_1_mod_v_meas.png
            -  hds_h_single_1_residual_time.png
            -  hds_h_single_3_mod_v_meas.png
            -  hds_h_single_3_residual_time.png
            -  hds_normal_year_all.png
            -  hds_normal_year_mod_v_meas.png
            -  hds_regular_mod_v_meas.png
            -  hds_regular_residual_time.png
            -  hds_regyear_h_g40_0041.png
            -  hds_regyear_h_g40_0366.png
            -  hds_regyear_h_g40_0367.png
            -  hds_regyear_h_g40_0415.png
            -  hds_regyear_h_g40_0416.png
            -  more_than_100_outers.png
            -  more_than_300_outers.png
            -  more_than_500_outers.png
            -  more_than_50_outers.png
            -  more_than_800_outers.png



    -  regular_hds_closeup: plots of changes in the fit to the regular observations (e.g. high frequency) through
       the optimisation process (e.g. at each optimisation step).
    -  obs_plots: plots of the model objective function and target residuals through the optimisation process (e.g. at
       each optimisation step).
    -  param_plots: plots of parameter values through the optimisation process (e.g. at each optimisation step).
    -  param_fail_plots: plots of parameter values that failed to converge vs those that did not.
    -  param_sen_plots: plots of parameter sensitivity through the optimisation process (e.g. at each optimisation step).
    -  parameters_norm_to_bounds.txt: a text file of the parameter values of the final model normalised to the parameter bounds.
    -  parameters_norm_to_bounds_close.txt: as above, but only those that are close to their bounds.
    -  parameter_norm_sy_kh.png: ignore, bug in plot
    -  jacobian_filled_0_of_1.png: plots of whether or not the Jacobian was filled (red values had model failure)
    -  hk_values.png: plot of the final hk parameter values at the pilot points.
    -  kh_array.png: plot of the interpolated final kh parameter values.
    -  sy_values.png: plot of the final sy parameter values at the pilot points.
    -  sy_array.png: plot of the interpolated final sy parameter values.

# todo
1 layer model (2D) optimisation
===============================
# todo
Terrace only model (2D) optimisation
====================================
# todo

3 layer model (3D) optimisation
===============================
# todo
3D_v1a
-------
# todo
3D_v1b
-------
# todo

3D_v1d (final model)
---------------------
# todo

Access to final optimised parameter sets and models
===================================================
# todo

Model limitations
=================
# todo

Recommended additional data
==========================

Optimisation working Notes
==========================

These working notes are largely verbatim except that the active branches are elevated above the abandoned branches.
the number indicates the order in which the branches were developed.


Active Branches (optimisation versions)
---------------------------------------

25. Main (3d_v1d)
~~~~~~~~~~~~~

-  The ‘final’ optimised model.
-  Contains 3d structure around the Lake Hawea Moraine
-  Best fits for the high frequency targets.
-  Bund elevation set to 335 msl
-  NGMP well head observations removed from objective function as there
   is significant tension between these records and the high frequency
   observations. The NGMP wells are pumped irrigation bores and the
   primary purpose for sampling was water quality monitoring.

20. 3d_v1a
~~~~~~

-  Identical to “Main (3d_v1d)” except that the NGMP wells were included
   in the objective function
-  decent history matching; however “Main (3d_v1d)” provides better
   results
-  retained as active branch for comparison to “3d_v1b”

21. 3d_v1b
~~~~~~

-  Identical to “3d_v1a” except that the Bund elevation was set to 333
   MSL.
-  history matching results were similar to “3d_v1a” suggesting that the
   bund elevation is largely non-unique
-  retained to demonstrate the non-uniqueness of the 3d structure

14. terrace_only
~~~~~~~~~~~~

-  This model structure only includes the high terrace (south of Hawea
   Flat) to the clutha river
-  this optimisation was undertaken to see if the high terrace could be
   history matched (within the accepted parameter ranges) in isolation
   from the rest of the Hawea aquifer system.
-  History matching was not achieved.

Abandoned branches (releases, optimisation versions)
----------------------------------------------------

There are many previous branches that were issued as pre releases and
then deleted (effectively archived). There should be no reason for other
users to delve into these previous branches as they ended up with
unsatisfactory history matching; however they are available and briefly
described below (working notes) for completeness.

#.  Main (before 2/11/22) The main build branch. First structural
    version

#.  Structure v2, Changes:

    -  Increase parameterization via pilot points to Mangawera
    -  Add recharge multiplier pilot points across model (NI)
    -  Remove sandy point from model
    -  abandoned but retained

#.  Structure v3,Changes:

    -  Set ss=sy
    -  Set the model to confined to reduce computational burden
    -  This helped but the model preformed poorly,
    -  Error did not reduce saturated thickness.
    -  abandoned and deleted

#.  Structure_v4:

    -  From structure v2
    -  Add new mean annual head targets from regular
    -  Increase steps to 7 in transient
    -  Expand hillside streams to all adjacent cells (up to 9 cells per
       hill)
    -  Optimisation never run here, just saved to version structural
       changes

#.  Structure_v5

    -  From structure_v4
    -  Remove near river pumping wells.

#.  Structure_v6

    -  From structure 5
    -  Add a 1m confined layer below the bottom of layer 1 (may improve
       stability)

#.  Structure_v6a

    -  From v6, but set ss to sy

#.  Structure_v7 (built but not run)

    -  From structure 5
    -  Reduce thickness to reasonable pumped thickness and then Maximum
       30m sat thickness
    -  Set ss = sy
    -  run as a confined model

#.  Structure_v8

    -  From structure_v6a
    -  increase initial conductivity (to 50, 100 and 70 was too
       unstable)
    -  rch multiplier only by irrigated not irrigated bounds of
       multiplier 0.5-1.2

#. Structure_v9

    -  Fix river targets (they were backwards!)
    -  Implement grandview and john creek (+Hawea and Clutha) as str
       package
    -  Lake stage vs g40_0415
    -  Looks fine, honestly the fact that them model isn’t’ matching it
       suggests some sort of structural error. Reworked transport in
       grandview stream?/ water through grandview stream??? Likely the
       problem google maps shows water in grandview to the lake (and in
       john creek (to the north), all other creeks are probably fine.
    -  Lower basement around g40_0366

#. Structure_v10

    -  Set weight of regular year targets to 0
    -  set each of the ‘h_hf’ targets equal weights despite different
       data lengths
    -  look/lower basement in dry cells near model boundaries
    -  NE hillside area (done)
    -  Near clutha river (done)
    -  I think I need some more pilot points
    -  Near pt 402 on camp hill moraine (move mangawera south?) ()
       and another in the moraine (to interpolate with other river group
    -  To stop dry cells south of camp hill moraine
    -  Significant number in the hillslope area just off the bounds to
       allow conductivity to fall there if needed for stability. And to
       manage the change in geologic setting near hillslope
    -  Adjust some locations based on the new pilot point locations
    -  New rivergroup south of mangawera valley entrance to allow for
       the difference between the two settings
    -  Additional point in the middle of the terrace to manage near
       hillside environment.
    -  Try lowering hillside conductance → set to 100 vs 1000 for
       hawea/clutha, which means much of the peak flow does does not
       make it into the model.

#. Structure_v11

    -  Move to 1 global recharge modifier (done)
    -  Much higher initial kh (lake=5, rest = 300) (in progress
    -  Lower sy, and lower sy bounds
    -  Change weights (lower low frequency targets)
    -  Bit of a hail mary before the weekend
    -  retired (even though I’m happy with the parameterization. If I
       want to change back to vll parameters do it from v12

#. Structure_v12

    -  Increase kh/sy parameterization in the near lake environment

#. terrace only

    - see above

#. p_lake

    -  As per structure_v11 but with a single additive parameter for
       lake heads (e.g. lake hds = lake hds + mod
    -  A test to see if the lake levels problems are sorted everything
       else works great?
    -  Note the parameter is offset by 100m as pyemu has bugs!

#. lake_bar

    -  Add a 1 cell thick barrier for kh
    -  Remove additional v12 parameterization

#. cond_int

    -  Try to fit the heads by simply setting lake conductance (1 cell
       width lake)

#. 3d_v1

    -  Address the 3d moraine issues in structure
    -  3 layers the bottom two pinch out against the bottom of the
       model.
    -  well management
    -  target management
    -  other structural pieces
    -  Add abrupt parameter change at terrace interface
    -  Remove from dam to “dam control” road from model (e.g. no flow)
    -  Re-run pre_optimisation_overview.py
    -  remove the slope fixer on the east side
    -  remove additional parameterization of v12

#. 3d_v2

    -  As per v1 but fully confined (to increase stability)
    -  Ss[0] = sy[0]
    -  Initial parameters do not manage the drop quite so well. This may
       really need the unconfined aspects of the model.
    -  Bit of a hail mary over xmas. Really need the unconfined action
       to make the ‘waterfall happen’

#. 3d_v1a

    - see above

#. 3d_v1b

    - see above

#. 3d_v1c

    -  As 3d_v1a but with top of bund set to 337
    -  great difficulty getting this to converge
    -  abandoned

#. 3d_v4

    -  As 3d_v1a, but top of bund is set to 340m MSL instead of 335
    -  Difficult to get model to converge
    -  abandoned

#. 3d_v5

    -  As 3d_v1a, but top of bund is parameterised
    -  Largely unstable

#. 3d_v1d

    - see above

References
===========

- `Wilson, J., 2012. Hawea Basin Groundwater Review. prepared by Resource Science Unit of Otago Regional Council,
   June 2012, Dunedin. <../scott_model/Hawea_Basin_Groundwater_Review_2012_FINAL.pdf>`_