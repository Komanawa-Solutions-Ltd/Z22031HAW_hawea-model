"""
created matt_dumont 
on: 8/09/22
"""
import pandas as pd
import numpy as np
from model_build.supporting_data_analysis.all_wells import get_all_wells
from project_base import base_model_build_data_dir, processed_model_build_data_dir
from model_build.project_model_tools import smt

flow_meter_data_path = base_model_build_data_dir.joinpath('water_permit_meter_results_2022-07-20',
                                                          'water_permit_meter_yearly_data_2022-07-20.csv')


def get_well_flowmeter_mapper(incl_surface_water=False, recalc=False):
    if incl_surface_water:
        processed_path = processed_model_build_data_dir.joinpath('flowmeter_loc_mapper_inc_sw.csv')
    else:
        processed_path = processed_model_build_data_dir.joinpath('flowmeter_loc_mapper.csv')

    if processed_path.exists() and not recalc:
        outdata = pd.read_csv(processed_path, index_col=0)
        outdata.loc[:, 'i'] = outdata.loc[:, 'i'].astype(int)
        outdata.loc[:, 'j'] = outdata.loc[:, 'j'].astype(int)
        outdata.loc[:, 'k'] = outdata.loc[:, 'k'].astype(int)
        return outdata

    consents_data_path = base_model_build_data_dir.joinpath('consent_database_from_Mike_kitterage.csv')
    consents = pd.read_csv(consents_data_path)

    flow_meter_data = pd.read_csv(flow_meter_data_path)
    if not incl_surface_water:
        flow_meter_data = flow_meter_data.loc[flow_meter_data.gw_allo > 0]
    unique_flow_data = flow_meter_data[['permit_id', 'water_meter_no']].value_counts()
    unique_flow_data = unique_flow_data.reset_index().drop(columns=0)
    unique_flow_consents = unique_flow_data.loc[:, 'permit_id'].unique()
    use_consents = consents.loc[np.in1d(consents.ConsentID, unique_flow_consents)]
    num_waps = unique_flow_data.groupby('permit_id').count()
    print(num_waps)
    print(num_waps.describe())
    print('num consents with more than 1 wap:', len(num_waps[num_waps.water_meter_no > 1]))

    all_wells = get_all_wells()
    all_well_consents = np.unique(all_wells.loc[:, 'takeconsent'].dropna())

    print('number of flow data consents in consents database:', np.in1d(unique_flow_consents, consents.ConsentID).sum(),
          f'of {len(unique_flow_consents)}')
    print('number of flow data consents missing in consents database:',
          (~np.in1d(unique_flow_consents, consents.ConsentID)).sum(), f'of {len(unique_flow_consents)}')

    print('number of flow data consents in wells database:', np.in1d(unique_flow_consents, all_well_consents).sum(),
          f'of {len(unique_flow_consents)}')
    print('number of flow data consents missing in wells database',
          (~np.in1d(unique_flow_consents, all_well_consents)).sum(), f'of {len(unique_flow_consents)}')

    use_consents.rename(columns={
        'B1_X_COORD': 'consent_b_x', 'B1_Y_COORD': 'consent_b_y', 'EastingTM': 'consent_x',
        'NorthingTM': 'consent_y'
    }, inplace=True)
    consent_transfer_keys = ['WellNumber', 'consent_b_x',
                             'consent_b_y', 'consent_x', 'consent_y']
    unique_well_consents = use_consents[['ConsentID'] + consent_transfer_keys].value_counts()
    unique_well_consents = unique_well_consents.reset_index().drop(columns=0)

    num_waps_from_consents = unique_well_consents.groupby('ConsentID').count()

    # based on this there are 9 individuaal causes where the number of flow meters does not = the number of wells,
    # two of these simply do not have well numbers associated with them.  This is a manageable set
    num_waps.loc[num_waps_from_consents.index, 'consent_count'] = num_waps_from_consents.WellNumber

    # the consents that have the same number of wells as flow meters, can directly map these
    matching_single_consents = num_waps.index[(num_waps.water_meter_no == num_waps.consent_count) &
                                              (num_waps.water_meter_no == 1)]
    matching_mult_consents = num_waps.index[(num_waps.water_meter_no == num_waps.consent_count) &
                                            (num_waps.water_meter_no > 1)]
    missmatch_consents = num_waps.index[
        (num_waps.water_meter_no != num_waps.consent_count) & num_waps.consent_count.notna()]

    missing_consents = num_waps.index[num_waps.consent_count.isna()]

    outdata = unique_flow_data.copy(deep=True)
    outdata = pd.merge(outdata,
                       unique_well_consents.loc[np.in1d(unique_well_consents.ConsentID, matching_single_consents)],
                       how='left', left_on='permit_id', right_on='ConsentID')
    outdata.drop(columns='ConsentID', inplace=True)

    for cid in missing_consents:
        outdata.loc[np.in1d(outdata.permit_id, [cid]), consent_transfer_keys] = use_consents.loc[
            np.in1d(use_consents.ConsentID, [cid]), consent_transfer_keys].values

    # matching_multi_consents
    for cid in matching_mult_consents:
        outdata.loc[np.in1d(outdata.permit_id, [cid]), consent_transfer_keys] = unique_well_consents.loc[
            np.in1d(unique_well_consents.ConsentID, [cid]), consent_transfer_keys].values

    # mismatch consents
    for cid in missmatch_consents:
        nwm, ncons = num_waps.loc[cid]
        if ncons == 1:
            outdata.loc[np.in1d(outdata.permit_id, [cid]),
                        consent_transfer_keys] = unique_well_consents.loc[
                np.in1d(unique_well_consents.ConsentID, [cid]), consent_transfer_keys].values
        else:
            # where there are multiple wells but they don't match to the number of consents
            # include multiple runs for all of the data in outdata
            temp = outdata.loc[np.in1d(outdata.permit_id, [cid])]
            outdata = outdata.loc[~np.in1d(outdata.permit_id, [cid])]
            temp_outdata = []
            for permit, meter in temp.loc[:, ['permit_id', 'water_meter_no']].itertuples(False, None):
                t = unique_well_consents.loc[np.in1d(unique_well_consents.ConsentID, [cid]), consent_transfer_keys]
                t.loc[:, 'permit_id'] = permit
                t.loc[:, 'water_meter_no'] = meter
                temp_outdata.append(t)
            temp_outdata = pd.concat(temp_outdata)
            outdata = pd.concat([outdata, temp_outdata])

    # check all flow meters and consents are included
    assert (set(unique_flow_data.itertuples(False, None))
            == set(outdata.loc[:, ['permit_id', 'water_meter_no']].itertuples(False, None)))

    # add well xy
    outdata.loc[:, 'well_name'] = outdata.loc[:, 'WellNumber'].str.replace('/', '_').str.lower()
    idx = outdata.well_name.notna()
    missing_wells = set(np.unique(outdata.well_name[idx])) - set(all_wells.index)
    idx = idx & ~np.in1d(outdata.well_name, list(missing_wells))
    outdata.loc[idx, 'well_x'] = all_wells.loc[outdata.well_name[idx], 'nztmx'].values
    outdata.loc[idx, 'well_y'] = all_wells.loc[outdata.well_name[idx], 'nztmy'].values

    # create usex usey
    for k in ['consent_b', 'consent', 'well']:
        idx = outdata.loc[:, f'{k}_x'].notna()
        outdata.loc[idx, 'use_x'] = outdata.loc[idx, f'{k}_x']
        outdata.loc[idx, 'use_y'] = outdata.loc[idx, f'{k}_y']
    assert outdata.use_x.notna().all() and outdata.use_y.notna().all()

    # add row, col... layer isn't going to happen.
    i, j = smt.convert_coords_to_matix(outdata.use_x, outdata.use_y)
    outdata.loc[:, 'i'] = i
    outdata.loc[:, 'j'] = j
    outdata.loc[:, 'k'] = 0

    ibound = smt.get_no_flow(0)
    outdata.loc[:, 'ibound'] = ibound[outdata.i, outdata.j]

    outdata = outdata.reset_index(drop=True)
    outdata.loc[:, 'name'] = [f'w_{e:03d}' for e in outdata.index]
    outdata.set_index('name', inplace=True)
    outdata.to_csv(processed_path)

    return outdata


if __name__ == '__main__':
    get_well_flowmeter_mapper(recalc=True)
