"""
created matt_dumont 
on: 2/23/26
"""
import pickle
from komanawa.hawea.hawea_base import proj_root
import numpy as np
import pandas as pd


def convert_pickle_historical():  # done
    # historical_investigation/generated_data/min_fit_lake_bore_butterfields_curve.p, skipping. Error: Expected data to be a dictionary, got <class 'tuple'>
    # historical_investigation/generated_data/min_fit_lake_bore_315_curve.p, skipping. Error: Expected data to be a dictionary, got <class 'tuple'>
    # historical_investigation/generated_data/min_fit_lake_bore_515_curve.p, skipping. Error: Expected data to be a dictionary, got <class 'tuple'>
    # targets_and_sensitive_sites/processed_data/min_fit_lake_g40_0415_curve_brute.p, skipping. Error: Expected data to be a dictionary, got <class 'tuple'>

    pickle_paths = [
        # 'min_fit_lake_bore_315_curve.p',
        # 'min_fit_lake_bore_515_curve.p',
        # 'min_fit_lake_bore_butterfields_curve.p',
    ]
    pickle_paths = [proj_root.joinpath('historical_investigation/generated_data', p) for p in pickle_paths]
    pickle_paths.append(
        proj_root.joinpath('targets_and_sensitive_sites/processed_data/min_fit_lake_g40_0415_curve_brute.p'))
    for p in pickle_paths:
        with p.open('rb') as f:
            data = pickle.load(f)
            assert isinstance(data, tuple)
            assert len(data) == 4
            save_data = {str(i): v for i, v in enumerate(data)}
            npz_path = p.with_suffix('.npz')
            np.savez_compressed(npz_path, **save_data)


def convert_dict_df_pickles():  # done
    paths = [
        'Scenarios/processed_input_data/hill_stress_period_data-hist_lows.p',
        'Scenarios/processed_input_data/hill_stress_period_data-scenario_period.p',
    ]
    paths = [proj_root.joinpath(p) for p in paths]
    for p in paths:
        with p.open('rb') as f:
            data = pickle.load(f)
            assert isinstance(data, dict)
            for k, v in data.items():
                assert isinstance(v, pd.DataFrame)
            savedata = []
            for k, v in data.items():
                v['per'] = k
                savedata.append(v)
            savedata = pd.concat(savedata)
            savedata.to_hdf(p.with_suffix('.hdf'), key='data', complib='zlib', complevel=4)


def convert_spd_pickles_pd1(): # done
    # required pandas 1.5.3
    paths = [
        'Scenarios/processed_input_data/race_stress_period_data-scenario_period.p',
        'Scenarios/processed_input_data/race_stress_period_data-hist_lows.p',
    ]
    paths = [proj_root.joinpath(p) for p in paths]
    for p in paths:
        with p.open('rb') as f:
            data = pickle.load(f)
            assert isinstance(data, dict)
            for k, v in data.items():
                assert isinstance(v, pd.DataFrame)
            savedata = []
            for k, v in data.items():
                v['per'] = k
                savedata.append(v)
            savedata = pd.concat(savedata)
            savedata.to_hdf(p.with_suffix('.hdf'), key='data', complib='zlib', complevel=4)

def convert_well_opt():
    with proj_root.joinpath('model_build/processed_input_data/well_stress_period_data-optimisation_period.p').open('rb') as f:
        data = pickle.load(f)
    keys = ('race_spd', 'hill_spd', 'pumping_spd')
    assert len(data) == 3
    for topkey, d in zip(keys, data):
        assert isinstance(d, dict)
        for k,v in d.items():
            assert isinstance(k, int)

    for topkey, d in zip(keys, data):
        save_data = []
        for k, v in d.items():
            if not isinstance(v, pd.DataFrame):
                v = pd.DataFrame(v)
            v['per'] = k
            save_data.append(v)
        save_data = pd.concat(save_data)
        save_path = proj_root.joinpath(f'model_build/processed_input_data/well_stress_period_data_{topkey}-optimisation_period.hdf')
        save_data.to_hdf(save_path, key='data', complib='zlib', complevel=4)


if __name__ == '__main__':
    # convert_pickle_historical()
    # convert_dict_df_pickles()
    # convert_spd_pickles_pd1()
    convert_well_opt()
    pass
