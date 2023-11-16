Analysis of Historical Lake Hawea Low Lake levels corresponding groundwater levels)
###########################################################################################

.. figure:: ../historical_investigation/figures/simple_smoothing_model/bespoke_ssm_bore_315.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: Historical Low level levels*

:Author:  Matt Dumont
:Date:  2023-11-14
:Version:  1.0.0
:Status:  Draft
:KSL project: Z22031HAW_hawea-model - supplemental
:Purpose: This document provides the results of a re-analysis of the historical low lake levels at Lake Hawea (1976-1979). The analysis was conducted to determine the corresponding groundwater levels at the time of the low lake levels.

Index
=====
.. contents:: Table of Contents

Module Index
============
# todo make module index


Investigation Context and Objectives
=======================================

A key prediction of the Lake Hawea groundwater model hosted in this repository was that there was some threshold lake level below which the lake would become disconnected from the groundwater system.  Subsequently groundwater levels could fall significantly.  These predictions were based on the model structure required to match observed groundwater levels, particularly in bore G40/0415. This repository holds more information on the `model structure <../model_build/README.rst#multi-layer-3d-model-structure`_ and `predictions at low lake levels <../Scenarios/README.rst#lake-drop-scenario-results>`_.

.. figure:: ../support_figures/concept_diagram_0.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: conceptual model of the Lake Hawea Moraine (across the moraine)*


.. figure:: ../Scenarios/low_lake_scenarios/0_results/lake_drop/comp_plots/hds_monitoring.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: Responses at the high frequency monitoring bores for the lake drop scenarios.*


Modern Lake Hawea levels are strictly controlled to be above 338 m msl. Historically, between 1976 to 1979, Lake Hawea levels fell to their lowest recorded level of c. 327.5 m MSL.  This was because of #todo

.. figure:: ../historical_investigation/figures/lake_heads.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: Lake Hawea levels from 1976 to 1979.*


As part of the Lake Hawea modelling project the authors requested all information on historic lake levels and groundwater levels.  It was understood that there were no regular groundwater monitoring records concurrent with the historic low lake levels. This was incorrect. At the end of the modelling project one of the modelling team found a record of an appendix to a 1984 Ministry of works and development report which contained plots of high frequency groundwater level data for bores during the historic low lake levels. A copy of this appendix is included in this repository and is `accessible here <../historical_investigation/base_data/MWD Hawea Flats Groundwater 1984.pdf>`_. This appendix was previously unknown to the modelling team, the science team at the Otago Regional Council.  # todo ask jens where this came from. It's discovery was too late to be included in the modelling project; however the Otago Regional counil commissioned this addendum to the modelling project to digitise the data, investigate the implications of the historic low lake levels on groundwater levels, and to ascertain if the model predictions were consistent with the newly available historic groundwater level data.

Digitization of Historical data and discussion of their results
===================================================================

Summary of the historical data
--------------------------------

The historical appendix contains:

* a map of the historic monitoring bores (figure reproduced below)
* groundwater level records at 5 bores during the historic low lake levels
    * Bore 13
    * Bore 315
    * Bore 513
    * Bore 515
    * "Butterfields" bore
* a contoured map of the chane in groundwater level for every 1 meter drop in lake level (figure reproduced below)
* a contoured map which identifies the lake level where the groundwater level is unlikely to be affected by the lake level (figure reproduced below)
* discussion and conclusions

..figure:: ../historical_investigation/figures/historical_head_locs.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: Map of the historic groundwater monitoring bores.*

The key results from the appendix are:

* Variation in Lake Hawea levels below 329.66 m msl (330 m Dunedin 1958) are unlikely to have any impact on the groundwater levels.
* Groundwater levels further from the lake edge are less affected by variations in lake level.
* the threshold for lake level variations to affect groundwater levels varies by distance from the lake edge:
    * "A lake level of between 330 and 333m will influence the area within 2.8 km of the lake but no further"
    * "A lake level of between 333 and 336m will influence the area within 2.8 to 5.3 km of the lake but no further"

Digitization of the historical data and data access
------------------------------------------------------

All historical data was digitized and is included in the repository.  The geospatial data (contours and bore locations) were geo-referenced using Qgis. The maps of bore locations appear to have been distorted (either while printing or being scanned), therefore we manually adjusted the locations of the reported bores based on the available landmarks (road intersections etc.).  The contour maps contained less distortion, but should be considered indicative only. The digitized geospatial data available in the `base_data/georeferenced folder <../historical_investigation/base_data/georeferenced>`_.

The historic groundwater levels were digitized using the `WebPlotDigitizer <https://automeris.io/WebPlotDigitizer/>`_ software.  The raw digitized data is available in the `base_data folder <../historical_investigation/base_data>`_. The digitized data was then processed to convert to groundwater levels to meters above sea level (msl) from meters Dunedin 1958. The digitisation was then checked by comparing the digitised historic lake levels with the available lake level record.

.. figure:: ../historical_investigation/figures/lake_heads_from_hist_document.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: Comparison of the digitised lake levels with the available lake level record.*

The digitised groundwater levels are available in the `generated_data/historical_data.hdf file <../historical_investigation/generated_data>`_. The data is also available as csv files in the `generated_data/csv_archive <../historical_investigation/generated_data/csv_archive>`_ folder. For more information see the "Dataset and Resources" section at the end of this document.

Discussion of the historical results
---------------------------------------

A full re-analysis of the data is described below, but as a summary:

1. We generally agree with the level of the lake level at which groundwater levels are affected.
2. We disagree with the interpretation that the threshold for lake level variations to affect groundwater levels varies by distance from the lake edge. We believe that the observed insensitivities are better accounted for by the smoothing of the groundwater level response to lake level variations.

Re-analysis of Historical Lake Hawea Low Lake levels & corresponding groundwater levels
==========================================================================================

Observed groundwater level response to historic lake level variations
-----------------------------------------------------------------------

The digitised groundwater levels were plotted against the available lake level record.  The results are shown below.

.. figure:: ../historical_investigation/figures/historic_period_hds/bore_13_hds.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: Observed groundwater level response to historic lake level variations at bore 13.*

.. figure:: ../historical_investigation/figures/historic_period_hds/bore_315_hds.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: Observed groundwater level response to historic lake level variations at bore 315.*

.. figure:: ../historical_investigation/figures/historic_period_hds/bore_513_hds.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: Observed groundwater level response to historic lake level variations at bore 513.*

.. figure:: ../historical_investigation/figures/historic_period_hds/bore_515_hds.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: Observed groundwater level response to historic lake level variations at bore 515.*

.. figure:: ../historical_investigation/figures/historic_period_hds/bore_butterfields_hds.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: Observed groundwater level response to historic lake level variations at bore butterfields.*


Smoothed Extrema matching
---------------------------
#todo well lake extrema


Lake and Groundwater level data comparison
--------------------------------------------
#todo  lake_v_hds_[nearest|modelled]

Shifted level comparison
---------------------------
# todo well_lake_delta


Simple smoothing model
---------------------------

In the model build a simple smoothing model was developed to match the observed groundwater level response to lake level variations. The details for this model are described in the `model build documentation <../model_build/README.rst#lake-hawea-moraine-conceptual-model>`_.  The model was developed to match the observed groundwater level response to lake level variations at bore G40/0415.  The purpose of this model was to define the model structure required to match the observed groundwater level response to lake level variations. Here we apply the model to the historical bores to see where it deviates from the observed groundwater level response to lake level variations.

Simple smoothing model from bore G40/0415
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We applied the simple smoothing model developed for bore G40/0415 to the nearby historical Bore 315.  The results are shown below.

.. figure:: ../historical_investigation/figures/simple_smoothing_model/ssm_bore_315_g40_0415.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: Simple smoothing model trained on bore G40/0415 applied to the historical Bore 315.*


Bespoke simple smoothing models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition, we trained the simple smoothing model on the historical bore data (Bores 315, 515, Butterfields) after 1979-03-01 (once Lake Hawea levels returned to their normal opperational range). The results are shown below.

.. figure:: ../historical_investigation/figures/simple_smoothing_model/bespoke_ssm_bore_315.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: Bespoke simple smoothing model trained on bore 315.*

.. figure:: ../historical_investigation/figures/simple_smoothing_model/bespoke_ssm_bore_515.png

    :height: 650 px
    :align: center

.. class:: centered

        *Figure: Bespoke simple smoothing model trained on bore 515.*

.. figure:: ../historical_investigation/figures/simple_smoothing_model/bespoke_ssm_bore_butterfields.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: Bespoke simple smoothing model trained on bore butterfields.*


Simple smoothing model results and discussion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# todo

Model performance during Historic Low Lake levels
==================================================

To assess the current model preformance during the historic low lake levels we:

1. ran the existing optimised model (3d_v1d) for the period 1976-01-01 to 1983-01-01, extracted the predicted groundwater levels at the historical bore locations, and compared the results to the observed groundwater levels.
2. developed a new model (3d_v10a) which set the invert of the bund (see `model build documentation <../model_build/README.rst#lake-hawea-moraine-conceptual-model>`_) to 330 m msl and ran the new model for the period 1976-01-01 to 1983-01-01. We then extracted the predicted groundwater levels at the historical bore locations and compared the results to the observed groundwater levels.
3. Extracted the lake drop scenario results (see `Scenarios documentation <../Scenarios/README.rst#lake-drop-scenario-results>`_) at the historical bore locations, matched teh results so that the time that the lake drop scenario went below the 3d_v1a bund elevation (335m) matched the time that the observed lake levels went below the historically observed limit (330m msl), and compared the results to the observed groundwater levels.

3d_v1d model results
----------------------

The modelled vs observed groundwater levels for the 3d_v1d model are shown below.

.. figure:: ../historical_investigation/figures/3d_v1d_historical/bore_13_modelled.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: 3d_v1d model results for bore 13.*

.. figure:: ../historical_investigation/figures/3d_v1d_historical/bore_315_modelled.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v1d model results for bore 315.*

.. figure:: ../historical_investigation/figures/3d_v1d_historical/bore_513_modelled.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v1d model results for bore 513.*

.. figure:: ../historical_investigation/figures/3d_v1d_historical/bore_515_modelled.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v1d model results for bore 515.*

.. figure:: ../historical_investigation/figures/3d_v1d_historical/bore_butterfields_modelled.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v1d model results for bore butterfields.*

3d_v10a historical period model results
-----------------------------------------

The modelled vs observed groundwater levels for the 3d_v10a model are shown below.

.. figure:: ../historical_investigation/figures/3d_v10a_historical/bore_13_modelled.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: 3d_v10a model results for bore 13.*

.. figure:: ../historical_investigation/figures/3d_v10a_historical/bore_315_modelled.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v10a model results for bore 315.*


.. figure:: ../historical_investigation/figures/3d_v10a_historical/bore_513_modelled.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v10a model results for bore 513.*

.. figure:: ../historical_investigation/figures/3d_v10a_historical/bore_515_modelled.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v10a model results for bore 515.*

.. figure:: ../historical_investigation/figures/3d_v10a_historical/bore_butterfields_modelled.png
        :height: 650 px
        :align: center

.. class:: centered

            *Figure: 3d_v10a model results for bore butterfields.*

3d_v10a model period results
-----------------------------

As the 3d_v10a model was not optimised for the model period we also present the modelled vs observed groundwater level for the high frequency targets (`see the target documentation for more information <../targets_and_sensitive_sites/README.rst#high-and-moderate-frequency-targets`) for the 3d_v10a model.  The results are shown below.

.. figure:: ../historical_investigation/figures/3d_v10a_historical/reg_opt_period/hds_closeup_g40_0041.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: 3d_v10a model results for bore G40/0041.*

.. figure:: ../historical_investigation/figures/3d_v10a_historical/reg_opt_period/hds_closeup_g40_0366.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v10a model results for bore G40/0366.*

.. figure:: ../historical_investigation/figures/3d_v10a_historical/reg_opt_period/hds_closeup_g40_0367.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v10a model results for bore G40/0367.*

.. figure:: ../historical_investigation/figures/3d_v10a_historical/reg_opt_period/hds_closeup_g40_0415.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v10a model results for bore G40/0415.*

.. figure:: ../historical_investigation/figures/3d_v10a_historical/reg_opt_period/hds_closeup_g40_0416.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: 3d_v10a model results for bore G40/0416.*


Lake Drop scenarios (3d_v1d model)
-----------------------------------

Note we have only presented the lake drop 320 results here, but the results for the other lake drop scenarios are available in the `figures/lake_drop_scenarios <../historical_investigation/figures/lake_drop_scenarios>`_ folder.

.. figure:: ../historical_investigation/figures/lake_drop_scenarios/bore_13_lake_drop_320.png
   :height: 650 px
   :align: center

.. class:: centered

    *Figure: Lake drop scenario results for bore 13.*

.. figure:: ../historical_investigation/figures/lake_drop_scenarios/bore_315_lake_drop_320.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: Lake drop scenario results for bore 315.*

.. figure:: ../historical_investigation/figures/lake_drop_scenarios/bore_513_lake_drop_320.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: Lake drop scenario results for bore 513.*

.. figure:: ../historical_investigation/figures/lake_drop_scenarios/bore_515_lake_drop_320.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: Lake drop scenario results for bore 515.*

.. figure:: ../historical_investigation/figures/lake_drop_scenarios/bore_butterfields_lake_drop_320.png
    :height: 650 px
    :align: center

.. class:: centered

        *Figure: Lake drop scenario results for bore butterfields.*

Model performance discussion
-----------------------------
# todo

Conclusions and Recommendations
==================================

Dataset and Resources
=======================
# explain the data in the base_data, figures, and generated_data folders


Top readme addtiions
=====================
# todo
* add links to this readme
* add module index from this readme
* add 3d_v10a model to active branches
* check links



