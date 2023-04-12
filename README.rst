Hawea Transient groundwater model (Hawea Model)
===============================================
:Author:  Matt Dumont
:Date:  2021-11-02
:Version:  1.0.0
:Status:  Draft
:KSL project: Z22031HAW_hawea-model

.. figure:: ./support_figures/domain.png
   :width: 600
   :align: center

    The Hawea model domain.  The inactive portions of the model are coloured grey


The Hawea model domain. The model domain is a 3D model of the Hawea
aquifer systems including the Mangawera Valley.
The model domain is bounded by Lake Hawea to the North the Clutha River to
the South, and the hillslopes to the East and West The model domain is
17 km by 23.5 km. The model cell spacing is 100 m and the model is on a
regular North-South grid

Index
=====
.. contents:: Table of Contents




#todo

Modelling methodology and results
==============================

#todo

Git repo structure
==================

The full modelling process for the Hawea model was undertaken within
this Github repo. The only exceptions are several large datasets
(LIDAR/DEMs) which were simplified (code in repo) and then the
simplified product was saved in the Github Repo. This means that no
external datasets are necissary to completely recreate the Hawea model
and the full methodology is present in this Repo.

Repo index
----------

#todo

Python Environment
------------------
This model was developed in python on linux (ubuntu 20.04).  The python environment was created using the anaconda package manager.
The environment was created using the following command:



proprietary packages
--------------------

For the most part we relied on open source packages to create #todo

Branches and releases
=====================

The process of the model optimisation required multiple structural
changes to the model as well as changes to the objective function to
attain a satisfactory history match. These different structures and
changes were all set up as unique branches within the Repo. For more
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
-  Contains 3d structure around the Lake Hawea Moraine
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

-  Identical to “3d_v1a” except that the Bund elevation was set to 333
   MSL.
-  history matching results were similar to “3d_v1a” suggesting that the
   bund elevation is largely non-unique
-  retained to demonstrate the non-uniqueness of the 3d structure

terrace_only
~~~~~~~~~~~~

-  This model structure only includes the high terrace (south of Hawea
   Flat) to the clutha river
-  this optimisation was undertaken to see if the high terrace could be
   history matched (within the accepted parameter ranges) in isolation
   from the rest of the Hawea aquifer system.
-  History matching was not achieved.

previous branches (releases)
----------------------------

There are many previous branches that were issued as pre releases and
then deleted (effectively archived). There should be no reason for other
users to delve into these previous branches as they ended up with
unsatisfactory history matching; however they are available and briefly
described below (working notes) for completeness.

1.  Main (before 2/11/22) The main build branch. First structural
    version

2.  Structure v2, Changes:

    -  Increase parameterization via pilot points to Mangawera
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
    -  todo increase initial conductivity (to 50, 100 and 70 was too
       unstable)
    -  rch multiplier only by irrigated not irrigated bounds of
       multiplier 0.5-1.2

10. Structure_v9

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

11. Structure_v10

    -  Set weight of regular year targets to 0
    -  set each of the ‘h_hf’ targets equal weights despite different
       data lengths
    -  look/lower basement in dry cells near model boundaries
    -  NE hillside area (done)
    -  Near clutha river (done)
    -  I think I need some more pilot points
    -  Near pt 402 on camp hill moraine (move mangawera south?) (todo)
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

12. Structure_v11

    -  Move to 1 global recharge modifier (done)
    -  Much higher initial kh (lake=5, rest = 300) (in progress
    -  Lower sy, and lower sy bounds
    -  Change weights (lower low frequency targets)
    -  Bit of a hail mary before the weekend
    -  retired (even though I’m happy with the parameterization. If I
       want to change back to vll parameters do it from v12

13. Structure_v12

    -  Increase kh/sy parameterization in the near lake environment

14. p_lake

    -  As per structure_v11 but with a single additive parameter for
       lake heads (e.g. lake hds = lake hds + mod
    -  A test to see if the lake levels problems are sorted everything
       else works great?
    -  Note the parameter is offset by 100m as pyemu has bugs!

15. lake_bar

    -  Add a 1 cell thick barrier for kh
    -  Remove additional v12 parameterization

16. cond_int

    -  Try to fit the heads by simply setting lake conductance (1 cell
       width lake)

17. 3d_v1

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

