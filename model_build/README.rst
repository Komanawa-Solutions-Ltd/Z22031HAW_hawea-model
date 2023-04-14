Hawea Transient groundwater model (Hawea Model) build methods and results
############################################################################

.. figure:: ../support_figures/domain.png
   :width: 600
   :align: center

    test caption
    # todo make a good figure with all boundary conditions


:Author:  Matt Dumont
:Date:  2021-11-02
:Version:  1.0.0
:Status:  Draft
:KSL project: Z22031HAW_hawea-model
:Purpose: This document provides the methodology and results for the model build process


Index
=====
.. contents:: Table of Contents



Module Index
============
# todo copy from base readme
-  `README.rst <model_build/README.rst>`_: this document
-  `base_data <model_build/base_data>`_: raw input data for the model build
-  `processed_input_data <model_build/processed_input_data>`_: processed data for the model build that was built by the scripts in this folder from the raw data in the base_data folder
-  `project_model_tools.py <model_build/project_model_tools.py>`_: a script to define the model tools instance, and the model structure
-  `get_boundary_condition_data.py <model_build/get_boundary_condition_data.py>`_: a script to get the boundary condition data
-  `supporting_data_analysis <model_build/supporting_data_analysis>`_: scripts to support creating the boundary condition data and structure
    -  `all_wells.py <model_build/supporting_data_analysis/all_wells.py>`_: a script to get all the well location data
    -  `base_concept_diagram.py <model_build/supporting_data_analysis/base_concept_diagram.py>`_: a script to build a base concept diagram of the 3d model structure
    -  `compare_met_era5land.py <model_build/supporting_data_analysis/compare_met_era5land.py>`_: compare precip and PET between the available met station and the ERA5 land data
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
-  `modflow_model.py <model_build/modflow_model.py>`_: a script to build a modflow model instance
-  `utils.py <model_build/utils.py>`_: a script to define some utility functions
-  `zones.py <model_build/zones.py>`_: a script to define indicative model zones

Model boundaries
================

The model domain (see figure below) was initially defined to include the following aquifers:

- **The main Hawea flat aquifer** stretching from Lake Hawea in the North to the base of the High terrace in the South. This aquifer is bounded by the Hawea river on the West and the Grandview Ridge on the East
- **The High terrace aquifer** stretching from the base of the High terrace in the North to Clutha River in the South This aquifer is also bounded by the Hawea river on the West and the Grandview Ridge on the East
- **Aquifers near the Hawea river** including Te Awa, Maungawera Flat, and river adjacent aquifers to the south of Maungawera flat and east of the High terrace.
- **The Maungawera Valley aquifer** including the Maungawera valley aquifer from the approximate Hawea River/ Lake Wanaka flow divide in the Northwest to the Maungawera Flat Aquifer
- **The Sandy Point Aquifer** which is to the East of the Clutha river to the South of the High terrace aquifer.  This aquifer is also bounded by the Grandview Ridge on the East

During the model build the steep topography of the Sandy Point Aquifer caused model convergence issues.
The Sandy Point has minimal data available (one historical groundwater measurement) Therefore we resolved the convergence
issue by removing the Sandy Point Aquifer from the model domain. We still produced estimates of Land surface recharge (LSR) and
Hillside inflows to this aquifer, which were used to inform groundwater allocation decisions.

The boundaries of the model domain were all defined by no-flow boundary conditions. In addition at the Lake Hawea Dam,
Camp Hill, and Cameron Hill bedrock is exposed. Therefore these outcrops were also defined as no-flow boundaries.
Finally, the Camp Hill Medial Moraine, located between Te Awa and the Maungawera Flat aquifers, is comprised of poorly sorted
and unworked moraine sediments. While there are a few domestic supply bores in this area, the groundwater system is
likely minimal, particularly in comparison with the other outwash dominated aquifers.  We therefore chose to defined this area
as a no-flow boundary.


.. figure:: ./support_figures/domain.png
   :width: 600
   :align: center

    # todo make a good figure with all boundary conditions, the aquifers and ID the no flow inclusions


Model Structure
===============

2d model structure
------------------

# todo top, bottom definitino

3d model structure
------------------


Model boundary conditions
=========================

Land surface recharge (LSR)
---------------------------

LSR model
^^^

LSR model inputs -> Precip and PET
^^^^

ERA5-land and met station data


Correcting ERA5-land data
^^^^

LSR model inputs -> Irrigated area and efficiency
^^^^

Correcting ERA5-land based LSR
^^^

Generating a Long record of LSR
^^^^^^

Groundwater Abstraction (pumping)
----------------------------------

Major Rivers (Hawea river and Clutha River)
-------------------------------------------
The Hawea and Clutha rivers were included in the model using `the stream boundary condition package. <https://water.usgs.gov/nrp/gwsoftware/modflow2000/MFDOC/str.html>`_.
The stream boundary condition package models both stream flow and surface-ground water interactions. While the
Package allows for modelling of stream stage, for this model we specified the stream stage. The package requires the following inputs:

- Stream location and river bed elevation
- Stream stage
- Stream flow (at the top segment of each stream)
- `The stream bed conductance factor <https://water.usgs.gov/nrp/gwsoftware/modflow2000/MFDOC/frequently_asked_questions.html?anchor=conductance>`_

We defined the stream location with a carefully drawn line along the river bed informed by a LiDAR dataset provided by Otago Regional Council.
The raw river bed elevation was defined as the minimum LiDAR elevation in each river model cell.  This left a river profile that was
not consistently decreasing downstream.  To correct this we used a rolling mean to define the river bed elevation.  Finally we inset the
river bottom by 2.5 m so that the river bed elevation was always below the river stage.

.. figure:: ../support_figures/river_top_bot.png
   :width: 600
   :align: center

The stream bed conductance factor was a parameter in the model inversion.  See `the model parameterisation readme for more information <model_parameterisation/README.rst>`_
The steam flow did not need to be particularly precise as the river would never come close to losing all of its water to the
aquifer system.  Therefore we set the Hawea river flow to the the historical flow measured at Camp Hill.  The Clutha river
flow was arbitrarily set to 10 * the Hawea river flow.  We prescribed the river stage for both the Hawea and Clutha rivers
by interpolating historical river stage data at Camp Hill (Hawea River) and at a point on the Clutha River 200 m
downstream of Luggate Confluence. The Clutha stage data did not cover the full historical record; therefore we used the
ISO-weekly mean river stage for the missing data. The Hawea river stage data was temporally complete. To interpolate the
river stage spatially we simply applied the stage measured at camphill relative to the river bed elevation to the river bed elevation
in all other Hawea River model cells.  The same approach was used for the Clutha river; however where the Clutha river joined the
Hawea river there was an offset. To avoid this offset causing model convergence issues we linearly interpolated the Stage
at the end of the Hawea River to the stage on the Clutha River 200m downstream of Luggate Confluence.

.. figure:: ../optimisation/pre_optimisation_plots_png/stress_period_data/River_profile.png
   :scale: 50 %

    test caption

Lake Hawea
----------

Irrigation Supply Race Losses (race losses)
-------------------------------------------

Hillside stream inflows (hillside inflows)
------------------------------------------

Method to estimate hillside inflows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Large Hillside Inflows (Grandview and John Creek) implementation
^^^^^^^^^

Smaller Hillside inflows (other hillside inflows) implementation
^^^^

Model Zones
===========

References
===========
