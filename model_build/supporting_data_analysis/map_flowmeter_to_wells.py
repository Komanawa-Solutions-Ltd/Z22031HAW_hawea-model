"""
created matt_dumont 
on: 8/09/22
"""
import pandas as pd

from model_build.supporting_data_analysis.all_wells import get_all_wells
from project_base import base_model_build_data_dir

use_data_path = base_model_build_data_dir.joinpath('water_permit_meter_results_2022-07-20',
                                                   'water_permit_meter_yearly_data_2022-07-20.csv')


# todo this should have all of the data in hawea.


def map_from_jens_data():
    data_path = base_model_build_data_dir.joinpath('Estimate of Current indiv gw take consents and meters.xlsx')
    jens_data = pd.read_excel(data_path, 'Amalgated take data')

    raise NotImplementedError


def map_from_wells_db():
    all_wells = get_all_wells()


def from_consents_database():
    consents_data_path = base_model_build_data_dir.joinpath('consent_database_from_Mike_kitterage.csv')
    # todo only if many consents are missing!!!, will need to get data from Jens
    raise NotImplementedError
