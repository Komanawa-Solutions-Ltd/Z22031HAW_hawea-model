"""
created matt_dumont 
on: 8/09/22
"""
import pandas as pd
import numpy as np
from model_build.supporting_data_analysis.all_wells import get_all_wells
from project_base import base_model_build_data_dir

flow_meter_data_path = base_model_build_data_dir.joinpath('water_permit_meter_results_2022-07-20',
                                                   'water_permit_meter_yearly_data_2022-07-20.csv')


# todo this should have all of the data in hawea.


def map_from_jens_data():
    # todo see how much data is missing, which consents missing (from flow meter data)
    # todo compare both consents and well meter ids
    # separately?
    # in Jens, consent number - ConsentNumber, well meter = ?
    # in Mike K's consent number - permit_id, well meter = water_meter_no

    data_path = base_model_build_data_dir.joinpath('Estimate of Current indiv gw take consents and meters.xlsx')
    jens_data = pd.read_excel(data_path, 'Amalgated take data')
    flow_meter_data = pd.read_csv(flow_meter_data_path)

    # sorting Mike's data so that only the unique RC and flow meter combos are left
    unique_flow_data = flow_meter_data[['permit_id', 'water_meter_no']].value_counts()
    # a series. Could turn this into a df and just subset the first two columns

    df1 = pd.DataFrame(unique_flow_data).reset_index()
    # this is a dataframe containing only the unique permit_id and water_meter_no pairs
    # from Mike K's data. 120 of them
    unique_flow_data_df = df1[['permit_id', 'water_meter_no']]

    # finding the common numbers using np.in1d
    # doing on the two columns
    # consent number
    common_consent_numbers = np.in1d(unique_flow_data_df['permit_id'], jens_data['ConsentNumber'])
    # flow_meter_no
    # first adjusting Jens' data
    jens_data['WM#1'] = jens_data["WM#1"].str.replace('WM', '')
    # checking Jens' against Mike's to see which are missing
    common_flow_meters_ = np.in1d(unique_flow_data_df['water_meter_no'], jens_data['WM#1'])

    # todo provide overviews
    # todo how many missing present
    # todo lists of missing and present


    #jens_data['permit_id'] = jens_data['ConsentNumber']
    #print(flow_meter_data)
    # finding the common consent conditions between both data sets
    #common = flow_meter_data.merge(jens_data, on='permit_id')
    #print(common)



    raise NotImplementedError


def map_from_wells_db():
    all_wells = get_all_wells()

    #todo take the flow meter data (RCs in this data)
    # todo see what wells are associated with what RC
    # todo how many RCs are missing well etc


def from_consents_database():
    consents_data_path = base_model_build_data_dir.joinpath('consent_database_from_Mike_kitterage.csv')
    # todo only if many consents are missing!!!, will need to get data from Jens
    raise NotImplementedError

if __name__ == '__main__':
    map_from_jens_data()