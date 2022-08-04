# -*- coding: utf-8 -*-
"""
qgis3_16

Created on Mon March 28 13:10:24 2022

@author: Jungho Park

This Automation script contructs a (Hawea) MODFLOW model using FloPy, 
DEM, the Scott's old Hawea model, the Rushton model and Hawea RC data and
generates a MODFLOW model. The generated model can be imported to Groundwater Vistas
or Aquaveo Groundwater Modeling System to utilize the graphical user interface. With
some modification, scenario models can be generated with minimal effort.

The EPSG is 2913 (NZGD2000).

Construction of a FloPy Model
#1. Set the modelling period and grid size.
#2. Create a model domain using ArcGIS or QGIS and get the extent of the vector file.
#3. Create MODFLOW Grid (Polygon) using the extent.
#4. Select the Grids using the model boundary and set "ibound" field of the selected grid (vector geopackage) to 1.
#5. Using QGIS or ArcGIS, process a DEM file and set "top" field of the grid with the mean elevation
#6. Create a FloPy MODFLOW
#7. MODFLOW Output Control (basic settings)
#8. MODFLOW NWT package (basic settings)
#9. Using the Scott's old model, adjust the bottom elevation.
#10. MODFLOW DIS package (basic settings)
#11. MODFLOW BAS package (basic settings)
#12. MODFLOW UPW package (basic settings)
#13. MODFLOW RIV package (time varying stages of Hawea and Clutha rivers, 'River_Level_Hawea.csv')
#14. MODFLOW GHB package (time varying lake level, 'Lake_Hawea.csv')
#15. Process Irrigation
#16. MODFLOW RCH package (time varying recharge rates using the Rushton model)
    'Soils_Hawea.csv', 'Rainfall_Hawea.csv', 
#17. MODFLOW WEL package (time varying pumping, 'hawea_allo_usage_data.csv', hillside recharge and irrigation)
#18. MODFLOW HOB package (time varying and constant observations for calibration targets, 'Target.csv')
#19. Write MODFLOW files
#20. Run the MODFLOW model
#21. Calibrate the model

Variable name conventions:
prefix np => Numpy array
prefix gp => Geopandas DataFrame
prefix df => Pandas DataFrame
prefix dic => Dictionary
prefix dt => Datetime variable
"""




import os
import numpy as np
from scipy.ndimage.filters import uniform_filter1d
import pandas as pd
import copy
import flopy
import flopy.utils.binaryfile as bf
import matplotlib.pyplot as plt
import math

import time
import datetime as dt
from datetime import timedelta

import geopandas as gp

# Point class
from shapely.geometry import Point 
# Polygon class
from shapely.geometry import Polygon





# Function definitions
# Calculate distance between two points
def dist(x1,y1,x2,y2):
    return(math.sqrt((x1-x2)**2+(y1-y2)**2))


# Find the MODFLOW j, i at x, y location using a flopy modflow variable
def findMfGrid(mf, Left1, Top1, x, y):
    # j,i = 74,47
    for j in range(mf.nrow-1):
        for i in range(mf.ncol-1):
            if x >= Left1 + np.sum(mf.dis.delr[:i]) and x <= Left1 + np.sum(mf.dis.delr[:i+1])\
                and y <= Top1 - np.sum(mf.dis.delc[:j]) and y >= Top1 - np.sum(mf.dis.delc[:j+1]):
                xfrac = (x - (Left1 + np.sum(mf.dis.delr[:i])))/mf.dis.delr[i]
                yfrac = ((Top1 - np.sum(mf.dis.delc[:j]))-y)/mf.dis.delc[j]
                return j,i,yfrac,xfrac
    return -1,-1,-1.0,-1.0 # When the element was not found


# Return the x, y location at the centre of j, i grid using a flopy modflow variable
def findMfLocation(mf, Left1, Top1, j, i):
    # j,i = 74,47
    return Left1 + np.sum(mf.dis.delr[:i])+mf.dis.delr[i]*0.5,\
        Top1 - np.sum(mf.dis.delc[:j])-mf.dis.delc[j]*0.5


# Find the elevation of a river at the nearest of xLoc, yLoc
# rivZList1 is a lit of the following items
# [X, Y, river conductivity zone, elevation, distance, slope]
# This function return the elevation and river conductivity zone
def findRivElev(rivZList1, xLoc, yLoc):
    iMin1, iMin2 = -1, -1
    minDist1, minDist2 = 1e8, 1e8
    len1 = len(rivZList1)
    # i = 0
    for i in range(len1):
        x1,y1 = rivZList1[i][0], rivZList1[i][1]
        dist1 = dist(xLoc,yLoc,x1,y1)
        if dist1<minDist2:
            if dist1<minDist1:
                minDist2 = minDist1
                minDist1 = dist1
                iMin2 = iMin1
                iMin1 = i
            else:
                minDist2 = dist1
                iMin2 = i
    frac = minDist2/(minDist1+minDist2)
    return rivZList1[iMin1][3]*frac + rivZList1[iMin2][3]*(1.0-frac), rivZList1[iMin1][2]


"""
Using dfSoils, dfRain and targetSM_Fraction, generate dicRushton and dicIrrigation.
dfSoils contains soil info for Rushton model (e.g., 'Soils_Hawea.csv').
dfRain is a rainfall and PET dataframe time series (e.g., 'Rainfall_Hawea.csv'). 
dfRain.Rainfall and PET are the precipitation and PET data.
TargetSM_Fraction is the target soil moisture fraction of PAW for irrigation.
If it is zero, irrigation calculation is not performed.
By increasing the TargetSM_Fraction, we can increase the amount of irrigation but the 
relationship is not linear. The total irrigation should not exceed the amount of 
groundwater and surface water intakes.
"""
def Rushton(dfSoils, dfRain, targetSM_Fraction, dicRushton, dicIrrigation):
    # These initial values are arbitrary values.
    # Thus, the first year Rushton model will not be relieable due to the unknown initial conditions.
    initNearSurfStor = 0.0
    initSMD = 8.0
    for j in range(len(dfSoils)):
        dicIrrigation[j]={}
        dicRushton[j]=pd.DataFrame(data = np.zeros([nPeriod,8]), index=dfRain.index, \
            columns=['Runoff', 'Infiltration', 'IrrigationDeficit', 'IrrigationApplied',\
            'NearSurfStor', 'TotalActualEvap', 'SoilMoistureDeficit', 'Recharge'])
        PAW = dfSoils.PAW[j] # TAW
        PRAW = dfSoils.PRAW[j] # RAW
        Fracstor = dfSoils.Fracstor[j]
        SCS = dfSoils.SCS[j]

        # If TargetSM is 0.0, irrigation is off
        # No irrigation for Hillside
        if j==0:
            TargetSM = 0.0
        else:        
            TargetSM = PAW*targetSM_Fraction
        SoilRetentionNum = 254.0*(100.0/SCS-1.0)
        for i in range(len(dfRain)):
            year = dfRain.DateT.iloc[i].year
            if year not in dicIrrigation[j].keys():
                dicIrrigation[j][year]=0.0
            rainfall = dfRain.Rainfall[i]
            # rushtonIdx = j*nPeriod+i
            # Calculate runoff
            if rainfall > 0.2*SoilRetentionNum:
                dicRushton[j].loc[i,'Runoff'] = (rainfall - 0.2*SoilRetentionNum)**2 \
                    /(rainfall+0.8*SoilRetentionNum)
            else:
                dicRushton[j].loc[i,'Runoff'] = 0.0
                
            # Calculate infiltration
            if i==0:
                dicRushton[j].loc[i,'Infiltration'] = rainfall - dicRushton[j].loc[i,'Runoff'] +\
                    initNearSurfStor
            else:
                dicRushton[j].loc[i,'Infiltration'] = rainfall - dicRushton[j].loc[i,'Runoff'] +\
                    dicRushton[j].loc[i-1,'NearSurfStor']
                    
            # previous Soil Moisture Deficit
            if i == 0:
                pSMD = initSMD
            else:
                pSMD = dicRushton[j].loc[i-1,'SoilMoistureDeficit']
                
            # Calculate irrigation
            if TargetSM > 0.0:
                # Calculate irrigation deficit and irrigation applied
                if pSMD-dicRushton[j].loc[i, 'Infiltration']>PAW-TargetSM:
                    dicRushton[j].loc[i, 'IrrigationDeficit'] = pSMD-dicRushton[j].loc[i, 'Infiltration']
                    dicRushton[j].loc[i, 'IrrigationApplied'] = dicRushton[j].loc[i, 'IrrigationDeficit']-\
                        (PAW-TargetSM)
                    dicIrrigation[j][year] += dicRushton[j].loc[i,'IrrigationApplied']
                else:
                    dicRushton[j].loc[i,'IrrigationDeficit'] = 0.0
                    dicRushton[j].loc[i,'IrrigationApplied'] = 0.0
            else:
                dicRushton[j].loc[i,'IrrigationDeficit'] = 0.0
                dicRushton[j].loc[i,'IrrigationApplied'] = 0.0
                    
            # Calculate Near Surface Storage
            if dicRushton[j].loc[i, 'Infiltration']+dicRushton[j].loc[i,'IrrigationApplied'] > dfRain.PET[i]:
                dicRushton[j].loc[i,'NearSurfStor'] = Fracstor*(dicRushton[j].loc[i, 'Infiltration'] +\
                        dicRushton[j].loc[i,'IrrigationApplied'] - dfRain.PET[i])
            else:
                dicRushton[j].loc[i,'NearSurfStor'] = 0.0
                
            # Calculate Total Actual Evaporation
            if pSMD < PRAW or dicRushton[j].loc[i, 'Infiltration']+dicRushton[j].loc[i,'IrrigationApplied']\
                >= dfRain.PET[i]:
                dicRushton[j].loc[i,'TotalActualEvap'] = dfRain.PET[i]
            elif dicRushton[j].loc[i, 'Infiltration']+dicRushton[j].loc[i,'IrrigationApplied'] < dfRain.PET[i]\
                and PAW >= pSMD >= PRAW:
                dicRushton[j].loc[i,'TotalActualEvap'] = dicRushton[j].loc[i, 'Infiltration']+\
                    dicRushton[j].loc[i,'IrrigationApplied'] + \
                    (dfRain.PET[i]-dicRushton[j].loc[i, 'Infiltration']-dicRushton[j].loc[i,'IrrigationApplied'])\
                        *((PAW-pSMD)/(PAW-PRAW))
            else:
                dicRushton[j].loc[i,'TotalActualEvap'] = dicRushton[j].loc[i, 'Infiltration'] + \
                    dicRushton[j].loc[i,'IrrigationApplied']
            
            # Calculate Soil Moisture Deficit
            if pSMD-dicRushton[j].loc[i, 'Infiltration']-dicRushton[j].loc[i,'IrrigationApplied']\
                +dicRushton[j].loc[i,'NearSurfStor']+dicRushton[j].loc[i,'TotalActualEvap'] < 0:
                dicRushton[j].loc[i,'SoilMoistureDeficit'] = 0.0
            else:
                dicRushton[j].loc[i,'SoilMoistureDeficit'] = pSMD-dicRushton[j].loc[i, 'Infiltration']\
                    -dicRushton[j].loc[i,'IrrigationApplied']+dicRushton[j].loc[i,'NearSurfStor']\
                    +dicRushton[j].loc[i,'TotalActualEvap']
            
            # Calculate Groundwater Recharge (mm)
            if dicRushton[j].loc[i,'SoilMoistureDeficit'] > 0:
                dicRushton[j].loc[i,'Recharge'] = 0.0
            else:
                dicRushton[j].loc[i,'Recharge'] = -1.0*(pSMD-dicRushton[j].loc[i, 'Infiltration']+\
                    +dicRushton[j].loc[i,'NearSurfStor']+dicRushton[j].loc[i,'TotalActualEvap'])         








# Set the start time to measure run time
start1 = time.time()

# Set the testLevel number
# The testLevel should be 3 and bSteay should be False for a normal model generation
# Any value smaller than 3 will produce a simpler model

# The testLevel number means
# 0 Basic (No GHB, simple starting head, simple kx values)
# 1 GHB, River, Basic recharge (simple kx values, simple recharge, simple well)
# 2 Full recharge (simple well)
# 3 All packages
testLevel = 3
# True for a steady State model for initial testing
bSteady = False





# #1. Set the modelling period and grid size.

# All data files are in the same directory of this script except GIS data.
# Pumping (hawea_allo_usage_data.csv), 
# surface irrigation (Hawea Irrigation Co - Lake Hawea Takes (daily).csv)
# and objservation data (GW_Level_Hawea.csv) start on
# 01/07/2014, 11/09/2014 and 25/07/2014 and end on 30/06/2021, 
# 1/7/2021, 21/02/2022, respectively.
# If there is a good initial condition, the model can start on 01/01/2013
# If it is difficult to find a good initial condition, the starting
# period should be much earlier.
# As the data ends in 2021, the model should end at the end of 2020 or
# it can run up to 30/06/2021.
# Due to the data availability, the model will not be stable in 2014. 
# So, the observation should start in 2015.
# if bShort is True, it will generate a short test model
bShort = False
if bShort:
    dateBegin=dt.datetime(2018,1,1)
else:    
    dateBegin=dt.datetime(2013,1,1)
dateEnd=dt.datetime(2020,12,31)
dtIndex = pd.date_range(dateBegin, dateEnd,freq='1D')
# obsStartDate is the start date for observation.
# Since the model may not be reliable during the initial time period,
# it would be better to start observation for calibration later.
if bSteady:
    obsStartDate = dt.datetime(dateBegin.year,1,1)
else:
    # The observation should not start from the first period for transient models
    if bShort:
        obsStartDate = dt.datetime(dateBegin.year,1,1)+timedelta(days=1)
    else:        
        obsStartDate = dt.datetime(2015,1,1)


# Directory setup
# mainDir is a directory for the flopy modflow model output
mainDir = './MODFLOW/'
if not os.path.exists(mainDir):
    os.mkdir(mainDir)
# gisDir is a directory for GIS data
gisDir = './GIS/'
if not os.path.exists(gisDir):
    os.mkdir(gisDir)





# #2. Create a model domain using ArcGIS or QGIS and get the extent of the vector file.
# We will construct a MODFLOW grid using this extent.
# modelBoundaryFile = gisDir + 'HaweaModelBoundary3.gpkg'
modelBoundaryFile = gisDir + 'HaweaModelBoundaryReduced.gpkg'
modelBoundary = gp.read_file(modelBoundaryFile)
# a polygon for the model domain
boundaryPoly= modelBoundary.geometry[0]

# Set the grid parameters
delX = 250.0
delY = 250.0
# Left = 1296250
Left = np.floor(modelBoundary.bounds.minx[0]/delX)*delX
# Bottom = 5032500
Bottom = np.floor(modelBoundary.bounds.miny[0]/delY)*delY
# Right = 1313750
Right = np.ceil(modelBoundary.bounds.maxx[0]/delX)*delX
# Top = 5057000
Top = np.ceil(modelBoundary.bounds.maxy[0]/delY)*delY
# Calculate the numbers of rows and columns of MODFLOW grids
nrow = int((Top-Bottom)/delY)
ncol = int((Right-Left)/delX)
# Set the delr and delc values of MODFLOW grids
delr = [float(delX) for i in range(ncol)]
delc = [float(delY) for i in range(nrow)]
# Number of layers of MODFLOW grids
nlay = 1


# Read rainfall and PET.
dfRain = pd.read_csv('Rainfall_Hawea.csv',parse_dates={'DateT':[0]}, dayfirst=True, 
            header=0, low_memory=False)
# Cut the rainfall and PET data using the modelling period.
dfRain = dfRain.loc[(dfRain.DateT>=dateBegin) & (dfRain.DateT<=dateEnd)]
dfRain.reset_index(inplace=True)
# Numpy array of the rainfall
npRain = dfRain.Rainfall.to_numpy()
# Set the nPeriod using the number of modelling period.
nPeriod = len(dfRain)





# #3. Create MODFLOW Grid (Polygon) using the extent (Model Boundary).
# #4. Select the Grids using the model boundary and set "ibound" field of the selected grid (vector geopackage) to 1.
# MF_extent is the extent of a MODFLOW model boundary
MF_extent = "{a},{b},{c},{d}".format(a=Left, b=Right, c=Bottom, d=Top)

# MODFLOW grid generation
name_ext2 = "mf_grid.gpkg"
grid_file = gisDir + name_ext2
crsStr="EPSG:2193"
polygons = []
row = []
col = []
for j in range(nrow):
    yLoc1 = Top - sum(delc[:j])
    yLoc2 = yLoc1 - delc[j]
    for i in range(ncol):
        xLoc1 =  Left + sum(delr[:i])
        xLoc2 = xLoc1 + delr[i]
        polygons.append(Polygon([(xLoc1,yLoc1), (xLoc2,yLoc1),
        (xLoc2, yLoc2), (xLoc1, yLoc2)]))
        row.append(j+1)
        col.append(i+1)

gpMfGrid = gp.GeoDataFrame({'geometry':polygons})
gpMfGrid.set_crs(crsStr, inplace=True)
gpMfGrid.reset_index()
gpMfGrid['grid_id']=gpMfGrid.index+1
gpMfGrid['row']=row
gpMfGrid['col']=col
gpMfGrid['ibound']=0
gpMfGrid.loc[gpMfGrid.intersects(boundaryPoly),'ibound'] = 1

gpMfGrid.to_file(grid_file, driver="GPKG")






# #5. Using QGIS, process a DEM file covering the model domain
# and set "top_mean" field of the grid_file (mf_grid2.gpkg) with the mean elevation
# Evaluate Zonal Statistics (Process Toolbox->Zonal Statistics) using DEM (southi_15mdem_Hawea.tif) and mf_grid.gpkg
# Use top_ as output column prefix and the output file should be mf_grid2.gpkg
# Top elevation
grid_file = gisDir + "mf_grid2.gpkg"
# Read the grid_file
gpMfGrid = gp.read_file(grid_file)
# Set the top of the model domain
topDEM = gpMfGrid.top_mean.to_numpy().reshape(nrow,ncol)





# #6. Create a skeleton FloPy MODFLOW
# Units are days and meters
# Start of MODFLOW
modelname = 'Hawea1'
model_ws= mainDir
exeName = 'MODFLOW-NWT_64.exe'
mfVersion = 'mfnwt'
mf = flopy.modflow.Modflow(modelname, exe_name=exeName, version=mfVersion, model_ws=model_ws)





# #7. MODFLOW Output Control
# stress_period_data is a dictionary of output control list
# The dictionary key is a tuple with the zero-based period and step (IPEROC, ITSOC) for 
# each print/save option list. If stress_period_data is None, then heads are saved 
# for the last time step of each stress period. (default is None)
ocDic = {}
# The list can have any valid MODFLOW OC print/save option:
# PRINT HEAD, PRINT DRAWDOWN, PRINT BUDGET, SAVE HEAD, SAVE DRAWDOWN, SAVE BUDGET, SAVE IBOUND
# The lists can also include (1) DDREFERENCE in the list to reset drawdown reference to the period and step and (2) a list of layers for PRINT HEAD, SAVE HEAD, PRINT DRAWDOWN, SAVE DRAWDOWN, and SAVE IBOUND.
# stress_period_data = {(0,1):[‘save head’]}) would save the head for the second timestep in the first stress period.
# ocDic[(k,0)] = spd = {(0, 0): ["print head", "print budget", "save head", "save budget"]}
ocLst = ['save head','save budget']
if bSteady:
    ocDic[(0,0)]=copy.deepcopy(ocLst)
else:
    for k in range(nPeriod):
        ocDic[(k,0)]=copy.deepcopy(ocLst)
oc = flopy.modflow.ModflowOc(mf, stress_period_data=ocDic, compact=True)





# #8. MODFLOW NWT Package
# MODFLOW NWT package is used for rewetting option but any package can be used for one layer model.
# headtol=1e-5,fluxtol=100,linmeth=2,options='COMPLEX',thickfact=1e-4
nwt = flopy.modflow.ModflowNwt(mf, headtol=1e-4, iprnwt=1, maxiterout=1000,\
                               linmeth=2, options='COMPLEX')





# #9. Using the Scott's old model, adjust the bottom elevation.
# Read the Scott's model and extract the bottom data.
LeftS = 1296000
BottomS = 5032000
modelNameS = 'gv10'
modelS_ws = './Scott/'
nameFileScott = modelNameS+'.nam'
mfS = flopy.modflow.Modflow.load(nameFileScott, version=mfVersion, exe_name=exeName, \
  model_ws=modelS_ws)

topS = mfS.dis.top.array
botmS = mfS.dis.botm.array
thicknessS = topS - botmS.reshape(mfS.dis.nrow,mfS.dis.ncol)
delcS = mfS.dis.delc.array
delrS = mfS.dis.delr.array
widthS = sum(delrS)
heightS = sum(delcS)
XLocS = LeftS + delrS.cumsum()-delrS/2.0
YLocS = BottomS + heightS -(delcS.cumsum()-delcS/2.0)
# The centre point of the elements of Scott's model
centerLoc = np.array([(x,y) for y in YLocS for x in XLocS])





# #10. MODFLOW DIS package (Discretization)
# Model geometry setup. 
# delX, delY, top, bottom, # of periods, period linegth, # of steps, steady state vs transient
# ztop is the mean elevation of the DEM
ztop = gpMfGrid.top_mean.to_numpy().reshape((nrow,ncol))

# The bottom is set to top - 20 metres.
zbot = (ztop - 20.0).reshape((1,nrow,ncol))

# Number of steps.
nstp = 2
# Setup steady state/transient setting
steady = []
if bSteady:
    steady.append(True)
    dis = flopy.modflow.ModflowDis(mf, nlay, nrow, ncol, delr=delY, delc=delX, top=ztop,\
        botm=zbot, nper=1, perlen=1.0, steady=steady, nstp=nstp, tsmult=1)
else:
    for k in range(nPeriod):
        steady.append(False)
    dis = flopy.modflow.ModflowDis(mf, nlay, nrow, ncol, delr=delY, delc=delX, top=ztop,\
        botm=zbot, nper=nPeriod, perlen=1.0, steady=steady, nstp=nstp, tsmult=1)


top = mf.dis.top.array
delc = mf.dis.delc.array
delr = mf.dis.delr.array
XLoc = Left + delr.cumsum()-delr/2.0
YLoc = Top -(delc.cumsum()-delc/2.0)


# Transfer the bottom from Scott's to my model
topS2 = topS.flatten()
botmS2 = botmS.flatten()
# Copy the top to botm2 and make adjustment
botm2 = gpMfGrid.top_mean.to_numpy().reshape((nrow,ncol)).copy()
# topDEM is the mean elevation of the grids
for j in range(topDEM.shape[0]):
    for i in range(topDEM.shape[1]):
        xloc, yloc = findMfLocation(mf, Left, Top, j, i)
        # xloc = XLoc[i]
        # yloc = YLoc[i]
        tLoc = np.array([xloc,yloc])
        # Calculate the distance of Scott's model elements
        # from the current main MODFLOW elelment location
        dist1 = np.linalg.norm(centerLoc - tLoc, axis=1)
        # Obtain the index of the closest element of Scott's model
        idx = np.argmin(dist1)
        # Calculate the thickness from Scott's model
        thick1 = topS2[idx] - botmS2[idx]
        # If the thickness is less than 40, make it 40.
        if thick1<40.0:
            botm2[j,i]=top[j,i]-40.0
        else:
            botm2[j,i]=top[j,i]-thick1
        # Make sure the bottom is less than or equal to 260.0
        # The water table is expected to be at least 260. 
        # This will prevent dry cells.
        if botm2[j,i]>260.0: # min bottom 260?
            botm2[j,i]=260.0




    
# #11. MODFLOW BAS package
# Set ibound from the grid file.
# Set the initial head from the prepared head binary file.
ibound = gpMfGrid.ibound.to_numpy().reshape((nlay,nrow,ncol))
strt = np.ones((nlay, nrow, ncol), dtype=np.float32)*900.0
bas = flopy.modflow.ModflowBas(mf, ibound=ibound, strt=strt)





# #12. MODFLOW UPW package
# Constant values of 10 and 1 are assigned for the horizontal and vertical hydraulic conductivity:
# kx = 2.45759 # calibrated value
kx = np.ones((1, nrow,ncol))*20.0
# if layvka==0, VKA is vertical hydraulic conductivity, if not, VKA is the ratio of HK to VK
upw = flopy.modflow.ModflowUpw(mf, laytyp=1, hk=kx, layvka=1, vka=1, ss=1e-5, \
                               sy=0.15, ipakcb=53, unitnumber=25)





# #13. MODFLOW RIV package (time varying stages of Hawea and Clutha rivers, 'River_Level_Hawea.csv')
# Create 3D polyline river
# Functional Surface->Interplate Shape->Using Terrain data, River.shp and Linear method
# Read the riverZ file and process it to make it monotonously increase

# rvCond1 = 6.178298E-02 Calibrated value
rvCond1 = 10000
rvCond2 = 10001
rvCond = [[rvCond1,rvCond1,rvCond1,rvCond1],[rvCond2,rvCond2,rvCond2,rvCond2],\
          [rvCond2]]
rivZShp = "RiversZ.shp"
rivZShp_file = gisDir + rivZShp
dfRivZShp = gp.read_file(rivZShp_file)
interval = 250
rivZList = []
# j = 0
for j in range(len(rvCond)):
    data = np.flip(np.asarray(dfRivZShp.iloc[j].geometry),axis=0)
    data1=np.c_[data,np.zeros((data.shape[0],1)),np.zeros((data.shape[0],1)), \
                np.zeros((data.shape[0],1))]
    nDiv = int(np.ceil(data1.shape[0]/float(len(rvCond[j]))))
    # Universal spline calculation
    for i in range(0,data1.shape[0]):
        dist1 = 0.0
        data1[i,5] = i//nDiv
        if i>0:
            x,y,x1,y1 = data1[i][0],data1[i][1],data1[i-1][0],data1[i-1][1]
            dist1 = dist(x,y,x1,y1)
            data1[i,3]=data1[i-1,3]+dist1
    # spl=UnivariateSpline(data1[:,3],data1[:,2],s=0.5)
    # data1[:,4]=spl(data1[:,3])
    # Moving average calculation
    N = 400 # 300 is the minimum
    data1[:,4] = uniform_filter1d(data1[:,2], size=N, mode='nearest')
    dfTemp1 = pd.DataFrame(data1[:,4])
    # dfTemp1.to_clipboard(index=False,header=False)
    cnt = 0
    for i in range(1,data1.shape[0]):
        if data1[i][4]>data1[i-1][4]:
            cnt+= 1
            print('Not decreasing:{0},{1}'.format(j,i))
                
    dist1 = 0.0
    slope = 0.0
    prevData = 0
    tList = []

    for i in range(0,data1.shape[0],interval):
        if i>0:
            x,y,x1,y1 = data1[i][0],data1[i][1],data[i-interval][0],data[i-interval][1]
            dist1 = dist(x,y,x1,y1)
            val = np.mean(data[i-interval:i+interval],axis=0)[2]
            slope = (val-prevData)/dist1
            if slope>0:
                print('Slope:{0} is positve at {1},{2}'.format(slope,j,i))
        else:
            val = data1[i][2]
        tList.append([data1[i][0],data1[i][1],int(data1[i][5]),val,dist1,slope])
        prevData = val
    if data1.shape[0]%(interval) >0:
        x1,y1 = data1[-1][0],data1[-1][1]
        dist1 = dist(x,y,x1,y1)
        val = data[-1][2]
        slope = (val-prevData)/dist1
        # X, Y, river conductivity zone, elevation, distance, slope
        tList.append([data1[-1][0],data1[-1][1],int(data1[i][5]),val,dist1,slope])
    rivZList.append(tList)
del(tList)


# River package
riverToRemove=[]


# Hawea River at Camphill Bridge(1302363	5049022)
HaweaRiverCamphillBridge = Point(1302363,5049022)
elevHawaeCamphill,condZone1 = findRivElev(rivZList[0], HaweaRiverCamphillBridge.x, \
                                       HaweaRiverCamphillBridge.y)
# Clutha River at 2200 m (1307859, 5038569)
Clutha2200 = Point(1307859, 5038569)
elevClutha2200,condZone2 = findRivElev(rivZList[1], Clutha2200.x, Clutha2200.y)
CluthaIdxs = findMfGrid(mf, Left, Top, Clutha2200.x, Clutha2200.y)

riverShpFile = gisDir + 'Rivers.shp'
riverShp = gp.read_file(riverShpFile)
rivList = []
iRivList = 0
gpMfGrid['iRiver'] = 0
gpMfGrid['rivElev'] = 0.0
gpMfGrid['rivCondZone'] = 0
rivMat = np.zeros((nrow,ncol),dtype=int)
# i=0
for i in range(len(riverShp)):
    riverPoly= riverShp.geometry[i]
    dfTemp = gpMfGrid.loc[gpMfGrid.intersects(riverPoly)]
    # j = 0
    for j in range(dfTemp.shape[0]):
        rowVal = dfTemp.iloc[j]
        iCol, iRow = rowVal.col, rowVal.row
        bInclude = True
        if 'riverToRemove' in locals():
            for row in riverToRemove:
                if row[0]==iRow and row[1]==iCol:
                    bInclude = False
                    break
        if bInclude:
            idx1 = dfTemp.index[j]
            xLoc, yLoc = Left + (iCol-0.5)*delX, Top - (iRow-0.5)*delY
            elev1,condZone = findRivElev(rivZList[i], xLoc, yLoc)
            gpMfGrid.loc[idx1,'rivElev']=elev1
            gpMfGrid.loc[idx1,'rivCondZone']=condZone
            gpMfGrid.loc[idx1,'iRiver'] = i+1


# i = 0
for i in range(len(riverShp)):
    dfTemp = gpMfGrid.loc[gpMfGrid.iRiver==i+1].sort_values('rivElev',ascending=False)
    # j = 0
    for j in range(dfTemp.shape[0]):
        rowVal = dfTemp.iloc[j]
        iCol, iRow = rowVal.col, rowVal.row
        xLoc, yLoc = Left + (iCol-0.5)*delX, Top - (iRow-0.5)*delY
        elev1,condZone = findRivElev(rivZList[i], xLoc, yLoc)
        # Fix the bottom elevation
        if botm2[iRow,iCol]>elev1-3.0:
            botm2[iRow,iCol]=elev1-3.0
        rivMat[iRow-1,iCol-1]=1
        rivList.append([0,iRow-1,iCol-1,0.0,rvCond[i][condZone],elev1-3.0,i+1]) # Assumes the bottom is 3.0m below the measured surface
        if iRow-1 == CluthaIdxs[0] and iCol-1 == CluthaIdxs[1]:
            idxClutha2200 = iRivList                
        iRivList += 1


# Read river stage
dfRiver_Level = pd.read_csv('River_Level_Hawea.csv',parse_dates={'DateT':[0]}, dayfirst=True, 
            header=0, low_memory=False)
dfRiver_Level = dfRiver_Level.loc[(dfRiver_Level.DateT>=dateBegin) & (dfRiver_Level.DateT<=dateEnd)]
dfRiver_Level.reset_index(inplace=True)


# Construct river dictionary data for RIV package
rivDic = {}
# TODO: I need to interpolate the river stages from Hawea river to at 2200m downstream
nRivList = len(rivList)
if bSteady:
    # i = 0
    for i in range(1):
        rivList2 = copy.deepcopy(rivList)
        rivList3 = copy.deepcopy(rivList)
        for j in range(nRivList):
            # Adjust the daily river stage
            if rivList2[j][6]==1:# For Hawea river
                rivList2[j][3] = dfRiver_Level.Level_Camphill[i]+\
                    rivList2[j][5]+3.0-elevHawaeCamphill # set the min(base) stage to 3.0
                rivList3[j][3] = dfRiver_Level.Level_Camphill[i]+\
                    rivList3[j][5]+3.0-elevHawaeCamphill # set the min(base) stage to 3.0
                if i==0:
                    iHaweaRiver = j+1
            else: # For Clutha River
                if i==0 and rivList2[j][6]==2: # For Clutha river
                    iClutha = j+1
                rivList2[j][3] = dfRiver_Level.Stage_Clutha2200[i]+\
                    rivList2[j][5]+3.0-elevClutha2200 # set the min(base) stage to 3.0
                rivList3[j][3] = dfRiver_Level.Stage_Clutha2200[i]+\
                    rivList3[j][5]+3.0-elevClutha2200 # set the min(base) stage to 3.0
        # Smoothly connect the first river (Hawea river) and the second river (Clutha)
        diff1 = rivList2[iHaweaRiver-1][3]-rivList2[iHaweaRiver][3]
        for j in range(iHaweaRiver, idxClutha2200):
            rivList2[j][3] += (idxClutha2200-j)/(idxClutha2200-iHaweaRiver-1)*diff1
        diff2 = rivList2[iHaweaRiver][3]-rivList2[-1][3]
        for j in range(iClutha, nRivList):
            rivList2[j][3] += (j-iClutha)/(nRivList-iClutha)*diff2
        for j in range(nRivList):
            del(rivList2[j][6])
        rivDic[i] = copy.deepcopy(rivList2);
else:
    for i in range(nPeriod):
        rivList2 = copy.deepcopy(rivList)
        rivList3 = copy.deepcopy(rivList)
        for j in range(nRivList):
            # Adjust the daily river stage
            if rivList2[j][6]==1:# For Hawea river
                rivList2[j][3] = dfRiver_Level.Level_Camphill[i]+\
                    rivList2[j][5]+3.0-elevHawaeCamphill # set the min(base) stage to 3.0
                rivList3[j][3] = dfRiver_Level.Level_Camphill[i]+\
                    rivList3[j][5]+3.0-elevHawaeCamphill # set the min(base) stage to 3.0
                if i==0:
                    iHaweaRiver = j+1
            else: # For Clutha River
                if i==0 and rivList2[j][6]==2: # For Clutha river
                    iClutha = j+1
                rivList2[j][3] = dfRiver_Level.Stage_Clutha2200[i]+\
                    rivList2[j][5]+3.0-elevClutha2200 # set the min(base) stage to 3.0
                rivList3[j][3] = dfRiver_Level.Stage_Clutha2200[i]+\
                    rivList3[j][5]+3.0-elevClutha2200 # set the min(base) stage to 3.0
        # Smoothly connect the first river (Hawea river) and the second river (Clutha)
        diff1 = rivList2[iHaweaRiver-1][3]-rivList2[iHaweaRiver][3]
        for j in range(iHaweaRiver, idxClutha2200):
            rivList2[j][3] += (idxClutha2200-j)/(idxClutha2200-iHaweaRiver-1)*diff1
        diff2 = rivList2[iHaweaRiver][3]-rivList2[-1][3]
        for j in range(iClutha, nRivList):
            rivList2[j][3] += (j-iClutha)/(nRivList-iClutha)*diff2
        for j in range(nRivList):
            del(rivList2[j][6])
        rivDic[i] = copy.deepcopy(rivList2);
# stress_period_data =
# {0: [
#     [lay, row, col, stage, cond, rbot],
#     [lay, row, col, stage, cond, rbot],
#     [lay, row, col, stage, cond, rbot]
#     ],
# 1:  [
#     [lay, row, col, stage, cond, rbot],
#     [lay, row, col, stage, cond, rbot],
#     [lay, row, col, stage, cond, rbot]
#     ], ...
# kper:
#     [
#     [lay, row, col, stage, cond, rbot],
#     [lay, row, col, stage, cond, rbot],
#     [lay, row, col, stage, cond, rbot]
#     ]
# }
riv = flopy.modflow.ModflowRiv(mf, stress_period_data=rivDic)

# Reset the bottom to prevent the river from being below the bottom of the layer
zbot = botm2.reshape((1,nrow,ncol))


# Update Discretization package
if bSteady:
    dis = flopy.modflow.ModflowDis(mf, nlay, nrow, ncol, delr=delY, delc=delX, top=ztop,\
        botm=zbot, nper=1, perlen=1.0, steady=steady, nstp=nstp, tsmult=1)
else:
    dis = flopy.modflow.ModflowDis(mf, nlay, nrow, ncol, delr=delY, delc=delX, top=ztop,\
        botm=zbot, nper=nPeriod, perlen=1.0, steady=steady, nstp=nstp, tsmult=1)


    


# #14. MODFLOW GHB package (time varying lake level, 'Lake_Hawea.csv')
# ghc1=8.884816E-02 Calibrated value
ghc1=50000
ghbConds = [ghc1, ghc1, ghc1]
gpMfGrid['iLake'] = 0
lakeGHBShpFile = gisDir + 'LakeGHB.shp'
lakeGHBShp = gp.read_file(lakeGHBShpFile)
ghbCells =[]
lakeGHBList = []
# i=0
for i in range(len(lakeGHBShp)):
    lakePoly= lakeGHBShp.geometry[i]
    gpMfGrid.loc[gpMfGrid.intersects(lakePoly),'iLake'] = i+1
    dfTemp = gpMfGrid.loc[gpMfGrid.intersects(lakePoly)]
    nDiv = int(np.ceil(len(dfTemp)/float(len(ghbConds))))
    for j in range(dfTemp.shape[0]):
        rowVal = dfTemp.iloc[j]
        ghbCells.append([0,rowVal.row-1,rowVal.col-1,0.0,ghbConds[j//nDiv],j//nDiv+1]) #

gpMfGrid.to_file(grid_file, driver="GPKG")

dfLake = pd.read_csv('Lake_Hawea.csv',parse_dates={'DateT':[0]}, dayfirst=True, 
            header=0, low_memory=False)
dfLake = dfLake.loc[(dfLake.DateT>=dateBegin) & (dfLake.DateT<=dateEnd)]
dfLake.reset_index(inplace=True)


ghbDic = {}
# stress_period_data =
# {0: [
#     [lay, row, col, stage, cond],
#     [lay, row, col, stage, cond],
#     [lay, row, col, stage, cond],
#     ],
# 1:  [
#     [lay, row, col, stage, cond],
#     [lay, row, col, stage, cond],
#     [lay, row, col, stage, cond],
#     ], ...
# kper:
#     [
#     [lay, row, col, stage, cond],
#     [lay, row, col, stage, cond],
#     [lay, row, col, stage, cond],
#     ]
# }
# Lake Hawea level
for i in range(len(ghbCells)):
    del(ghbCells[i][5])
if bSteady:
    for j in range(1):
        for i in range(len(ghbCells)):
            ghbCells[i][3] = dfLake.LakeLevel_m[j]
        ghbDic[j]=copy.deepcopy(ghbCells)
else:
    for j in range(nPeriod):
        for i in range(len(ghbCells)):
            ghbCells[i][3] = dfLake.LakeLevel_m[j]
        ghbDic[j]=copy.deepcopy(ghbCells)

if testLevel==0:
    if 'GHB' in mf.get_package_list():
        mf.remove_package('GHB')
else:
    ghb = flopy.modflow.ModflowGhb(mf, stress_period_data=ghbDic)





# #15. Process Irrigation
# Irrigation map read
gpIrrigation = gp.read_file('GIS\\Otago Irrigated Area Layer 26Oct2021.shp')
# gpIrrigation['iriGrid']=gpIrrigation.index
# Find grid cells that contain an irrigation polygon (This is slow)
start = time.time()
gpMfGrid['iIrrigation'] = np.nan
for i in range(len(gpIrrigation.geometry)):
    gpMfGrid.loc[gpMfGrid.geometry.centroid.intersects(gpIrrigation.geometry[i]),'iIrrigation'] = 1
for j in range(nrow):
    for i in range(ncol):
        if ibound[0,j,i]<=0:
            gpMfGrid.loc[j*ncol+i,'iIrrigation']=np.nan
print(time.time()-start)
# gpMfGrid.to_file(grid_file, driver="GPKG")





# #16. MODFLOW RCH package (time varying recharge rates using the Rushton model)
# Read soil data table
# The table has data (e.g., PAW) for Rushton model
dfSoils = pd.read_csv('Soils_Hawea.csv')
nSoils = len(dfSoils)
# Create a soil map from PAW to the row of the table
soilMap = {}
for i in range(len(dfSoils)):
    soilMap[dfSoils.PAW[i]] = i


# Read soil map and set the soil type at each grid location
soilname = "LowlandSoils2.gpkg"
soil_file = gisDir + soilname
dfSoil = gp.read_file(soil_file)
# j,i=30,35
# This takes more than 375 seconds
gpMfGrid['iRch'] = -1
cIdx = gpMfGrid.columns.get_loc('iRch')
if testLevel>1:
    # It takes 390 seconds
    start = time.time()
    # j,i = 30,41
    for j in range(nrow):
        for i in range(ncol):
            xloc = XLoc[i]
            yloc = YLoc[j]
            tPoint = Point(xloc,yloc)
            poly = dfSoil.intersects(tPoint)
            idx = -1
            if len(dfSoil[poly==True])>0 and not dfSoil[poly==True].PAW.isna().iloc[0]:
                paw = int(dfSoil[poly==True].PAW)
                idx = soilMap[paw]
            elif ibound[0,j,i]>0:
                idx = 0
            gpMfGrid.iloc[j*ncol+i,cIdx] = idx
    print(time.time()-start)


# Calculate areas for each soil type
areaSoils = {}
for i in np.sort(gpMfGrid.iRch.unique()):
    if i>=0:
        areaSoils[i]=np.sum(gpMfGrid[gpMfGrid.iRch==i].geometry.area)


# Recharge and Irrigation calculation using the Rushton model
# If targetSM_Fraction is 0.0, irrigation is off
# It took 34 seconds
start = time.time()
dicRushton = {}
dicIrrigation = {}
targetFracs = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 2]
# Calculate the Rushton recharge models at 0, 0.4, 0.8, 1.2, 1.6 targetSM_Fraction
irrigationYear = {}
for i in range(len(targetFracs)):
    irrigationYear[i] = {}
    targetSM_Fraction = targetFracs[i]
    tdicRushton = {}
    tdicIrrigation = {}
    Rushton(dfSoils, dfRain, targetSM_Fraction, tdicRushton, tdicIrrigation)
    dicRushton[i]=tdicRushton
    for j in tdicIrrigation.keys():
        if j in areaSoils.keys():
            dicIrrigation[i]=tdicIrrigation
            for k in tdicIrrigation.keys():
                irrigationYear[i][k] = dicIrrigation[i][k] * areaSoils[j]/1000.0 # convert mm to m
print(time.time()-start)


# Adjust the targetSM_Fraction against the surface water intake + pumping
# Needs to be finished
for i in range(len(targetFracs)):
    pass

# Setup recharge array
# npRecharge = np.zeros((nPeriod,nrow,ncol))
# k=2 is temporary setting. Needs to be finished.
k = 2
if testLevel<=1:
    rechMat = np.ones((nPeriod,nrow,ncol))*0.8
else:
    rechMat = np.zeros((nPeriod,nrow,ncol))
    for j in range(nrow):
        for i in range(ncol):
            idx = gpMfGrid.iloc[j*ncol+i,cIdx]
            if idx>=0:
                rech = dicRushton[k][idx].Recharge.to_numpy()
                rechMat[:,j,i]=rech


rech = {}
if bSteady:
    for i in range(1):
        #rech[i]=rechMat[i,:,:]*2e-4 # Convert mm to m
        rech[i]=np.mean(rechMat,axis=0)*1.e-3 # Convert mm to m
else:
    for i in range(nPeriod):
        #rech[i]=rechMat[i,:,:]*2e-4 # Convert mm to m
        rech[i]=rechMat[i,:,:]*1.e-3 # Convert mm to m

rch = flopy.modflow.ModflowRch(mf,rech=rech)





# #17. MODFLOW WEL package (time varying pumping, 'hawea_allo_usage_data.csv', hillside recharge and irrigation)
# Set matrix for wells
wellMat = np.zeros((nPeriod,nlay,nrow,ncol))
wellMat2 = np.zeros((nlay,nrow,ncol))
# Read water usage data
pumpLst = []
gpMfGrid['iWell'] = 0
cIdx = gpMfGrid.columns.get_loc('iWell')
dfWell = pd.DataFrame(index=dtIndex)

# ORC Water Metre data
pumpTableFile = gisDir + 'PumpsHawea.csv'
dfPumpTable = pd.read_csv(pumpTableFile, header=0, low_memory=False, encoding = 'ISO-8859-1')
dfPumpTable.index = dfPumpTable.SiteName

# Hillside recharge using the Rushton model (soil index==0 provides the hillside recharge model)
rechHillFile = gisDir + 'RechargePoints.gpkg'
gpHillRechPoints = gp.read_file(rechHillFile)
rechHill = []
for k in range(len(gpHillRechPoints)):
    easting = gpHillRechPoints.loc[k].geometry.x
    northing = gpHillRechPoints.loc[k].geometry.y
    j,i,yfrac,xfrac = findMfGrid(mf, Left, Top, easting, northing)
    if i>=0 and j>=0:
        if ibound[0,j,i]>0:
            # Both recharge and runoff will be eventually fed into streams. So, use them both.
            # Positive values to add the water into the model
            values = gpHillRechPoints.loc[k,'AreaH']*(dicRushton[0][0].Recharge+dicRushton[0][0].Runoff).to_numpy()/1000.0 # convert mm to m
            wellMat[:,0,j,i] += values
            wellMat2[0,j,i] = wellMat[:,0,j,i].mean()


waterMetreFile = 'ORC_WaterMetre.csv'
dfWaterMetre = pd.read_csv(waterMetreFile, header=0, parse_dates={'DateT':[1]}, low_memory=False, encoding = 'ISO-8859-1')
# Number of sites = 38
sites = dfWaterMetre.Site.unique()

# site = sites[0]
for site in sites:
    iSite = int(site[3:])
    easting = dfPumpTable.loc[dfPumpTable.SiteName==site].Easting.iloc[0]
    northing = dfPumpTable.loc[dfPumpTable.SiteName==site].Northing.iloc[0]
    j,i,yfrac,xfrac = findMfGrid(mf, Left, Top, easting, northing)
    gpMfGrid.iloc[j*ncol+i,cIdx] = 1
    dfTemp = copy.deepcopy(dfWaterMetre[dfWaterMetre.Site==site])
    dfTemp.set_index('DateT', inplace=True)
    dfTemp.sort_values(by=['DateT'], inplace=True)
    if False:
        dfTemp['pDate'] = dfTemp.index.shift(periods=1,freq='D')
        dfTemp['diffDate'] = dfTemp.index - dfTemp['pDate']
        if len(dfTemp[dfTemp.diffDate!=timedelta(days=-1)])>0:
            print(site)
    dfWell[site]=dfTemp.Value
    # Wells are assumed to be in the top layer
    wellMat[:,0,j,i] += dfWell[site]
    wellMat2[0,j,i] = wellMat[:,0,j,i].mean()


# negative flux is pumping
# well_stress_period_data = {0: [
# [lay, row, col, flux], [lay, row, col, flux], [lay, row, col, flux] ],
# 1: [
# [lay, row, col, flux], [lay, row, col, flux], [lay, row, col, flux] ], …
# kper:
# [ [lay, row, col, flux], [lay, row, col, flux], [lay, row, col, flux] ]
# }
wellDic = {}
if bSteady:
    wells = []
    for j in range(nrow):
        for i in range(ncol):
            if wellMat2[0,j,i]>0.0 and rivMat[j,i] == 0:
                wells.append([0,j,i,-wellMat2[0,j,i]])
    for k in range(1):
        wellDic[k]=copy.deepcopy(wells)
else:
    if testLevel<=2:
        wells = []
        for j in range(nrow):
            for i in range(ncol):
                if wellMat2[0,j,i]>0.0 and rivMat[j,i] == 0:
                    wells.append([0,j,i,-wellMat2[0,j,i]])
        for k in range(nPeriod):
            wellDic[k]=copy.deepcopy(wells)
    else:
        wellMat3 = wellMat
        for k in range(nPeriod):
            wells = []
            for j in range(nrow):
                for i in range(ncol):
                    if wellMat2[0,j,i]>0.0 and rivMat[j,i] == 0:
                        if np.isnan(wellMat3[k,0,j,i]):
                            wellMat3[k,0,j,i] = 0.0
                        wells.append([0,j,i,-wellMat3[k,0,j,i]])
            wellDic[k]=copy.deepcopy(wells)
well = flopy.modflow.ModflowWel(mf, stress_period_data=wellDic)





# #18. MODFLOW HOB package (time varying and constant observations for calibration targets)
# HaweaSites.csv (The locations of Hawea sites)
# GW_Level_Hawea.csv (Transient head data. This is the main target, Format: Time, Site1, Site2, Site3)
# The transient data starts on 25/07/2014 and ends on 21/02/2022. 
# We need to skip at least one year. 
# The modelling should start at 1/1/2013
# The observation should start on 25/07/2014
# Target.csv (Static target. As there is no date for the measurements,  
# we need to apply the same heads for the entire period. This is unrelasitc and, thus, use a smaller weight)
# iObsStart is the time step when the observation starts
iObsStart = (obsStartDate - dateBegin).days
# dfOldGW is old static groundwater levels.
dfOldGW = pd.read_csv('Target.csv', header=0, low_memory=False)
# tsd => [totim, hob]
# Observation should start from period 1 with a transient model
# tsd1 = [[1.,54.4], [2., 55.2]]
# tsd2 = [[1.,51.4], [2., 52.2]]
# hobList = [flopy.modflow.HeadObservation(mf, layer=0, row=5,column=5, time_series_data=tsd1),
#            flopy.modflow.HeadObservation(mf, layer=0, row=5,column=4, time_series_data=tsd2)]

hobList = []
for idx, row in dfOldGW.iterrows():
    tsd1 = []
    if bSteady:
        for k in range(1):
            tsd1.append([k,row.Target])
    else:
        for k in range(iObsStart, nPeriod):
            tsd1.append([k,row.Target])
    iCol2 = (row.X - Left)/delX
    iRow2 = (Top - row.Y)/delY
    iCol = int(iCol2)
    iRow = int(iRow2)
    roff = iRow2-iRow-0.5
    coff = iCol2-iCol-0.5
    if iRow<nrow and iCol<ncol:
        if ibound[0,iRow,iCol]>0 and wellMat2[0,iRow,iCol]==0.0 and rivMat[iRow,iCol]==0:
            hobList.append(flopy.modflow.HeadObservation(mf, obsname='OBST{0:03}'.format(idx), \
                layer=0, row=iRow, column=iCol, roff=roff, coff=coff, time_series_data=tsd1))

dfObs = pd.DataFrame(index=dtIndex)
dfSites = pd.read_csv('HaweaSites.csv', header=0, low_memory=False)
dfSites.index = dfSites.Site
dfGW_Level = pd.read_csv('GW_Level_Hawea.csv',parse_dates={'DateT':[0]}, dayfirst=True, 
            header=0, low_memory=False)
dfGW_Level = dfGW_Level.loc[(dfGW_Level.DateT>=dateBegin) & (dfGW_Level.DateT<=dateEnd)]
dfGW_Level.index = dfGW_Level.DateT
# dfGW_Level.reset_index(inplace=True)

for idx1, idx in enumerate(list(dfGW_Level.columns)[1:]):
    dfObs[idx]=dfGW_Level[idx]
    tsd1 = []
    if bSteady:
        for k in range(1):
            if not np.isnan(dfObs[idx][k]):
                tsd1.append([k,dfObs[idx][k]])
    else:
        for k in range(iObsStart, nPeriod):
            if not np.isnan(dfObs[idx][k]):
                tsd1.append([k,dfObs[idx][k]])
    iCol2 = (dfSites.loc[idx].Easting - Left)/delX
    iRow2 = (Top - dfSites.loc[idx].Northing)/delY
    iCol = int(iCol2)
    iRow = int(iRow2)
    roff = iRow2-iRow-0.5
    coff = iCol2-iCol-0.5
    if iRow<nrow and iCol<ncol:
        if ibound[0,iRow,iCol]>0 and wellMat2[0,iRow,iCol]==0.0 and rivMat[iRow,iCol]==0:
            hobList.append(flopy.modflow.HeadObservation(mf, obsname='OBTR{0:03}'.format(idx1), \
                layer=0, row=iRow, column=iCol, roff=roff, coff=coff, time_series_data=tsd1))
    
hob = flopy.modflow.ModflowHob(mf, obs_data=hobList)





# #19. Write MODFLOW files
# It takes 20 seconds for a short model (2018 to 2020)
# It takes 100 seconds for a full model (2013 to 2020)
start = time.time()
gpMfGrid.to_file(grid_file, driver="GPKG")
mf.write_input()
print(time.time()-start)
print(time.time()-start1)





# #20. Run the MODFLOW model
# #21. Calibrate the model
start = time.time()
success, buff = mf.run_model()
print(time.time()-start)

