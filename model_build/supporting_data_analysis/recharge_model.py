"""
created matt_dumont 
on: 2/08/22
"""
import geopandas as gpd
# todo use https://github.com/mullenkamp/lsrm-archive
# todo that LSR model is really set up for Ecan's context..., perhaps program in rushton...
import numpy as np
import pandas as pd
from project_base import base_model_data_dir, processed_model_data_dir, modelling_dir
from model_build.project_model_tools import smt

irrigated_area_dir = base_model_data_dir.joinpath('irrigated_area')
irrigated_area_dir.mkdir(exist_ok=True)

irrigated_area_codes = {
    0: 'Gun', 1: 'Borderdyke', 2: 'Pivot', 3: 'Solid-set', 4: 'K-line/Long lateral',
    5: 'Unknown', 6: 'Drip/micro', 7: 'Rotorainer', 8: 'Wild flooding', 9: 'Linear boom'}

irrigation_effciency = {}  # todo!!


def get_met_data(start_date, end_date, frequency='D'):
    data = pd.read_csv(base_model_data_dir.joinpath('Rainfall_Hawea.csv'))
    data.loc[:, 'datetime'] = dt = pd.to_datetime(data.loc[:, 'Date'], format='%d/%m/%Y')
    data.drop(columns='Date', inplace=True)
    data.set_index('datetime', inplace=True)

    if start_date is None:
        start_date = dt.min()
    if end_date is None:
        end_date = dt.max()

    idx = ((dt >= start_date) & (dt <= end_date)).values
    use_data = data.loc[idx].resample(frequency).sum()
    return use_data


def _process_irrigated_area():
    # Keynote irrigated area is additive (e.g. no/minial overlap)
    data = gpd.read_file(modelling_dir.joinpath('input_data/otago_irrigated_area_26oct2021_model_extent.shp'))
    data.loc[:, 'itype_code'] = data.loc[:, 'type'].replace({v: k for k, v in irrigated_area_codes.items()})
    data.to_file(irrigated_area_dir.joinpath(f'otago_irrigated_area_26oct2021_model_extent.shp'))
    for y in data.loc[:, 'year_irr'].unique():
        temp = data.loc[data.year_irr == y]
        temp.to_file(irrigated_area_dir.joinpath(f'ia_{y}.shp'))


def data_checks():
    import matplotlib.pyplot as plt
    # plot met data
    fig, (ax1, ax2) = plt.subplots(2, sharex=True)
    data = get_met_data(None, None, 'M')
    ax1.plot(data.index, data.Rainfall)
    ax1.set_title('Rainfall')
    ax2.plot(data.index, data.PET)
    ax2.set_title('PET')
    # make annual maps of irrigated area...
    files = list(irrigated_area_dir.glob('*.shp'))
    for f in files:
        temp = smt.io.shape_file_to_model_array(f, 'itype_code', alltouched=True)
        smt.plot.plt_matrix(temp, base_map=True, title=f.name)

    # plot soil paw
    soil_paw = get_soil_paw(fix_nan=False)
    smt.plot.plt_matrix(soil_paw, title='PAW', base_map=True)
    print('number of soil PAWs', len(np.unique(soil_paw)))
    print('soil paws', np.unique(soil_paw))
    ibound = smt.get_no_flow(0)
    print('number of nan soils', np.isnan(soil_paw[ibound >= 1]).sum())
    smt.plot.plt_matrix(np.isnan(soil_paw), title='PAW is nan', base_map=True)

    smt.plot.plt_matrix(soil_paw == 0, title='soil paw 0', base_map=True)

    smt.plot.show()

    # todo more....


def get_soil_paw(fix_nan=True):
    soil_paw = smt.io.shape_file_to_model_array(base_model_data_dir.joinpath('soils_with_paw.shp'),
                                                'PAW', alltouched=True)
    if fix_nan:
        soil_paw[np.isnan(soil_paw)] = np.nanmin(soil_paw)

    # todo the soil PAW has null values that are being burned as 0...
    # todo I may need ather soil data...
    return soil_paw

def get_irrigation_status(): # todo
    raise NotImplementedError
def make_rch():
    raise NotImplementedError


if __name__ == '__main__':
    data_checks()
