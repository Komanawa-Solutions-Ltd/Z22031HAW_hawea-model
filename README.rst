Hawea Transient groundwater model (Hawea Model)
################################################

.. figure:: support_figures/domain.png
   :height: 650 px
   :align: center

:Author:  Matt Dumont
:Date:  2021-11-02
:Version:  1.0.0
:Status:  Final
:KSL project: Z22031HAW_hawea-model
:Purpose: This document describes the Hawea Model repo


The Hawea model domain; the inactive portions of the model are coloured dark grey. The model domain is a 3D model of the Hawea
aquifer systems including the Maungawera Valley.
The model domain is bounded by Lake Hawea to the North, the Clutha River to
the South, and the hillslopes to the East and West. The model domain is
17 km by 23.5 km. The model cell spacing is 100 m and the model is on a
regular North-South grid.
The model is loosely based on the 2D model of the Hawea aquifer system developed by Wilson et al, (2011).

Index
=====
.. contents:: Table of Contents


Modelling methodology and results
==================================
Rather than a traditional model report this repository serves as the detailed documentation of the modelling process.
`The final report with the interpretation of the modelling process and results is available in the repo here <Final_report.pdf>`_.
The modelling process was broadly undertaken in the following steps; each step has its own readme document detailing
its methodology and, where applicable, the results of the step:

1.  `Model build <model_build/README.rst>`_: build the model structure and boundary conditions
2.  `Model targets <targets_and_sensitive_sites/README.rst>`_: define the model targets and objective function
3.  `Model Parameterisation <model_parameterisation/README.rst>`_: define the initial model parameters and parameterisation
4.  `Model Optimisation and limitations <optimisation/README.rst>`_: optimise the model to the available data
5.  `Model Scenarios <Scenarios/README.rst>`_: run a series of scenarios to better understand the model behaviour and to predict the systems response to changing conditions

Subsequent Investigations
=========================

1. `Historical Hawea groundwater investigation <historical_investigation/README.rst>`_: investigate the historical data from 1976 - 1979 when the lake fell to the lowest level in the historical record (c. 327.5 m msl)
2. `Quartz Creek LSR <quartz_creek_lsr/README.rst>`_: investigate the LSR for the Quartz Creek area which was not included in the final model

Modelling Software
===================
Most of the model was produced using open source Python packages and the MODFLOW suite. Specifically the model was built
using MODFLOW NWT, optimised using PEST, and scenarios were run in MT3DMS-usgs.

Python Environment
==================
This model was developed in Python on linux (ubuntu 20.04).  The Python environment was created using the Anaconda package manager.
The environment was created using the following command: ::

    conda create -c conda-forge --name hawea python numpy pandas pytables openpyxl matplotlib scipy netcdf4 psutil geopandas flopy pysheds scikit-learn py7zr
    conda activate hawea
    pip install pyemu
    pip install ppscore
    pip install tabulate
    pip install fpdf
    pip install pdfkit


Versioned Conda Install
---------------------------

If you wish to use the exact package versions you may install with: ::

    conda create -c conda-forge --name hawea python=3.10.5 numpy=1.23.4 pandas=1.4.3 pytables=3.7.0 openpyxl=3.0.9 matplotlib=3.5.2 scipy=1.9.0 netcdf4=1.6.0 psutil=5.9.1 geopandas=0.11.1 flopy=3.3.5 pysheds=0.3.3 scikit-learn=1.1.1 py7zr=0.20.0
    
    conda activate hawea
    pip install pyemu==1.2.0
    pip install ppscore==1.3.0
    pip install tabulate==0.9.0
    pip install fpdf==1.7.2
    pip install pdfkit==1.0.0

This install was tested successfully on windows 10 on 13/07/2023


In addition to the creation code above, the repo environment was exported in:

-  `environment.yml <environment.yml>`_
-  `environment.txt <environment.txt>`_

However these exports are raw and therefore may be difficult to directly install and may contain proprietary packages (e.g. kslcore) We have left them as they provide an exact copy of the development environment if future users have versioning problems with the above conda installs

Github repo structure
======================

The full modelling process for the Hawea model was undertaken within
this Github repo. The only exceptions are several large datasets
(LIDAR/DEMs) which were simplified (code in repo) and then the
simplified product was saved in the Github repo. This means that no
external datasets are necessary to completely recreate the Hawea model
and the full methodology is present in this repo.

Comment keyword standards:
---------------------------

We have used a number of keywords (case insensitive) to support identifying important comments within the text. These are:

-  TODO: A comment that identifies a task that needs to be completed
-  FIXME: A comment that identifies a problem that needs to be fixed
-  KEYNOTE: A comment that identifies a key assumption or point of interest
-  OPEN SOURCE IMPROVE: A comment that identifies a potential improvement to existing open source code repos

At this point only KEYNOTE and OPEN SOURCE IMPROVE should remain in the repo, however it is possible that some
TODOs and FIXMEs will remain accidentally. Note that these have been dealt with, but were accidentally not removed from the code.
Many IDEs have a search function that can be used to find these keywords, which we encourage you to use.

Repo index
----------
Below is a rough guide to the repo structure. Not every file in the repo is described.  Often the best way to find out
what information a file contains is to look through the appropriate Python function and read the docstrings.
The repo has been documented to a reasonable extent, but there is still
some work that could be done to make the repo more user friendly.
If you have any questions please contact Matt Dumont (matt@komanawa.com)

-  `README.rst <README.rst>`_: This document
-  `project_base.py <project_base.py>`_: A script to set up the project environment and manage paths
-  `scott_model <scott_model>`_: A copy of the original 2D model of the Hawea aquifer system developed by Wilson et al, (2011)
-  `model_build <model_build>`_: model build process and datasets
    -  `README.rst <model_build/README.rst>`_: a readme file for the model build
    -  `base_data <model_build/base_data>`_: raw input data for the model build
    -  `processed_input_data <model_build/processed_input_data>`_: processed data for the model build that was built by the scripts in this folder from the raw data in the base_data folder
    -  `project_model_tools.py <model_build/project_model_tools.py>`_: a script to define the model tools instance, and the model structure
    -  `get_boundary_condition_data.py <model_build/get_boundary_condition_data.py>`_: a script to get the boundary condition data
    -  `supporting_data_analysis <model_build/supporting_data_analysis>`_: scripts to support creating the boundary condition data and structure
        -  `all_wells.py <model_build/supporting_data_analysis/all_wells.py>`_: a script to get all the well location data
        -  `base_concept_diagram.py <model_build/supporting_data_analysis/base_concept_diagram.py>`_: a script to build a base concept diagram of the 3D model structure
        -  `compare_met_era5land.py <model_build/supporting_data_analysis/compare_met_era5land.py>`_: compare precipitation and PET between the available met station and the ERA5-land data
        -  `explore_structure.py <model_build/supporting_data_analysis/explore_structure.py>`_:
        -  `get_era_5_land.py <model_build/supporting_data_analysis/get_era_5_land.py>`_: script to get ERA5-land data
        -  `get_pumping_data.py <model_build/supporting_data_analysis/get_pumping_data.py>`_: get and process historical pumping data
        -  `hillside_inflows.py <model_build/supporting_data_analysis/hillside_inflows.py>`_: model and process estimates from the hillside inflows
        -  `irrigation_race_losses.py <model_build/supporting_data_analysis/irrigation_race_losses.py>`_:  get and process the historical race loss data
        -  `lake_data.py <model_build/supporting_data_analysis/lake_data.py>`_: get and process the historical lake data
        -  `map_flowmeter_to_wells.py <model_build/supporting_data_analysis/map_flowmeter_to_wells.py>`_: a process to map the flowmeter data to the most likely well
        -  `plot_borelogs.py <model_build/supporting_data_analysis/plot_borelogs.py>`_:  a process to plot the borelogs in the model
        -  `recharge_model.py <model_build/supporting_data_analysis/recharge_model.py>`_: develop and create LSR estimates from met and ERA5-land data
        -  `river_data.py <model_build/supporting_data_analysis/river_data.py>`_: : a process to get and process the river data
    -  `modflow_model.py <model_build/modflow_model.py>`_: a script to build a MODFLOW model instance
    -  `utils.py <model_build/utils.py>`_: a script to define some utility functions
    -  `zones.py <model_build/zones.py>`_: a script to define indicative model zones
-  `model_parameterisation <model_parameterisation>`_:  model parameterisation and implementation
    -  `README.rst <model_parameterisation/README.rst>`_: a readme file for the model parameterisation
    -  `base_data <model_parameterisation/base_data>`_: raw input data for the model parameterisation
    -  `processed_data <model_parameterisation/processed_data>`_: processed data for the model parameterisation that was built by the scripts in this folder from the raw data in the base_data folder
    -  `static_params.py <model_parameterisation/static_params.py>`_: a script to define the static model parameters
    -  `pilot_points.py <model_parameterisation/pilot_points.py>`_: a script to create, define, and interpolate pilot points for kh and sy
    -  `inital_parametersiation.py <model_parameterisation/inital_parametersiation.py>`_: a script to define the initial model parameters (before optimisation)
    -  `plot_parameter_names.py <model_parameterisation/plot_parameter_names.py>`_: a script to plot the parameter names generates parameter_map.png
    -  `optimised_parameterisation.py <model_parameterisation/optimised_parameterisation.py>`_: a script to easily access optimised parameter sets
    -  `optimised_parameter_sets <model_parameterisation/optimised_parameter_sets>`_: optimised parameter sets
        - `3d_v1a_opt.par <model_parameterisation/optimised_parameter_sets/3d_v1a_opt.par>`_: optimised parameter set for the 3D model version 1a
        - `3d_v1b_opt.par <model_parameterisation/optimised_parameter_sets/3d_v1b_opt.par>`_: optimised parameter set for the 3D model version 1b
        - `3d_v1d_opt.par <model_parameterisation/optimised_parameter_sets/3d_v1d_opt.par>`_: optimised parameter set for the 3D model version 1d
    -  `parameter_map.png <model_parameterisation/parameter_map.png>`_: a map of the model parameters
-  `targets_and_sensitive_sites <targets_and_sensitive_sites>`_: target development and data
    -  `README.rst <targets_and_sensitive_sites/README.rst>`_ : readme document detailing the methods and data used to develop the targets
    -  `model_output.py <targets_and_sensitive_sites/model_output.py>`_: script to extract consistent model outputs and plots
    -  `get_raw_target_data.py <targets_and_sensitive_sites/get_raw_target_data.py>`_:  ingest raw target data
    -  `get_indicative_times.py <targets_and_sensitive_sites/get_indicative_times.py>`_: get indicative times for the targets that fall outside of the optimisation period
    -  `head_targets.py <targets_and_sensitive_sites/head_targets.py>`_:  definition of the head targets
    -  `riv_gain_loss_targets.py <targets_and_sensitive_sites/riv_gain_loss_targets.py>`_:  definition of the river gain and loss targets
    -  `senstive_sites.py <targets_and_sensitive_sites/senstive_sites.py>`_: identification of sensitive sites
    -  `target_structure_checks.py <targets_and_sensitive_sites/target_structure_checks.py>`_: checks to ensure that the targets and the model structure were not mutually exclusive
    -  `base_data <targets_and_sensitive_sites/base_data>`_: base input data for the targets
    -  `processed_data <targets_and_sensitive_sites/processed_data>`_: processed target data, this was developed from the raw data in the base_data folder
-  `optimisation <optimisation>`_:  optimisation code and results
    -  `README.rst <optimisation/README.rst>`_: readme document detailing the optimisation process and methodology
    -  PEST optimisation build, run, and post processing scripts
        -  `build_optimisation.py <optimisation/build_optimisation.py>`_: script and functions to build the PEST files
        -  `a_build_run_optimisation_version.py <optimisation/a_build_run_optimisation_version.py>`_: build and run a PEST optimisation
        -  `run_opt_step_models.py <optimisation/run_opt_step_models.py>`_:  run the step models from a PEST optimisation
        -  `manual_optimisations <optimisation/manual_optimisations>`_:  manual optimisations that were run, in the end these never contributed more than some information to the modeller
        -  `model_utils_for_forward_run.py <optimisation/model_utils_for_forward_run.py>`_: functions to build and run a model from PEST parameter files
        -  `compare_parameterisations.py <optimisation/compare_parameterisations.py>`_: script to compare parameters across multiple parameter files
        -  `hawea_plot_optimisation.py <optimisation/hawea_plot_optimisation.py>`_: script to plot the optimisation results
        -  `plot_multiple_high_freq.py <optimisation/plot_multiple_high_freq.py>`_: script to plot multiple high frequency observations for given PEST obs files
    -  Manage optimisation period:
        -  `determine_opt_start.py <optimisation/determine_opt_start.py>`_: script to determine the start and end of the optimisation period
        -  `optimisation_period.py <optimisation/optimisation_period.py>`_: script to manage and hold the information about the optimisation period
    -  Optimisation Results
        -  `optimisation_results <optimisation/optimisation_results>`_: results for the optimisation holding all of the pest input and output files
            -  `3d_v1a <optimisation/optimisation_results/3d_v1a>`_:  optimisation results for the 3D model version 1a
            -  `3d_v1b <optimisation/optimisation_results/3d_v1b>`_:  optimisation results for the 3D model version 1b
            -  `3d_v1d <optimisation/optimisation_results/3d_v1d>`_:  optimisation results for the 3D model version 1d (final model)
        -  `final_opt_models <optimisation/final_opt_models>`_:  the final optimised model files
            -  `3d_v1a <optimisation/final_opt_models/3d_v1a>`_: final optimised model files for the 3D model version 1a
            -  `3d_v1b <optimisation/final_opt_models/3d_v1b>`_: final optimised model files for the 3D model version 1b
            -  `3d_v1d <optimisation/final_opt_models/3d_v1d>`_: final optimised model files for the 3D model version 1d (final model)
            -  `compress_uncompress_model.py <optimisation/final_opt_models/compress_uncompress_model.py>`_:  utilities to compress and uncompress the model files so they could be included in the Git repo (50mb limit)
    -  Computational support files
        -  `compile_pest <optimisation/compile_pest>`_: compile PEST for linux
        -  `pest_run_data <optimisation/pest_run_data>`_: static data needed by PEST to run the model
        -  `git_setup.sh <optimisation/git_setup.sh>`_: script to setup the Git repo for the optimisation on a machine
    - Model overview
        -  `pre_optimisation_overview.py <optimisation/pre_optimisation_overview.py>`_: make pre optimisation overview plots
        -  `make_preopt_slideshow.py <optimisation/make_preopt_slideshow.py>`_: make a pre optimisation slideshow
        -  `pre_optimisation_plots_png <optimisation/pre_optimisation_plots_png>`_: pre optimisation plots of boundary conditions, targets, parameterisation, and other supporting work, many of these figures are referenced in the various readme.rst files
        -  `make_opt_presentation.py <optimisation/make_opt_presentation.py>`_: make a presentation of the optimisation results for a meeting
- `quartz_creek_lsr <quartz_creek_lsr>`_: modelling of LSR for the Quartz Creek area see the `Scenarios readme <Scenarios/README.rst>`_ for more information
    - ` results <quartz_creek_lsr/results>`_: results from the LSR modelling
    - ` model_qtz_ck_lsr.py <quartz_creek_lsr/model_qtz_ck_lsr.py>`_: script for LSR modelling
-  `Scenarios <Scenarios>`_: scenario modelling code and results
    -  `README.rst <Scenarios/README.rst>`_: document describing the scenario modelling methods and results
    -  Scenario development and supporting scripts
        -  `scen_period.py <Scenarios/scen_period.py>`_: script to handle the scenario period
        -  `boundary_condition_plots <Scenarios/boundary_condition_plots>`_: plots of the scenarios boundary conditions
        -  `base_data <Scenarios/base_data>`_: base input data for the scenarios
        -  `processed_input_data <Scenarios/processed_input_data>`_: processed input data for the scenarios, these files were all developed from the base data
        -  `boundary_conditions.py <Scenarios/boundary_conditions.py>`_:  develop the input boundary conditions for the scenarios
        -  `supporting_data_analysis <Scenarios/supporting_data_analysis>`_: additional data analysis scripts to support creating boundary conditions
        -  `scenario_outputs.py <Scenarios/scenario_outputs.py>`_: script to make consistent scenario outputs
        -  `run_flow_scenario.py <Scenarios/run_flow_scenario.py>`_: script to run a flow scenario
        -  `run_scenario.py <Scenarios/run_scenario.py>`_: script to run a scenario (in multiprocessing)
    -  Model information and MT3D indicator modelling
        -  `run_mt3d_scenario.py <Scenarios/run_mt3d_scenario.py>`_:  script to support running MT3D
        -  `mt3d_indicator_scens.py <Scenarios/mt3d_indicator_scens.py>`_: script to run MT3D indicator scenarios
        -  `compare_boundary_sensitivity.py <Scenarios/compare_boundary_sensitivity.py>`_: compare the results of the boundary condition sensitivity analysis
        -  `model_info_scenarios.py <Scenarios/model_info_scenarios.py>`_: script to run model information scenarios
        -  `model_info_scen_results <Scenarios/model_info_scen_results>`_: model results and plots for model information scenarios
            -  `0_results <Scenarios/model_info_scen_results/0_results>`_: plots for model information scenarios
            -  {scenario name}: Model results for model information scenarios: input and output data for the scenario
        -  `mt3d_indicator_scenarios <Scenarios/mt3d_indicator_scenarios>`_: model results and plots for the MT3D scenarios
    -  Low Lake Hawea level scenarios
        -  `low_lake_scenario_data.py <Scenarios/low_lake_scenario_data.py>`_: script to develop typological lake levels and perturbations
        -  `low_lake_scenarios.py <Scenarios/low_lake_scenarios.py>`_: script to run low lake scenarios
        -  `compare_low_lake.py <Scenarios/compare_low_lake.py>`_: script to compare low lake scenarios
        -  `low_lake_scenarios <Scenarios/low_lake_scenarios>`_: model results and plots for low lake scenarios
            -  `0_results <Scenarios/low_lake_scenarios/0_results>`_: plots for low lake scenarios
            -  {scenario name}: Model results for low lake scenarios: input and output data for the lake scenario
    - Allocation modelling
        -  `allocation_zones.py <Scenarios/allocation_zones.py>`_: get and plot allocation zones
        -  `allo_rch_hillside.py <Scenarios/allo_rch_hillside.py>`_: scripts to get and compare the allocation, hillside recharge, and LSR for each zone
        -  `allocation_scenarios.py <Scenarios/allocation_scenarios.py>`_: script to develop all allocation scenarios and to run the non-gridded allocation scenarios
        -  `run_grid_allocation.py <Scenarios/run_grid_allocation.py>`_: script to run the gridded allocation scenarios
        -  `compare_allocation_scens.py <Scenarios/compare_allocation_scens.py>`_: script to compare allocation scenarios
        -  `allocation_scenarios <Scenarios/allocation_scenarios>`_:  model results for allocation scenarios
        -  `allocation_results <Scenarios/allocation_results>`_: plots of allocation results
            -  `old_allo_zones.png <Scenarios/allocation_results/old_allo_zones.png>`_: figure of the old allocation zones (Wilson et al., 2012)
            -  `new_allo_zones.png <Scenarios/allocation_results/new_allo_zones.png>`_: figure of the new allocation zones
            -  `Hawea Flat_results <Scenarios/allocation_results/Hawea Flat_results>`_: results for the gridded Hawea Flat allocation scenarios
            -  `Maungawera Flat_results <Scenarios/allocation_results/Maungawera Flat_results>`_: results for the gridded Maungawera Flat allocation scenarios
            -  `Terrace-Hill_results <Scenarios/allocation_results/Terrace-Hill_results>`_: results for the gridded Terrace-Hill allocation scenarios
            -  `nat_current_full <Scenarios/allocation_results/nat_current_full>`_: results for the naturalised, current allocation, and full allocation scenarios
            -  `Te Awa_results <Scenarios/allocation_results/Te Awa_results>`_: results for the gridded Te Awa allocation scenarios
            -  `Terrace-River_results <Scenarios/allocation_results/Terrace-River_results>`_: results for the gridded Terrace-River allocation scenarios
            -  `mangawera_valley <Scenarios/allocation_results/mangawera_valley>`_: results for the Maungawera Valley allocation reduction scenarios
            -  `allo_zone_rch <Scenarios/allocation_results/allo_zone_rch>`_: results comparing LSR, hillside inflows, and allocation for each zone
            -  `example_quantile_plots <Scenarios/allocation_results/example_quantile_plots>`_: example quantile plots for the allocation scenarios to support presentations
    -  Wetland Setback Modelling
        -  `wetland_setback_campbells <Scenarios/wetland_setback_campbells>`_: wetland setback modelling for Campbells wetland scripts and results
        -  `wetland_setback_butterfield <Scenarios/wetland_setback_butterfield>`_: wetland setback modelling for Butterfield wetland scripts and results
-  `support_figures <support_figures>`_: supporting figures for this and other README.rst documents
-  `dummy_packages <dummy_packages>`_: dummy packages for the proprietary packages used in the model, these packages have some, but not all of functionality of the original packages
- `historical_investigation <historical_investigation>`_:  historical Hawea groundwater investigation of historical data from 1976 - 1979 where the lake fell to the lowest level in the historical record (c. 327.5 m msl)
    - `README.rst <historical_investigation
/README.rst>`_: This document
    - `base_data <historical_investigation
/base_data>`_: The raw input data for the historical analysis.  For more info see the "Dataset and Resources" section at the end of this document.
        - `MWD_Hawea_Flats_Groundwater_1984.pdf <historical_investigation
/base_data/MWD_Hawea_Flats_Groundwater_1984.pdf>`_: The original PDF of the Ministry of Works and Development report, which contains the historical data.
    - `current_model_prediction.py <historical_investigation
/current_model_prediction.py>`_: run the naturalised 3d_v1d model for the historical period with low lake levels
    - `figures <historical_investigation
/figures>`_: output figures from the historical analysis.  For more info see the "Dataset and Resources" section at the end of this document.
    - `generated_data <historical_investigation
/generated_data>`_: data generated by the analysis.  For more info see the "Dataset and Resources" section at the end of this document.
    - `get_historical_data.py <historical_investigation
/get_historical_data.py>`_: read in and access the historical data
    - `lake_drop_scenarios.py <historical_investigation
/lake_drop_scenarios.py>`_: run and compare the lake drop scenarios to the historical data
    - `mt3d_indicator_scenarios <historical_investigation
/mt3d_indicator_scenarios>`_: results for the MT3d component analysis
    - `mt3d_indicator_scens.py <historical_investigation
/mt3d_indicator_scens.py>`_: run the MT3d component analysis on a steady state model with low lake levels
    - `plot_historical_data.py <historical_investigation
/plot_historical_data.py>`_: plot the historical data
    - `plot_historical_natualised_model.py <historical_investigation
/plot_historical_natualised_model.py>`_: plot the historical data and the naturalised model results
    - `shift_diff.py <historical_investigation
/shift_diff.py>`_: compare lake and historical data, and calculate the shift between the two
    - `simple_smoothing_model.py <historical_investigation
/simple_smoothing_model.py>`_: develop and apply a simple smoothing model to the historical data


Supporting data index
--------------------------------
This repository contains all of the input and processed data needed to build and run the model.  There are two exceptions
to this; the 1 m LIDAR dem for the Clutha and Hawea rivers and the 15 m DEM used for the model top.  Both DEMs are too large
to store in the repo, so they have been simplified and the simplified versions are stored in the repo. There are a number
of directories in the repo that contain the input and processed data each of these directories contains a readme.rst file
that briefly describes the data in the directory.  The directories are:

- `model_build/base_data <model_build/base_data/README.rst>`_: contains the base data used to build the model
- `model_build/processed_input_data <model_build/processed_input_data/README.rst>`_: contains the processed data used to build the model
- `model_parameterisation/base_data <model_parameterisation/base_data/README.rst>`_: contains the base data used to parameterise the model
- `model_parameterisation/processed_data <model_parameterisation/processed_data/README.rst>`_: contains the processed data used to parameterise the model
- `Scenarios/wetland_setback_butterfield/base_input_data <Scenarios/wetland_setback_butterfield/base_input_data/README.rst>`_: contains the base data used to run the butterfield wetland setback scenario
- `Scenarios/wetland_setback_butterfield/processed_input_data <Scenarios/wetland_setback_butterfield/processed_input_data/README.rst>`_: contains the processed data used to run the butterfield wetland setback scenario
- `Scenarios/base_data <Scenarios/base_data/README.rst>`_: contains the base data used to run the scenarios
- `Scenarios/processed_input_data <Scenarios/processed_input_data/README.rst>`_: contains the processed data used to run the scenarios
- `Scenarios/wetland_setback_campbells/base_input_data <Scenarios/wetland_setback_campbells/base_input_data/README.rst>`_: contains the base data used to run the campbells wetland setback scenario
- `Scenarios/wetland_setback_campbells/processed_input_data <Scenarios/wetland_setback_campbells/processed_input_data/README.rst>`_: contains the processed data used to run the campbells wetland setback scenario
- `targets_and_sensitive_sites/base_data <targets_and_sensitive_sites/base_data/README.rst>`_: contains the base data used to define the model targets and objective function
- `targets_and_sensitive_sites/processed_data <targets_and_sensitive_sites/processed_data/README.rst>`_: contains the processed data used to define the model targets and objective function


Proprietary packages
--------------------
For the most part we relied on open source packages to create the Hawea model, but we did use some proprietary in
house packages. These packages are not included in this repository, but we have included dummy packages that
contain the same structure as the original packages and replicates some of the functionality.
These dummy packages are located in the `dummy_packages folder <dummy_packages>`_ in the model repo and the python
scripts have all been adjusted to load the dummy package version if the original version is not available.

Additionally, to ensure future use of this model we have included outputs of the data which
necessitated the use of the proprietary packages. These outputs are located in the `processed_input_data` folders.
The functions that use these packages to develop the outputs tend to follow are "recalc" structure, that is: ::

        def get_data(*args, **kwargs, recalc=False):
            save_path = processed_data_dir.joinpath('data.csv') # path in the processed data folder where the outputs are saved
            if save_path.exists() and not recalc:
                # read the data from the saved path and return it
                # sometimes additional processing (e.g. other args) is done after loading the data
                return pd.read_csv(save_path)
            else:
                # the process by which the data was generated
                outdata = None
                # save the data to the save_path
                outdata.to_csv(save_path)
                return outdata

This structure allows the user to run the model without the proprietary packages, but also allows the user to
see the full methodology used to generate the outputs. This also keeps the links between the data generation and
the data use (e.g. in a model) explicit.  This prevents the 'black box' problem that can occur when the data is
generated by a different process and then ingested into the model.


Excluding a full model re-build, these proprietary packages should not be needed; however, if the user wishes to run the model with the proprietary packages
or to generate a next generation with the proprietary packages they are encouraged to contact the author of this model: matt@komanawa.com

The proprietary packages used in this model are:

- Dummy packages provided:
    - from model_tools.time_discretization import TimeDis
        - mange the human time to model time
    - from model_tools.regular_modeltools import ModelTools_RegularGrid
        - manage the model structure and real world coordinates to model coordinates
- No Dummy packages provided
    - kslcore
        - an internal package used to ensure consistant access to our computational resources (google drive, NAS, etc.) across multiple machines 
    - from rushton_model.rushton import Rushton
        - land surface recharge model
    - from run_managers.beopest_manager import BeopestManager
        - Manage Beopest across multiple linux machines
    - from run_managers.ssh_distributor import SshDist
        - Distribute a list of model runs across linux machines
    - from model_tools.util_functions.list_file_utils import ListSolverInfo
        - extract solver information from the list file
    - from model_tools.plot_borelogs import plot_borelogs, plot_single_log, make_single_log_handles
        - plot bore logs
    - from model_tools.model_plotting import plot_spd, first, last, FakePath
        - plot model results
    - from model_tools.plot_optimisation import plot_optimisation_and_extract_info
        - plot optimisation results

Dead links
----------
We have made a substantial effort to ensure that all links in the model are valid. However, there are likely some links that
return a 404 error.  If you come across this, then please contact the author of this model: Matt@komanawa.com so that
he can fix the links.  Typically the links are relative to the repository.  if the link is broken you can likely infer
the correct location by looking at the link and the repo structure.



Branches and releases
=====================

The process of the model optimisation required multiple structural
changes to the model as well as changes to the objective function to
attain a satisfactory history match. These different structures and
changes were all set up as unique branches within the repo. For more
information on branches see `github’s explanation of
branches <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches>`__.
At the end of the calibration process there were 24 unique branches,
most of which were abandoned. These branches were issued as
pre-production releases (`More information about
releases <https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases>`__).
Only the key structures were retained and the “final” model was merged
back to the main branch.

Active Branches
---------------

Main (3d_v1d)
~~~~~~~~~~~~~

-  The ‘final’ optimised model.
-  Contains 3D structure around the Lake Hawea Moraine
-  Best fits for the high frequency targets.
-  Bund elevation set to 335 msl
-  NGMP well head observations removed from objective function as there
   is significant tension between these records and the high frequency
   observations. The NGMP wells are pumped irrigation bores and the
   primary purpose for sampling was water quality monitoring.

3d_v1a
~~~~~~

-  Identical to “Main (3d_v1d)” except that the NGMP wells were included
   in the objective function
-  decent history matching; however “Main (3d_v1d)” provides better
   results
-  retained as active branch for comparison to “3d_v1b”

3d_v1b
~~~~~~

-  Identical to “3d_v1a” except that the bund elevation was set to 333
   MSL.
-  history matching results were similar to “3d_v1a” suggesting that the
   bund elevation is largely non-unique
-  retained to demonstrate the non-uniqueness of the 3D structure

terrace_only
~~~~~~~~~~~~

-  This model structure only includes the High Terrace (south of Hawea
   Flat) to the Clutha river
-  this optimisation was undertaken to see if the High Terrace could be
   history matched (within the accepted parameter ranges) in isolation
   from the rest of the Hawea aquifer system.
-  History matching was not achieved.

3d_v10a
~~~~~~

-  Identical to “Main (3d_v1d)” including parameterisation, but the bund elevation was set to 330 m
   MSL to investigate the predictions of the historical investigation.

previous branches (releases)
----------------------------

There are many previous branches that were issued as pre releases and
then deleted (effectively archived). There should be no reason for other
users to delve into these previous branches as they ended up with
unsatisfactory history matching; however, they are available and briefly
described below (working notes) for completeness.

1.  Main (before 2/11/22) The main build branch. First structural
    version

2.  Structure v2, Changes:

    -  Increase parameterisation via pilot points to Maungawera
    -  Add recharge multiplier pilot points across model (NI)
    -  Remove sandy point from model
    -  abandoned but retained

3.  Structure v3,Changes:

    -  Set ss=sy
    -  Set the model to confined to reduce computational burden
    -  This helped but the model preformed poorly,
    -  Error did not reduce saturated thickness.
    -  abandoned and deleted

4.  Structure_v4:

    -  From structure v2
    -  Add new mean annual head targets from regular
    -  Increase steps to 7 in transient
    -  Expand hillside streams to all adjacent cells (up to 9 cells per
       hill)
    -  Optimisation never run here, just saved to version structural
       changes

5.  Structure_v5

    -  From structure_v4
    -  Remove near river pumping wells.

6.  Structure_v6

    -  From structure 5
    -  Add a 1m confined layer below the bottom of layer 1 (may improve
       stability)

7.  Structure_v6a

    -  From v6, but set ss to sy

8.  Structure_v7 (built but not run)

    -  From structure 5
    -  Reduce thickness to reasonable pumped thickness and then Maximum
       30m sat thickness
    -  Set ss = sy
    -  run as a confined model

9.  Structure_v8

    -  From structure_v6a
    -  increase initial conductivity (to 50, 100 and 70 was too
       unstable)
    -  rch multiplier only by irrigated not irrigated bounds of
       multiplier 0.5-1.2

10. Structure_v9

    -  Fix river targets (they were backwards!)
    -  Implement grandview and john creek (+Hawea and Clutha) as str
       package
    -  Lake stage vs g40_0415
    -  Looks fine, honestly the fact that them model isn’t matching it
       suggests some sort of structural error. Reworked transport in
       grandview stream?/ water through grandview stream??? Likely the
       problem google maps shows water in grandview to the lake (and in
       john creek (to the north), all other creeks are probably fine.
    -  Lower basement around g40_0366

11. Structure_v10

    -  Set weight of regular year targets to 0
    -  set each of the ‘h_hf’ targets equal weights despite different
       data lengths
    -  look/lower basement in dry cells near model boundaries
    -  NE hillside area (done)
    -  Near clutha river (done)
    -  I think I need some more pilot points
    -  Near pt 402 on camp hill moraine (move Maungawera south?) ()
       and another in the moraine (to interpolate with other river group
    -  To stop dry cells south of camp hill moraine
    -  Significant number in the hillslope area just off the bounds to
       allow conductivity to fall there if needed for stability. And to
       manage the change in geologic setting near hillslope
    -  Adjust some locations based on the new pilot point locations
    -  New rivergroup south of Maungawera valley entrance to allow for
       the difference between the two settings
    -  Additional point in the middle of the terrace to manage near
       hillside environment.
    -  Try lowering hillside conductance → set to 100 vs 1000 for
       Hawea/Clutha, which means much of the peak flow does does not
       make it into the model.

12. Structure_v11

    -  Move to 1 global recharge modifier (done)
    -  Much higher initial kh (lake=5, rest = 300) (in progress
    -  Lower sy, and lower sy bounds
    -  Change weights (lower low frequency targets)
    -  Bit of a hail mary before the weekend
    -  retired (even though I’m happy with the parameterisation. If I
       want to change back to vll parameters do it from v12

13. Structure_v12

    -  Increase kh/sy parameterisation in the near lake environment

14. p_lake

    -  As per structure_v11 but with a single additive parameter for
       lake heads (e.g. lake hds = lake hds + mod
    -  A test to see if the lake levels problems are sorted everything
       else works great?
    -  Note the parameter is offset by 100m as pyemu has bugs!

15. lake_bar

    -  Add a 1 cell thick barrier for kh
    -  Remove additional v12 parameterisation

16. cond_int

    -  Try to fit the heads by simply setting lake conductance (1 cell
       width lake)

17. 3d_v1

    -  Address the 3D moraine issues in structure
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

18. 3d_v2

    -  As per v1 but fully confined (to increase stability)
    -  Ss[0] = sy[0]
    -  Initial parameters do not manage the drop quite so well. This may
       really need the unconfined aspects of the model.
    -  Bit of a hail mary over xmas. Really need the unconfined action
       to make the ‘waterfall happen’

19. 3d_v1c

    -  As 3d_v1a but with top of bund set to 337
    -  great difficulty getting this to converge
    -  abandoned

20. 3d_v4

    -  As 3d_v1a, but top of bund is set to 340m MSL instead of 335
    -  Difficult to get model to converge
    -  abandoned

21. 3d_v5

    -  As 3d_v1a, but top of bund is parameterised
    -  Largely unstable


References
===========

- `Wilson, J., 2012. Hawea Basin Groundwater Review. prepared by Resouce Science Unit of Otago Regional Council, June 2012, Dunedin. <scott_model/Hawea_Basin_Groundwater_Review_2012_FINAL.pdf>`_
